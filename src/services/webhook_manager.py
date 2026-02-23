"""
Jackdaw Sentry - Webhook Manager (M16)

Outbound webhook delivery with HMAC-SHA256 payload signing.
"""

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

logger = logging.getLogger(__name__)

VALID_EVENTS = frozenset(
    {
        "alert.triggered",
        "investigation.created",
        "investigation.updated",
        "evidence.added",
        "sanctions.match",
        "risk.high",
    }
)


def sign_payload(payload: str, secret: str) -> str:
    """Return HMAC-SHA256 hex signature for a payload string."""
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


async def dispatch_webhook(
    url: str,
    secret: str,
    event: str,
    data: Dict[str, Any],
    timeout: float = 5.0,
) -> bool:
    """POST a signed JSON payload to url. Returns True on HTTP 2xx."""
    import httpx

    body = json.dumps(
        {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
    )
    sig = sign_payload(body, secret)
    headers = {
        "Content-Type": "application/json",
        "X-JDS-Signature": f"sha256={sig}",
        "X-JDS-Event": event,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, content=body, headers=headers)
            return resp.is_success
    except Exception as exc:
        logger.warning("Webhook delivery failed to %s: %s", url, exc)
        return False


async def register_webhook(
    conn,
    user_id: str,
    url: str,
    events: List[str],
    secret: str,
) -> Dict[str, Any]:
    """Persist a new webhook registration. Returns the created record."""
    hook_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    events_str = ",".join(events)
    await conn.execute(
        """
        INSERT INTO webhooks (hook_id, user_id, url, events, secret, created_at, active)
        VALUES ($1, $2, $3, $4, $5, $6, true)
        """,
        hook_id,
        user_id,
        url,
        events_str,
        secret,
        now,
    )
    return {
        "hook_id": hook_id,
        "url": url,
        "events": events,
        "created_at": now.isoformat(),
        "active": True,
    }


async def list_webhooks(conn, user_id: str) -> List[Dict[str, Any]]:
    """Return all active webhooks for a user."""
    rows = await conn.fetch(
        "SELECT hook_id, url, events, created_at, active FROM webhooks "
        "WHERE user_id = $1 ORDER BY created_at DESC",
        user_id,
    )
    result = []
    for r in rows:
        d = dict(r)
        d["events"] = d["events"].split(",") if d.get("events") else []
        result.append(d)
    return result


async def delete_webhook(conn, hook_id: str, user_id: str) -> bool:
    """Delete a webhook by ID (scoped to user). Returns True if deleted."""
    result = await conn.execute(
        "DELETE FROM webhooks WHERE hook_id = $1 AND user_id = $2",
        hook_id,
        user_id,
    )
    return result != "DELETE 0"
