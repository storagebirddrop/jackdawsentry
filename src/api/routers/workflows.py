"""
Compliance Workflow Automation API Router

Endpoints for managing compliance workflows including:
- Workflow listing and details
- Workflow triggering and execution
- Workflow enable/disable controls
- Scheduler management
"""

import logging
from datetime import datetime
from datetime import timezone
from functools import lru_cache
from typing import Any
from typing import Dict
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from src.api.auth import User
from src.api.auth import check_permissions
from src.api.auth import get_current_user
from src.automation.compliance_workflow import ComplianceWorkflowEngine
from src.automation.compliance_workflow import WorkflowStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@lru_cache(maxsize=1)
def get_workflow_engine() -> ComplianceWorkflowEngine:
    """Dependency provider for ComplianceWorkflowEngine."""
    return ComplianceWorkflowEngine()


@router.get("/")
async def list_workflows(
    workflow_engine: ComplianceWorkflowEngine = Depends(get_workflow_engine),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"])),
):
    """List all workflows"""
    try:
        status = await workflow_engine.get_workflow_status()
        return {"success": True, **status}
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_workflow_statistics(
    workflow_engine: ComplianceWorkflowEngine = Depends(get_workflow_engine),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"])),
):
    """Get workflow statistics"""
    try:
        status = await workflow_engine.get_workflow_status()
        snapshot = list(workflow_engine.executions.values())
        completed = [e for e in snapshot if e.status == WorkflowStatus.COMPLETED]
        failed = [e for e in snapshot if e.status == WorkflowStatus.FAILED]
        return {
            "success": True,
            "statistics": {
                "total_workflows": status.get("total_workflows", 0),
                "enabled_workflows": status.get("enabled_workflows", 0),
                "total_executions": len(snapshot),
                "completed_executions": len(completed),
                "failed_executions": len(failed),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Failed to get workflow statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workflow_id}")
async def get_workflow_details(
    workflow_id: str,
    workflow_engine: ComplianceWorkflowEngine = Depends(get_workflow_engine),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"])),
):
    """Get workflow details"""
    try:
        status = await workflow_engine.get_workflow_status(workflow_id)
        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])
        return {"success": True, **status}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{workflow_id}/trigger")
async def trigger_workflow(
    workflow_id: str,
    trigger_data: Dict[str, Any] = None,
    workflow_engine: ComplianceWorkflowEngine = Depends(get_workflow_engine),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"])),
):
    """Trigger a workflow"""
    try:
        execution = await workflow_engine.trigger_workflow(
            workflow_id=workflow_id,
            trigger_data=trigger_data or {},
            triggered_by=current_user.username,
        )
        return {
            "success": True,
            "execution_id": execution.execution_id,
            "workflow_id": execution.workflow_id,
            "status": execution.status.value,
            "started_at": (
                execution.started_at.isoformat() if execution.started_at else None
            ),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{workflow_id}/enable")
async def enable_workflow(
    workflow_id: str,
    workflow_engine: ComplianceWorkflowEngine = Depends(get_workflow_engine),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["admin:full"])),
):
    """Enable a workflow"""
    try:
        success = await workflow_engine.enable_workflow(workflow_id)
        if not success:
            raise HTTPException(
                status_code=404, detail=f"Workflow {workflow_id} not found"
            )
        return {"success": True, "message": f"Workflow {workflow_id} enabled"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enable workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{workflow_id}/disable")
async def disable_workflow(
    workflow_id: str,
    workflow_engine: ComplianceWorkflowEngine = Depends(get_workflow_engine),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["admin:full"])),
):
    """Disable a workflow"""
    try:
        success = await workflow_engine.disable_workflow(workflow_id)
        if not success:
            raise HTTPException(
                status_code=404, detail=f"Workflow {workflow_id} not found"
            )
        return {"success": True, "message": f"Workflow {workflow_id} disabled"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disable workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def workflow_health_check(
    workflow_engine: ComplianceWorkflowEngine = Depends(get_workflow_engine),
):
    """Workflow service health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "compliance_workflows",
        "workflows_count": len(workflow_engine.workflows),
    }
