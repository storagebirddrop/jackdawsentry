"""
Jackdaw Sentry — Alert Rules Engine (M12)

Stores configurable alert rules in PostgreSQL and evaluates each incoming
transaction against all active rules.  When a rule matches, the engine
publishes a structured alert to a Redis pub/sub channel so all connected
WebSocket clients receive it within milliseconds.

Rule conditions (combinable with AND logic):
  - address_match  : tx sender or receiver equals a watched address
  - value_gte      : native token value >= threshold
  - chain          : only evaluate on a specific blockchain
  - pattern_type   : only fire when a named AML pattern is present (passed in)
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from src.api.database import get_postgres_pool
from src.api.database import get_redis_client

logger = logging.getLogger(__name__)

ALERT_CHANNEL = "jackdaw:alerts"


# ---------------------------------------------------------------------------
# Data models (plain dicts / dataclasses — no ORM needed for speed)
# ---------------------------------------------------------------------------


def _new_rule(
    name: str,
    conditions: Dict[str, Any],
    severity: str = "medium",
    description: str = "",
    created_by: str = "system",
) -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "description": description,
        "conditions": conditions,
        "severity": severity,
        "enabled": True,
        "created_by": created_by,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "trigger_count": 0,
    }


def _new_alert(
    rule: Dict[str, Any], tx: Dict[str, Any], detail: str = ""
) -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "rule_id": rule["id"],
        "rule_name": rule["name"],
        "severity": rule["severity"],
        "detail": detail,
        "transaction_hash": tx.get("hash"),
        "blockchain": tx.get("blockchain"),
        "from_address": tx.get("from"),
        "to_address": tx.get("to"),
        "value": tx.get("value"),
        "fired_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# PostgreSQL helpers
# ---------------------------------------------------------------------------

_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS alert_rules (
    id          UUID PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    conditions  JSONB NOT NULL DEFAULT '{}',
    severity    TEXT NOT NULL DEFAULT 'medium',
    enabled     BOOLEAN NOT NULL DEFAULT TRUE,
    created_by  TEXT NOT NULL DEFAULT 'system',
    trigger_count BIGINT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alert_events (
    id              UUID PRIMARY KEY,
    rule_id         UUID REFERENCES alert_rules(id) ON DELETE CASCADE,
    rule_name       TEXT,
    severity        TEXT,
    detail          TEXT,
    transaction_hash TEXT,
    blockchain      TEXT,
    from_address    TEXT,
    to_address      TEXT,
    value           NUMERIC,
    fired_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_events_fired_at ON alert_events (fired_at DESC);
CREATE INDEX IF NOT EXISTS idx_alert_rules_enabled ON alert_rules (enabled) WHERE enabled = TRUE;
"""


async def ensure_tables() -> None:
    """Create alert_rules and alert_events tables if they don't exist."""
    pool = get_postgres_pool()
    async with pool.acquire() as conn:
        await conn.execute(_CREATE_TABLES_SQL)


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------


async def create_rule(
    name: str,
    conditions: Dict[str, Any],
    severity: str = "medium",
    description: str = "",
    created_by: str = "system",
) -> Dict[str, Any]:
    """Persist a new alert rule and return it."""
    rule = _new_rule(name, conditions, severity, description, created_by)
    pool = get_postgres_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO alert_rules (id, name, description, conditions, severity, enabled, created_by)
            VALUES ($1, $2, $3, $4, $5, TRUE, $6)
            """,
            uuid.UUID(rule["id"]),
            rule["name"],
            rule["description"],
            json.dumps(rule["conditions"]),
            rule["severity"],
            rule["created_by"],
        )
    return rule


async def list_rules(enabled_only: bool = False) -> List[Dict[str, Any]]:
    """Return all alert rules (optionally only enabled ones)."""
    pool = get_postgres_pool()
    where = "WHERE enabled = TRUE" if enabled_only else ""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT * FROM alert_rules {where} ORDER BY created_at DESC"
        )
    return [_row_to_rule(r) for r in rows]


async def get_rule(rule_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single rule by id."""
    pool = get_postgres_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM alert_rules WHERE id = $1", uuid.UUID(rule_id)
        )
    return _row_to_rule(row) if row else None


async def update_rule(rule_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Update mutable fields on a rule."""
    pool = get_postgres_pool()
    allowed = {"name", "description", "conditions", "severity", "enabled"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return await get_rule(rule_id)

    set_parts = []
    values = []
    for i, (k, v) in enumerate(updates.items(), start=1):
        if k == "conditions":
            v = json.dumps(v)
        set_parts.append(f"{k} = ${i}")
        values.append(v)

    values.append(uuid.UUID(rule_id))
    set_parts.append(f"updated_at = NOW()")
    sql = f"UPDATE alert_rules SET {', '.join(set_parts)} WHERE id = ${len(values)} RETURNING *"

    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, *values)
    return _row_to_rule(row) if row else None


async def delete_rule(rule_id: str) -> bool:
    """Delete a rule. Returns True if a row was deleted."""
    pool = get_postgres_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM alert_rules WHERE id = $1", uuid.UUID(rule_id)
        )
    return result.endswith("1")


def _row_to_rule(row) -> Dict[str, Any]:
    d = dict(row)
    d["id"] = str(d["id"])
    d["rule_id"] = d.get("rule_id") and str(d["rule_id"])
    if isinstance(d.get("conditions"), str):
        d["conditions"] = json.loads(d["conditions"])
    for ts_field in ("created_at", "updated_at", "fired_at"):
        if d.get(ts_field) and hasattr(d[ts_field], "isoformat"):
            d[ts_field] = d[ts_field].isoformat()
    return d


# ---------------------------------------------------------------------------
# Rule evaluation
# ---------------------------------------------------------------------------


def _matches(
    rule: Dict[str, Any], tx: Dict[str, Any], patterns: List[str] = None
) -> bool:
    """Return True if *tx* satisfies all conditions in *rule*."""
    cond = rule.get("conditions", {})

    # Chain filter
    chain = cond.get("chain")
    if chain and tx.get("blockchain", "").lower() != chain.lower():
        return False

    # Address watch
    watched = cond.get("address_match")
    if watched:
        watched_lower = watched.lower()
        if (
            tx.get("from", "").lower() != watched_lower
            and tx.get("to", "").lower() != watched_lower
        ):
            return False

    # Value threshold
    min_val = cond.get("value_gte")
    if min_val is not None:
        try:
            if float(tx.get("value", 0) or 0) < float(min_val):
                return False
        except (TypeError, ValueError):
            return False

    # Pattern type match
    required_pattern = cond.get("pattern_type")
    if required_pattern:
        patterns = patterns or []
        if required_pattern not in patterns:
            return False

    return True


async def evaluate_transaction(
    tx: Dict[str, Any], patterns: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Evaluate *tx* against all enabled rules.

    Returns a list of alert dicts for each rule that fired.
    Each alert is also persisted to alert_events and published to Redis.
    """
    rules = await list_rules(enabled_only=True)
    fired: List[Dict[str, Any]] = []

    for rule in rules:
        if not _matches(rule, tx, patterns):
            continue

        detail = f"Rule '{rule['name']}' matched tx {tx.get('hash', 'unknown')}"
        alert = _new_alert(rule, tx, detail)
        fired.append(alert)

        # Persist alert event
        try:
            pool = get_postgres_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO alert_events
                        (id, rule_id, rule_name, severity, detail,
                         transaction_hash, blockchain, from_address, to_address, value, fired_at)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,NOW())
                    """,
                    uuid.UUID(alert["id"]),
                    uuid.UUID(rule["id"]),
                    alert["rule_name"],
                    alert["severity"],
                    alert["detail"],
                    alert["transaction_hash"],
                    alert["blockchain"],
                    alert["from_address"],
                    alert["to_address"],
                    float(alert["value"]) if alert["value"] is not None else None,
                )
                await conn.execute(
                    "UPDATE alert_rules SET trigger_count = trigger_count + 1, updated_at = NOW() WHERE id = $1",
                    uuid.UUID(rule["id"]),
                )
        except Exception as exc:
            logger.error(f"Failed to persist alert: {exc}")

        # Publish to Redis pub/sub
        try:
            redis = get_redis_client()
            await redis.publish(ALERT_CHANNEL, json.dumps(alert))
        except Exception as exc:
            logger.error(f"Failed to publish alert to Redis: {exc}")

    return fired


# ---------------------------------------------------------------------------
# Recent alerts query
# ---------------------------------------------------------------------------


async def get_recent_alerts(
    limit: int = 50, severity: str = None
) -> List[Dict[str, Any]]:
    """Return recent alert events from PostgreSQL."""
    pool = get_postgres_pool()
    where = "WHERE severity = $2" if severity else ""
    params = [limit, severity] if severity else [limit]
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT * FROM alert_events {where} ORDER BY fired_at DESC LIMIT $1",
            *params,
        )
    return [_row_to_rule(r) for r in rows]
