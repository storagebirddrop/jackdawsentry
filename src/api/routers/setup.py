"""
Jackdaw Sentry - Initial Setup Router
First-launch admin setup flow. Endpoints are unauthenticated but locked
once the first admin user has been created.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, field_validator
import logging
import re

from src.api.auth import hash_password
from src.api.database import get_postgres_connection

logger = logging.getLogger(__name__)

router = APIRouter()


class SetupStatus(BaseModel):
    """Response for setup status check"""
    setup_required: bool
    message: str


class InitialAdminRequest(BaseModel):
    """Request body for creating the first admin user"""
    username: str
    email: str
    password: str
    confirm_password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be 3-50 characters")
        if not re.match(r"^[a-zA-Z0-9_.-]+$", v):
            raise ValueError("Username may only contain letters, digits, underscores, dots, and hyphens")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email address")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 128:
            raise ValueError("Password must be at most 128 characters")
        return v


async def _is_setup_required() -> bool:
    """Check whether any user with role='admin' exists in the database."""
    try:
        async with get_postgres_connection() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = true"
            )
        return count == 0
    except Exception as e:
        logger.error("Setup status check failed (database may not be initialized): %s", e)
        return True


@router.get("/status", response_model=SetupStatus)
async def setup_status():
    """Check whether initial setup is required.

    Returns setup_required=true when no active admin user exists in the
    database (i.e., fresh deployment or all admins removed).
    """
    required = await _is_setup_required()
    if required:
        return SetupStatus(
            setup_required=True,
            message="No admin account found. Initial setup is required.",
        )
    return SetupStatus(
        setup_required=False,
        message="Setup complete. An admin account already exists.",
    )


@router.post("/initialize", status_code=status.HTTP_201_CREATED)
async def initialize_admin(data: InitialAdminRequest):
    """Create the first admin user.

    This endpoint is only available when no admin user exists in the
    database. Once an admin is created, subsequent calls are rejected.
    """
    if not await _is_setup_required():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Setup already completed. An admin account exists.",
        )

    if data.password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Passwords do not match.",
        )

    password_hash = hash_password(data.password)

    try:
        async with get_postgres_connection() as conn:
            # Ensure the users table exists
            table_exists = await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'users')"
            )
            if not table_exists:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database schema not initialized. Run migrations first.",
                )

            # Atomic insert: only succeeds if no active admin exists AND
            # username is not taken. Single query avoids TOCTOU race.
            user_id = await conn.fetchval(
                "INSERT INTO users (username, email, password_hash, full_name, role, is_active, gdpr_consent_given) "
                "SELECT $1, $2, $3, $4, 'admin', true, false "
                "WHERE NOT EXISTS (SELECT 1 FROM users WHERE role = 'admin' AND is_active = true) "
                "ON CONFLICT (username) DO NOTHING "
                "RETURNING id",
                data.username,
                data.email,
                password_hash,
                "System Administrator",
            )

            if user_id is None:
                # Distinguish between "admin already exists" and "username taken"
                admin_exists = await conn.fetchval(
                    "SELECT EXISTS (SELECT 1 FROM users WHERE role = 'admin' AND is_active = true)"
                )
                if admin_exists:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Setup already completed. An admin account exists.",
                    )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Username '{data.username}' is already taken.",
                )

        logger.info("Initial admin user created: %s", data.username)
        return {
            "success": True,
            "message": "Admin account created successfully. You can now sign in.",
            "username": data.username,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create initial admin user: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create admin account. Check server logs.",
        )
