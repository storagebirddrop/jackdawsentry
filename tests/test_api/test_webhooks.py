"""
Unit/smoke tests for src/api/routers/webhooks.py (M16)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.webhook_manager import sign_payload


# ---------------------------------------------------------------------------
# sign_payload unit tests (pure function)
# ---------------------------------------------------------------------------


class TestSignPayload:
    def test_returns_hex_string(self):
        sig = sign_payload("hello", "mysecret")
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA-256 hex = 32 bytes = 64 chars

    def test_different_payloads_different_signatures(self):
        s1 = sign_payload("payload1", "secret")
        s2 = sign_payload("payload2", "secret")
        assert s1 != s2

    def test_different_secrets_different_signatures(self):
        s1 = sign_payload("payload", "secret1")
        s2 = sign_payload("payload", "secret2")
        assert s1 != s2

    def test_same_input_same_output(self):
        assert sign_payload("abc", "key") == sign_payload("abc", "key")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pg_ctx():
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value="INSERT 1")
    conn.fetch = AsyncMock(return_value=[])
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


_SAMPLE_HOOK = {
    "hook_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "url": "https://example.com/webhook",
    "events": ["alert.triggered"],
    "created_at": "2024-01-01T00:00:00+00:00",
    "active": True,
}


# ---------------------------------------------------------------------------
# POST /webhooks
# ---------------------------------------------------------------------------


class TestRegisterWebhook:
    def test_register_returns_201(self, client, admin_headers):
        with patch("src.services.webhook_manager.register_webhook", new_callable=AsyncMock,
                   return_value=_SAMPLE_HOOK), \
             patch("src.api.routers.webhooks.get_postgres_connection",
                   return_value=_pg_ctx()):
            resp = client.post(
                "/api/v1/webhooks",
                json={
                    "url": "https://example.com/wh",
                    "events": ["alert.triggered"],
                    "secret": "mysupersecretkey1234",
                },
                headers=admin_headers,
            )
        assert resp.status_code == 201
        assert resp.json()["webhook"]["hook_id"] == _SAMPLE_HOOK["hook_id"]

    def test_register_rejects_http_url(self, client, admin_headers):
        resp = client.post(
            "/api/v1/webhooks",
            json={
                "url": "ftp://bad.example.com",
                "events": ["alert.triggered"],
                "secret": "mysupersecretkey1234",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_register_rejects_empty_events(self, client, admin_headers):
        resp = client.post(
            "/api/v1/webhooks",
            json={
                "url": "https://example.com/wh",
                "events": [],
                "secret": "mysupersecretkey1234",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_register_rejects_unknown_event(self, client, admin_headers):
        resp = client.post(
            "/api/v1/webhooks",
            json={
                "url": "https://example.com/wh",
                "events": ["totally.unknown.event"],
                "secret": "mysupersecretkey1234",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_register_rejects_short_secret(self, client, admin_headers):
        resp = client.post(
            "/api/v1/webhooks",
            json={
                "url": "https://example.com/wh",
                "events": ["alert.triggered"],
                "secret": "short",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_register_requires_auth(self, client):
        resp = client.post(
            "/api/v1/webhooks",
            json={
                "url": "https://example.com/wh",
                "events": ["alert.triggered"],
                "secret": "mysupersecretkey1234",
            },
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /webhooks
# ---------------------------------------------------------------------------


class TestListWebhooks:
    def test_list_returns_200(self, client, admin_headers):
        with patch("src.services.webhook_manager.list_webhooks", new_callable=AsyncMock,
                   return_value=[_SAMPLE_HOOK]), \
             patch("src.api.routers.webhooks.get_postgres_connection",
                   return_value=_pg_ctx()):
            resp = client.get("/api/v1/webhooks", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1

    def test_list_requires_auth(self, client):
        resp = client.get("/api/v1/webhooks")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /webhooks/{hook_id}
# ---------------------------------------------------------------------------


class TestDeleteWebhook:
    def test_delete_returns_200(self, client, admin_headers):
        with patch("src.services.webhook_manager.delete_webhook", new_callable=AsyncMock,
                   return_value=True), \
             patch("src.api.routers.webhooks.get_postgres_connection",
                   return_value=_pg_ctx()):
            resp = client.delete(
                f"/api/v1/webhooks/{_SAMPLE_HOOK['hook_id']}",
                headers=admin_headers,
            )
        assert resp.status_code == 200
        assert resp.json()["deleted_hook_id"] == _SAMPLE_HOOK["hook_id"]

    def test_delete_404_when_not_found(self, client, admin_headers):
        with patch("src.services.webhook_manager.delete_webhook", new_callable=AsyncMock,
                   return_value=False), \
             patch("src.api.routers.webhooks.get_postgres_connection",
                   return_value=_pg_ctx()):
            resp = client.delete("/api/v1/webhooks/nonexistent", headers=admin_headers)
        assert resp.status_code == 404

    def test_delete_requires_auth(self, client):
        resp = client.delete("/api/v1/webhooks/some-id")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /webhooks/{hook_id}/test
# ---------------------------------------------------------------------------


class TestTestWebhook:
    def test_test_returns_200(self, client, admin_headers):
        resp = client.post(
            f"/api/v1/webhooks/{_SAMPLE_HOOK['hook_id']}/test",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_test_requires_auth(self, client):
        resp = client.post("/api/v1/webhooks/some-id/test")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /webhooks/events
# ---------------------------------------------------------------------------


class TestListEventTypes:
    def test_events_returns_200(self, client, admin_headers):
        resp = client.get("/api/v1/webhooks/events", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "event_types" in body
        assert "alert.triggered" in body["event_types"]
