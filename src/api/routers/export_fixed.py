"""
Compliance Export API Router

This module provides API endpoints for compliance data export functionality including:
- Export request creation and management
- Export status tracking
- File download endpoints
- Export history and cleanup
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid
import logging

from src.api.auth import get_current_user, check_permissions
from src.api.models.auth import User
from src.api.models.export import (
    ExportRequestCreate,
    ExportRequestResponse,
    ExportStatusResponse,
    ExportListResponse,
    ExportFilter
)
from src.export.compliance_export import (
    ComplianceExportEngine,
    ExportRequest,
    ExportResult,
    ExportType,
    ExportFormat
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/compliance/export", tags=["export"])
export_engine = ComplianceExportEngine()
background_tasks = BackgroundTasks()


@router.post("/request", response_model=ExportRequestResponse)
async def create_export_request(
    request: ExportRequestCreate,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["read_compliance"]))
):
    """Create a new export request"""
    try:
        # Generate unique export ID
        export_id = str(uuid.uuid4())
        
        # Create export request
        export_request = ExportRequest(
            export_id=export_id,
            export_type=ExportType(request.export_type),
            format=ExportFormat(request.format),
            filters=request.filters or {},
            date_range=request.date_range,
            include_sensitive=request.include_sensitive,
            compression=request.compression,
            metadata={
                "requested_by": current_user.username,
                "requested_at": datetime.utcnow().isoformat(),
                "user_id": current_user.id
            }
        )
        
        # Start export in background
        background_tasks.add_task(
            export_engine.create_export,
            export_request
        )
        
        return ExportRequestResponse(
            success=True,
            export_id=export_id,
            status="pending",
            message="Export request created and processing started"
        )
        
    except Exception as e:
        logger.error(f"Failed to create export request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{export_id}", response_model=ExportStatusResponse)
async def get_export_status(
    export_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["read_compliance"]))
):
    """Get export status"""
    try:
        result = await export_engine.get_export_status(export_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Export not found")
        
        return ExportStatusResponse(
            success=True,
            export_id=result.export_id,
            status=result.status,
            file_path=result.file_path,
            file_size=result.file_size,
            record_count=result.record_count,
            created_at=result.created_at,
            completed_at=result.completed_at,
            error_message=result.error_message,
            metadata=result.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get export status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{export_id}")
async def download_export(
    export_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["read_compliance"]))
):
    """Download export file"""
    try:
        result = await export_engine.get_export_status(export_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Export not found")
        
        if result.status != "completed":
            raise HTTPException(status_code=400, detail="Export not completed")
        
        if not result.file_path or not result.metadata:
            raise HTTPException(status_code=404, detail="Export file not available")
        
        file_path = result.file_path
        
        # Check if file exists
        from pathlib import Path
        if not Path(file_path).exists():
            raise HTTPException(status_code=404, detail="Export file not found")
        
        # Determine media type
        media_type = "application/octet-stream"
        if file_path.endswith('.json'):
            media_type = "application/json"
        elif file_path.endswith('.csv'):
            media_type = "text/csv"
        elif file_path.endswith('.xml'):
            media_type = "application/xml"
        elif file_path.endswith('.xlsx'):
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif file_path.endswith('.pdf'):
            media_type = "application/pdf"
        elif file_path.endswith('.zip'):
            media_type = "application/zip"
        
        # Generate filename
        filename = f"compliance_export_{export_id}"
        if file_path.endswith('.json'):
            filename += ".json"
        elif file_path.endswith('.csv'):
            filename += ".csv"
        elif file_path.endswith('.xml'):
            filename += ".xml"
        elif file_path.endswith('.xlsx'):
            filename += ".xlsx"
        elif file_path.endswith('.pdf'):
            filename += ".pdf"
        elif file_path.endswith('.zip'):
            filename += ".zip"
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download export: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=ExportListResponse)
async def list_exports(
    limit: int = 50,
    offset: int = 0,
    export_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["read_compliance"]))
:
    """List export requests"""
    try:
        # Get all exports
        all_exports = await export_engine.list_exports(limit=1000)
        
        # Apply filters
        filtered_exports = all_exports
        if export_type:
            filtered_exports = [
                e for e in filtered_exports 
                if e.metadata and e.metadata.get("export_type") == export_type
            ]
        
        if status:
            filtered_exports = [e for e in filtered_exports if e.status == status]
        
        # Apply pagination
        total_count = len(filtered_exports)
        paginated_exports = filtered_exports[offset:offset + limit]
        
        # Convert to response format
        export_list = []
        for result in paginated_exports:
            export_list.append({
                "export_id": result.export_id,
                "export_type": result.metadata.get("export_type") if result.metadata else None,
                "format": result.metadata.get("format") if result.metadata else None,
                "status": result.status,
                "file_size": result.file_size,
                "record_count": result.record_count,
                "created_at": result.created_at,
                "completed_at": result.completed_at,
                "requested_by": result.metadata.get("requested_by") if result.metadata else None
            })
        
        return ExportListResponse(
            success=True,
            exports=export_list,
            total_count=total_count,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"Failed to list exports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{export_id}")
async def delete_export(
    export_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["admin_compliance"]))
:
    """Delete export"""
    try:
        success = await export_engine.delete_export(export_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Export not found")
        
        return {"success": True, "message": f"Export {export_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete export: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_old_exports(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["admin_compliance"]))
:
    """Clean up old exports"""
    try:
        if days < 1:
            raise HTTPException(status_code=400, detail="Days must be at least 1")
        
        deleted_count = await export_engine.cleanup_old_exports(days)
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Cleaned up {deleted_count} exports older than {days} days"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cleanup exports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def get_export_templates(
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["read_compliance"]))
:
    """Get available export templates"""
    try:
        templates = {
            "regulatory_reports": {
                "name": "Regulatory Reports",
                "description": "Export regulatory reports with filtering options",
                "export_type": "regulatory_reports",
                "available_formats": ["json", "csv", "excel", "pdf"],
                "filters": {
                    "jurisdiction": ["usa_fincen", "uk_fca", "eu"],
                    "report_type": ["sar", "ctr", "str"],
                    "status": ["draft", "submitted", "acknowledged", "rejected"]
                }
            },
            "case_data": {
                "name": "Case Data",
                "description": "Export compliance cases with evidence",
                "export_type": "case_data",
                "available_formats": ["json", "csv", "excel", "pdf"],
                "filters": {
                    "case_type": ["suspicious_activity", "sanctions_screening", "investigation"],
                    "status": ["open", "in_progress", "under_review", "escalated", "closed"],
                    "priority": ["low", "medium", "high", "critical"]
                }
            },
            "risk_assessments": {
                "name": "Risk Assessments",
                "description": "Export risk assessment data and factors",
                "export_type": "risk_assessments",
                "available_formats": ["json", "csv", "excel", "pdf"],
                "filters": {
                    "entity_type": ["address", "transaction", "wallet"],
                    "risk_level": ["low", "medium", "high", "critical", "severe"],
                    "status": ["pending", "in_progress", "completed", "failed"]
                }
            },
            "audit_trail": {
                "name": "Audit Trail",
                "description": "Export audit events and compliance logs",
                "export_type": "audit_trail",
                "available_formats": ["json", "csv", "xml", "pdf"],
                "filters": {
                    "event_type": ["user_action", "compliance_check", "security_breach"],
                    "severity": ["info", "warning", "error", "critical"],
                    "resource_type": ["case", "report", "assessment", "evidence"]
                }
            },
            "compliance_summary": {
                "name": "Compliance Summary",
                "description": "Export comprehensive compliance summary statistics",
                "export_type": "compliance_summary",
                "available_formats": ["json", "pdf"],
                "filters": {}
            }
        }
        
        return {
            "success": True,
            "templates": templates
        }
        
    except Exception as e:
        logger.error(f"Failed to get export templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_export_statistics(
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["read_compliance"]))
:
    """Get export statistics"""
    try:
        # Get all exports
        all_exports = await export_engine.list_exports(limit=10000)
        
        # Calculate statistics
        total_exports = len(all_exports)
        completed_exports = len([e for e in all_exports if e.status == "completed"])
        failed_exports = len([e for e in all_exports if e.status == "failed"])
        pending_exports = len([e for e in all_exports if e.status == "pending"])
        
        # Calculate total file size
        total_size = sum(e.file_size or 0 for e in all_exports)
        
        # Calculate by export type
        type_stats = {}
        for export in all_exports:
            if export.metadata and "export_type" in export.metadata:
                export_type = export.metadata["export_type"]
                if export_type not in type_stats:
                    type_stats[export_type] = {"total": 0, "completed": 0, "failed": 0}
                type_stats[export_type]["total"] += 1
                if export.status == "completed":
                    type_stats[export_type]["completed"] += 1
                elif export.status == "failed":
                    type_stats[export_type]["failed"] += 1
        
        # Calculate by format
        format_stats = {}
        for export in all_exports:
            if export.metadata and "format" in export.metadata:
                export_format = export.metadata["format"]
                if export_format not in format_stats:
                    format_stats[export_format] = 0
                format_stats[export_format] += 1
        
        # Recent exports (last 7 days)
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        recent_exports = len([e for e in all_exports if e.created_at > cutoff_date])
        
        return {
            "success": True,
            "statistics": {
                "total_exports": total_exports,
                "completed_exports": completed_exports,
                "failed_exports": failed_exports,
                "pending_exports": pending_exports,
                "total_file_size": total_size,
                "recent_exports_7_days": recent_exports,
                "by_export_type": type_stats,
                "by_format": format_stats
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get export statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def export_health_check():
    """Export service health check"""
    try:
        # Check if export engine is working
        # This is a simple health check - in production you might check
        # database connectivity, file system access, etc.
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "compliance_export",
            "version": "1.5.0"
        }
        
    except Exception as e:
        logger.error(f"Export health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
