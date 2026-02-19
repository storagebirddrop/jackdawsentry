"""
Jackdaw Sentry - Team Workspace Service (M16)

Multi-tenant organization management backed by PostgreSQL.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


async def create_organization(
    conn,
    name: str,
    owner_id: str,
    plan: str = "standard",
) -> Dict[str, Any]:
    """Create a new organization and add the owner as an admin member."""
    org_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await conn.execute(
        """
        INSERT INTO organizations (org_id, name, owner_id, plan, created_at)
        VALUES ($1, $2, $3, $4, $5)
        """,
        org_id, name, owner_id, plan, now,
    )
    await conn.execute(
        """
        INSERT INTO org_members (org_id, user_id, role, joined_at)
        VALUES ($1, $2, 'admin', $3)
        """,
        org_id, owner_id, now,
    )
    return {
        "org_id": org_id,
        "name": name,
        "owner_id": owner_id,
        "plan": plan,
        "created_at": now.isoformat(),
    }


async def get_organization(conn, org_id: str) -> Optional[Dict[str, Any]]:
    """Fetch an organization by ID. Returns None if not found."""
    row = await conn.fetchrow(
        "SELECT org_id, name, owner_id, plan, created_at FROM organizations WHERE org_id = $1",
        org_id,
    )
    return dict(row) if row else None


async def add_member(
    conn,
    org_id: str,
    user_id: str,
    role: str = "member",
) -> Dict[str, Any]:
    """Add or update a user's role in an organization."""
    now = datetime.now(timezone.utc)
    await conn.execute(
        """
        INSERT INTO org_members (org_id, user_id, role, joined_at)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (org_id, user_id) DO UPDATE SET role = EXCLUDED.role
        """,
        org_id, user_id, role, now,
    )
    return {
        "org_id": org_id,
        "user_id": user_id,
        "role": role,
        "joined_at": now.isoformat(),
    }


async def list_members(conn, org_id: str) -> List[Dict[str, Any]]:
    """Return all members of an organization ordered by join date."""
    rows = await conn.fetch(
        "SELECT org_id, user_id, role, joined_at FROM org_members WHERE org_id = $1 ORDER BY joined_at",
        org_id,
    )
    return [dict(r) for r in rows]


async def remove_member(conn, org_id: str, user_id: str) -> bool:
    """Remove a user from an organization. Returns True if a row was deleted."""
    result = await conn.execute(
        "DELETE FROM org_members WHERE org_id = $1 AND user_id = $2",
        org_id, user_id,
    )
    return result != "DELETE 0"


async def get_user_org(conn, user_id: str) -> Optional[Dict[str, Any]]:
    """Return the primary organization for a user (first by join date)."""
    row = await conn.fetchrow(
        """
        SELECT o.org_id, o.name, o.owner_id, o.plan, o.created_at, m.role
        FROM org_members m
        JOIN organizations o ON o.org_id = m.org_id
        WHERE m.user_id = $1
        ORDER BY m.joined_at
        LIMIT 1
        """,
        user_id,
    )
    return dict(row) if row else None
