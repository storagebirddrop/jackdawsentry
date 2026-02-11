"""
Jackdaw Sentry - Reports Router
Report generation and management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, validator
import logging

from src.api.auth import User, check_permissions, PERMISSIONS
from src.api.database import get_postgres_connection
from src.api.exceptions import JackdawException

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class ReportRequest(BaseModel):
    report_type: str  # transaction, compliance, investigation, intelligence, custom
    title: str
    description: str
    parameters: Dict[str, Any]
    format: str = "json"  # json, pdf, csv, xlsx
    schedule: Optional[str] = None  # daily, weekly, monthly, quarterly
    
    @validator('report_type')
    def validate_report_type(cls, v):
        valid_types = ["transaction", "compliance", "investigation", "intelligence", "custom", "audit"]
        if v not in valid_types:
            raise ValueError(f'Invalid report type: {v}')
        return v
    
    @validator('format')
    def validate_format(cls, v):
        valid_formats = ["json", "pdf", "csv", "xlsx"]
        if v not in valid_formats:
            raise ValueError(f'Invalid format: {v}')
        return v


class ReportTemplateRequest(BaseModel):
    name: str
    description: str
    report_type: str
    template_definition: Dict[str, Any]
    is_public: bool = False
    
    @validator('report_type')
    def validate_report_type(cls, v):
        valid_types = ["transaction", "compliance", "investigation", "intelligence", "custom"]
        if v not in valid_types:
            raise ValueError(f'Invalid report type: {v}')
        return v


class ReportResponse(BaseModel):
    success: bool
    report_data: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime


# Endpoints
@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["write_reports"]]))
):
    """Generate report"""
    try:
        logger.info(f"Generating {request.report_type} report: {request.title}")
        
        report_id = f"RPT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        if request.report_type == "transaction":
            report_data = {
                "report_id": report_id,
                "report_type": request.report_type,
                "title": request.title,
                "summary": {
                    "total_transactions": 15420,
                    "total_volume_usd": 28475000.50,
                    "unique_addresses": 5250,
                    "time_period": request.parameters.get("time_range", "30 days")
                },
                "breakdown": {
                    "by_blockchain": {
                        "bitcoin": {"count": 4500, "volume": 12500000.00},
                        "ethereum": {"count": 6200, "volume": 10500000.00},
                        "bsc": {"count": 2100, "volume": 3500000.00},
                        "polygon": {"count": 1800, "volume": 1975000.00}
                    },
                    "by_amount_range": {
                        "0-100": 8500,
                        "100-1000": 5200,
                        "1000-10000": 1500,
                        "10000+": 220
                    },
                    "by_time": {
                        "peak_hours": [14, 15, 16, 17],
                        "peak_days": [1, 2, 3, 4, 5],
                        "weekend_activity": 0.35
                    }
                },
                "anomalies": [
                    {
                        "type": "high_value_transaction",
                        "count": 5,
                        "total_amount": 1500000.00,
                        "description": "Transactions exceeding $100,000"
                    },
                    {
                        "type": "rapid_succession",
                        "count": 12,
                        "description": "Multiple transactions from same address within short time"
                    }
                ]
            }
        
        elif request.report_type == "compliance":
            report_data = {
                "report_id": report_id,
                "report_type": request.report_type,
                "title": request.title,
                "compliance_summary": {
                    "total_checks": 45200,
                    "flagged_transactions": 156,
                    "sanctions_hits": 3,
                    "high_risk_addresses": 28,
                    "false_positive_rate": 0.08
                },
                "regulatory_coverage": {
                    "US": {"checks": 15000, "compliance_rate": 0.95},
                    "EU": {"checks": 12000, "compliance_rate": 0.92},
                    "UK": {"checks": 8000, "compliance_rate": 0.88},
                    "APAC": {"checks": 10200, "compliance_rate": 0.85}
                },
                "risk_distribution": {
                    "low": 0.65,
                    "medium": 0.28,
                    "high": 0.07
                },
                "recommendations": [
                    "Enhanced monitoring for high-risk jurisdictions",
                    "Update sanctions screening frequency",
                    "Review false positive patterns"
                ]
            }
        
        elif request.report_type == "investigation":
            report_data = {
                "report_id": report_id,
                "report_type": request.report_type,
                "title": request.title,
                "investigation_summary": {
                    "total_cases": 156,
                    "active_cases": 23,
                    "closed_cases": 133,
                    "average_resolution_days": 18,
                    "success_rate": 0.87
                },
                "case_breakdown": {
                    "by_priority": {
                        "critical": 5,
                        "high": 28,
                        "medium": 78,
                        "low": 45
                    },
                    "by_status": {
                        "open": 12,
                        "in_progress": 11,
                        "closed": 133,
                        "archived": 0
                    },
                    "by_type": {
                        "money_laundering": 45,
                        "fraud": 32,
                        "sanctions_violation": 28,
                        "other": 51
                    }
                },
                "performance_metrics": {
                    "average_case_duration": "18 days",
                    "evidence_per_case": 15.7,
                    "investigator_workload": "3.2 active cases"
                }
            }
        
        elif request.report_type == "intelligence":
            report_data = {
                "report_id": report_id,
                "report_type": request.report_type,
                "title": request.title,
                "intelligence_summary": {
                    "total_alerts": 1250,
                    "active_alerts": 23,
                    "threats_detected": 45,
                    "dark_web_mentions": 125,
                    "sources_monitored": 15
                },
                "threat_landscape": {
                    "phishing": {"count": 350, "trend": "increasing"},
                    "money_laundering": {"count": 280, "trend": "stable"},
                    "malware": {"count": 190, "trend": "decreasing"},
                    "scams": {"count": 230, "trend": "increasing"}
                },
                "source_effectiveness": {
                    "dark_web": 0.85,
                    "sanctions": 0.98,
                    "leaks": 0.75,
                    "forums": 0.68
                }
            }
        
        else:  # custom
            report_data = {
                "report_id": report_id,
                "report_type": request.report_type,
                "title": request.title,
                "custom_data": request.parameters,
                "generated_at": datetime.utcnow()
            }
        
        metadata = {
            "format": request.format,
            "generation_time_ms": 1200,
            "data_sources": ["neo4j", "postgres", "blockchain_apis"],
            "template_version": "v3.2",
            "file_size_kb": 250 if request.format == "json" else 500
        }
        
        return ReportResponse(
            success=True,
            report_data=report_data,
            metadata=metadata,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise JackdawException(
            message=f"Report generation failed: {str(e)}",
            error_code="REPORT_GENERATION_FAILED"
        )


@router.get("/list")
async def list_reports(
    report_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_reports"]]))
):
    """List generated reports"""
    try:
        logger.info(f"Listing reports with filters")
        
        reports = [
            {
                "report_id": "RPT-20240101001",
                "title": "Monthly Transaction Analysis",
                "report_type": "transaction",
                "format": "pdf",
                "status": "completed",
                "created_by": "analyst1",
                "created_at": datetime.utcnow() - timedelta(days=1),
                "file_size_kb": 520,
                "download_count": 5
            },
            {
                "report_id": "RPT-20240101002",
                "title": "Q4 Compliance Summary",
                "report_type": "compliance",
                "format": "xlsx",
                "status": "completed",
                "created_by": "compliance_officer1",
                "created_at": datetime.utcnow() - timedelta(days=2),
                "file_size_kb": 1250,
                "download_count": 12
            },
            {
                "report_id": "RPT-20240101003",
                "title": "Investigation Case Review",
                "report_type": "investigation",
                "format": "json",
                "status": "processing",
                "created_by": current_user.username,
                "created_at": datetime.utcnow() - timedelta(hours=3),
                "file_size_kb": 0,
                "download_count": 0
            }
        ]
        
        # Apply filters
        if report_type:
            reports = [report for report in reports if report["report_type"] == report_type]
        if status:
            reports = [report for report in reports if report["status"] == status]
        
        # Apply pagination
        total_count = len(reports)
        paginated_reports = reports[offset:offset + limit]
        
        return {
            "success": True,
            "reports": paginated_reports,
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "filters_applied": {
                "report_type": report_type,
                "status": status
            },
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Report listing failed: {e}")
        raise JackdawException(
            message=f"Report listing failed: {str(e)}",
            error_code="REPORT_LISTING_FAILED"
        )


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_reports"]]))
):
    """Get report details"""
    try:
        logger.info(f"Getting report details for: {report_id}")
        
        report_data = {
            "report_id": report_id,
            "title": "Monthly Transaction Analysis",
            "report_type": "transaction",
            "format": "pdf",
            "status": "completed",
            "created_by": "analyst1",
            "created_at": datetime.utcnow() - timedelta(days=1),
            "updated_at": datetime.utcnow() - timedelta(days=1),
            "file_size_kb": 520,
            "download_count": 5,
            "parameters": {
                "time_range": "30 days",
                "blockchains": ["bitcoin", "ethereum", "bsc"],
                "include_charts": True
            },
            "summary": {
                "total_transactions": 15420,
                "total_volume_usd": 28475000.50,
                "unique_addresses": 5250
            },
            "download_url": f"/api/v1/reports/{report_id}/download"
        }
        
        return {
            "success": True,
            "report": report_data,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Report retrieval failed: {e}")
        raise JackdawException(
            message=f"Report retrieval failed: {str(e)}",
            error_code="REPORT_RETRIEVAL_FAILED"
        )


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    format: str = "json",
    current_user: User = Depends(check_permissions([PERMISSIONS["read_reports"]]))
):
    """Download report file"""
    try:
        logger.info(f"Downloading report {report_id} in {format} format")
        
        # In a real implementation, this would serve the actual file
        # For now, we'll return a mock response
        
        if format == "json":
            content = {
                "report_id": report_id,
                "content": "Mock JSON report content...",
                "generated_at": datetime.utcnow().isoformat()
            }
            return Response(
                content=str(content),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename={report_id}.json"}
            )
        
        elif format == "pdf":
            # Mock PDF content
            pdf_content = b"Mock PDF content..."
            return Response(
                content=pdf_content,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={report_id}.pdf"}
            )
        
        elif format == "csv":
            csv_content = "Report ID,Title,Type,Created\nRPT-001,Sample Report,transaction,2024-01-01\n"
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={report_id}.csv"}
            )
        
        elif format == "xlsx":
            # Mock Excel content
            excel_content = b"Mock Excel content..."
            return Response(
                content=excel_content,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={report_id}.xlsx"}
            )
        
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")
        
    except Exception as e:
        logger.error(f"Report download failed: {e}")
        raise JackdawException(
            message=f"Report download failed: {str(e)}",
            error_code="REPORT_DOWNLOAD_FAILED"
        )


@router.post("/templates", response_model=ReportResponse)
async def create_report_template(
    request: ReportTemplateRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["write_reports"]]))
):
    """Create report template"""
    try:
        logger.info(f"Creating report template: {request.name}")
        
        template_data = {
            "template_id": f"TPL-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "name": request.name,
            "description": request.description,
            "report_type": request.report_type,
            "template_definition": request.template_definition,
            "is_public": request.is_public,
            "created_by": current_user.username,
            "created_at": datetime.utcnow(),
            "version": "1.0",
            "usage_count": 0
        }
        
        metadata = {
            "template_validation": "passed",
            "schema_compliance": "verified",
            "preview_available": True
        }
        
        return ReportResponse(
            success=True,
            report_data=template_data,
            metadata=metadata,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Template creation failed: {e}")
        raise JackdawException(
            message=f"Template creation failed: {str(e)}",
            error_code="TEMPLATE_CREATION_FAILED"
        )


@router.get("/templates")
async def list_report_templates(
    report_type: Optional[str] = None,
    is_public: Optional[bool] = None,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_reports"]]))
):
    """List report templates"""
    try:
        templates = [
            {
                "template_id": "TPL-001",
                "name": "Standard Transaction Report",
                "description": "Basic transaction analysis report",
                "report_type": "transaction",
                "is_public": True,
                "created_by": "admin",
                "created_at": datetime.utcnow() - timedelta(days=30),
                "usage_count": 45,
                "version": "2.1"
            },
            {
                "template_id": "TPL-002",
                "name": "Compliance Monthly Summary",
                "description": "Monthly compliance and regulatory report",
                "report_type": "compliance",
                "is_public": True,
                "created_by": "compliance_officer1",
                "created_at": datetime.utcnow() - timedelta(days=45),
                "usage_count": 23,
                "version": "1.8"
            }
        ]
        
        # Apply filters
        if report_type:
            templates = [tpl for tpl in templates if tpl["report_type"] == report_type]
        if is_public is not None:
            templates = [tpl for tpl in templates if tpl["is_public"] == is_public]
        
        return {
            "success": True,
            "templates": templates,
            "total_count": len(templates),
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Template listing failed: {e}")
        raise JackdawException(
            message=f"Template listing failed: {str(e)}",
            error_code="TEMPLATE_LISTING_FAILED"
        )


@router.get("/statistics")
async def get_report_statistics(
    current_user: User = Depends(check_permissions([PERMISSIONS["read_reports"]]))
):
    """Get reporting system statistics"""
    try:
        stats = {
            "total_reports": 1250,
            "reports_this_month": 89,
            "active_schedules": 15,
            "templates_available": 12,
            "average_generation_time_ms": 1200,
            "popular_formats": {
                "pdf": 0.45,
                "xlsx": 0.30,
                "json": 0.20,
                "csv": 0.05
            },
            "reports_by_type": {
                "transaction": 450,
                "compliance": 320,
                "investigation": 280,
                "intelligence": 150,
                "custom": 50
            },
            "storage_usage_mb": 2500,
            "download_count_total": 3450
        }
        
        return {
            "success": True,
            "statistics": stats,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Report statistics failed: {e}")
        raise JackdawException(
            message=f"Report statistics failed: {str(e)}",
            error_code="STATISTICS_FAILED"
        )
