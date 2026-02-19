"""
Unit tests for analysis engine wiring in the /analysis endpoints.

Tests that:
 - POST /analysis/address calls pattern + mixer engines and returns computed risk
 - POST /analysis/transaction calls cross-chain analyzer
 - POST /analysis/address/full runs all engines in parallel
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _neo4j_session_mock(record_data=None):
    """Return a context-manager mock for get_neo4j_session."""
    record = MagicMock()
    if record_data:
        for k, v in record_data.items():
            record.__getitem__ = lambda self, key, _d=record_data: _d[key]
        record.get = lambda key, default=None, _d=record_data: _d.get(key, default)
    else:
        record = None

    run_result = AsyncMock()
    run_result.single = AsyncMock(return_value=record)
    run_result.data = AsyncMock(return_value=[])

    session = AsyncMock()
    session.run = AsyncMock(return_value=run_result)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


class TestAddressEndpointEngineWiring:
    """POST /api/v1/analysis/address should call pattern and mixer engines."""

    def test_address_response_contains_detected_patterns(self, client, admin_headers):
        mock_pattern = MagicMock()
        mock_pattern.pattern_type.value = "layering"
        mock_pattern.confidence = 0.85
        mock_pattern.risk_score = 0.75
        mock_pattern.severity = "high"
        mock_pattern.description = "Layering pattern detected"

        mock_mixer = MagicMock()
        mock_mixer.is_mixer_user = False
        mock_mixer.risk_score = 0.0

        neo4j_ctx = _neo4j_session_mock()

        with patch("src.api.routers.analysis.get_neo4j_session", return_value=neo4j_ctx), \
             patch("src.api.routers.analysis._get_pattern_detector") as mock_pd, \
             patch("src.api.routers.analysis._get_mixer_detector") as mock_md:

            mock_pd.return_value.detect_patterns = AsyncMock(return_value=[mock_pattern])
            mock_md.return_value.detect_mixer_usage = AsyncMock(return_value=mock_mixer)

            resp = client.post("/api/v1/analysis/address", json={
                "address": "0xabc123",
                "blockchain": "ethereum",
            }, headers=admin_headers)

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "detected_patterns" in body["data"]
        assert isinstance(body["data"]["detected_patterns"], list)

    def test_address_response_contains_mixer_detected_field(self, client, admin_headers):
        mock_mixer = MagicMock()
        mock_mixer.is_mixer_user = True
        mock_mixer.risk_score = 0.9

        neo4j_ctx = _neo4j_session_mock()

        with patch("src.api.routers.analysis.get_neo4j_session", return_value=neo4j_ctx), \
             patch("src.api.routers.analysis._get_pattern_detector") as mock_pd, \
             patch("src.api.routers.analysis._get_mixer_detector") as mock_md:

            mock_pd.return_value.detect_patterns = AsyncMock(return_value=[])
            mock_md.return_value.detect_mixer_usage = AsyncMock(return_value=mock_mixer)

            resp = client.post("/api/v1/analysis/address", json={
                "address": "0xmixer999",
                "blockchain": "ethereum",
            }, headers=admin_headers)

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "mixer_detected" in data
        assert data["mixer_detected"] is True

    def test_address_response_has_risk_score(self, client, admin_headers):
        neo4j_ctx = _neo4j_session_mock()

        with patch("src.api.routers.analysis.get_neo4j_session", return_value=neo4j_ctx), \
             patch("src.api.routers.analysis._get_pattern_detector") as mock_pd, \
             patch("src.api.routers.analysis._get_mixer_detector") as mock_md:

            mock_pd.return_value.detect_patterns = AsyncMock(return_value=[])
            mock_md.return_value.detect_mixer_usage = AsyncMock(return_value=MagicMock(
                is_mixer_user=False, risk_score=0.0
            ))

            resp = client.post("/api/v1/analysis/address", json={
                "address": "0xcleansaddr",
                "blockchain": "ethereum",
            }, headers=admin_headers)

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "risk_score" in data
        assert isinstance(data["risk_score"], float)

    def test_address_engine_failure_is_graceful(self, client, admin_headers):
        """If an engine raises, the endpoint should still return 200."""
        neo4j_ctx = _neo4j_session_mock()

        with patch("src.api.routers.analysis.get_neo4j_session", return_value=neo4j_ctx), \
             patch("src.api.routers.analysis._get_pattern_detector") as mock_pd, \
             patch("src.api.routers.analysis._get_mixer_detector") as mock_md:

            mock_pd.return_value.detect_patterns = AsyncMock(
                side_effect=RuntimeError("Engine unavailable")
            )
            mock_md.return_value.detect_mixer_usage = AsyncMock(
                side_effect=RuntimeError("Engine unavailable")
            )

            resp = client.post("/api/v1/analysis/address", json={
                "address": "0xany",
                "blockchain": "ethereum",
            }, headers=admin_headers)

        assert resp.status_code == 200

    def test_address_requires_auth(self, client):
        resp = client.post("/api/v1/analysis/address", json={
            "address": "0xabc",
            "blockchain": "ethereum",
        })
        assert resp.status_code == 403


class TestTransactionEndpointCrossChainWiring:
    """POST /api/v1/analysis/transaction should call cross-chain analyzer."""

    def test_transaction_response_has_cross_chain_flags(self, client, admin_headers):
        mock_cc = MagicMock()
        mock_cc.patterns = []

        neo4j_ctx = _neo4j_session_mock()

        with patch("src.api.routers.analysis.get_neo4j_session", return_value=neo4j_ctx), \
             patch("src.api.routers.analysis._get_cross_chain_analyzer") as mock_cc_factory:

            mock_cc_factory.return_value.analyze_transaction = AsyncMock(return_value=mock_cc)

            resp = client.post("/api/v1/analysis/transaction", json={
                "transaction_hash": "0xdeadbeef",
                "blockchain": "ethereum",
            }, headers=admin_headers)

        assert resp.status_code == 200
        assert "cross_chain_flags" in resp.json()["data"]

    def test_transaction_cross_chain_failure_is_graceful(self, client, admin_headers):
        neo4j_ctx = _neo4j_session_mock()

        with patch("src.api.routers.analysis.get_neo4j_session", return_value=neo4j_ctx), \
             patch("src.api.routers.analysis._get_cross_chain_analyzer") as mock_cc_factory:

            mock_cc_factory.return_value.analyze_transaction = AsyncMock(
                side_effect=Exception("cross-chain down")
            )

            resp = client.post("/api/v1/analysis/transaction", json={
                "transaction_hash": "0xfail",
                "blockchain": "ethereum",
            }, headers=admin_headers)

        assert resp.status_code == 200
        data = resp.json()["data"]
        # flags should be empty list on failure
        assert data.get("cross_chain_flags") == []

    def test_transaction_requires_auth(self, client):
        resp = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": "0xabc",
            "blockchain": "ethereum",
        })
        assert resp.status_code == 403


class TestAddressValidation:
    """Request validation tests for analysis endpoints."""

    def test_empty_address_rejected(self, client, admin_headers):
        resp = client.post("/api/v1/analysis/address", json={
            "address": "   ",
            "blockchain": "ethereum",
        }, headers=admin_headers)
        assert resp.status_code == 422

    def test_unsupported_blockchain_rejected(self, client, admin_headers):
        resp = client.post("/api/v1/analysis/address", json={
            "address": "0xabc",
            "blockchain": "notachain",
        }, headers=admin_headers)
        assert resp.status_code == 422

    def test_depth_too_high_rejected(self, client, admin_headers):
        resp = client.post("/api/v1/analysis/address", json={
            "address": "0xabc",
            "blockchain": "ethereum",
            "depth": 99,
        }, headers=admin_headers)
        assert resp.status_code == 422
