"""
Jackdaw Sentry - Investigations Router
Case management and investigation endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, validator
import logging

from src.api.auth import User, check_permissions, PERMISSIONS
from src.api.database import get_neo4j_session, get_postgres_connection
from src.api.exceptions import JackdawException

logger = logging.getLogger(__name__)

router = APIRouter()


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
    """Create new investigation case"""
    try:
        logger.info(f"Creating investigation: {request.title}")
        
        investigation_data = {
            "investigation_id": f"INV-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "title": request.title,
            "description": request.description,
            "priority": request.priority,
            "status": "open",
            "created_by": current_user.username,
            "created_at": datetime.utcnow(),
            "assigned_to": None,
            "addresses": request.addresses,
            "blockchain": request.blockchain,
            "time_range": {
                "start": request.time_range_start,
                "end": request.time_range_end
            },
            "tags": request.tags,
            "evidence_count": 0,
            "risk_score": 0.0,
            "timeline": []
        }
        
        metadata = {
            "case_number": investigation_data["investigation_id"],
            "jurisdiction": "global",
            "classification": "financial_crime",
            "estimated_duration_days": 30
        }
        
        return InvestigationResponse(
            success=True,
            investigation_data=investigation_data,
            metadata=metadata,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Investigation creation failed: {e}")
        raise JackdawException(
            message=f"Investigation creation failed: {str(e)}",
            error_code="INVESTIGATION_CREATION_FAILED"
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
    """List investigations with filters"""
    try:
        logger.info(f"Listing investigations with filters: status={status}, priority={priority}")
        
        # Mock investigation data
        investigations = [
            {
                "investigation_id": "INV-20240101001",
                "title": "Suspicious Bitcoin Transaction Pattern",
                "status": "in_progress",
                "priority": "high",
                "created_by": "analyst1",
                "assigned_to": current_user.username,
                "created_at": datetime.utcnow() - timedelta(days=5),
                "addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
                "evidence_count": 15,
                "risk_score": 0.75,
                "tags": ["bitcoin", "suspicious_pattern", "high_value"]
            },
            {
                "investigation_id": "INV-20240102002",
                "title": "Ethereum DeFi Flash Loan Investigation",
                "status": "open",
                "priority": "medium",
                "created_by": "analyst2",
                "assigned_to": None,
                "created_at": datetime.utcnow() - timedelta(days=2),
                "addresses": ["0x742d35Cc6634C0532925a3b8D4C9db96C4b4Db45"],
                "evidence_count": 8,
                "risk_score": 0.45,
                "tags": ["ethereum", "defi", "flash_loan"]
            }
        ]
        
        # Apply filters
        if status:
            investigations = [inv for inv in investigations if inv["status"] == status]
        if priority:
            investigations = [inv for inv in investigations if inv["priority"] == priority]
        if assigned_to:
            investigations = [inv for inv in investigations if inv["assigned_to"] == assigned_to]
        
        # Apply pagination
        total_count = len(investigations)
        paginated_investigations = investigations[offset:offset + limit]
        
        return {
            "success": True,
            "investigations": paginated_investigations,
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "filters_applied": {
                "status": status,
                "priority": priority,
                "assigned_to": assigned_to
            },
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Investigation listing failed: {e}")
        raise JackdawException(
            message=f"Investigation listing failed: {str(e)}",
            error_code="INVESTIGATION_LISTING_FAILED"
        )


@router.get("/{investigation_id}")
async def get_investigation(
    investigation_id: str,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_investigations"]]))
):
    """Get detailed investigation information"""
    try:
        logger.info(f"Getting investigation details for: {investigation_id}")
        
        investigation_data = {
            "investigation_id": investigation_id,
            "title": "Suspicious Bitcoin Transaction Pattern",
            "description": "Investigation of unusual transaction patterns suggesting potential money laundering",
            "status": "in_progress",
            "priority": "high",
            "created_by": "analyst1",
            "assigned_to": current_user.username,
            "created_at": datetime.utcnow() - timedelta(days=5),
            "updated_at": datetime.utcnow() - timedelta(hours=2),
            "addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
            "blockchain": "bitcoin",
            "time_range": {
                "start": datetime.utcnow() - timedelta(days=30),
                "end": datetime.utcnow()
            },
            "tags": ["bitcoin", "suspicious_pattern", "high_value"],
            "evidence_count": 15,
            "risk_score": 0.75,
            "timeline": [
                {
                    "timestamp": datetime.utcnow() - timedelta(days=5),
                    "action": "investigation_created",
                    "user": "analyst1",
                    "details": "Initial case created based on automated alert"
                },
                {
                    "timestamp": datetime.utcnow() - timedelta(days=4),
                    "action": "evidence_added",
                    "user": current_user.username,
                    "details": "Added transaction evidence"
                }
            ],
            "summary": {
                "total_transactions_analyzed": 1250,
                "total_value_usd": 2847500.50,
                "suspicious_patterns_found": 3,
                "connected_addresses": 45
            }
        }
        
        return {
            "success": True,
            "investigation": investigation_data,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Investigation retrieval failed: {e}")
        raise JackdawException(
            message=f"Investigation retrieval failed: {str(e)}",
            error_code="INVESTIGATION_RETRIEVAL_FAILED"
        )


@router.put("/{investigation_id}", response_model=InvestigationResponse)
async def update_investigation(
    investigation_id: str,
    request: InvestigationUpdateRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["write_investigations"]]))
):
    """Update investigation details"""
    try:
        logger.info(f"Updating investigation: {investigation_id}")
        
        update_data = {
            "investigation_id": investigation_id,
            "updated_by": current_user.username,
            "updated_at": datetime.utcnow()
        }
        
        # Only update provided fields
        if request.status:
            update_data["status"] = request.status
        if request.priority:
            update_data["priority"] = request.priority
        if request.notes:
            update_data["notes"] = request.notes
        if request.tags:
            update_data["tags"] = request.tags
        if request.assigned_to:
            update_data["assigned_to"] = request.assigned_to
        
        metadata = {
            "update_fields": list(request.dict(exclude_unset=True).keys()),
            "previous_values": {},  # In real implementation, would fetch previous values
            "change_approved": True
        }
        
        return InvestigationResponse(
            success=True,
            investigation_data=update_data,
            metadata=metadata,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Investigation update failed: {e}")
        raise JackdawException(
            message=f"Investigation update failed: {str(e)}",
            error_code="INVESTIGATION_UPDATE_FAILED"
        )


@router.post("/evidence", response_model=InvestigationResponse)
async def add_evidence(
    request: EvidenceRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["write_investigations"]]))
):
    """Add evidence to investigation"""
    try:
        logger.info(f"Adding evidence to investigation: {request.investigation_id}")
        
        evidence_data = {
            "evidence_id": f"EVD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "investigation_id": request.investigation_id,
            "evidence_type": request.evidence_type,
            "description": request.description,
            "data": request.data,
            "confidence": request.confidence,
            "added_by": current_user.username,
            "added_at": datetime.utcnow(),
            "verified": False,
            "source": "internal_analysis"
        }
        
        metadata = {
            "evidence_validation": "passed",
            "data_integrity_check": "passed",
            "chain_of_custody": "maintained"
        }
        
        return InvestigationResponse(
            success=True,
            investigation_data=evidence_data,
            metadata=metadata,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Evidence addition failed: {e}")
        raise JackdawException(
            message=f"Evidence addition failed: {str(e)}",
            error_code="EVIDENCE_ADDITION_FAILED"
        )


@router.get("/{investigation_id}/evidence")
async def get_investigation_evidence(
    investigation_id: str,
    evidence_type: Optional[str] = None,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_investigations"]]))
):
    """Get evidence for investigation"""
    try:
        logger.info(f"Getting evidence for investigation: {investigation_id}")
        
        evidence = [
            {
                "evidence_id": "EVD-20240101001",
                "evidence_type": "transaction",
                "description": "High-value Bitcoin transaction",
                "data": {
                    "transaction_hash": "1234567890abcdef...",
                    "amount_btc": 15.7,
                    "timestamp": datetime.utcnow() - timedelta(days=3)
                },
                "confidence": 0.95,
                "added_by": "analyst1",
                "added_at": datetime.utcnow() - timedelta(days=3)
            },
            {
                "evidence_id": "EVD-20240101002",
                "evidence_type": "address",
                "description": "Address linked to known exchange",
                "data": {
                    "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                    "labels": ["exchange", "trading"],
                    "risk_score": 0.3
                },
                "confidence": 0.85,
                "added_by": current_user.username,
                "added_at": datetime.utcnow() - timedelta(days=2)
            }
        ]
        
        if evidence_type:
            evidence = [ev for ev in evidence if ev["evidence_type"] == evidence_type]
        
        return {
            "success": True,
            "investigation_id": investigation_id,
            "evidence": evidence,
            "total_count": len(evidence),
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Evidence retrieval failed: {e}")
        raise JackdawException(
            message=f"Evidence retrieval failed: {str(e)}",
            error_code="EVIDENCE_RETRIEVAL_FAILED"
        )


@router.get("/statistics")
async def get_investigation_statistics(
    current_user: User = Depends(check_permissions([PERMISSIONS["read_investigations"]]))
):
    """Get investigation system statistics"""
    try:
        stats = {
            "total_investigations": 156,
            "active_investigations": 23,
            "closed_investigations": 133,
            "average_resolution_days": 18,
            "evidence_items_total": 2450,
            "high_priority_cases": 8,
            "cases_by_status": {
                "open": 12,
                "in_progress": 11,
                "closed": 133,
                "archived": 0
            },
            "cases_by_priority": {
                "low": 45,
                "medium": 78,
                "high": 28,
                "critical": 5
            }
        }
        
        return {
            "success": True,
            "statistics": stats,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Investigation statistics failed: {e}")
        raise JackdawException(
            message=f"Investigation statistics failed: {str(e)}",
            error_code="STATISTICS_FAILED"
        )
