"""
Jackdaw Sentry - Authentication Unit Tests (M5.3)
Tests for password hashing, JWT token creation/verification, and RBAC.
No external services required.
"""

import pytest
import jwt as pyjwt
from datetime import datetime, timedelta, timezone
from uuid import UUID


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
class TestPasswordHashing:
    """Verify bcrypt hash/verify round-trips correctly."""

    @pytest.mark.unit
    @pytest.mark.auth
    def test_hash_password_returns_bcrypt_string(self):
        from src.api.auth import hash_password

        hashed = hash_password("MySecretPassword1!")
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
        assert len(hashed) == 60

    @pytest.mark.unit
    @pytest.mark.auth
    def test_verify_correct_password(self):
        from src.api.auth import hash_password, verify_password

        plain = "CorrectHorseBatteryStaple"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    @pytest.mark.unit
    @pytest.mark.auth
    def test_verify_wrong_password(self):
        from src.api.auth import hash_password, verify_password

        hashed = hash_password("RightPassword")
        assert verify_password("WrongPassword", hashed) is False

    @pytest.mark.unit
    @pytest.mark.auth
    def test_different_hashes_for_same_password(self):
        from src.api.auth import hash_password

        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # different salts


# ---------------------------------------------------------------------------
# JWT token creation
# ---------------------------------------------------------------------------
class TestTokenCreation:
    """Verify create_access_token produces valid JWTs."""

    @pytest.mark.unit
    @pytest.mark.auth
    def test_create_access_token_decodable(self, jwt_secret):
        from src.api.auth import create_access_token

        token = create_access_token({"sub": "alice", "user_id": "abc-123"})
        payload = pyjwt.decode(token, jwt_secret, algorithms=["HS256"])
        assert payload["sub"] == "alice"
        assert payload["user_id"] == "abc-123"
        assert "exp" in payload
        assert "iat" in payload

    @pytest.mark.unit
    @pytest.mark.auth
    def test_create_access_token_custom_expiry(self, jwt_secret):
        from src.api.auth import create_access_token

        token = create_access_token(
            {"sub": "bob"},
            expires_delta=timedelta(minutes=5),
        )
        payload = pyjwt.decode(token, jwt_secret, algorithms=["HS256"])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        delta = exp - iat
        assert 290 <= delta.total_seconds() <= 310  # ~5 min

    @pytest.mark.unit
    @pytest.mark.auth
    def test_create_access_token_default_expiry(self, jwt_secret):
        from src.api.auth import create_access_token
        from src.api.config import settings

        token = create_access_token({"sub": "carol"})
        payload = pyjwt.decode(token, jwt_secret, algorithms=["HS256"])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        delta = exp - iat
        expected = settings.JWT_EXPIRE_MINUTES * 60
        assert abs(delta.total_seconds() - expected) < 5


# ---------------------------------------------------------------------------
# JWT token verification
# ---------------------------------------------------------------------------
class TestTokenVerification:
    """Verify verify_token accepts good tokens and rejects bad ones."""

    @pytest.mark.unit
    @pytest.mark.auth
    def test_verify_valid_token(self, make_token):
        from src.api.auth import verify_token

        token = make_token(sub="dave", user_id="uid-1", permissions=["a:r"])
        data = verify_token(token)
        assert data.username == "dave"
        assert data.user_id == "uid-1"
        assert "a:r" in data.permissions

    @pytest.mark.unit
    @pytest.mark.auth
    def test_verify_expired_token_raises(self, jwt_secret):
        from src.api.auth import verify_token
        from fastapi import HTTPException

        expired = pyjwt.encode(
            {
                "sub": "eve",
                "exp": datetime.now(timezone.utc) - timedelta(hours=1),
                "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            },
            jwt_secret,
            algorithm="HS256",
        )
        with pytest.raises(HTTPException) as exc_info:
            verify_token(expired)
        assert exc_info.value.status_code == 401

    @pytest.mark.unit
    @pytest.mark.auth
    def test_verify_bad_signature_raises(self):
        from src.api.auth import verify_token
        from fastapi import HTTPException

        token = pyjwt.encode(
            {"sub": "frank", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "wrong-secret",
            algorithm="HS256",
        )
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == 401

    @pytest.mark.unit
    @pytest.mark.auth
    def test_verify_missing_sub_raises(self, jwt_secret):
        from src.api.auth import verify_token
        from fastapi import HTTPException

        token = pyjwt.encode(
            {"exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            jwt_secret,
            algorithm="HS256",
        )
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# RBAC role definitions
# ---------------------------------------------------------------------------
class TestRBAC:
    """Verify role/permission mappings are consistent."""

    @pytest.mark.unit
    @pytest.mark.auth
    def test_admin_has_all_permissions(self):
        from src.api.auth import ROLES, PERMISSIONS

        admin_perms = set(ROLES["admin"])
        all_perms = set(PERMISSIONS.values())
        assert all_perms.issubset(admin_perms)

    @pytest.mark.unit
    @pytest.mark.auth
    def test_viewer_is_read_only(self):
        from src.api.auth import ROLES

        viewer_perms = ROLES["viewer"]
        for perm in viewer_perms:
            assert ":read" in perm, f"Viewer has non-read perm: {perm}"

    @pytest.mark.unit
    @pytest.mark.auth
    def test_all_roles_are_lists(self):
        from src.api.auth import ROLES

        for role_name, perms in ROLES.items():
            assert isinstance(perms, list), f"ROLES[{role_name!r}] is not a list"
            assert len(perms) > 0, f"ROLES[{role_name!r}] is empty"

    @pytest.mark.unit
    @pytest.mark.auth
    def test_expected_roles_exist(self):
        from src.api.auth import ROLES

        for role in ("viewer", "analyst", "compliance_officer", "admin"):
            assert role in ROLES, f"Missing role: {role}"
