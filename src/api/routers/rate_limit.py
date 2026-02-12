"""
Compliance Rate Limiting API Router

Endpoints for rate limiting management including:
- Rate limit status per user
- Violation tracking and cleanup
- Rule CRUD operations
- Rate limiting statistics
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import logging

from src.api.auth import get_current_user, check_permissions, User
from src.rate_limiting.compliance_rate_limiting import ComplianceRateLimitingEngine

logger = logging.getLogger(__name__)

router = APIRouter()
rate_limit_engine = ComplianceRateLimitingEngine()


@router.get("/status/{user_id}")
async def get_rate_limit_status(
    user_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"]))
):
    """Get rate limit status for a user"""
    try:
        status = await rate_limit_engine.get_rate_limit_status(user_id=user_id)
        return {"success": True, **status}
    except Exception as e:
        logger.error(f"Failed to get rate limit status for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/violations")
async def get_violations(
    limit: int = 100,
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"]))
):
    """Get rate limit violations"""
    try:
        violations = await rate_limit_engine.get_violations(limit=limit, user_id=user_id)
        return {
            "success": True,
            "violations": [
                {
                    "violation_id": v.violation_id,
                    "rule_id": v.rule_id,
                    "user_id": v.user_id,
                    "ip_address": v.ip_address,
                    "endpoint": v.endpoint,
                    "timestamp": v.timestamp.isoformat(),
                    "action_taken": v.action_taken.value if v.action_taken else None,
                }
                for v in violations
            ],
            "total": len(violations),
        }
    except Exception as e:
        logger.error(f"Failed to get violations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-violations")
async def clear_violations(
    older_than_hours: int = 24,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["admin:full"]))
):
    """Clear old rate limit violations"""
    try:
        cleared = await rate_limit_engine.clear_violations(older_than_hours=older_than_hours)
        return {"success": True, "cleared_count": cleared, "older_than_hours": older_than_hours}
    except Exception as e:
        logger.error(f"Failed to clear violations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_rate_limit_statistics(
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"]))
):
    """Get rate limiting statistics"""
    try:
        stats = await rate_limit_engine.get_rate_limit_statistics()
        return {"success": True, **stats}
    except Exception as e:
        logger.error(f"Failed to get rate limit statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules")
async def create_rule(
    rule_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["admin:full"]))
):
    """Create a rate limit rule"""
    try:
        from src.rate_limiting.compliance_rate_limiting import RateLimitRule, RateLimitType, RateLimitAction
        rule = RateLimitRule(
            rule_id=rule_data["rule_id"],
            name=rule_data["name"],
            rate_limit_type=RateLimitType(rule_data["rate_limit_type"]),
            requests_per_window=rule_data["requests_per_window"],
            window_seconds=rule_data["window_seconds"],
            action=RateLimitAction(rule_data.get("action", "reject")),
            priority=rule_data.get("priority", 0),
            enabled=rule_data.get("enabled", True),
            conditions=rule_data.get("conditions"),
            metadata=rule_data.get("metadata"),
        )
        success = await rate_limit_engine.add_rule(rule)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to create rule")
        return {"success": True, "rule_id": rule.rule_id, "message": "Rule created"}
    except HTTPException:
        raise
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid rule data: {e}")
    except Exception as e:
        logger.error(f"Failed to create rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/rules/{rule_id}")
async def update_rule(
    rule_id: str,
    updates: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["admin:full"]))
):
    """Update a rate limit rule"""
    try:
        success = await rate_limit_engine.update_rule(rule_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
        return {"success": True, "message": f"Rule {rule_id} updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["admin:full"]))
):
    """Delete a rate limit rule"""
    try:
        success = await rate_limit_engine.delete_rule(rule_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
        return {"success": True, "message": f"Rule {rule_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def rate_limit_health_check():
    """Rate limiting service health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "compliance_rate_limiting",
        "rules_count": len(rate_limit_engine.rules),
    }
