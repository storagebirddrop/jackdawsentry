"""
Compliance Monitoring API Router

Endpoints for compliance monitoring and alerting including:
- Metrics summary and collection
- Alert management and resolution
- Health check status
- Prometheus metrics export
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from typing import Optional
from datetime import datetime, timezone
import logging

from src.api.auth import get_current_user, check_permissions, User
from src.monitoring.compliance_monitoring import (
    ComplianceMonitoringEngine,
    AlertSeverity,
    AlertStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter()
monitoring_engine = ComplianceMonitoringEngine()


@router.get("/metrics")
async def get_metrics_summary(
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"]))
):
    """Get metrics summary"""
    try:
        summary = await monitoring_engine.get_metrics_summary()
        return {"success": True, **summary}
    except Exception as e:
        logger.error(f"Failed to get metrics summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_alerts(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"]))
):
    """Get compliance alerts"""
    try:
        sev = AlertSeverity(severity) if severity else None
        st = AlertStatus(status) if status else None
        alerts = await monitoring_engine.get_alerts(severity=sev, status=st)
        return {
            "success": True,
            "alerts": [
                {
                    "alert_id": a.alert_id,
                    "name": a.name,
                    "description": a.description,
                    "severity": a.severity.value,
                    "status": a.status.value,
                    "metric_name": a.metric_name,
                    "threshold": a.threshold,
                    "current_value": a.current_value,
                    "timestamp": a.timestamp.isoformat(),
                    "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
                }
                for a in alerts
            ],
            "total": len(alerts),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"]))
):
    """Resolve a compliance alert"""
    try:
        success = await monitoring_engine.resolve_alert(alert_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found or already resolved")
        return {"success": True, "message": f"Alert {alert_id} resolved"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health-checks")
async def get_health_checks(
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"]))
):
    """Get health check results"""
    try:
        checks = await monitoring_engine.get_health_checks()
        return {
            "success": True,
            "health_checks": [
                {
                    "name": c.name,
                    "status": c.status,
                    "response_time_ms": c.response_time_ms,
                    "last_checked": c.last_checked.isoformat() if c.last_checked else None,
                    "metadata": c.metadata,
                }
                for c in checks
            ],
            "total": len(checks),
        }
    except Exception as e:
        logger.error(f"Failed to get health checks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prometheus", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """Get Prometheus metrics in text format"""
    try:
        metrics_text = await monitoring_engine.get_prometheus_metrics()
        return PlainTextResponse(content=metrics_text, media_type="text/plain; version=0.0.4")
    except Exception as e:
        logger.error(f"Failed to get Prometheus metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_monitoring_statistics(
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"]))
):
    """Get monitoring statistics"""
    try:
        summary = await monitoring_engine.get_metrics_summary()
        alerts = await monitoring_engine.get_alerts()
        firing = [a for a in alerts if a.status == AlertStatus.FIRING]
        return {
            "success": True,
            "statistics": {
                "metrics_enabled": monitoring_engine.metrics_enabled,
                "alerting_enabled": monitoring_engine.alerting_enabled,
                "total_metrics": summary.get("total_metrics", 0),
                "total_alerts": len(alerts),
                "firing_alerts": len(firing),
                "alert_rules_count": len(monitoring_engine.alert_rules),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Failed to get monitoring statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def monitoring_health_check():
    """Monitoring service health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "compliance_monitoring",
        "metrics_enabled": monitoring_engine.metrics_enabled,
        "alerting_enabled": monitoring_engine.alerting_enabled,
    }
