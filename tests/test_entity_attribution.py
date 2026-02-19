"""
Tests for the Entity Attribution Service (M11).
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.entity_attribution import (
    _classify_entity_type,
    _risk_for_type,
    lookup_address,
    lookup_addresses_bulk,
    get_entity_details,
    search_entities,
    sync_all_labels,
    get_sync_status,
    get_entity_counts,
    ingest_etherscan_labels,
)


# ---------------------------------------------------------------------------
# Unit tests for classification helpers
# ---------------------------------------------------------------------------

class TestClassifyEntityType:
    def test_exchange(self):
        assert _classify_entity_type("Binance Hot Wallet") == "exchange"

    def test_mixer(self):
        assert _classify_entity_type("Tornado Cash Router") == "mixer"

    def test_scam(self):
        assert _classify_entity_type("Phishing Contract") == "scam"

    def test_defi(self):
        assert _classify_entity_type("Uniswap V3", ["dex"]) == "defi_protocol"

    def test_unknown(self):
        assert _classify_entity_type("Some Random Name") == "unknown"

    def test_bridge(self):
        assert _classify_entity_type("Wormhole Bridge") == "bridge"

    def test_mining(self):
        assert _classify_entity_type("Ethermine Mining Pool") == "mining_pool"


class TestRiskForType:
    def test_high_risk(self):
        for t in ("mixer", "darknet_market", "ransomware", "scam", "gambling"):
            assert _risk_for_type(t) == "high"

    def test_medium_risk(self):
        for t in ("unknown", "smart_contract", "bridge"):
            assert _risk_for_type(t) == "medium"

    def test_low_risk(self):
        for t in ("exchange", "defi_protocol", "mining_pool", "payment_processor"):
            assert _risk_for_type(t) == "low"


# ---------------------------------------------------------------------------
# Tests for lookup functions (mocked DB)
# ---------------------------------------------------------------------------

def _make_mock_pool():
    """Create a mock asyncpg pool."""
    pool = MagicMock()
    conn = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=None)
    pool.acquire.return_value = ctx
    return pool, conn


@pytest.mark.asyncio
async def test_lookup_address_found():
    pool, conn = _make_mock_pool()
    conn.fetchrow.return_value = {
        "entity_name": "Binance",
        "entity_type": "exchange",
        "category": "cex",
        "risk_level": "low",
        "description": "Major exchange",
        "label": "Binance Hot Wallet 1",
        "confidence": 0.95,
        "source": "etherscan_labels",
        "blockchain": "ethereum",
        "website": None,
    }

    with patch("src.services.entity_attribution.get_postgres_pool", return_value=pool):
        result = await lookup_address("0xBINANCE", "ethereum")

    assert result is not None
    assert result["entity_name"] == "Binance"
    assert result["entity_type"] == "exchange"
    assert result["confidence"] == 0.95


@pytest.mark.asyncio
async def test_lookup_address_not_found():
    pool, conn = _make_mock_pool()
    conn.fetchrow.return_value = None

    with patch("src.services.entity_attribution.get_postgres_pool", return_value=pool):
        result = await lookup_address("0xUNKNOWN", "ethereum")

    assert result is None


@pytest.mark.asyncio
async def test_lookup_bulk():
    pool, conn = _make_mock_pool()
    conn.fetch.return_value = [
        {
            "address": "0xaaa",
            "entity_name": "Exchange A",
            "entity_type": "exchange",
            "category": "cex",
            "risk_level": "low",
            "label": "Exchange A Hot",
            "confidence": 0.9,
            "source": "etherscan_labels",
        },
    ]

    with patch("src.services.entity_attribution.get_postgres_pool", return_value=pool):
        result = await lookup_addresses_bulk(["0xAAA", "0xBBB"], "ethereum")

    assert "0xaaa" in result
    assert result["0xaaa"]["entity_name"] == "Exchange A"
    assert "0xbbb" not in result  # not found


@pytest.mark.asyncio
async def test_lookup_bulk_empty():
    with patch("src.services.entity_attribution.get_postgres_pool"):
        result = await lookup_addresses_bulk([])

    assert result == {}


@pytest.mark.asyncio
async def test_search_entities():
    pool, conn = _make_mock_pool()
    conn.fetch.return_value = [
        {
            "id": "uuid-1",
            "name": "Binance",
            "entity_type": "exchange",
            "category": "cex",
            "risk_level": "low",
            "description": "Major exchange",
        },
    ]

    with patch("src.services.entity_attribution.get_postgres_pool", return_value=pool):
        result = await search_entities("Binance")

    assert len(result) == 1
    assert result[0]["name"] == "Binance"


@pytest.mark.asyncio
async def test_get_entity_details_not_found():
    pool, conn = _make_mock_pool()
    conn.fetchrow.return_value = None

    with patch("src.services.entity_attribution.get_postgres_pool", return_value=pool):
        result = await get_entity_details("nonexistent-id")

    assert result is None


@pytest.mark.asyncio
async def test_sync_status():
    pool, conn = _make_mock_pool()
    conn.fetch.return_value = [
        {"source_key": "etherscan_labels", "name": "Etherscan Labels", "status": "success"},
    ]

    with patch("src.services.entity_attribution.get_postgres_pool", return_value=pool):
        result = await get_sync_status()

    assert len(result) == 1
    assert result[0]["source_key"] == "etherscan_labels"


@pytest.mark.asyncio
async def test_ingest_etherscan_labels_empty():
    """Verify ingest returns 0 when fetch returns nothing."""
    with patch("src.services.entity_attribution._fetch_json", new_callable=AsyncMock, return_value=None):
        count = await ingest_etherscan_labels()
    assert count == 0


@pytest.mark.asyncio
async def test_ingest_etherscan_labels_success():
    """Verify ingest processes entries correctly."""
    mock_data = {
        "0x1234567890abcdef1234567890abcdef12345678": {
            "nameTag": "Binance Hot Wallet",
            "labels": ["exchange"],
        },
        "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd": "Some Label",
    }

    pool, conn = _make_mock_pool()
    conn.fetchrow.return_value = {"id": "fake-uuid"}

    with (
        patch("src.services.entity_attribution._fetch_json", new_callable=AsyncMock, return_value=mock_data),
        patch("src.services.entity_attribution.get_postgres_pool", return_value=pool),
    ):
        count = await ingest_etherscan_labels()

    assert count == 2
