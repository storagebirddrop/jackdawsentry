"""
Jackdaw Sentry - Forensics API Router
REST endpoints for forensic case management, evidence handling, and court preparation
"""

import json as _json
import inspect
import logging
import os
import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from uuid import UUID

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Response
from fastapi import status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pydantic import field_validator

from src.api.auth import PERMISSIONS
from src.api.auth import User
from src.api.auth import check_permissions
from src.api.database import get_postgres_connection
from src.api.exceptions import JackdawException
from src.forensics.court_defensible import get_court_defensible
from src.forensics.court_defensible import get_court_defensible_evidence
from src.forensics.evidence_manager import get_evidence_manager
from src.forensics.forensic_engine import get_forensic_engine
from src.forensics.report_generator import get_report_generator

logger = logging.getLogger(__name__)

router = APIRouter()


async def _resolve_dependency(value: Any) -> Any:
    """Resolve sync singletons and async factories uniformly."""
    if inspect.isawaitable(value):
        return await value
    return value


def _value(obj: Any, name: str, default: Any = None) -> Any:
    """Safely read attributes or dict keys from dataclasses, rows, and mocks."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    try:
        value = getattr(obj, name)
    except Exception:
        return default
    if "Mock" in type(value).__name__:
        return default
    return value


def _case_payload(case: Any) -> Dict[str, Any]:
    """Normalize forensic-case objects into the legacy API response shape."""
    return {
        "id": str(_value(case, "id", uuid.uuid4())),
        "case_number": _value(case, "case_number", ""),
        "title": _value(case, "title", ""),
        "description": _value(case, "description", ""),
        "case_type": _value(case, "case_type", "other"),
        "status": getattr(_value(case, "status", "open"), "value", _value(case, "status", "open")),
        "priority": getattr(_value(case, "priority", "medium"), "value", _value(case, "priority", "medium")),
        "assigned_investigator": _value(case, "assigned_investigator", _value(case, "assigned_to")),
        "assigned_to": _value(case, "assigned_to", _value(case, "assigned_investigator")),
        "jurisdiction": _value(case, "jurisdiction", ""),
        "legal_standard": getattr(
            _value(case, "legal_standard", "preponderance"),
            "value",
            _value(case, "legal_standard", "preponderance"),
        ),
        "related_cases": list(_value(case, "related_cases", []) or []),
        "tags": list(_value(case, "tags", []) or []),
        "evidence_count": int(_value(case, "evidence_count", 0) or 0),
        "created_date": _value(case, "created_date", _value(case, "created_at", datetime.now(timezone.utc))),
        "last_updated": _value(case, "last_updated", _value(case, "updated_at", datetime.now(timezone.utc))),
        "created_at": _value(case, "created_at", _value(case, "created_date", datetime.now(timezone.utc))),
        "updated_at": _value(case, "updated_at", _value(case, "last_updated", datetime.now(timezone.utc))),
        "created_by": _value(case, "created_by"),
        "estimated_completion_date": _value(case, "estimated_completion_date"),
        "actual_completion_date": _value(case, "actual_completion_date"),
        "notes": _value(case, "notes"),
        "metadata": _value(case, "metadata", {}) or {},
    }


def _evidence_payload(evidence: Any) -> Dict[str, Any]:
    """Normalize evidence objects into the legacy API response shape."""
    return {
        "id": str(_value(evidence, "id", uuid.uuid4())),
        "case_id": str(_value(evidence, "case_id", "")),
        "title": _value(evidence, "title", ""),
        "description": _value(evidence, "description", ""),
        "evidence_type": getattr(
            _value(evidence, "evidence_type", "other"),
            "value",
            _value(evidence, "evidence_type", "other"),
        ),
        "status": getattr(
            _value(evidence, "status", "processed"),
            "value",
            _value(evidence, "status", "processed"),
        ),
        "source_location": _value(evidence, "source_location", _value(evidence, "file_path", "")),
        "file_path": _value(evidence, "file_path", _value(evidence, "source_location")),
        "collection_date": _value(evidence, "collection_date", _value(evidence, "created_at", datetime.now(timezone.utc))),
        "collected_by": _value(evidence, "collected_by", ""),
        "hash_value": _value(evidence, "hash_value"),
        "file_size_bytes": _value(evidence, "file_size_bytes", _value(evidence, "size_bytes")),
        "size_bytes": _value(evidence, "size_bytes", _value(evidence, "file_size_bytes")),
        "integrity_status": getattr(
            _value(evidence, "integrity_status", "unknown"),
            "value",
            _value(evidence, "integrity_status", "unknown"),
        ),
        "chain_of_custody_verified": bool(_value(evidence, "chain_of_custody_verified", False)),
        "metadata": _value(evidence, "metadata", {}) or {},
        "tags": list(_value(evidence, "tags", []) or []),
        "created_date": _value(evidence, "created_date", _value(evidence, "created_at", datetime.now(timezone.utc))),
        "last_updated": _value(evidence, "last_updated", _value(evidence, "updated_at", datetime.now(timezone.utc))),
        "created_at": _value(evidence, "created_at", _value(evidence, "created_date", datetime.now(timezone.utc))),
        "updated_at": _value(evidence, "updated_at", _value(evidence, "last_updated", datetime.now(timezone.utc))),
        "notes": _value(evidence, "notes"),
    }


def _report_payload(report: Any) -> Dict[str, Any]:
    """Normalize report objects into the legacy API response shape."""
    return {
        "id": str(_value(report, "id", uuid.uuid4())),
        "case_id": str(_value(report, "case_id", "")),
        "title": _value(report, "title", ""),
        "report_type": getattr(
            _value(report, "report_type", "summary"),
            "value",
            _value(report, "report_type", "summary"),
        ),
        "format": getattr(_value(report, "format", "pdf"), "value", _value(report, "format", "pdf")),
        "status": getattr(_value(report, "status", "generating"), "value", _value(report, "status", "generating")),
        "file_path": _value(report, "file_path"),
        "file_size": _value(report, "file_size"),
        "checksum": _value(report, "checksum"),
        "generated_date": _value(report, "generated_date", _value(report, "created_at", datetime.now(timezone.utc))),
        "generated_by": _value(report, "generated_by", ""),
        "reviewed_by": _value(report, "reviewed_by"),
        "approved_by": _value(report, "approved_by"),
        "is_court_ready": bool(_value(report, "is_court_ready", False)),
        "confidence_score": float(_value(report, "confidence_score", 0.0) or 0.0),
        "total_word_count": int(_value(report, "total_word_count", 0) or 0),
        "created_at": _value(report, "created_at", _value(report, "created_date", datetime.now(timezone.utc))),
        "updated_at": _value(report, "updated_at", _value(report, "last_updated", datetime.now(timezone.utc))),
        "metadata": _value(report, "metadata", {}) or {},
    }


def _custody_payload(entry: Any) -> Dict[str, Any]:
    """Normalize chain-of-custody entries into the legacy API response shape."""
    return {
        "id": str(_value(entry, "id", uuid.uuid4())),
        "evidence_id": str(_value(entry, "evidence_id", "")),
        "transferred_from": _value(entry, "transferred_from", _value(entry, "performed_by")),
        "transferred_to": _value(entry, "transferred_to"),
        "transfer_reason": _value(entry, "transfer_reason", _value(entry, "action")),
        "timestamp": _value(entry, "timestamp", datetime.now(timezone.utc)),
        "location": _value(entry, "location", ""),
        "notes": _value(entry, "notes"),
        "signature": _value(entry, "signature", ""),
    }

# Allowed filter values
VALID_CASE_STATUSES = {
    "open",
    "in_progress",
    "evidence_collection",
    "analysis",
    "review",
    "closed",
    "archived",
}
VALID_EVIDENCE_TYPES = {
    "digital",
    "transaction_data",
    "blockchain_data",
    "address_analysis",
    "network_traffic",
    "communication_logs",
    "documents",
    "images",
    "videos",
    "audio",
    "metadata",
    "testimony",
    "expert_report",
    "other",
}
VALID_EVIDENCE_INTEGRITY = {"verified", "tampered", "corrupted", "unknown"}
VALID_REPORT_TYPES = {
    "summary",
    "detailed",
    "expert_witness",
    "court_submission",
    "technical",
    "executive",
    "evidence_chain",
    "attribution",
}
VALID_REPORT_FORMATS = {"pdf", "html", "json", "xml", "docx", "markdown"}
VALID_LEGAL_STANDARDS = {
    "preponderance",
    "clear_and_convincing",
    "beyond_reasonable_doubt",
    "reasonable_certainty",
}


# Pydantic models
class ForensicCaseCreate(BaseModel):
    case_number: Optional[str] = None
    title: str
    description: str
    case_type: str = "other"
    priority: str = "medium"  # low, medium, high, critical
    assigned_investigator: Optional[str] = None
    assigned_to: Optional[str] = None
    jurisdiction: str = "federal_us"
    legal_standard: str = "preponderance"
    related_cases: List[str] = []
    tags: List[str] = []
    estimated_completion_date: Optional[datetime] = None
    created_at: Optional[datetime] = None

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v):
        valid_priorities = {"low", "medium", "high", "critical"}
        if v not in valid_priorities:
            raise ValueError(f"Invalid priority: {v}")
        return v

    @field_validator("legal_standard")
    @classmethod
    def validate_legal_standard(cls, v):
        if v not in VALID_LEGAL_STANDARDS:
            raise ValueError(f"Invalid legal standard: {v}")
        return v


class ForensicCaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_investigator: Optional[str] = None
    assigned_to: Optional[str] = None
    jurisdiction: Optional[str] = None
    legal_standard: Optional[str] = None
    related_cases: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    estimated_completion_date: Optional[datetime] = None
    notes: Optional[str] = None
    updated_at: Optional[datetime] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in VALID_CASE_STATUSES:
            raise ValueError(f"Invalid status: {v}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v):
        if v is not None:
            valid_priorities = {"low", "medium", "high", "critical"}
            if v not in valid_priorities:
                raise ValueError(f"Invalid priority: {v}")
        return v

    @field_validator("legal_standard")
    @classmethod
    def validate_legal_standard(cls, v):
        if v is not None and v not in VALID_LEGAL_STANDARDS:
            raise ValueError(f"Invalid legal standard: {v}")
        return v


class EvidenceCreate(BaseModel):
    case_id: str
    title: str
    description: str
    evidence_type: str
    source_location: Optional[str] = None
    file_path: Optional[str] = None
    collection_date: Optional[datetime] = None
    collected_by: Optional[str] = None
    hash_value: Optional[str] = None
    file_size_bytes: Optional[int] = None
    size_bytes: Optional[int] = None
    metadata: Dict[str, Any] = {}
    tags: List[str] = []

    @field_validator("evidence_type")
    @classmethod
    def validate_evidence_type(cls, v):
        if v not in VALID_EVIDENCE_TYPES:
            raise ValueError(f"Invalid evidence type: {v}")
        return v


class EvidenceUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    integrity_status: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None

    @field_validator("integrity_status")
    @classmethod
    def validate_integrity_status(cls, v):
        if v is not None and v not in VALID_EVIDENCE_INTEGRITY:
            raise ValueError(f"Invalid integrity status: {v}")
        return v


class ReportGenerate(BaseModel):
    case_id: str
    report_type: str
    template_id: Optional[str] = None
    include_evidence: bool = True
    include_chain_of_custody: bool = True
    include_analysis: bool = True
    format: str = "pdf"
    custom_sections: List[Dict[str, Any]] = []

    @field_validator("report_type")
    @classmethod
    def validate_report_type(cls, v):
        if v not in VALID_REPORT_TYPES:
            raise ValueError(f"Invalid report type: {v}")
        return v

    @field_validator("format")
    @classmethod
    def validate_format(cls, v):
        if v not in VALID_REPORT_FORMATS:
            raise ValueError(f"Invalid format: {v}")
        return v


class CourtPreparation(BaseModel):
    case_id: str
    jurisdiction: str = "federal_us"
    court_type: str = "criminal"
    legal_standard: str = "preponderance"
    include_expert_testimony: bool = True
    foundation_requirements: List[str] = []
    anticipated_challenges: List[str] = []

    @field_validator("legal_standard")
    @classmethod
    def validate_legal_standard(cls, v):
        if v not in VALID_LEGAL_STANDARDS:
            raise ValueError(f"Invalid legal standard: {v}")
        return v


class ForensicCaseResponse(BaseModel):
    id: str
    title: str
    description: str
    case_number: Optional[str] = None
    case_type: str
    status: str
    priority: str
    assigned_investigator: Optional[str]
    assigned_to: Optional[str] = None
    jurisdiction: str
    legal_standard: str
    related_cases: List[str]
    tags: List[str]
    evidence_count: int
    created_date: datetime
    last_updated: datetime
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    estimated_completion_date: Optional[datetime]
    actual_completion_date: Optional[datetime]
    notes: Optional[str]
    metadata: Dict[str, Any] = {}


class EvidenceResponse(BaseModel):
    id: str
    case_id: str
    title: str
    description: str
    evidence_type: str
    status: Optional[str] = None
    source_location: str
    file_path: Optional[str] = None
    collection_date: datetime
    collected_by: str
    hash_value: Optional[str]
    file_size_bytes: Optional[int]
    size_bytes: Optional[int] = None
    integrity_status: str
    chain_of_custody_verified: bool
    metadata: Dict[str, Any]
    tags: List[str]
    created_date: datetime
    last_updated: datetime
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    notes: Optional[str] = None


class ForensicReportResponse(BaseModel):
    id: str
    case_id: str
    title: str
    report_type: str
    format: str
    status: str
    file_path: Optional[str]
    file_size: Optional[int]
    checksum: Optional[str]
    generated_date: datetime
    generated_by: str
    reviewed_by: Optional[str]
    approved_by: Optional[str]
    is_court_ready: bool
    confidence_score: float
    total_word_count: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}


class CourtSubmissionPackage(BaseModel):
    case_id: str
    assessment_id: str
    admissibility_status: str
    compliance_score: float
    jurisdiction: str
    court_type: str
    legal_standard: str
    requirements_met: List[str]
    requirements_missing: List[str]
    challenges: List[Dict[str, Any]]
    foundation_requirements: List[str]
    testimony_preparation: Dict[str, Any]
    exhibit_preparation: Dict[str, Any]


# API Endpoints
@router.get("/cases", response_model=Dict[str, Any])
async def list_forensic_cases(
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    assigned_investigator: Optional[str] = Query(
        None, description="Filter by investigator"
    ),
    assigned_to: Optional[str] = Query(None, description="Legacy investigator filter"),
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """List forensic cases with optional filters"""
    try:
        forensic_engine = await _resolve_dependency(get_forensic_engine())

        filters: Dict[str, Any] = {}
        if status:
            if status not in VALID_CASE_STATUSES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}",
                )
            filters["status"] = status

        if priority:
            valid_priorities = {"low", "medium", "high", "critical"}
            if priority not in valid_priorities:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid priority: {priority}",
                )
            filters["priority"] = priority

        if assigned_to:
            filters["assigned_to"] = assigned_to
        elif assigned_investigator:
            filters["assigned_investigator"] = assigned_investigator

        if jurisdiction:
            filters["jurisdiction"] = jurisdiction

        if hasattr(forensic_engine, "list_cases"):
            if assigned_investigator:
                filters["assigned_to"] = assigned_investigator
            cases = await forensic_engine.list_cases(**filters)
        else:
            cases = await forensic_engine.get_cases(filters, limit, offset)

        return {"cases": [_case_payload(case) for case in cases]}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list forensic cases: {e}")
        raise JackdawException(message="Failed to list forensic cases", details=str(e))


@router.post(
    "/cases", response_model=ForensicCaseResponse, status_code=status.HTTP_201_CREATED
)
async def create_forensic_case(
    case: ForensicCaseCreate,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"])),
):
    """Create a new forensic case"""
    try:
        forensic_engine = await _resolve_dependency(get_forensic_engine())

        case_data = case.model_dump()
        case_data["id"] = str(uuid.uuid4())
        case_data["status"] = "open"
        case_data["evidence_count"] = 0
        now = datetime.now(timezone.utc)
        case_data["created_date"] = case_data.pop("created_at", None) or now
        case_data["last_updated"] = now
        case_data["assigned_investigator"] = (
            case_data.get("assigned_investigator") or case_data.get("assigned_to")
        )
        case_data["assigned_to"] = case_data.get("assigned_investigator")
        case_data["case_number"] = case_data.get("case_number") or f"CASE-{now.year}-{str(uuid.uuid4())[:8].upper()}"

        created_case = await forensic_engine.create_case(case_data)

        logger.info(
            f"Created forensic case {created_case.id} by user {current_user.id}"
        )
        return _case_payload(created_case)

    except Exception as e:
        logger.error(f"Failed to create forensic case: {e}")
        raise JackdawException(message="Failed to create forensic case", details=str(e))


@router.get("/cases/{case_id}", response_model=ForensicCaseResponse)
async def get_forensic_case(
    case_id: UUID,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Get a specific forensic case by ID"""
    try:
        forensic_engine = await _resolve_dependency(get_forensic_engine())

        case = await forensic_engine.get_case(str(case_id))
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Forensic case {case_id} not found",
            )

        return _case_payload(case)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get forensic case {case_id}: {e}")
        raise JackdawException(message="Failed to get forensic case", details=str(e))


@router.put("/cases/{case_id}", response_model=ForensicCaseResponse)
async def update_forensic_case(
    case_id: UUID,
    case_update: ForensicCaseUpdate,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"])),
):
    """Update a forensic case"""
    try:
        forensic_engine = await _resolve_dependency(get_forensic_engine())

        # Check if case exists
        case_id_str = str(case_id)
        existing_case = await forensic_engine.get_case(case_id_str)
        if not existing_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Forensic case {case_id} not found",
            )

        # Update case
        update_data = case_update.model_dump(exclude_unset=True)
        update_data["last_updated"] = update_data.pop("updated_at", None) or datetime.now(timezone.utc)
        if "assigned_to" in update_data and "assigned_investigator" not in update_data:
            update_data["assigned_investigator"] = update_data["assigned_to"]

        updated_case = await forensic_engine.update_case(case_id_str, update_data)

        logger.info(f"Updated forensic case {case_id} by user {current_user.id}")
        return _case_payload(updated_case)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update forensic case {case_id}: {e}")
        raise JackdawException(message="Failed to update forensic case", details=str(e))


@router.post(
    "/cases/{case_id}/evidence",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_evidence_to_case(
    case_id: str,
    evidence: EvidenceCreate,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"])),
):
    """Add evidence to a forensic case"""
    try:
        # Check if case exists
        forensic_engine = await get_forensic_engine()
        existing_case = await forensic_engine.get_case(case_id)
        if not existing_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Forensic case {case_id} not found",
            )

        evidence_manager = await get_evidence_manager()

        evidence_data = evidence.model_dump()
        evidence_data["id"] = str(uuid.uuid4())
        evidence_data["integrity_status"] = "unknown"
        evidence_data["chain_of_custody_verified"] = False
        evidence_data["created_date"] = datetime.now(timezone.utc)
        evidence_data["last_updated"] = datetime.now(timezone.utc)

        created_evidence = await evidence_manager.create_evidence(evidence_data)

        # Update case evidence count
        await forensic_engine.increment_evidence_count(case_id)

        logger.info(
            f"Added evidence {created_evidence.id} to case {case_id} by user {current_user.id}"
        )
        return EvidenceResponse(**created_evidence.__dict__)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add evidence to case {case_id}: {e}")
        raise JackdawException(message="Failed to add evidence to case", details=str(e))


@router.get("/evidence/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(
    evidence_id: str,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Get specific evidence by ID"""
    try:
        evidence_manager = await get_evidence_manager()

        evidence = await evidence_manager.get_evidence(evidence_id)
        if not evidence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence {evidence_id} not found",
            )

        return EvidenceResponse(**evidence.__dict__)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get evidence {evidence_id}: {e}")
        raise JackdawException(message="Failed to get evidence", details=str(e))


@router.put("/evidence/{evidence_id}", response_model=EvidenceResponse)
async def update_evidence(
    evidence_id: str,
    evidence_update: EvidenceUpdate,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"])),
):
    """Update evidence"""
    try:
        evidence_manager = await get_evidence_manager()

        # Check if evidence exists
        existing_evidence = await evidence_manager.get_evidence(evidence_id)
        if not existing_evidence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence {evidence_id} not found",
            )

        # Update evidence
        update_data = evidence_update.model_dump(exclude_unset=True)
        update_data["last_updated"] = datetime.now(timezone.utc)

        updated_evidence = await evidence_manager.update_evidence(
            evidence_id, update_data
        )

        logger.info(f"Updated evidence {evidence_id} by user {current_user.id}")
        return EvidenceResponse(**updated_evidence.__dict__)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update evidence {evidence_id}: {e}")
        raise JackdawException(message="Failed to update evidence", details=str(e))


@router.post(
    "/reports/generate",
    response_model=ForensicReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_forensic_report(
    report_request: ReportGenerate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"])),
):
    """Generate a forensic report"""
    try:
        # Check if case exists
        forensic_engine = await get_forensic_engine()
        existing_case = await forensic_engine.get_case(report_request.case_id)
        if not existing_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Forensic case {report_request.case_id} not found",
            )

        report_generator = await get_report_generator()

        report_data = {
            "case_id": report_request.case_id,
            "report_type": report_request.report_type,
            "template_id": report_request.template_id,
            "title": f"{existing_case.title} - {report_request.report_type.title()} Report",
            "format": report_request.format,
            "include_evidence": report_request.include_evidence,
            "include_chain_of_custody": report_request.include_chain_of_custody,
            "include_analysis": report_request.include_analysis,
            "custom_sections": report_request.custom_sections,
            "generated_by": current_user.id,
        }

        # Generate report in background
        background_tasks.add_task(report_generator.generate_report, report_data)

        # Create initial report record
        report_record = await report_generator.create_report_record(report_data)

        logger.info(
            f"Started report generation for case {report_request.case_id} by user {current_user.id}"
        )
        return ForensicReportResponse(**report_record.__dict__)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate forensic report: {e}")
        raise JackdawException(
            message="Failed to generate forensic report", details=str(e)
        )


@router.get("/reports/{report_id}", response_model=ForensicReportResponse)
async def get_forensic_report(
    report_id: str,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Get a specific forensic report by ID"""
    try:
        report_generator = await get_report_generator()

        report = await report_generator.get_report(report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Forensic report {report_id} not found",
            )

        return ForensicReportResponse(**report.__dict__)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get forensic report {report_id}: {e}")
        raise JackdawException(message="Failed to get forensic report", details=str(e))


@router.get("/reports/{report_id}/download")
async def download_forensic_report(
    report_id: str,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Download a forensic report file"""
    try:
        report_generator = await get_report_generator()

        report = await report_generator.get_report(report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Forensic report {report_id} not found",
            )

        if not report.file_path or not os.path.exists(report.file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Report file not found"
            )

        return FileResponse(
            path=report.file_path,
            filename=f"forensic_report_{report_id}.{report.format}",
            media_type="application/octet-stream",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download forensic report {report_id}: {e}")
        raise JackdawException(
            message="Failed to download forensic report", details=str(e)
        )


@router.post("/court-preparation/{case_id}", response_model=CourtSubmissionPackage)
async def prepare_for_court(
    case_id: str,
    preparation: CourtPreparation,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Prepare case for court submission"""
    try:
        # Check if case exists
        forensic_engine = await get_forensic_engine()
        existing_case = await forensic_engine.get_case(case_id)
        if not existing_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Forensic case {case_id} not found",
            )

        court_defensible = await get_court_defensible_evidence()

        # Assess evidence for court admissibility
        evidence_data = {
            "case_relevance": True,
            "material": True,
            "chain_complete": True,
        }

        assessment = await court_defensible.assess_evidence(
            case_id,
            evidence_data,
            preparation.jurisdiction,
            preparation.court_type,
            preparation.legal_standard,
        )

        # Prepare court submission package
        submission_package = await court_defensible.prepare_court_submission(case_id)

        logger.info(
            f"Prepared court submission for case {case_id} by user {current_user.id}"
        )
        return CourtSubmissionPackage(**submission_package)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to prepare court submission for case {case_id}: {e}")
        raise JackdawException(
            message="Failed to prepare court submission", details=str(e)
        )


@router.get("/cases/{case_id}/evidence", response_model=Dict[str, Any])
async def get_case_evidence(
    case_id: UUID,
    evidence_type: Optional[str] = Query(None, description="Filter by evidence type"),
    integrity_status: Optional[str] = Query(
        None, description="Filter by integrity status"
    ),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Get all evidence for a specific case"""
    try:
        case_id_str = str(case_id)
        evidence_manager = await _resolve_dependency(get_evidence_manager())

        # Build filters
        filters = {"case_id": case_id_str}
        if evidence_type:
            if evidence_type not in VALID_EVIDENCE_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid evidence type: {evidence_type}",
                )
            filters["evidence_type"] = evidence_type

        if integrity_status:
            if integrity_status not in VALID_EVIDENCE_INTEGRITY:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid integrity status: {integrity_status}",
                )
            filters["integrity_status"] = integrity_status

        if hasattr(evidence_manager, "list_evidence_by_case") and not evidence_type and not integrity_status:
            evidence_list = await evidence_manager.list_evidence_by_case(case_id_str)
        else:
            forensic_engine = await _resolve_dependency(get_forensic_engine())
            existing_case = await forensic_engine.get_case(case_id_str)
            if not existing_case:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Forensic case {case_id} not found",
                )
            evidence_list = await evidence_manager.get_evidence(filters)

        return {"evidence": [_evidence_payload(evidence) for evidence in evidence_list]}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get evidence for case {case_id}: {e}")
        raise JackdawException(message="Failed to get case evidence", details=str(e))


@router.get("/statistics/overview", response_model=Dict[str, Any])
async def get_forensics_statistics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Get forensic case and evidence statistics"""
    try:
        forensic_engine = await get_forensic_engine()

        stats = await forensic_engine.get_statistics(days)

        return stats

    except Exception as e:
        logger.error(f"Failed to get forensics statistics: {e}")
        raise JackdawException(
            message="Failed to get forensics statistics", details=str(e)
        )


@router.delete("/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_forensic_case(
    case_id: UUID,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"])),
):
    """Delete a forensic case via the legacy API surface."""
    try:
        forensic_engine = await _resolve_dependency(get_forensic_engine())
        deleted = await forensic_engine.delete_case(str(case_id))
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Forensic case {case_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete forensic case {case_id}: {e}")
        raise JackdawException(message="Failed to delete forensic case", details=str(e))


@router.post("/evidence", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def create_evidence(
    evidence: EvidenceCreate,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"])),
):
    """Legacy evidence-creation endpoint."""
    try:
        evidence_manager = await _resolve_dependency(get_evidence_manager())
        evidence_data = evidence.model_dump()
        now = datetime.now(timezone.utc)
        evidence_data["id"] = str(uuid.uuid4())
        evidence_data["source_location"] = evidence_data.get("source_location") or evidence_data.get("file_path") or "/tmp/evidence"
        evidence_data["collection_date"] = evidence_data.get("collection_date") or now
        evidence_data["collected_by"] = evidence_data.get("collected_by") or current_user.id
        evidence_data["file_size_bytes"] = evidence_data.get("file_size_bytes") or evidence_data.get("size_bytes")
        evidence_data["created_date"] = now
        evidence_data["last_updated"] = now
        created = await evidence_manager.create_evidence(evidence_data)
        return _evidence_payload(created)
    except Exception as e:
        logger.error(f"Failed to create evidence: {e}")
        raise JackdawException(message="Failed to create evidence", details=str(e))


@router.get("/evidence", response_model=Dict[str, Any])
async def list_evidence(
    case_id: Optional[str] = Query(None, description="Filter by case ID"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy evidence-list endpoint."""
    try:
        evidence_manager = await _resolve_dependency(get_evidence_manager())
        if case_id and hasattr(evidence_manager, "list_evidence_by_case"):
            evidence = await evidence_manager.list_evidence_by_case(case_id)
        elif hasattr(evidence_manager, "list_evidence"):
            evidence = await evidence_manager.list_evidence(case_id=case_id)
        else:
            filters = {"case_id": case_id} if case_id else {}
            evidence = await evidence_manager.get_evidence(filters)
        return {"evidence": [_evidence_payload(item) for item in evidence]}
    except Exception as e:
        logger.error(f"Failed to list evidence: {e}")
        raise JackdawException(message="Failed to list evidence", details=str(e))


@router.post("/evidence/{evidence_id}/verify", response_model=Dict[str, Any])
async def verify_evidence(
    evidence_id: UUID,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy evidence-integrity verification endpoint."""
    try:
        evidence_manager = await _resolve_dependency(get_evidence_manager())
        return await evidence_manager.verify_integrity(str(evidence_id))
    except Exception as e:
        logger.error(f"Failed to verify evidence {evidence_id}: {e}")
        raise JackdawException(message="Failed to verify evidence", details=str(e))


@router.get("/evidence/{evidence_id}/custody", response_model=Dict[str, Any])
async def get_evidence_custody(
    evidence_id: UUID,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy chain-of-custody endpoint."""
    try:
        evidence_manager = await _resolve_dependency(get_evidence_manager())
        chain = await evidence_manager.get_chain_of_custody(str(evidence_id))
        return {"chain": [_custody_payload(entry) for entry in chain]}
    except Exception as e:
        logger.error(f"Failed to get chain of custody for {evidence_id}: {e}")
        raise JackdawException(message="Failed to get chain of custody", details=str(e))


@router.post("/reports", response_model=ForensicReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    report_request: Dict[str, Any],
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"])),
):
    """Legacy report-creation endpoint."""
    try:
        report_generator = await _resolve_dependency(get_report_generator())
        payload = dict(report_request)
        payload.setdefault("format", "pdf")
        payload.setdefault("generated_by", current_user.id)
        report = await report_generator.create_report(payload)
        return _report_payload(report)
    except Exception as e:
        logger.error(f"Failed to create report: {e}")
        raise JackdawException(message="Failed to create report", details=str(e))


@router.get("/reports", response_model=Dict[str, Any])
async def list_reports(
    case_id: Optional[str] = Query(None, description="Filter by case ID"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy report-list endpoint."""
    try:
        report_generator = await _resolve_dependency(get_report_generator())
        if case_id and hasattr(report_generator, "list_reports_by_case"):
            reports = await report_generator.list_reports_by_case(case_id)
        else:
            reports = await report_generator.list_reports(case_id=case_id)
        return {"reports": [_report_payload(report) for report in reports]}
    except Exception as e:
        logger.error(f"Failed to list reports: {e}")
        raise JackdawException(message="Failed to list reports", details=str(e))


@router.get("/cases/{case_id}/reports", response_model=Dict[str, Any])
async def list_case_reports(
    case_id: UUID,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy per-case report list endpoint."""
    try:
        report_generator = await _resolve_dependency(get_report_generator())
        reports = await report_generator.list_reports_by_case(str(case_id))
        return {"reports": [_report_payload(report) for report in reports]}
    except Exception as e:
        logger.error(f"Failed to list reports for case {case_id}: {e}")
        raise JackdawException(message="Failed to list case reports", details=str(e))


@router.post("/reports/{report_id}/generate/{output_format}")
async def generate_report_file(
    report_id: UUID,
    output_format: str,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy file-generation endpoints for HTML/PDF responses."""
    try:
        report_generator = await _resolve_dependency(get_report_generator())
        tmp_name = f"/tmp/{report_id}.{output_format}"
        if output_format == "pdf":
            result = await report_generator.generate_pdf_report(str(report_id), tmp_name)
            content_type = "application/pdf"
        elif output_format == "html":
            result = await report_generator.generate_html_report(str(report_id), tmp_name)
            content_type = "text/html"
        else:
            raise HTTPException(status_code=400, detail="Unsupported report format")

        if isinstance(result, bytes):
            return Response(content=result, media_type=None, headers={"content-type": content_type})
        elif isinstance(result, str):
            return Response(content=result, media_type=None, headers={"content-type": content_type})
        elif isinstance(result, dict):
            file_path = result.get("file_path", tmp_name)
        else:
            file_path = tmp_name
        if content_type == "application/pdf":
            with open(file_path, "rb") as handle:
                content = handle.read()
        else:
            with open(file_path, "r", encoding="utf-8") as handle:
                content = handle.read()
        return Response(content=content, media_type=None, headers={"content-type": content_type})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate {output_format} report for {report_id}: {e}")
        raise JackdawException(message="Failed to generate report file", details=str(e))


@router.post("/evidence/{evidence_id}/assess-compliance", response_model=Dict[str, Any])
async def assess_legal_compliance(
    evidence_id: UUID,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy per-evidence compliance assessment endpoint."""
    try:
        court_defensible = await _resolve_dependency(get_court_defensible())
        result = await court_defensible.assess_legal_compliance(str(evidence_id))
        return dict(result.__dict__)
    except Exception as e:
        logger.error(f"Failed compliance assessment for {evidence_id}: {e}")
        raise JackdawException(message="Failed to assess legal compliance", details=str(e))


@router.post("/evidence/{evidence_id}/prepare-foundation", response_model=Dict[str, Any])
async def prepare_foundation(
    evidence_id: UUID,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy foundation-preparation endpoint."""
    try:
        court_defensible = await _resolve_dependency(get_court_defensible())
        result = await court_defensible.prepare_foundation_requirements(str(evidence_id))
        return dict(result.__dict__)
    except Exception as e:
        logger.error(f"Failed foundation preparation for {evidence_id}: {e}")
        raise JackdawException(message="Failed to prepare foundation requirements", details=str(e))


@router.post("/evidence/{evidence_id}/prepare-testimony", response_model=Dict[str, Any])
async def prepare_testimony(
    evidence_id: UUID,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy testimony-preparation endpoint."""
    try:
        court_defensible = await _resolve_dependency(get_court_defensible())
        result = await court_defensible.prepare_testimony(str(evidence_id), "expert", "criminal")
        return dict(result.__dict__)
    except Exception as e:
        logger.error(f"Failed testimony preparation for {evidence_id}: {e}")
        raise JackdawException(message="Failed to prepare testimony", details=str(e))


@router.post("/evidence/{evidence_id}/prepare-exhibit", response_model=Dict[str, Any])
async def prepare_exhibit(
    evidence_id: UUID,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy exhibit-preparation endpoint."""
    try:
        court_defensible = await _resolve_dependency(get_court_defensible())
        result = await court_defensible.prepare_exhibit(str(evidence_id))
        return dict(result.__dict__)
    except Exception as e:
        logger.error(f"Failed exhibit preparation for {evidence_id}: {e}")
        raise JackdawException(message="Failed to prepare exhibit", details=str(e))


@router.get("/statistics/cases", response_model=Dict[str, Any])
async def get_case_statistics(
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy case-statistics endpoint."""
    try:
        forensic_engine = await _resolve_dependency(get_forensic_engine())
        stats = await forensic_engine.get_case_statistics()
        return dict(stats.__dict__)
    except Exception as e:
        logger.error(f"Failed to get case statistics: {e}")
        raise JackdawException(message="Failed to get case statistics", details=str(e))


@router.get("/statistics/evidence", response_model=Dict[str, Any])
async def get_evidence_statistics(
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy evidence-statistics endpoint."""
    try:
        evidence_manager = await _resolve_dependency(get_evidence_manager())
        stats = await evidence_manager.get_evidence_statistics()
        return dict(stats.__dict__)
    except Exception as e:
        logger.error(f"Failed to get evidence statistics: {e}")
        raise JackdawException(message="Failed to get evidence statistics", details=str(e))


@router.get("/statistics/reports", response_model=Dict[str, Any])
async def get_report_statistics_legacy(
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy report-statistics endpoint."""
    try:
        report_generator = await _resolve_dependency(get_report_generator())
        stats = await report_generator.get_report_statistics()
        return dict(stats.__dict__)
    except Exception as e:
        logger.error(f"Failed to get report statistics: {e}")
        raise JackdawException(message="Failed to get report statistics", details=str(e))
