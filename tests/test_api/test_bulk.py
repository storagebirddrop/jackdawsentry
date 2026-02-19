"""
Unit/smoke tests for src/api/routers/bulk.py (M16)
"""
import pytest


# ---------------------------------------------------------------------------
# POST /bulk/screen
# ---------------------------------------------------------------------------


class TestBulkScreen:
    def test_screen_returns_200(self, client, admin_headers):
        resp = client.post(
            "/api/v1/bulk/screen",
            json={"addresses": ["0xabc", "0xdef"], "chain": "ethereum"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["screened_count"] == 2
        assert len(body["results"]) == 2

    def test_screen_rejects_empty_list(self, client, admin_headers):
        resp = client.post(
            "/api/v1/bulk/screen",
            json={"addresses": []},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_screen_rejects_over_limit(self, client, admin_headers):
        resp = client.post(
            "/api/v1/bulk/screen",
            json={"addresses": [f"0x{i:040x}" for i in range(501)]},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    def test_screen_vasp_match_included(self, client, admin_headers):
        resp = client.post(
            "/api/v1/bulk/screen",
            json={"addresses": ["0x1111abcdef"], "chain": "ethereum"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        result = resp.json()["results"][0]
        assert result["vasp_match"] is not None
        assert result["vasp_match"]["name"] == "Coinbase"

    def test_screen_no_vasp_null(self, client, admin_headers):
        resp = client.post(
            "/api/v1/bulk/screen",
            json={"addresses": ["0xdeadbeefdeadbeef"], "chain": "ethereum"},
            headers=admin_headers,
        )
        result = resp.json()["results"][0]
        assert result["vasp_match"] is None

    def test_screen_requires_auth(self, client):
        resp = client.post("/api/v1/bulk/screen", json={"addresses": ["0xabc"]})
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /bulk/screen/export
# ---------------------------------------------------------------------------


class TestBulkScreenExport:
    def test_export_returns_csv(self, client, admin_headers):
        resp = client.post(
            "/api/v1/bulk/screen/export",
            json={"addresses": ["0xabc", "0xdef"]},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")

    def test_export_csv_has_header_row(self, client, admin_headers):
        resp = client.post(
            "/api/v1/bulk/screen/export",
            json={"addresses": ["0xabc"]},
            headers=admin_headers,
        )
        csv_text = resp.text
        assert "address" in csv_text
        assert "chain" in csv_text

    def test_export_requires_auth(self, client):
        resp = client.post("/api/v1/bulk/screen/export", json={"addresses": ["0xabc"]})
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /bulk/analyze/contract
# ---------------------------------------------------------------------------


class TestContractAnalyze:
    def test_erc20_calldata_classified(self, client, admin_headers):
        # ERC-20 transfer selector
        resp = client.post(
            "/api/v1/bulk/analyze/contract",
            json={
                "calldata": "0xa9059cbb" + "0" * 64,
                "contract_address": "0xtoken",
                "chain": "ethereum",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["classification"]["standard"] == "ERC-20"
        assert body["nft"]["is_nft_transfer"] is False

    def test_nft_calldata_detected(self, client, admin_headers):
        # ERC-721 safeTransferFrom selector
        resp = client.post(
            "/api/v1/bulk/analyze/contract",
            json={
                "calldata": "0x42842e0e" + "0" * 96,
                "contract_address": "0xnft",
                "chain": "ethereum",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["nft"]["is_nft_transfer"] is True

    def test_contract_analyze_requires_auth(self, client):
        resp = client.post(
            "/api/v1/bulk/analyze/contract",
            json={"calldata": "0xa9059cbb" + "0" * 64, "contract_address": "0x1"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /bulk/stats
# ---------------------------------------------------------------------------


class TestBulkStats:
    def test_stats_returns_200(self, client, admin_headers):
        resp = client.get("/api/v1/bulk/stats", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["max_addresses_per_request"] == 500
        assert "features" in body

    def test_stats_requires_auth(self, client):
        resp = client.get("/api/v1/bulk/stats")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Travel Rule API tests
# ---------------------------------------------------------------------------


class TestTravelRuleApi:
    def test_check_below_threshold(self, client, admin_headers):
        resp = client.post(
            "/api/v1/travel-rule/check",
            json={
                "tx_hash": "0xtx1",
                "originator_address": "0xabc",
                "beneficiary_address": "0xdef",
                "amount_usd": 500.0,
            },
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["travel_rule_required"] is False

    def test_check_above_threshold(self, client, admin_headers):
        resp = client.post(
            "/api/v1/travel-rule/check",
            json={
                "tx_hash": "0xtx2",
                "originator_address": "0xabc",
                "beneficiary_address": "0xdef",
                "amount_usd": 5000.0,
            },
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["travel_rule_required"] is True

    def test_check_requires_auth(self, client):
        resp = client.post(
            "/api/v1/travel-rule/check",
            json={"tx_hash": "0x1", "originator_address": "0xa",
                  "beneficiary_address": "0xb", "amount_usd": 1000.0},
        )
        assert resp.status_code == 403

    def test_vasp_lookup_known_address(self, client, admin_headers):
        resp = client.get("/api/v1/travel-rule/vasp/0x1111abcdef", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["vasp"]["name"] == "Coinbase"

    def test_vasp_lookup_unknown_address(self, client, admin_headers):
        resp = client.get("/api/v1/travel-rule/vasp/0xunknown", headers=admin_headers)
        assert resp.status_code == 404

    def test_vasp_validate_complete(self, client, admin_headers):
        resp = client.post(
            "/api/v1/travel-rule/vasp/validate",
            json={"name": "Coinbase", "jurisdiction": "US", "lei": "KGCEPHLVVKVRZYO1"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["valid"] is True
        assert resp.json()["errors"] == []

    def test_vasp_validate_incomplete(self, client, admin_headers):
        resp = client.post(
            "/api/v1/travel-rule/vasp/validate",
            json={"name": "", "jurisdiction": "", "lei": ""},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["valid"] is False
        assert len(resp.json()["errors"]) >= 3

    def test_threshold_endpoint(self, client, admin_headers):
        resp = client.get("/api/v1/travel-rule/threshold", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["threshold_usd"] == 1000.0
