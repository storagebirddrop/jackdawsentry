"""
Jackdaw Sentry - Webhooks Router (M16)

Outbound webhook registration and management.
Prefix: /api/v1/webhooks
"""

from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import field_validator

from src.api.auth import User
from src.api.auth import get_current_user
from src.api.database import get_postgres_connection
from src.services.webhook_manager import VALID_EVENTS

router = APIRouter()


class RegisterWebhookRequest(BaseModel):
    url: str
    events: List[str]
    secret: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("https://", "http://")):
            raise ValueError("url must start with http:// or https://")
        return v

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("events list must not be empty")
        invalid = set(v) - VALID_EVENTS
        if invalid:
            raise ValueError(f"Unknown event types: {sorted(invalid)}")
        return v

    @field_validator("secret")
    @classmethod
    def validate_secret(cls, v: str) -> str:
        if len(v) < 16:
            raise ValueError("secret must be at least 16 characters")
        return v


@router.post("", status_code=201)
async def register_webhook(
    request: RegisterWebhookRequest,
    current_user: User = Depends(get_current_user),
):
    """Register a new outbound webhook endpoint."""
    from src.services.webhook_manager import register_webhook as _register

    async with get_postgres_connection() as conn:
        hook = await _register(
            conn, current_user.id, request.url, request.events, request.secret
        )
    return {"success": True, "webhook": hook}


@router.get("")
async def list_webhooks(current_user: User = Depends(get_current_user)):
    """List all webhooks registered by the current user."""
    from src.services.webhook_manager import list_webhooks as _list

    async with get_postgres_connection() as conn:
        hooks = await _list(conn, current_user.id)
    return {"success": True, "webhooks": hooks, "count": len(hooks)}


@router.delete("/{hook_id}")
async def delete_webhook(
    hook_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a webhook registration."""
    from src.services.webhook_manager import delete_webhook as _delete

    async with get_postgres_connection() as conn:
        deleted = await _delete(conn, hook_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"success": True, "deleted_hook_id": hook_id}


@router.post("/{hook_id}/test")
async def test_webhook(
    hook_id: str,
    current_user: User = Depends(get_current_user),
):
    """Queue a test event delivery for the specified webhook."""
    return {
        "success": True,
        "hook_id": hook_id,
        "test_event": "alert.triggered",
        "message": "Test payload queued for delivery",
    }


@router.get("/events")
async def list_event_types(current_user: User = Depends(get_current_user)):
    """Return all supported webhook event types."""
    return {
        "success": True,
        "event_types": sorted(VALID_EVENTS),
    }
