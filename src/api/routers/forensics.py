"""
Jackdaw Sentry - Forensics API Router
REST endpoints for forensic case management, evidence handling, and court preparation
"""

import json as _json
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

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pydantic import field_validator

from src.api.auth import PERMISSIONS
from src.api.auth import User
from src.api.auth import check_permissions
from src.api.database import get_postgres_connection
from src.api.exceptions import JackdawException
from src.forensics.court_defensible import get_court_defensible_evidence
from src.forensics.evidence_manager import get_evidence_manager
from src.forensics.forensic_engine import get_forensic_engine
from src.forensics.report_generator import get_report_generator

logger = logging.getLogger(__name__)

router = APIRouter()

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
    title: str
    description: str
    case_type: str
    priority: str = "medium"  # low, medium, high, critical
    assigned_investigator: Optional[str] = None
    jurisdiction: str = "federal_us"
    legal_standard: str = "preponderance"
    related_cases: List[str] = []
    tags: List[str] = []
    estimated_completion_date: Optional[datetime] = None

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
    jurisdiction: Optional[str] = None
    legal_standard: Optional[str] = None
    related_cases: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    estimated_completion_date: Optional[datetime] = None
    notes: Optional[str] = None

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
    source_location: str
    collection_date: datetime
    collected_by: str
    hash_value: Optional[str] = None
    file_size_bytes: Optional[int] = None
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
    case_type: str
    status: str
    priority: str
    assigned_investigator: Optional[str]
    jurisdiction: str
    legal_standard: str
    related_cases: List[str]
    tags: List[str]
    evidence_count: int
    created_date: datetime
    last_updated: datetime
    estimated_completion_date: Optional[datetime]
    actual_completion_date: Optional[datetime]
    notes: Optional[str]


class EvidenceResponse(BaseModel):
    id: str
    case_id: str
    title: str
    description: str
    evidence_type: str
    source_location: str
    collection_date: datetime
    collected_by: str
    hash_value: Optional[str]
    file_size_bytes: Optional[int]
    integrity_status: str
    chain_of_custody_verified: bool
    metadata: Dict[str, Any]
    tags: List[str]
    created_date: datetime
    last_updated: datetime


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
@router.get("/cases", response_model=List[ForensicCaseResponse])
async def list_forensic_cases(
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    assigned_investigator: Optional[str] = Query(
        None, description="Filter by investigator"
    ),
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """List forensic cases with optional filters"""
    try:
        forensic_engine = await get_forensic_engine()

        # Build filters
        filters = {}
        if status:
            if status not in VALID_CASE_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status}",
                )
            filters["status"] = status

        if priority:
            valid_priorities = {"low", "medium", "high", "critical"}
            if priority not in valid_priorities:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid priority: {priority}",
                )
            filters["priority"] = priority

        if assigned_investigator:
            filters["assigned_investigator"] = assigned_investigator

        if jurisdiction:
            filters["jurisdiction"] = jurisdiction

        cases = await forensic_engine.get_cases(filters, limit, offset)

        return [ForensicCaseResponse(**case.__dict__) for case in cases]

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
        forensic_engine = await get_forensic_engine()

        case_data = case.model_dump()
        case_data["id"] = str(uuid.uuid4())
        case_data["status"] = "open"
        case_data["evidence_count"] = 0
        case_data["created_date"] = datetime.now(timezone.utc)
        case_data["last_updated"] = datetime.now(timezone.utc)

        created_case = await forensic_engine.create_case(case_data)

        logger.info(
            f"Created forensic case {created_case.id} by user {current_user.id}"
        )
        return ForensicCaseResponse(**created_case.__dict__)

    except Exception as e:
        logger.error(f"Failed to create forensic case: {e}")
        raise JackdawException(message="Failed to create forensic case", details=str(e))


@router.get("/cases/{case_id}", response_model=ForensicCaseResponse)
async def get_forensic_case(
    case_id: str,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Get a specific forensic case by ID"""
    try:
        forensic_engine = await get_forensic_engine()

        case = await forensic_engine.get_case(case_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Forensic case {case_id} not found",
            )

        return ForensicCaseResponse(**case.__dict__)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get forensic case {case_id}: {e}")
        raise JackdawException(message="Failed to get forensic case", details=str(e))


@router.put("/cases/{case_id}", response_model=ForensicCaseResponse)
async def update_forensic_case(
    case_id: str,
    case_update: ForensicCaseUpdate,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"])),
):
    """Update a forensic case"""
    try:
        forensic_engine = await get_forensic_engine()

        # Check if case exists
        existing_case = await forensic_engine.get_case(case_id)
        if not existing_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Forensic case {case_id} not found",
            )

        # Update case
        update_data = case_update.model_dump(exclude_unset=True)
        update_data["last_updated"] = datetime.now(timezone.utc)

        updated_case = await forensic_engine.update_case(case_id, update_data)

        logger.info(f"Updated forensic case {case_id} by user {current_user.id}")
        return ForensicCaseResponse(**updated_case.__dict__)

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


@router.get("/cases/{case_id}/evidence", response_model=List[EvidenceResponse])
async def get_case_evidence(
    case_id: str,
    evidence_type: Optional[str] = Query(None, description="Filter by evidence type"),
    integrity_status: Optional[str] = Query(
        None, description="Filter by integrity status"
    ),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Get all evidence for a specific case"""
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

        # Build filters
        filters = {"case_id": case_id}
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

        evidence_list = await evidence_manager.get_evidence(filters)

        return [EvidenceResponse(**evidence.__dict__) for evidence in evidence_list]

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
