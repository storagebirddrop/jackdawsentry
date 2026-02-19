"""
Unit/smoke tests for src/api/routers/teams.py (M16)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pg_ctx(fetchrow_value=None, fetch_value=None, execute_value="INSERT 1"):
    """Build a mock asyncpg connection context manager."""
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=fetchrow_value)
    conn.fetch = AsyncMock(return_value=fetch_value or [])
    conn.execute = AsyncMock(return_value=execute_value)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


_SAMPLE_ORG = {
    "org_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "name": "Acme Corp",
    "owner_id": "00000000-0000-0000-0000-000000000001",
    "plan": "standard",
    "created_at": "2024-01-01T00:00:00+00:00",
}

_SAMPLE_MEMBER = {
    "org_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "user_id": "bbbbbbbb-0000-0000-0000-000000000002",
    "role": "member",
    "joined_at": "2024-01-02T00:00:00+00:00",
}


# ---------------------------------------------------------------------------
# POST /teams/organizations
# ---------------------------------------------------------------------------


class TestCreateOrganization:
    def test_create_returns_201(self, client, admin_headers):
        mock_org = {**_SAMPLE_ORG, "created_at": "2024-01-01T00:00:00"}
        with patch("src.services.teams.create_organization", new_callable=AsyncMock,
                   return_value=mock_org), \
             patch("src.api.routers.teams.get_postgres_connection",
                   return_value=_pg_ctx()):
            resp = client.post(
                "/api/v1/teams/organizations",
                json={"name": "Acme Corp", "plan": "standard"},
                headers=admin_headers,
            )
        assert resp.status_code == 201
        assert resp.json()["organization"]["name"] == "Acme Corp"

    def test_create_rejects_empty_name(self, client, admin_headers):
        resp = client.post(
            "/api/v1/teams/organizations",
            json={"name": "   "},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_create_rejects_invalid_plan(self, client, admin_headers):
        resp = client.post(
            "/api/v1/teams/organizations",
            json={"name": "Org", "plan": "superduper"},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_create_requires_auth(self, client):
        resp = client.post(
            "/api/v1/teams/organizations",
            json={"name": "Test"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /teams/organizations/{org_id}
# ---------------------------------------------------------------------------


class TestGetOrganization:
    def test_get_returns_200(self, client, admin_headers):
        with patch("src.services.teams.get_organization", new_callable=AsyncMock,
                   return_value=_SAMPLE_ORG), \
             patch("src.api.routers.teams.get_postgres_connection",
                   return_value=_pg_ctx()):
            resp = client.get(
                f"/api/v1/teams/organizations/{_SAMPLE_ORG['org_id']}",
                headers=admin_headers,
            )
        assert resp.status_code == 200
        assert resp.json()["organization"]["name"] == "Acme Corp"

    def test_get_404_when_not_found(self, client, admin_headers):
        with patch("src.services.teams.get_organization", new_callable=AsyncMock,
                   return_value=None), \
             patch("src.api.routers.teams.get_postgres_connection",
                   return_value=_pg_ctx()):
            resp = client.get("/api/v1/teams/organizations/nonexistent", headers=admin_headers)
        assert resp.status_code == 404

    def test_get_requires_auth(self, client):
        resp = client.get("/api/v1/teams/organizations/some-id")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /teams/organizations/{org_id}/members
# ---------------------------------------------------------------------------


class TestAddMember:
    def test_add_member_returns_201(self, client, admin_headers):
        with patch("src.services.teams.get_organization", new_callable=AsyncMock,
                   return_value=_SAMPLE_ORG), \
             patch("src.services.teams.add_member", new_callable=AsyncMock,
                   return_value=_SAMPLE_MEMBER), \
             patch("src.api.routers.teams.get_postgres_connection",
                   return_value=_pg_ctx()):
            resp = client.post(
                f"/api/v1/teams/organizations/{_SAMPLE_ORG['org_id']}/members",
                json={"user_id": "bbbbbbbb-0000-0000-0000-000000000002", "role": "member"},
                headers=admin_headers,
            )
        assert resp.status_code == 201
        assert resp.json()["success"] is True

    def test_add_member_rejects_invalid_role(self, client, admin_headers):
        resp = client.post(
            "/api/v1/teams/organizations/some-id/members",
            json={"user_id": "uid", "role": "superuser"},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_add_member_requires_admin(self, client, auth_headers):
        resp = client.post(
            "/api/v1/teams/organizations/some-id/members",
            json={"user_id": "uid", "role": "member"},
            headers=auth_headers,
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /teams/organizations/{org_id}/members
# ---------------------------------------------------------------------------


class TestListMembers:
    def test_list_returns_200(self, client, admin_headers):
        with patch("src.services.teams.get_organization", new_callable=AsyncMock,
                   return_value=_SAMPLE_ORG), \
             patch("src.services.teams.list_members", new_callable=AsyncMock,
                   return_value=[_SAMPLE_MEMBER]), \
             patch("src.api.routers.teams.get_postgres_connection",
                   return_value=_pg_ctx()):
            resp = client.get(
                f"/api/v1/teams/organizations/{_SAMPLE_ORG['org_id']}/members",
                headers=admin_headers,
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1

    def test_list_requires_auth(self, client):
        resp = client.get("/api/v1/teams/organizations/some-id/members")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /teams/organizations/{org_id}/members/{user_id}
# ---------------------------------------------------------------------------


class TestRemoveMember:
    def test_remove_returns_200(self, client, admin_headers):
        with patch("src.services.teams.get_organization", new_callable=AsyncMock,
                   return_value=_SAMPLE_ORG), \
             patch("src.services.teams.remove_member", new_callable=AsyncMock,
                   return_value=True), \
             patch("src.api.routers.teams.get_postgres_connection",
                   return_value=_pg_ctx()):
            resp = client.delete(
                f"/api/v1/teams/organizations/{_SAMPLE_ORG['org_id']}/members/uid-123",
                headers=admin_headers,
            )
        assert resp.status_code == 200

    def test_remove_404_when_member_missing(self, client, admin_headers):
        with patch("src.services.teams.get_organization", new_callable=AsyncMock,
                   return_value=_SAMPLE_ORG), \
             patch("src.services.teams.remove_member", new_callable=AsyncMock,
                   return_value=False), \
             patch("src.api.routers.teams.get_postgres_connection",
                   return_value=_pg_ctx()):
            resp = client.delete(
                f"/api/v1/teams/organizations/{_SAMPLE_ORG['org_id']}/members/nonexistent",
                headers=admin_headers,
            )
        assert resp.status_code == 404

    def test_remove_requires_admin(self, client, auth_headers):
        resp = client.delete(
            "/api/v1/teams/organizations/org/members/user",
            headers=auth_headers,
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /teams/my-org
# ---------------------------------------------------------------------------


class TestMyOrg:
    def test_my_org_returns_200(self, client, admin_headers):
        org_with_role = {**_SAMPLE_ORG, "role": "admin"}
        with patch("src.services.teams.get_user_org", new_callable=AsyncMock,
                   return_value=org_with_role), \
             patch("src.api.routers.teams.get_postgres_connection",
                   return_value=_pg_ctx()):
            resp = client.get("/api/v1/teams/my-org", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["organization"]["name"] == "Acme Corp"

    def test_my_org_404_when_no_org(self, client, admin_headers):
        with patch("src.services.teams.get_user_org", new_callable=AsyncMock,
                   return_value=None), \
             patch("src.api.routers.teams.get_postgres_connection",
                   return_value=_pg_ctx()):
            resp = client.get("/api/v1/teams/my-org", headers=admin_headers)
        assert resp.status_code == 404

    def test_my_org_requires_auth(self, client):
        resp = client.get("/api/v1/teams/my-org")
        assert resp.status_code == 403
