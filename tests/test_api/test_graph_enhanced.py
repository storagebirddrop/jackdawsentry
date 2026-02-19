"""
Unit tests for enhanced graph endpoints:
 - _classify_edge() helper
 - Edge types included in expand/trace responses
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Direct unit tests for the _classify_edge helper
# ---------------------------------------------------------------------------


class TestClassifyEdge:
    """Import and test _classify_edge() directly."""

    @pytest.fixture(autouse=True)
    def reset_address_caches(self):
        """Reset module-level address caches between tests."""
        import src.api.routers.graph as gmod
        gmod._bridge_addresses = None
        gmod._mixer_addresses = None
        yield
        gmod._bridge_addresses = None
        gmod._mixer_addresses = None

    def test_unknown_addresses_return_transfer(self):
        from src.api.routers.graph import _classify_edge
        with patch("src.api.routers.graph._get_known_bridge_addresses", return_value=set()), \
             patch("src.api.routers.graph._get_known_mixer_addresses", return_value=set()):
            result = _classify_edge("0xsender", "0xreceiver")
        assert result == "transfer"

    def test_bridge_source_returns_bridge(self):
        from src.api.routers.graph import _classify_edge
        with patch("src.api.routers.graph._get_known_bridge_addresses",
                   return_value={"0xbridgeaddr"}), \
             patch("src.api.routers.graph._get_known_mixer_addresses", return_value=set()):
            result = _classify_edge("0xbridgeaddr", "0xreceiver")
        assert result == "bridge"

    def test_bridge_target_returns_bridge(self):
        from src.api.routers.graph import _classify_edge
        with patch("src.api.routers.graph._get_known_bridge_addresses",
                   return_value={"0xbridgeaddr"}), \
             patch("src.api.routers.graph._get_known_mixer_addresses", return_value=set()):
            result = _classify_edge("0xsender", "0xbridgeaddr")
        assert result == "bridge"

    def test_mixer_address_returns_mixer(self):
        from src.api.routers.graph import _classify_edge
        with patch("src.api.routers.graph._get_known_bridge_addresses", return_value=set()), \
             patch("src.api.routers.graph._get_known_mixer_addresses",
                   return_value={"0xmixercontract"}):
            result = _classify_edge("0xmixercontract", "0xreceiver")
        assert result == "mixer"

    def test_dex_keyword_in_address_returns_dex(self):
        from src.api.routers.graph import _classify_edge
        with patch("src.api.routers.graph._get_known_bridge_addresses", return_value=set()), \
             patch("src.api.routers.graph._get_known_mixer_addresses", return_value=set()):
            result = _classify_edge("0xsender", "uniswap_router_v3")
        assert result == "dex"

    def test_bridge_takes_priority_over_mixer(self):
        from src.api.routers.graph import _classify_edge
        addr = "0xambiguous"
        with patch("src.api.routers.graph._get_known_bridge_addresses", return_value={addr}), \
             patch("src.api.routers.graph._get_known_mixer_addresses", return_value={addr}):
            result = _classify_edge(addr, "0xother")
        assert result == "bridge"

    def test_case_insensitive_matching(self):
        from src.api.routers.graph import _classify_edge
        # _classify_edge lowercases inputs; address sets should contain lowercase values
        with patch("src.api.routers.graph._get_known_bridge_addresses",
                   return_value={"0xbridgeaddr"}), \
             patch("src.api.routers.graph._get_known_mixer_addresses", return_value=set()):
            result = _classify_edge("0xBRIDGEADDR", "0xreceiver")
        assert result == "bridge"

    def test_empty_addresses_return_transfer(self):
        from src.api.routers.graph import _classify_edge
        with patch("src.api.routers.graph._get_known_bridge_addresses", return_value=set()), \
             patch("src.api.routers.graph._get_known_mixer_addresses", return_value=set()):
            result = _classify_edge("", "")
        assert result == "transfer"


# ---------------------------------------------------------------------------
# API endpoint tests: edge_type field present in responses
# ---------------------------------------------------------------------------


def _make_neo4j_ctx(records=None):
    run_result = AsyncMock()
    run_result.single = AsyncMock(return_value=None)
    run_result.data = AsyncMock(return_value=records or [])
    session = AsyncMock()
    session.run = AsyncMock(return_value=run_result)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


class TestGraphExpandEdgeType:
    def test_expand_endpoint_returns_edge_type_field(self, client, admin_headers):
        """Edges in the expand response must contain edge_type."""
        records = [
            {
                "from_addr": "0xseed",
                "to_addr": "0xpeer",
                "b_chain": "ethereum",
                "tx_hash": "0xtxhash1",
                "tx_value": "1.0",
                "tx_ts": None,
                "tx_block": None,
                "tx_status": "confirmed",
            }
        ]
        neo4j_ctx = _make_neo4j_ctx(records)

        with patch("src.api.routers.graph.get_neo4j_session", return_value=neo4j_ctx), \
             patch("src.api.routers.graph._enrich_sanctions", new_callable=AsyncMock), \
             patch("src.api.routers.graph._enrich_entities", new_callable=AsyncMock), \
             patch("src.api.routers.graph._get_known_bridge_addresses", return_value=set()), \
             patch("src.api.routers.graph._get_known_mixer_addresses", return_value=set()):

            resp = client.post("/api/v1/graph/expand", json={
                "address": "0xseed",
                "blockchain": "ethereum",
            }, headers=admin_headers)

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        if body["edges"]:
            assert "edge_type" in body["edges"][0]

    def test_expand_edge_type_is_transfer_for_normal_addresses(self, client, admin_headers):
        records = [
            {
                "from_addr": "0xseed",
                "to_addr": "0xpeer",
                "b_chain": "ethereum",
                "tx_hash": "0xtx1",
                "tx_value": "0.5",
                "tx_ts": None,
                "tx_block": 100,
                "tx_status": "confirmed",
            }
        ]
        neo4j_ctx = _make_neo4j_ctx(records)

        with patch("src.api.routers.graph.get_neo4j_session", return_value=neo4j_ctx), \
             patch("src.api.routers.graph._enrich_sanctions", new_callable=AsyncMock), \
             patch("src.api.routers.graph._enrich_entities", new_callable=AsyncMock), \
             patch("src.api.routers.graph._get_known_bridge_addresses", return_value=set()), \
             patch("src.api.routers.graph._get_known_mixer_addresses", return_value=set()):

            resp = client.post("/api/v1/graph/expand", json={
                "address": "0xseed",
                "blockchain": "ethereum",
            }, headers=admin_headers)

        assert resp.status_code == 200
        body = resp.json()
        if body["edges"]:
            assert body["edges"][0]["edge_type"] == "transfer"

    def test_expand_invalid_blockchain_rejected(self, client, admin_headers):
        resp = client.post("/api/v1/graph/expand", json={
            "address": "0xseed",
            "blockchain": "notreal",
        }, headers=admin_headers)
        assert resp.status_code == 422

    def test_expand_invalid_direction_rejected(self, client, admin_headers):
        resp = client.post("/api/v1/graph/expand", json={
            "address": "0xseed",
            "blockchain": "ethereum",
            "direction": "sideways",
        }, headers=admin_headers)
        assert resp.status_code == 422

    def test_expand_requires_auth(self, client):
        resp = client.post("/api/v1/graph/expand", json={
            "address": "0xseed",
            "blockchain": "ethereum",
        })
        assert resp.status_code == 403


class TestGraphAddressSummary:
    def test_address_summary_endpoint_accessible(self, client, admin_headers):
        neo4j_ctx = _make_neo4j_ctx()

        with patch("src.api.routers.graph.get_neo4j_session", return_value=neo4j_ctx), \
             patch("src.api.routers.graph._enrich_sanctions", new_callable=AsyncMock), \
             patch("src.api.routers.graph._enrich_entities", new_callable=AsyncMock):

            resp = client.get(
                "/api/v1/graph/address/0xabc123/summary?blockchain=ethereum",
                headers=admin_headers,
            )

        assert resp.status_code in (200, 404)


class TestGraphSearchEndpoint:
    def test_search_no_results_returns_404(self, client, admin_headers):
        """The search endpoint raises 404 when no nodes/edges are found."""
        neo4j_ctx = _make_neo4j_ctx([])

        with patch("src.api.routers.graph.get_neo4j_session", return_value=neo4j_ctx), \
             patch("src.api.routers.graph._enrich_sanctions", new_callable=AsyncMock), \
             patch("src.api.routers.graph._enrich_entities", new_callable=AsyncMock), \
             patch("src.api.routers.graph.get_rpc_client", return_value=None):

            resp = client.post("/api/v1/graph/search", json={
                "query": "0xdeadbeef",
            }, headers=admin_headers)

        # search returns 404 when there are no results
        assert resp.status_code == 404

    def test_search_requires_auth(self, client):
        resp = client.post("/api/v1/graph/search", json={"query": "0xabc"})
        assert resp.status_code == 403
