"""
Compliance Mobile API Router

Endpoints for mobile compliance clients including:
- Lightweight dashboard summaries
- Mobile alert feed
- User settings management
- Push notification dispatch
- Offline data packaging
- Client-server data synchronization
"""

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

from src.api.auth import get_current_user, check_permissions, User
from src.mobile.compliance_mobile import (
    ComplianceMobileEngine,
    NotificationType,
    NotificationPriority,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@lru_cache(maxsize=1)
def get_mobile_engine() -> ComplianceMobileEngine:
    """Dependency provider for ComplianceMobileEngine."""
    return ComplianceMobileEngine()


class MobileSettingsResponse(BaseModel):
    """Pydantic model for mobile settings response."""
    user_id: str
    push_enabled: bool
    alert_notifications: bool
    deadline_notifications: bool
    case_update_notifications: bool
    risk_change_notifications: bool
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    dashboard_widgets: List[str] = []
    offline_data_categories: List[str] = []
    sync_interval_minutes: int
    updated_at: datetime

    class Config:
        orm_mode = True


class NotificationRequest(BaseModel):
    """Pydantic model for notification dispatch requests."""
    user_id: str
    title: str = "Notification"
    body: str = ""
    type: str = "system"
    priority: str = "medium"
    data: Optional[Dict[str, Any]] = None


@router.get("/dashboard")
async def get_mobile_dashboard(
    mobile_engine: ComplianceMobileEngine = Depends(get_mobile_engine),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"]))
):
    """Get mobile-optimised dashboard data"""
    try:
        dashboard = await mobile_engine.get_dashboard(current_user.username)
        return {"success": True, **dashboard}
    except Exception as e:
        logger.error(f"Failed to get mobile dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_mobile_alerts(
    limit: int = 50,
    unread_only: bool = False,
    mobile_engine: ComplianceMobileEngine = Depends(get_mobile_engine),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"]))
):
    """Get mobile alert feed"""
    try:
        alerts = await mobile_engine.get_alerts(
            current_user.username, limit=limit, unread_only=unread_only
        )
        return {"success": True, "alerts": alerts, "total": len(alerts)}
    except Exception as e:
        logger.error(f"Failed to get mobile alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{notification_id}/read")
async def mark_alert_read(
    notification_id: str,
    mobile_engine: ComplianceMobileEngine = Depends(get_mobile_engine),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"]))
):
    """Mark a notification as read"""
    try:
        success = await mobile_engine.mark_notification_read(
            current_user.username, notification_id
        )
        if not success:
            raise HTTPException(status_code=404, detail="Notification not found")
        return {"success": True, "message": f"Notification {notification_id} marked as read"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark notification read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings")
async def get_mobile_settings(
    mobile_engine: ComplianceMobileEngine = Depends(get_mobile_engine),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"]))
):
    """Get mobile settings for current user"""
    try:
        settings = await mobile_engine.get_settings(current_user.username)
        return {
            "success": True,
            "settings": MobileSettingsResponse.from_orm(settings).dict(),
        }
    except Exception as e:
        logger.error(f"Failed to get mobile settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings")
async def update_mobile_settings(
    updates: Dict[str, Any],
    mobile_engine: ComplianceMobileEngine = Depends(get_mobile_engine),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"]))
):
    """Update mobile settings for current user"""
    try:
        settings = await mobile_engine.update_settings(current_user.username, updates)
        return {
            "success": True,
            "message": "Settings updated",
            "updated_at": settings.updated_at.isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to update mobile settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications")
async def send_notification(
    notification_data: NotificationRequest,
    mobile_engine: ComplianceMobileEngine = Depends(get_mobile_engine),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["admin:full"]))
):
    """Send a mobile notification to a user"""
    try:
        notif_type = NotificationType(notification_data.type)
        priority = NotificationPriority(notification_data.priority)

        notification = await mobile_engine.send_notification(
            user_id=notification_data.user_id,
            title=notification_data.title,
            body=notification_data.body,
            notification_type=notif_type,
            priority=priority,
            data=notification_data.data,
        )
        return {
            "success": True,
            "notification_id": notification.notification_id,
            "sent_to": notification_data.user_id,
        }
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid notification data: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/offline-data")
async def get_offline_data(
    categories: Optional[str] = None,
    mobile_engine: ComplianceMobileEngine = Depends(get_mobile_engine),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"]))
):
    """Get packaged data for offline mobile use"""
    try:
        cat_list = categories.split(",") if categories else None
        package = await mobile_engine.get_offline_data(
            current_user.username, categories=cat_list
        )
        return {"success": True, **package}
    except Exception as e:
        logger.error(f"Failed to get offline data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_mobile_data(
    sync_data: Dict[str, Any],
    mobile_engine: ComplianceMobileEngine = Depends(get_mobile_engine),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"]))
):
    """Synchronize data between mobile client and server"""
    try:
        device_id = sync_data.get("device_id", "unknown")
        client_data = sync_data.get("data")

        record = await mobile_engine.sync_data(
            user_id=current_user.username,
            device_id=device_id,
            client_data=client_data,
        )
        return {
            "success": True,
            "sync_id": record.sync_id,
            "status": record.status.value,
            "records_uploaded": record.records_uploaded,
            "records_downloaded": record.records_downloaded,
            "conflicts": record.conflicts,
            "completed_at": record.completed_at.isoformat() if record.completed_at else None,
        }
    except Exception as e:
        logger.error(f"Failed to sync mobile data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def mobile_health_check():
    """Mobile service health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "compliance_mobile",
    }
