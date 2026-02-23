"""
Compliance Scheduler API Router

Endpoints for compliance task scheduling including:
- Task listing and status
- Task enable/disable controls
- On-demand task execution
- Scheduler start/stop controls
"""

import logging
import time
from datetime import datetime
from datetime import timezone
from typing import Dict

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from src.api.auth import User
from src.api.auth import check_permissions
from src.api.auth import get_current_user
from src.scheduling.compliance_scheduler import compliance_scheduler

logger = logging.getLogger(__name__)

router = APIRouter()

# Per-task cooldown tracking (task_id -> last successful run monotonic time)
_task_last_run: Dict[str, float] = {}
TASK_COOLDOWN_SECONDS: float = 60.0


@router.get("/tasks")
async def list_tasks(
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"])),
):
    """List all scheduled tasks"""
    try:
        status = compliance_scheduler.get_task_status()
        return {"success": True, **status}
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to list scheduled tasks")


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"])),
):
    """Get status of a specific task"""
    try:
        status = compliance_scheduler.get_task_status(task_id)
        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])
        return {"success": True, **status}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve task status")


@router.post("/tasks/{task_id}/run")
async def run_task_now(
    task_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["admin:full"])),
):
    """Run a task immediately (subject to cooldown)"""
    try:
        # Enforce per-task cooldown
        now = time.monotonic()
        last_run = _task_last_run.get(task_id)
        if last_run is not None:
            elapsed = now - last_run
            if elapsed < TASK_COOLDOWN_SECONDS:
                remaining = int(TASK_COOLDOWN_SECONDS - elapsed) + 1
                raise HTTPException(
                    status_code=429,
                    detail=f"Task {task_id} is in cooldown. Retry in {remaining}s.",
                )

        success = await compliance_scheduler.run_task_now(task_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        _task_last_run[task_id] = time.monotonic()
        return {"success": True, "message": f"Task {task_id} executed"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to run task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to execute task")


@router.put("/tasks/{task_id}/enable")
async def enable_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["admin:full"])),
):
    """Enable a scheduled task"""
    try:
        success = compliance_scheduler.enable_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return {"success": True, "message": f"Task {task_id} enabled"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enable task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to enable task")


@router.put("/tasks/{task_id}/disable")
async def disable_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["admin:full"])),
):
    """Disable a scheduled task"""
    try:
        success = compliance_scheduler.disable_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return {"success": True, "message": f"Task {task_id} disabled"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disable task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to disable task")


@router.post("/start")
async def start_scheduler(
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["admin:full"])),
):
    """Start the compliance scheduler"""
    try:
        compliance_scheduler.start()
        return {
            "success": True,
            "message": "Scheduler started",
            "running": compliance_scheduler.running,
        }
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        raise HTTPException(status_code=500, detail="Failed to start scheduler")


@router.post("/stop")
async def stop_scheduler(
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["admin:full"])),
):
    """Stop the compliance scheduler"""
    try:
        compliance_scheduler.stop()
        return {
            "success": True,
            "message": "Scheduler stopped",
            "running": compliance_scheduler.running,
        }
    except Exception as e:
        logger.error(f"Failed to stop scheduler: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop scheduler")


@router.get("/status")
async def get_scheduler_status(
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"])),
):
    """Get scheduler status"""
    try:
        status = compliance_scheduler.get_task_status()
        return {
            "success": True,
            "running": compliance_scheduler.running,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **status,
        }
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve scheduler status"
        )


@router.get("/health")
async def scheduler_health_check():
    """Scheduler service health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "compliance_scheduler",
        "running": compliance_scheduler.running,
        "tasks_count": len(compliance_scheduler.tasks),
    }
