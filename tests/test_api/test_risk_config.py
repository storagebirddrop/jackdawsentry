"""
Unit / smoke tests for src/api/routers/risk_config.py (M14)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_weights():
    return [
        {"feature_name": "mixer_usage", "weight": 0.30, "description": "Mixer"},
        {"feature_name": "sanctions_entity", "weight": 0.40, "description": "Sanctions"},
    ]


def _fake_rule():
    return {
        "id": "aaaaaaaa-0000-0000-0000-000000000001",
        "name": "high-mixer",
        "description": "Flag high mixer usage",
        "conditions": {"mixer_usage": {"op": "gte", "value": 0.8}},
        "risk_bump": 0.15,
        "enabled": True,
        "created_by": "admin",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }


# ---------------------------------------------------------------------------
# GET /risk-config/weights
# ---------------------------------------------------------------------------


class TestListWeights:
    def test_list_weights_returns_200(self, client, admin_headers):
        with patch("src.analysis.ml_risk_model.list_weights", new_callable=AsyncMock,
                   return_value=_fake_weights()):
            resp = client.get("/api/v1/risk-config/weights", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "weights" in body
        assert body["count"] == 2

    def test_list_weights_requires_auth(self, client):
        resp = client.get("/api/v1/risk-config/weights")
        assert resp.status_code == 403

    def test_list_weights_analyst_can_read(self, client, auth_headers):
        with patch("src.analysis.ml_risk_model.list_weights", new_callable=AsyncMock,
                   return_value=_fake_weights()):
            resp = client.get("/api/v1/risk-config/weights", headers=auth_headers)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# PATCH /risk-config/weights/{feature}
# ---------------------------------------------------------------------------


class TestUpdateWeight:
    def test_update_weight_returns_200(self, client, admin_headers):
        with patch("src.analysis.ml_risk_model._DEFAULT_WEIGHTS",
                   {"mixer_usage": (0.30, "Mixer")}), \
             patch("src.analysis.ml_risk_model.save_weight", new_callable=AsyncMock):
            resp = client.patch(
                "/api/v1/risk-config/weights/mixer_usage",
                json={"weight": 0.45},
                headers=admin_headers,
            )
        assert resp.status_code == 200
        assert resp.json()["updated"] is True

    def test_update_weight_rejects_unknown_feature(self, client, admin_headers):
        with patch("src.analysis.ml_risk_model._DEFAULT_WEIGHTS", {}):
            resp = client.patch(
                "/api/v1/risk-config/weights/nonexistent",
                json={"weight": 0.5},
                headers=admin_headers,
            )
        assert resp.status_code == 404

    def test_update_weight_rejects_out_of_range(self, client, admin_headers):
        resp = client.patch(
            "/api/v1/risk-config/weights/mixer_usage",
            json={"weight": 1.5},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_update_weight_requires_admin(self, client, auth_headers):
        resp = client.patch(
            "/api/v1/risk-config/weights/mixer_usage",
            json={"weight": 0.3},
            headers=auth_headers,
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /risk-config/weights/reset
# ---------------------------------------------------------------------------


class TestResetWeights:
    def test_reset_returns_200(self, client, admin_headers):
        with patch("src.analysis.ml_risk_model._DEFAULT_WEIGHTS",
                   {"mixer_usage": (0.30, "Mixer"), "sanctions_entity": (0.40, "Sanctions")}), \
             patch("src.analysis.ml_risk_model.save_weight", new_callable=AsyncMock):
            resp = client.post("/api/v1/risk-config/weights/reset", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["reset"] is True

    def test_reset_requires_admin(self, client, auth_headers):
        resp = client.post("/api/v1/risk-config/weights/reset", headers=auth_headers)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /risk-config/rules
# ---------------------------------------------------------------------------


class TestListRules:
    def test_list_rules_returns_200(self, client, admin_headers):
        with patch("src.analysis.ml_risk_model.list_custom_rules", new_callable=AsyncMock,
                   return_value=[_fake_rule()]):
            resp = client.get("/api/v1/risk-config/rules", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1

    def test_list_rules_requires_auth(self, client):
        resp = client.get("/api/v1/risk-config/rules")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /risk-config/rules
# ---------------------------------------------------------------------------


class TestCreateRule:
    def test_create_rule_returns_201(self, client, admin_headers):
        with patch("src.analysis.ml_risk_model.create_custom_rule", new_callable=AsyncMock,
                   return_value=_fake_rule()):
            resp = client.post(
                "/api/v1/risk-config/rules",
                json={
                    "name": "high-mixer",
                    "conditions": {"mixer_usage": {"op": "gte", "value": 0.8}},
                    "risk_bump": 0.15,
                    "description": "Flag high mixer usage",
                },
                headers=admin_headers,
            )
        assert resp.status_code == 201
        assert resp.json()["name"] == "high-mixer"

    def test_create_rule_rejects_empty_name(self, client, admin_headers):
        resp = client.post(
            "/api/v1/risk-config/rules",
            json={"name": "", "conditions": {}, "risk_bump": 0.1},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_create_rule_rejects_zero_bump(self, client, admin_headers):
        resp = client.post(
            "/api/v1/risk-config/rules",
            json={"name": "test", "conditions": {}, "risk_bump": 0.0},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_create_rule_rejects_high_bump(self, client, admin_headers):
        resp = client.post(
            "/api/v1/risk-config/rules",
            json={"name": "test", "conditions": {}, "risk_bump": 0.9},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_create_rule_requires_admin(self, client, auth_headers):
        resp = client.post(
            "/api/v1/risk-config/rules",
            json={"name": "x", "conditions": {}, "risk_bump": 0.1},
            headers=auth_headers,
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /risk-config/rules/{id}
# ---------------------------------------------------------------------------


class TestDeleteRule:
    def test_delete_rule_returns_200(self, client, admin_headers):
        rule_id = "aaaaaaaa-0000-0000-0000-000000000001"
        with patch("src.analysis.ml_risk_model.delete_custom_rule", new_callable=AsyncMock,
                   return_value=True):
            resp = client.delete(
                f"/api/v1/risk-config/rules/{rule_id}",
                headers=admin_headers,
            )
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    def test_delete_rule_not_found_returns_404(self, client, admin_headers):
        rule_id = "aaaaaaaa-0000-0000-0000-000000000002"
        with patch("src.analysis.ml_risk_model.delete_custom_rule", new_callable=AsyncMock,
                   return_value=False):
            resp = client.delete(
                f"/api/v1/risk-config/rules/{rule_id}",
                headers=admin_headers,
            )
        assert resp.status_code == 404

    def test_delete_rule_requires_admin(self, client, auth_headers):
        resp = client.delete(
            "/api/v1/risk-config/rules/aaaaaaaa-0000-0000-0000-000000000001",
            headers=auth_headers,
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /risk-config/score
# ---------------------------------------------------------------------------


class TestScoreEndpoint:
    def test_score_returns_200(self, client, admin_headers):
        mock_result = {
            "score": 0.62,
            "risk_level": "high",
            "feature_vector": {},
            "weights_used": {},
            "model": "ml_v1",
        }
        with patch("src.analysis.ml_risk_model.compute_ml_risk_score",
                   new_callable=AsyncMock, return_value=mock_result):
            resp = client.post(
                "/api/v1/risk-config/score",
                json={"mixer_usage": True, "transaction_count": 50},
                headers=admin_headers,
            )
        assert resp.status_code == 200
        assert resp.json()["model"] == "ml_v1"

    def test_score_requires_auth(self, client):
        resp = client.post("/api/v1/risk-config/score", json={})
        assert resp.status_code == 403

    def test_score_with_entity_info(self, client, admin_headers):
        mock_result = {
            "score": 0.91, "risk_level": "critical",
            "feature_vector": {}, "weights_used": {}, "model": "ml_v1",
        }
        with patch("src.analysis.ml_risk_model.compute_ml_risk_score",
                   new_callable=AsyncMock, return_value=mock_result):
            resp = client.post(
                "/api/v1/risk-config/score",
                json={"entity_type": "darknet_market", "risk_level": "critical"},
                headers=admin_headers,
            )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /risk-config/deobfuscate
# ---------------------------------------------------------------------------


class TestDeobfuscateEndpoint:
    def test_deobfuscate_returns_200(self, client, admin_headers):
        txs = [
            {
                "tx_hash": "0xd1", "from_address": "0xuser",
                "to_address": "0xmixer", "value": 1.0,
                "timestamp": 1700000000, "chain": "ethereum",
                "interaction_type": "mixer_deposit",
            },
            {
                "tx_hash": "0xw1", "from_address": "0xmixer",
                "to_address": "0xother", "value": 1.0,
                "timestamp": 1700007200, "chain": "ethereum",
                "interaction_type": "mixer_withdraw",
            },
        ]
        resp = client.post(
            "/api/v1/risk-config/deobfuscate",
            json={"transactions": txs},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "total_pairs" in body
        assert "candidate_pairs" in body

    def test_deobfuscate_empty_transactions_rejected(self, client, admin_headers):
        resp = client.post(
            "/api/v1/risk-config/deobfuscate",
            json={"transactions": []},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_deobfuscate_no_mixer_txs_returns_empty_pairs(self, client, admin_headers):
        txs = [
            {
                "tx_hash": "0xt1", "from_address": "0xa",
                "to_address": "0xb", "value": 1.0,
                "timestamp": 1700000000, "chain": "ethereum",
                "interaction_type": "dex_swap",
            }
        ]
        resp = client.post(
            "/api/v1/risk-config/deobfuscate",
            json={"transactions": txs},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total_pairs"] == 0

    def test_deobfuscate_requires_auth(self, client):
        resp = client.post(
            "/api/v1/risk-config/deobfuscate",
            json={"transactions": [{"tx_hash": "0x1"}]},
        )
        assert resp.status_code == 403

    def test_deobfuscate_invalid_confidence_rejected(self, client, admin_headers):
        resp = client.post(
            "/api/v1/risk-config/deobfuscate",
            json={
                "transactions": [{"tx_hash": "0x1"}],
                "min_confidence": 1.5,
            },
            headers=admin_headers,
        )
        assert resp.status_code == 422
