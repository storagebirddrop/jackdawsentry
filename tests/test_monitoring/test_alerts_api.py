"""
Unit tests for the M12 alerts REST API endpoints.

Covers:
  GET  /api/v1/alerts/rules
  POST /api/v1/alerts/rules
  GET  /api/v1/alerts/rules/{id}
  PATCH /api/v1/alerts/rules/{id}
  DELETE /api/v1/alerts/rules/{id}
  GET  /api/v1/alerts/recent
"""

import pytest
from unittest.mock import AsyncMock, patch

SAMPLE_RULE = {
    "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    "name": "Whale alert",
    "description": "Fire on large txs",
    "conditions": {"value_gte": 100.0},
    "severity": "high",
    "enabled": True,
    "created_by": "admin",
    "trigger_count": 0,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
}

SAMPLE_ALERT = {
    "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    "rule_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    "rule_name": "Whale alert",
    "severity": "high",
    "detail": "Matched tx 0xdeadbeef",
    "transaction_hash": "0xdeadbeef",
    "blockchain": "ethereum",
    "from_address": "0xsender",
    "to_address": "0xreceiver",
    "value": 500.0,
    "fired_at": "2024-01-01T12:00:00",
}


class TestListAlertRules:
    def test_requires_auth(self, client):
        resp = client.get("/api/v1/alerts/rules")
        assert resp.status_code == 403

    def test_returns_rules_list(self, client, auth_headers):
        with patch("src.api.routers.alerts.list_rules", new_callable=AsyncMock,
                   return_value=[SAMPLE_RULE]):
            resp = client.get("/api/v1/alerts/rules", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["count"] == 1
        assert body["rules"][0]["name"] == "Whale alert"

    def test_returns_empty_list_when_no_rules(self, client, auth_headers):
        with patch("src.api.routers.alerts.list_rules", new_callable=AsyncMock,
                   return_value=[]):
            resp = client.get("/api/v1/alerts/rules", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["count"] == 0


class TestCreateAlertRule:
    def test_requires_admin(self, client, auth_headers):
        resp = client.post("/api/v1/alerts/rules", json={
            "name": "Test", "conditions": {}
        }, headers=auth_headers)
        assert resp.status_code == 403

    def test_creates_rule(self, client, admin_headers):
        with patch("src.api.routers.alerts.create_rule", new_callable=AsyncMock,
                   return_value=SAMPLE_RULE):
            resp = client.post("/api/v1/alerts/rules", json={
                "name": "Whale alert",
                "conditions": {"value_gte": 100.0},
                "severity": "high",
            }, headers=admin_headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["success"] is True
        assert body["rule"]["name"] == "Whale alert"

    def test_rejects_invalid_severity(self, client, admin_headers):
        resp = client.post("/api/v1/alerts/rules", json={
            "name": "Bad Rule",
            "conditions": {},
            "severity": "extreme",
        }, headers=admin_headers)
        assert resp.status_code == 422

    def test_rejects_empty_name(self, client, admin_headers):
        resp = client.post("/api/v1/alerts/rules", json={
            "name": "   ",
            "conditions": {},
        }, headers=admin_headers)
        assert resp.status_code == 422


class TestGetAlertRule:
    def test_returns_rule(self, client, auth_headers):
        rule_id = SAMPLE_RULE["id"]
        with patch("src.api.routers.alerts.get_rule", new_callable=AsyncMock,
                   return_value=SAMPLE_RULE):
            resp = client.get(f"/api/v1/alerts/rules/{rule_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["rule"]["id"] == rule_id

    def test_404_when_missing(self, client, auth_headers):
        with patch("src.api.routers.alerts.get_rule", new_callable=AsyncMock,
                   return_value=None):
            resp = client.get("/api/v1/alerts/rules/nonexistent", headers=auth_headers)
        assert resp.status_code == 404


class TestUpdateAlertRule:
    def test_requires_admin(self, client, auth_headers):
        resp = client.patch("/api/v1/alerts/rules/some-id", json={
            "enabled": False
        }, headers=auth_headers)
        assert resp.status_code == 403

    def test_updates_rule(self, client, admin_headers):
        updated = {**SAMPLE_RULE, "enabled": False}
        with patch("src.api.routers.alerts.update_rule", new_callable=AsyncMock,
                   return_value=updated):
            resp = client.patch(
                f"/api/v1/alerts/rules/{SAMPLE_RULE['id']}",
                json={"enabled": False},
                headers=admin_headers,
            )
        assert resp.status_code == 200
        assert resp.json()["rule"]["enabled"] is False

    def test_404_when_rule_missing(self, client, admin_headers):
        with patch("src.api.routers.alerts.update_rule", new_callable=AsyncMock,
                   return_value=None):
            resp = client.patch("/api/v1/alerts/rules/missing", json={
                "enabled": False
            }, headers=admin_headers)
        assert resp.status_code == 404

    def test_400_on_no_fields(self, client, admin_headers):
        resp = client.patch(
            f"/api/v1/alerts/rules/{SAMPLE_RULE['id']}",
            json={},
            headers=admin_headers,
        )
        assert resp.status_code == 400


class TestDeleteAlertRule:
    def test_requires_admin(self, client, auth_headers):
        resp = client.delete("/api/v1/alerts/rules/some-id", headers=auth_headers)
        assert resp.status_code == 403

    def test_deletes_rule(self, client, admin_headers):
        with patch("src.api.routers.alerts.delete_rule", new_callable=AsyncMock,
                   return_value=True):
            resp = client.delete(
                f"/api/v1/alerts/rules/{SAMPLE_RULE['id']}",
                headers=admin_headers,
            )
        assert resp.status_code == 204

    def test_404_when_missing(self, client, admin_headers):
        with patch("src.api.routers.alerts.delete_rule", new_callable=AsyncMock,
                   return_value=False):
            resp = client.delete("/api/v1/alerts/rules/missing", headers=admin_headers)
        assert resp.status_code == 404


class TestRecentAlerts:
    def test_requires_auth(self, client):
        resp = client.get("/api/v1/alerts/recent")
        assert resp.status_code == 403

    def test_returns_alert_list(self, client, auth_headers):
        with patch("src.api.routers.alerts.get_recent_alerts", new_callable=AsyncMock,
                   return_value=[SAMPLE_ALERT]):
            resp = client.get("/api/v1/alerts/recent", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        assert body["alerts"][0]["rule_name"] == "Whale alert"

    def test_empty_when_no_alerts(self, client, auth_headers):
        with patch("src.api.routers.alerts.get_recent_alerts", new_callable=AsyncMock,
                   return_value=[]):
            resp = client.get("/api/v1/alerts/recent", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_limit_param_validated(self, client, auth_headers):
        resp = client.get("/api/v1/alerts/recent?limit=0", headers=auth_headers)
        assert resp.status_code == 422
