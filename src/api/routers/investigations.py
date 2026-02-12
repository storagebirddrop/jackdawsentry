"""
Jackdaw Sentry - Investigations Router
Case management and investigation endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, validator
import json as _json
import logging
import uuid

from src.api.auth import User, check_permissions, PERMISSIONS
from src.api.database import get_neo4j_session, get_postgres_connection
from src.api.exceptions import JackdawException

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_LIMIT = 100


# Pydantic models
class InvestigationRequest(BaseModel):
    title: str
    description: str
    priority: str = "medium"  # low, medium, high, critical
    addresses: List[str]
    blockchain: str
    time_range_start: datetime
    time_range_end: datetime
    tags: List[str] = []
    
    @validator('priority')
    def validate_priority(cls, v):
        valid_priorities = ["low", "medium", "high", "critical"]
        if v not in valid_priorities:
            raise ValueError(f'Invalid priority: {v}')
        return v
    
    @validator('addresses')
    def validate_addresses(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one address must be provided')
        return [addr.strip() for addr in v if addr.strip()]


class InvestigationUpdateRequest(BaseModel):
    status: Optional[str] = None  # open, in_progress, closed, archived
    priority: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    assigned_to: Optional[str] = None


class EvidenceRequest(BaseModel):
    investigation_id: str
    evidence_type: str  # transaction, address, pattern, external
    description: str
    data: Dict[str, Any]
    confidence: float = 0.5
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if v < 0.0 or v > 1.0:
            raise ValueError('Confidence must be between 0.0 and 1.0')
        return v


class InvestigationResponse(BaseModel):
    success: bool
    investigation_data: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime


# Endpoints
@router.post("/create", response_model=InvestigationResponse)
async def create_investigation(
    request: InvestigationRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["write_investigations"]]))
):
    """Create new investigation case and persist to Neo4j"""
    try:
        logger.info(f"Creating investigation: {request.title}")
        now = datetime.now(timezone.utc)
        inv_id = f"INV-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        async with get_neo4j_session() as session:
            await session.run(
                """
                CREATE (i:Investigation {
                    investigation_id: $inv_id,
                    title: $title,
                    description: $description,
                    priority: $priority,
                    status: 'open',
                    created_by: $created_by,
                    created_at: $created_at,
                    addresses: $addresses,
                    blockchain: $blockchain,
                    time_range_start: $time_start,
                    time_range_end: $time_end,
                    tags: $tags,
                    evidence_count: 0,
                    risk_score: 0.0
                })
                """,
                inv_id=inv_id,
                title=request.title,
                description=request.description,
                priority=request.priority,
                created_by=current_user.username,
                created_at=now.isoformat(),
                addresses=request.addresses,
                blockchain=request.blockchain,
                time_start=request.time_range_start.isoformat(),
                time_end=request.time_range_end.isoformat(),
                tags=request.tags,
            )

        investigation_data = {
            "investigation_id": inv_id,
            "title": request.title,
            "description": request.description,
            "priority": request.priority,
            "status": "open",
            "created_by": current_user.username,
            "created_at": now.isoformat(),
            "addresses": request.addresses,
            "blockchain": request.blockchain,
            "tags": request.tags,
        }

        metadata = {
            "case_number": inv_id,
            "persisted_to": "neo4j",
        }

        return InvestigationResponse(
            success=True,
            investigation_data=investigation_data,
            metadata=metadata,
            timestamp=now,
        )

    except Exception as e:
        logger.error(f"Investigation creation failed: {e}")
        raise JackdawException(
            message=f"Investigation creation failed: {str(e)}",
            error_code="INVESTIGATION_CREATION_FAILED",
        )


@router.get("/list")
async def list_investigations(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_investigations"]]))
):
    """List investigations from Neo4j with filters"""
    try:
        if limit > MAX_LIMIT:
            raise HTTPException(
                status_code=400,
                detail=f"limit must not exceed {MAX_LIMIT}, got {limit}",
            )
        if limit < 1:
            raise HTTPException(
                status_code=400,
                detail="limit must be at least 1",
            )

        logger.info(f"Listing investigations with filters: status={status}, priority={priority}")

        where_clauses = []
        params: Dict[str, Any] = {"skip_val": offset, "limit_val": limit}
        if status:
            where_clauses.append("i.status = $status")
            params["status"] = status
        if priority:
            where_clauses.append("i.priority = $priority")
            params["priority"] = priority
        if assigned_to:
            where_clauses.append("i.assigned_to = $assigned_to")
            params["assigned_to"] = assigned_to

        where_str = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        async with get_neo4j_session() as session:
            count_result = await session.run(
                f"MATCH (i:Investigation) {where_str} RETURN count(i) AS total", **params
            )
            count_record = await count_result.single()
            total_count = count_record["total"] if count_record else 0

            result = await session.run(
                f"""
                MATCH (i:Investigation) {where_str}
                RETURN i ORDER BY i.created_at DESC SKIP $skip_val LIMIT $limit_val
                """,
                **params,
            )
            records = await result.data()

        investigations = []
        for record in records:
            props = dict(record["i"])
            investigations.append(props)

        return {
            "success": True,
            "investigations": investigations,
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count,
            },
            "filters_applied": {"status": status, "priority": priority, "assigned_to": assigned_to},
            "timestamp": datetime.now(timezone.utc),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Investigation listing failed: {e}")
        raise JackdawException(
            message=f"Investigation listing failed: {str(e)}",
            error_code="INVESTIGATION_LISTING_FAILED",
        )


@router.get("/{investigation_id}")
async def get_investigation(
    investigation_id: str,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_investigations"]]))
):
    """Get detailed investigation from Neo4j"""
    try:
        logger.info(f"Getting investigation details for: {investigation_id}")

        async with get_neo4j_session() as session:
            result = await session.run(
                """
                MATCH (i:Investigation {investigation_id: $inv_id})
                OPTIONAL MATCH (i)<-[:EVIDENCE_FOR]-(e:Evidence)
                RETURN i, count(e) AS evidence_count
                """,
                inv_id=investigation_id,
            )
            record = await result.single()

        if not record or not record["i"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")

        investigation_data = dict(record["i"])
        investigation_data["evidence_count"] = record["evidence_count"]

        return {
            "success": True,
            "investigation": investigation_data,
            "timestamp": datetime.now(timezone.utc),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Investigation retrieval failed: {e}")
        raise JackdawException(
            message=f"Investigation retrieval failed: {str(e)}",
            error_code="INVESTIGATION_RETRIEVAL_FAILED",
        )


@router.put("/{investigation_id}", response_model=InvestigationResponse)
async def update_investigation(
    investigation_id: str,
    request: InvestigationUpdateRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["write_investigations"]]))
):
    """Update investigation in Neo4j"""
    try:
        logger.info(f"Updating investigation: {investigation_id}")
        now = datetime.now(timezone.utc)

        set_clauses = ["i.updated_at = $updated_at", "i.updated_by = $updated_by"]
        params: Dict[str, Any] = {
            "inv_id": investigation_id,
            "updated_at": now.isoformat(),
            "updated_by": current_user.username,
        }

        if request.status:
            set_clauses.append("i.status = $status")
            params["status"] = request.status
        if request.priority:
            set_clauses.append("i.priority = $priority")
            params["priority"] = request.priority
        if request.notes:
            set_clauses.append("i.notes = $notes")
            params["notes"] = request.notes
        if request.tags is not None:
            set_clauses.append("i.tags = $tags")
            params["tags"] = request.tags
        if request.assigned_to:
            set_clauses.append("i.assigned_to = $assigned_to")
            params["assigned_to"] = request.assigned_to

        async with get_neo4j_session() as session:
            result = await session.run(
                f"""
                MATCH (i:Investigation {{investigation_id: $inv_id}})
                SET {', '.join(set_clauses)}
                RETURN i
                """,
                **params,
            )
            record = await result.single()

        if not record or not record["i"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")

        update_data = dict(record["i"])

        metadata = {
            "update_fields": [k for k, v in request.model_dump(exclude_unset=True).items() if v is not None],
            "persisted_to": "neo4j",
        }

        return InvestigationResponse(
            success=True,
            investigation_data=update_data,
            metadata=metadata,
            timestamp=now,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Investigation update failed: {e}")
        raise JackdawException(
            message=f"Investigation update failed: {str(e)}",
            error_code="INVESTIGATION_UPDATE_FAILED",
        )


@router.post("/evidence", response_model=InvestigationResponse)
async def add_evidence(
    request: EvidenceRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["write_investigations"]]))
):
    """Add evidence to investigation and persist to Neo4j"""
    try:
        logger.info(f"Adding evidence to investigation: {request.investigation_id}")
        now = datetime.now(timezone.utc)
        evd_id = f"EVD-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        async with get_neo4j_session() as session:
            # Verify investigation exists
            check = await session.run(
                "MATCH (i:Investigation {investigation_id: $inv_id}) RETURN i",
                inv_id=request.investigation_id,
            )
            if not await check.single():
                raise HTTPException(status_code=404, detail="Investigation not found")

            await session.run(
                """
                MATCH (i:Investigation {investigation_id: $inv_id})
                CREATE (e:Evidence {
                    evidence_id: $evd_id,
                    evidence_type: $evidence_type,
                    description: $description,
                    data: $data,
                    confidence: $confidence,
                    added_by: $added_by,
                    added_at: $added_at,
                    verified: false
                })-[:EVIDENCE_FOR]->(i)
                SET i.evidence_count = coalesce(i.evidence_count, 0) + 1
                """,
                inv_id=request.investigation_id,
                evd_id=evd_id,
                evidence_type=request.evidence_type,
                description=request.description,
                data=_json.dumps(request.data),
                confidence=request.confidence,
                added_by=current_user.username,
                added_at=now.isoformat(),
            )

        evidence_data = {
            "evidence_id": evd_id,
            "investigation_id": request.investigation_id,
            "evidence_type": request.evidence_type,
            "description": request.description,
            "confidence": request.confidence,
            "added_by": current_user.username,
            "added_at": now.isoformat(),
        }

        metadata = {"persisted_to": "neo4j", "chain_of_custody": "maintained"}

        return InvestigationResponse(
            success=True,
            investigation_data=evidence_data,
            metadata=metadata,
            timestamp=now,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Evidence addition failed: {e}")
        raise JackdawException(
            message=f"Evidence addition failed: {str(e)}",
            error_code="EVIDENCE_ADDITION_FAILED",
        )


@router.get("/{investigation_id}/evidence")
async def get_investigation_evidence(
    investigation_id: str,
    evidence_type: Optional[str] = None,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_investigations"]]))
):
    """Get evidence for investigation from Neo4j"""
    try:
        logger.info(f"Getting evidence for investigation: {investigation_id}")

        type_filter = "AND e.evidence_type = $evidence_type" if evidence_type else ""
        params: Dict[str, Any] = {"inv_id": investigation_id}
        if evidence_type:
            params["evidence_type"] = evidence_type

        async with get_neo4j_session() as session:
            # Verify investigation exists
            check = await session.run(
                "MATCH (i:Investigation {investigation_id: $inv_id}) RETURN i",
                inv_id=investigation_id,
            )
            if not await check.single():
                raise HTTPException(status_code=404, detail="Investigation not found")

            result = await session.run(
                f"""
                MATCH (e:Evidence)-[:EVIDENCE_FOR]->(i:Investigation {{investigation_id: $inv_id}})
                {type_filter}
                RETURN e ORDER BY e.added_at DESC
                """,
                **params,
            )
            records = await result.data()

        evidence = [dict(r["e"]) for r in records]

        return {
            "success": True,
            "investigation_id": investigation_id,
            "evidence": evidence,
            "total_count": len(evidence),
            "timestamp": datetime.now(timezone.utc),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Evidence retrieval failed: {e}")
        raise JackdawException(
            message=f"Evidence retrieval failed: {str(e)}",
            error_code="EVIDENCE_RETRIEVAL_FAILED",
        )


@router.get("/statistics")
async def get_investigation_statistics(
    current_user: User = Depends(check_permissions([PERMISSIONS["read_investigations"]]))
):
    """Get investigation statistics from Neo4j"""
    try:
        stats: Dict[str, Any] = {}
        async with get_neo4j_session() as session:
            result = await session.run(
                """
                MATCH (i:Investigation)
                RETURN count(i) AS total,
                       count(CASE WHEN i.status IN ['open','in_progress'] THEN 1 END) AS active,
                       count(CASE WHEN i.status = 'closed' THEN 1 END) AS closed
                """
            )
            record = await result.single()
            stats["total_investigations"] = record["total"] if record else 0
            stats["active_investigations"] = record["active"] if record else 0
            stats["closed_investigations"] = record["closed"] if record else 0

            status_result = await session.run(
                "MATCH (i:Investigation) RETURN i.status AS status, count(i) AS count"
            )
            status_records = await status_result.data()
            stats["cases_by_status"] = {r["status"]: r["count"] for r in status_records if r["status"]}

            prio_result = await session.run(
                "MATCH (i:Investigation) RETURN i.priority AS priority, count(i) AS count"
            )
            prio_records = await prio_result.data()
            stats["cases_by_priority"] = {r["priority"]: r["count"] for r in prio_records if r["priority"]}

            evd_result = await session.run("MATCH (e:Evidence) RETURN count(e) AS total")
            evd_record = await evd_result.single()
            stats["evidence_items_total"] = evd_record["total"] if evd_record else 0

        return {
            "success": True,
            "statistics": stats,
            "timestamp": datetime.now(timezone.utc),
        }

    except Exception as e:
        logger.error(f"Investigation statistics failed: {e}")
        raise JackdawException(
            message=f"Investigation statistics failed: {str(e)}",
            error_code="STATISTICS_FAILED",
        )
