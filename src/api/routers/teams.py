"""
Jackdaw Sentry - Teams Router (M16)

Multi-tenant organization management endpoints.
Prefix: /api/v1/teams
"""

from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import field_validator

from src.api.auth import User
from src.api.auth import get_current_user
from src.api.auth import require_admin
from src.api.database import get_postgres_connection

router = APIRouter()

_VALID_PLANS = {"standard", "professional", "enterprise"}
_VALID_ROLES = {"admin", "member", "viewer"}


class CreateOrgRequest(BaseModel):
    name: str
    plan: str = "standard"

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be empty")
        if len(v) > 100:
            raise ValueError("name must not exceed 100 characters")
        return v

    @field_validator("plan")
    @classmethod
    def validate_plan(cls, v: str) -> str:
        if v not in _VALID_PLANS:
            raise ValueError(f"plan must be one of {sorted(_VALID_PLANS)}")
        return v


class AddMemberRequest(BaseModel):
    user_id: str
    role: str = "member"

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in _VALID_ROLES:
            raise ValueError(f"role must be one of {sorted(_VALID_ROLES)}")
        return v


@router.post("/organizations", status_code=201)
async def create_organization(
    request: CreateOrgRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a new organization; the caller becomes the org admin."""
    from src.services.teams import create_organization as _create

    async with get_postgres_connection() as conn:
        org = await _create(conn, request.name, current_user.id, request.plan)
    return {"success": True, "organization": org}


@router.get("/organizations/{org_id}")
async def get_organization(
    org_id: str,
    current_user: User = Depends(get_current_user),
):
    """Fetch organization details."""
    from src.services.teams import get_organization as _get

    async with get_postgres_connection() as conn:
        org = await _get(conn, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"success": True, "organization": org}


@router.post("/organizations/{org_id}/members", status_code=201)
async def add_member(
    org_id: str,
    request: AddMemberRequest,
    current_user: User = Depends(require_admin),
):
    """Add or update a member in an organization (admin only)."""
    from src.services.teams import add_member as _add
    from src.services.teams import get_organization as _get

    async with get_postgres_connection() as conn:
        if not await _get(conn, org_id):
            raise HTTPException(status_code=404, detail="Organization not found")
        member = await _add(conn, org_id, request.user_id, request.role)
    return {"success": True, "member": member}


@router.get("/organizations/{org_id}/members")
async def list_members(
    org_id: str,
    current_user: User = Depends(get_current_user),
):
    """List all members of an organization."""
    from src.services.teams import get_organization as _get
    from src.services.teams import list_members as _list

    async with get_postgres_connection() as conn:
        if not await _get(conn, org_id):
            raise HTTPException(status_code=404, detail="Organization not found")
        members = await _list(conn, org_id)
    return {"success": True, "members": members, "count": len(members)}


@router.delete("/organizations/{org_id}/members/{user_id}")
async def remove_member(
    org_id: str,
    user_id: str,
    current_user: User = Depends(require_admin),
):
    """Remove a member from an organization (admin only)."""
    from src.services.teams import get_organization as _get
    from src.services.teams import remove_member as _remove

    async with get_postgres_connection() as conn:
        if not await _get(conn, org_id):
            raise HTTPException(status_code=404, detail="Organization not found")
        deleted = await _remove(conn, org_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"success": True, "removed_user_id": user_id}


@router.get("/my-org")
async def get_my_org(current_user: User = Depends(get_current_user)):
    """Return the current user's primary organization."""
    from src.services.teams import get_user_org

    async with get_postgres_connection() as conn:
        org = await get_user_org(conn, current_user.id)
    if not org:
        raise HTTPException(
            status_code=404, detail="No organization found for this user"
        )
    return {"success": True, "organization": org}
