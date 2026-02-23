"""
Jackdaw Sentry - Victim Reports API Router
REST endpoints for victim report management and verification
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, field_validator, ConfigDict
import logging
import uuid
import json as _json

from src.api.auth import User, check_permissions, PERMISSIONS
from src.api.database import get_postgres_connection
from src.api.exceptions import JackdawException
from src.intelligence.victim_reports import get_victim_reports_db

logger = logging.getLogger(__name__)

router = APIRouter()

# Allowed filter values
VALID_SEVERITIES = {"low", "medium", "high", "critical", "severe"}
VALID_STATUSES = {"pending", "verified", "false_positive", "investigating", "resolved", "closed"}
VALID_REPORT_TYPES = {"scam", "fraud", "phishing", "hack", "rug_pull", "theft", "impersonation", "money_laundering", "terrorism_financing", "other"}

# Pydantic models
class VictimReportCreate(BaseModel):
    report_type: str
    victim_contact: str
    incident_date: datetime
    amount_lost: Optional[float] = None
    currency: Optional[str] = None
    description: str
    related_addresses: List[str] = []
    related_transactions: List[str] = []
    evidence_files: List[str] = []
    severity: str = "medium"
    source_ip: Optional[str] = None
    source_platform: Optional[str] = None
    
    @field_validator('report_type')
    @classmethod
    def validate_report_type(cls, v):
        if v not in VALID_REPORT_TYPES:
            raise ValueError(f'Invalid report type: {v}')
        return v
    
    @field_validator('severity')
    @classmethod
    def validate_severity(cls, v):
        if v not in VALID_SEVERITIES:
            raise ValueError(f'Invalid severity: {v}')
        return v

class VictimReportUpdate(BaseModel):
    report_type: Optional[str] = None
    victim_contact: Optional[str] = None
    incident_date: Optional[datetime] = None
    amount_lost: Optional[float] = None
    currency: Optional[str] = None
    description: Optional[str] = None
    related_addresses: Optional[List[str]] = None
    related_transactions: Optional[List[str]] = None
    evidence_files: Optional[List[str]] = None
    severity: Optional[str] = None
    source_ip: Optional[str] = None
    source_platform: Optional[str] = None
    
    @field_validator('report_type')
    @classmethod
    def validate_report_type(cls, v):
        if v is not None and v not in VALID_REPORT_TYPES:
            raise ValueError(f'Invalid report type: {v}')
        return v
    
    @field_validator('severity')
    @classmethod
    def validate_severity(cls, v):
        if v is not None and v not in VALID_SEVERITIES:
            raise ValueError(f'Invalid severity: {v}')
        return v

class VictimReportResponse(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if isinstance(v, datetime) else v
        }
    )
    
    id: str
    report_type: str
    victim_contact: str
    incident_date: datetime
    amount_lost: Optional[float]
    currency: Optional[str]
    description: str
    related_addresses: List[str]
    related_transactions: List[str]
    evidence_files: List[str]
    severity: str
    status: str
    source_ip: Optional[str]
    source_platform: Optional[str]
    created_date: datetime
    last_updated: datetime
    verified_by: Optional[str]
    verification_date: Optional[datetime]
    notes: Optional[str]

class ReportVerification(BaseModel):
    status: str
    notes: Optional[str] = None
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v not in {"verified", "false_positive", "investigating"}:
            raise ValueError(f'Invalid verification status: {v}')
        return v

class ReportStatistics(BaseModel):
    total_reports: int
    reports_by_status: Dict[str, int]
    reports_by_type: Dict[str, int]
    reports_by_severity: Dict[str, int]
    reports_by_timeframe: Dict[str, int]
    total_amount_lost: float
    average_amount_lost: float
    verification_rate: float

# API Endpoints
@router.post("/", response_model=VictimReportResponse, status_code=status.HTTP_201_CREATED)
async def create_victim_report(
    report: VictimReportCreate,
    current_user: User = Depends(check_permissions([PERMISSIONS["write_intelligence"]]))
):
    """Create a new victim report"""
    try:
        victim_reports_db = await get_victim_reports_db()
        
        report_data = report.model_dump()
        report_data["id"] = str(uuid.uuid4())
        report_data["status"] = "pending"
        report_data["created_date"] = datetime.now(timezone.utc)
        report_data["last_updated"] = datetime.now(timezone.utc)
        
        created_report = await victim_reports_db.create_report(report_data)
        
        logger.info(f"Created victim report {created_report.id} by user {current_user.id}")
        return VictimReportResponse(**created_report.to_dict())
        
    except Exception as e:
        logger.error(f"Failed to create victim report: {e}")
        raise JackdawException(
            message="Failed to create victim report",
            details=str(e)
        )

@router.get("/", response_model=List[VictimReportResponse])
async def list_victim_reports(
    status: Optional[str] = Query(None, description="Filter by status"),
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(check_permissions([PERMISSIONS["read_intelligence"]]))
):
    """List victim reports with optional filters"""
    try:
        victim_reports_db = await get_victim_reports_db()
        
        # Build filters
        filters = {}
        if status:
            if status not in VALID_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status}"
                )
            filters["status"] = status
        
        if report_type:
            if report_type not in VALID_REPORT_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid report type: {report_type}"
                )
            filters["report_type"] = report_type
        
        if severity:
            if severity not in VALID_SEVERITIES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid severity: {severity}"
                )
            filters["severity"] = severity
        
        if start_date:
            filters["start_date"] = start_date
        
        if end_date:
            filters["end_date"] = end_date
        
        reports = await victim_reports_db.get_reports(filters, limit, offset)
        
        return [VictimReportResponse(**report.to_dict()) for report in reports]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list victim reports: {e}")
        raise JackdawException(
            message="Failed to list victim reports",
            details=str(e)
        )

@router.get("/{report_id}", response_model=VictimReportResponse)
async def get_victim_report(
    report_id: str,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_intelligence"]]))
):
    """Get a specific victim report by ID"""
    try:
        victim_reports_db = await get_victim_reports_db()
        
        report = await victim_reports_db.get_report(report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Victim report {report_id} not found"
            )
        
        return VictimReportResponse(**report.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get victim report {report_id}: {e}")
        raise JackdawException(
            message="Failed to get victim report",
            details=str(e)
        )

@router.put("/{report_id}", response_model=VictimReportResponse)
async def update_victim_report(
    report_id: str,
    report_update: VictimReportUpdate,
    current_user: User = Depends(check_permissions([PERMISSIONS["write_intelligence"]]))
):
    """Update a victim report"""
    try:
        victim_reports_db = await get_victim_reports_db()
        
        # Check if report exists
        existing_report = await victim_reports_db.get_report(report_id)
        if not existing_report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Victim report {report_id} not found"
            )
        
        # Update report
        update_data = report_update.model_dump(exclude_unset=True)
        update_data["last_updated"] = datetime.now(timezone.utc)
        
        updated_report = await victim_reports_db.update_report(report_id, update_data)
        
        logger.info(f"Updated victim report {report_id} by user {current_user.id}")
        return VictimReportResponse(**updated_report.__dict__)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update victim report {report_id}: {e}")
        raise JackdawException(
            message="Failed to update victim report",
            details=str(e)
        )

@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_victim_report(
    report_id: str,
    current_user: User = Depends(check_permissions([PERMISSIONS["write_intelligence"]]))
):
    """Delete a victim report"""
    try:
        victim_reports_db = await get_victim_reports_db()
        
        # Check if report exists
        existing_report = await victim_reports_db.get_report(report_id)
        if not existing_report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Victim report {report_id} not found"
            )
        
        await victim_reports_db.delete_report(report_id)
        
        logger.info(f"Deleted victim report {report_id} by user {current_user.id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete victim report {report_id}: {e}")
        raise JackdawException(
            message="Failed to delete victim report",
            details=str(e)
        )

@router.post("/{report_id}/verify", response_model=VictimReportResponse)
async def verify_victim_report(
    report_id: str,
    verification: ReportVerification,
    current_user: User = Depends(check_permissions([PERMISSIONS["write_intelligence"]]))
):
    """Verify a victim report"""
    try:
        victim_reports_db = await get_victim_reports_db()
        
        # Check if report exists
        existing_report = await victim_reports_db.get_report(report_id)
        if not existing_report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Victim report {report_id} not found"
            )
        
        # Update verification status
        verification_data = {
            "status": verification.status,
            "verified_by": current_user.id,
            "verification_date": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc)
        }
        
        if verification.notes:
            verification_data["notes"] = verification.notes
        
        updated_report = await victim_reports_db.update_report(report_id, verification_data)
        
        logger.info(f"Verified victim report {report_id} with status {verification.status} by user {current_user.id}")
        return VictimReportResponse(**updated_report.__dict__)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify victim report {report_id}: {e}")
        raise JackdawException(
            message="Failed to verify victim report",
            details=str(e)
        )

@router.get("/statistics/overview", response_model=ReportStatistics)
async def get_report_statistics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(check_permissions([PERMISSIONS["read_intelligence"]]))
):
    """Get victim report statistics"""
    try:
        victim_reports_db = await get_victim_reports_db()
        
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        stats = await victim_reports_db.get_statistics(start_date)
        
        return ReportStatistics(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get victim report statistics: {e}")
        raise JackdawException(
            message="Failed to get victim report statistics",
            details=str(e)
        )

@router.get("/search/addresses", response_model=List[VictimReportResponse])
async def search_reports_by_address(
    address: str = Query(..., description="Blockchain address to search"),
    current_user: User = Depends(check_permissions([PERMISSIONS["read_intelligence"]]))
):
    """Search victim reports by related blockchain address"""
    try:
        victim_reports_db = await get_victim_reports_db()
        
        reports = await victim_reports_db.search_by_address(address)
        
        return [VictimReportResponse(**report.to_dict()) for report in reports]
        
    except Exception as e:
        logger.error(f"Failed to search victim reports by address {address}: {e}")
        raise JackdawException(
            message="Failed to search victim reports by address",
            details=str(e)
        )

@router.get("/search/transactions", response_model=List[VictimReportResponse])
async def search_reports_by_transaction(
    transaction_hash: str = Query(..., description="Transaction hash to search"),
    current_user: User = Depends(check_permissions([PERMISSIONS["read_intelligence"]]))
):
    """Search victim reports by related transaction hash"""
    try:
        victim_reports_db = await get_victim_reports_db()
        
        reports = await victim_reports_db.search_by_transaction(transaction_hash)
        
        return [VictimReportResponse(**report.to_dict()) for report in reports]
        
    except Exception as e:
        logger.error(f"Failed to search victim reports by transaction {transaction_hash}: {e}")
        raise JackdawException(
            message="Failed to search victim reports by transaction",
            details=str(e)
        )
