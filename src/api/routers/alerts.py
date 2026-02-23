"""
Jackdaw Sentry — Alerts API Router (M12)

REST endpoints for alert rule CRUD + recent alerts query.
WebSocket endpoint for live alert streaming via Redis pub/sub.

Endpoints:
  GET    /api/v1/alerts/rules               list all rules
  POST   /api/v1/alerts/rules               create rule
  GET    /api/v1/alerts/rules/{id}          get rule
  PATCH  /api/v1/alerts/rules/{id}          update rule
  DELETE /api/v1/alerts/rules/{id}          delete rule
  GET    /api/v1/alerts/recent              recent alert events
  WS     /api/v1/alerts/ws                  live alert stream
"""

import asyncio
import json
import logging
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from pydantic import BaseModel
from pydantic import field_validator

from src.api.auth import PERMISSIONS
from src.api.auth import User
from src.api.auth import check_permissions
from src.api.auth import require_admin
from src.api.database import get_redis_client
from src.monitoring.alert_rules import ALERT_CHANNEL
from src.monitoring.alert_rules import create_rule
from src.monitoring.alert_rules import delete_rule
from src.monitoring.alert_rules import get_recent_alerts
from src.monitoring.alert_rules import get_rule
from src.monitoring.alert_rules import list_rules
from src.monitoring.alert_rules import update_rule

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class CreateRuleRequest(BaseModel):
    name: str
    description: str = ""
    conditions: Dict[str, Any]
    severity: str = "medium"

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        allowed = {"low", "medium", "high", "critical"}
        if v not in allowed:
            raise ValueError(f"severity must be one of {allowed}")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be empty")
        return v


class UpdateRuleRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    severity: Optional[str] = None
    enabled: Optional[bool] = None


# ---------------------------------------------------------------------------
# REST — rules CRUD
# ---------------------------------------------------------------------------


@router.get("/rules")
async def list_alert_rules(
    enabled_only: bool = Query(False),
    current_user: User = Depends(check_permissions([PERMISSIONS["read_analysis"]])),
):
    rules = await list_rules(enabled_only=enabled_only)
    return {"success": True, "rules": rules, "count": len(rules)}


@router.post("/rules", status_code=201)
async def create_alert_rule(
    body: CreateRuleRequest,
    current_user: User = Depends(require_admin),
):
    rule = await create_rule(
        name=body.name,
        conditions=body.conditions,
        severity=body.severity,
        description=body.description,
        created_by=current_user.username,
    )
    return {"success": True, "rule": rule}


@router.get("/rules/{rule_id}")
async def get_alert_rule(
    rule_id: str,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_analysis"]])),
):
    rule = await get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return {"success": True, "rule": rule}


@router.patch("/rules/{rule_id}")
async def update_alert_rule(
    rule_id: str,
    body: UpdateRuleRequest,
    current_user: User = Depends(require_admin),
):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    rule = await update_rule(rule_id, **updates)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return {"success": True, "rule": rule}


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_alert_rule(
    rule_id: str,
    current_user: User = Depends(require_admin),
):
    deleted = await delete_rule(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Alert rule not found")


# ---------------------------------------------------------------------------
# REST — recent alerts
# ---------------------------------------------------------------------------


@router.get("/recent")
async def recent_alerts(
    limit: int = Query(50, ge=1, le=500),
    severity: Optional[str] = Query(None),
    current_user: User = Depends(check_permissions([PERMISSIONS["read_analysis"]])),
):
    alerts = await get_recent_alerts(limit=limit, severity=severity)
    return {"success": True, "alerts": alerts, "count": len(alerts)}


# ---------------------------------------------------------------------------
# WebSocket — live alert stream
# ---------------------------------------------------------------------------


@router.websocket("/ws")
async def alert_websocket(websocket: WebSocket):
    """
    WebSocket endpoint — streams alerts in real time via Redis pub/sub.

    Authentication: send a valid JWT as the first text message after connect.
    The server responds {"status": "authenticated"} before streaming begins.

    Each alert message is a JSON string matching the alert_events schema.
    """
    await websocket.accept()

    # --- Lightweight JWT auth over WebSocket ---
    try:
        token_msg = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        token_data = (
            json.loads(token_msg) if token_msg.startswith("{") else {"token": token_msg}
        )
        token = token_data.get("token", token_msg)
        _verify_ws_token(token)
        await websocket.send_text(json.dumps({"status": "authenticated"}))
    except asyncio.TimeoutError:
        await websocket.close(code=4001, reason="Authentication timeout")
        return
    except Exception as exc:
        await websocket.close(code=4003, reason=f"Authentication failed: {exc}")
        return

    # --- Subscribe to Redis pub/sub ---
    redis = get_redis_client()
    pubsub = redis.pubsub()
    await pubsub.subscribe(ALERT_CHANNEL)
    logger.info(f"[alerts/ws] client connected, subscribed to {ALERT_CHANNEL}")

    try:
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if message and message.get("type") == "message":
                await websocket.send_text(message["data"])
            else:
                # Keep-alive ping
                try:
                    await asyncio.wait_for(websocket.receive_text(), timeout=0.05)
                except asyncio.TimeoutError:
                    pass
    except WebSocketDisconnect:
        logger.info("[alerts/ws] client disconnected")
    except Exception as exc:
        logger.warning(f"[alerts/ws] error: {exc}")
    finally:
        await pubsub.unsubscribe(ALERT_CHANNEL)
        await pubsub.close()


def _verify_ws_token(token: str) -> None:
    """Minimal JWT verification for WebSocket auth (reuses existing auth logic)."""
    from src.api.auth import verify_token

    payload = verify_token(token)
    if not payload:
        raise ValueError("Invalid or expired token")
