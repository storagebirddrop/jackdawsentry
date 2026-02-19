"""
Unit tests for the entity attribution service (M11).

Covers:
 - _classify_entity_type()  — keyword-based classification
 - _risk_for_type()          — risk level defaults by type
 - lookup_address()          — single address lookup
 - lookup_addresses_bulk()   — bulk lookup
 - get_entity_details()      — full entity with addresses
 - search_entities()         — name/type search
 - sync_all_labels()         — orchestration + partial failure handling
 - ingest_etherscan_labels() — HTTP fetch + record ingestion
 - ingest_scam_databases()   — scam DB ingest
 - ingest_community_labels() — community label ingest
"""

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
    ingest_etherscan_labels,
    ingest_scam_databases,
)


# ---------------------------------------------------------------------------
# _classify_entity_type
# ---------------------------------------------------------------------------


class TestClassifyEntityType:
    def test_exchange_keyword(self):
        assert _classify_entity_type("Binance Hot Wallet") == "exchange"

    def test_mixer_keyword(self):
        assert _classify_entity_type("Tornado Cash Mixer") == "mixer"

    def test_darknet_keyword(self):
        assert _classify_entity_type("AlphaBay darknet") == "darknet_market"

    def test_scam_keyword(self):
        assert _classify_entity_type("Fake Elon Giveaway scam") == "scam"

    def test_bridge_keyword(self):
        assert _classify_entity_type("Wormhole Bridge") == "bridge"

    def test_unknown_fallback(self):
        assert _classify_entity_type("xyzqwerty123") == "unknown"

    def test_labels_augment_classification(self):
        # name alone is ambiguous but labels tip it over
        result = _classify_entity_type("SomeWallet", labels=["exchange", "cex"])
        assert result == "exchange"

    def test_empty_name_returns_unknown(self):
        assert _classify_entity_type("") == "unknown"

    def test_none_name_returns_unknown(self):
        assert _classify_entity_type(None) == "unknown"


# ---------------------------------------------------------------------------
# _risk_for_type
# ---------------------------------------------------------------------------


class TestRiskForType:
    def test_mixer_is_high(self):
        assert _risk_for_type("mixer") == "high"

    def test_darknet_is_high(self):
        assert _risk_for_type("darknet_market") == "high"

    def test_scam_is_high(self):
        assert _risk_for_type("scam") == "high"

    def test_ransomware_is_high(self):
        assert _risk_for_type("ransomware") == "high"

    def test_exchange_is_low(self):
        assert _risk_for_type("exchange") == "low"

    def test_bridge_is_medium(self):
        assert _risk_for_type("bridge") == "medium"

    def test_unknown_is_medium(self):
        assert _risk_for_type("unknown") == "medium"


# ---------------------------------------------------------------------------
# Helpers for DB mocking
# ---------------------------------------------------------------------------


def _make_pg_pool(fetchrow_result=None, fetch_result=None):
    """Return a mock asyncpg pool that returns canned results."""
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=fetchrow_result)
    conn.fetch = AsyncMock(return_value=fetch_result or [])
    conn.execute = AsyncMock(return_value=None)

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=_async_ctx(conn))
    return pool, conn


def _async_ctx(value):
    """Minimal async context manager returning *value*."""
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=value)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


# ---------------------------------------------------------------------------
# lookup_address
# ---------------------------------------------------------------------------


class TestLookupAddress:
    @pytest.mark.asyncio
    async def test_returns_entity_dict_when_found(self):
        row = {
            "entity_name": "Binance",
            "entity_type": "exchange",
            "category": "cex",
            "risk_level": "low",
            "description": None,
            "website": "https://binance.com",
            "label": "Binance Hot Wallet",
            "confidence": 0.95,
            "source": "etherscan_labels",
            "blockchain": "ethereum",
        }
        pool, _ = _make_pg_pool(fetchrow_result=row)

        with patch("src.services.entity_attribution.get_postgres_pool", return_value=pool):
            result = await lookup_address("0xBINANCE", "ethereum")

        assert result is not None
        assert result["entity_name"] == "Binance"
        assert result["entity_type"] == "exchange"
        assert result["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        pool, _ = _make_pg_pool(fetchrow_result=None)

        with patch("src.services.entity_attribution.get_postgres_pool", return_value=pool):
            result = await lookup_address("0xunknown")

        assert result is None

    @pytest.mark.asyncio
    async def test_normalises_address_to_lowercase(self):
        pool, conn = _make_pg_pool(fetchrow_result=None)

        with patch("src.services.entity_attribution.get_postgres_pool", return_value=pool):
            await lookup_address("0xABCDEF", "ethereum")

        # fetchrow is called once; verify first positional arg is lowercased
        call_args = conn.fetchrow.call_args
        assert "0xabcdef" in call_args[0]

    @pytest.mark.asyncio
    async def test_confidence_defaults_to_1_when_none(self):
        row = {
            "entity_name": "SomeExchange",
            "entity_type": "exchange",
            "category": None,
            "risk_level": "low",
            "description": None,
            "website": None,
            "label": None,
            "confidence": None,
            "source": "community",
            "blockchain": "ethereum",
        }
        pool, _ = _make_pg_pool(fetchrow_result=row)

        with patch("src.services.entity_attribution.get_postgres_pool", return_value=pool):
            result = await lookup_address("0xaddr")

        assert result["confidence"] == 1.0


# ---------------------------------------------------------------------------
# lookup_addresses_bulk
# ---------------------------------------------------------------------------


class TestLookupAddressesBulk:
    @pytest.mark.asyncio
    async def test_empty_input_returns_empty_dict(self):
        pool, _ = _make_pg_pool()
        with patch("src.services.entity_attribution.get_postgres_pool", return_value=pool):
            result = await lookup_addresses_bulk([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_dict_keyed_by_address(self):
        rows = [
            {
                "address": "0xaaa",
                "entity_name": "Exchange A",
                "entity_type": "exchange",
                "category": "cex",
                "risk_level": "low",
                "label": "EA Hot",
                "confidence": 0.9,
                "source": "etherscan_labels",
            }
        ]
        pool, _ = _make_pg_pool(fetch_result=rows)

        with patch("src.services.entity_attribution.get_postgres_pool", return_value=pool):
            result = await lookup_addresses_bulk(["0xaaa", "0xbbb"])

        assert "0xaaa" in result
        assert result["0xaaa"]["entity_name"] == "Exchange A"
        assert "0xbbb" not in result  # not in DB

    @pytest.mark.asyncio
    async def test_no_results_returns_empty_dict(self):
        pool, _ = _make_pg_pool(fetch_result=[])
        with patch("src.services.entity_attribution.get_postgres_pool", return_value=pool):
            result = await lookup_addresses_bulk(["0xzzz"])
        assert result == {}


# ---------------------------------------------------------------------------
# get_entity_details
# ---------------------------------------------------------------------------


class TestGetEntityDetails:
    @pytest.mark.asyncio
    async def test_returns_none_for_missing_entity(self):
        pool, conn = _make_pg_pool(fetchrow_result=None)

        with patch("src.services.entity_attribution.get_postgres_pool", return_value=pool):
            result = await get_entity_details("nonexistent-uuid")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_entity_with_addresses(self):
        entity_row = {
            "id": "uuid-1",
            "name": "Binance",
            "entity_type": "exchange",
            "category": "cex",
            "risk_level": "low",
            "description": None,
            "website": "https://binance.com",
            "country": "KY",
            "metadata": None,
            "created_at": None,
            "updated_at": None,
        }
        address_rows = [
            {
                "address": "0xbinance1",
                "blockchain": "ethereum",
                "label": "Binance Hot Wallet 1",
                "confidence": 0.99,
                "source": "etherscan_labels",
                "first_seen_at": None,
                "last_verified_at": None,
            }
        ]
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=entity_row)
        conn.fetch = AsyncMock(return_value=address_rows)
        pool = MagicMock()
        pool.acquire = MagicMock(return_value=_async_ctx(conn))

        with patch("src.services.entity_attribution.get_postgres_pool", return_value=pool):
            result = await get_entity_details("uuid-1")

        assert result is not None
        assert result["name"] == "Binance"
        assert len(result["addresses"]) == 1
        assert result["addresses"][0]["address"] == "0xbinance1"


# ---------------------------------------------------------------------------
# search_entities
# ---------------------------------------------------------------------------


class TestSearchEntities:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        rows = [
            {
                "id": "uuid-1",
                "name": "Binance",
                "entity_type": "exchange",
                "category": "cex",
                "risk_level": "low",
                "description": None,
            }
        ]
        pool, _ = _make_pg_pool(fetch_result=rows)

        with patch("src.services.entity_attribution.get_postgres_pool", return_value=pool):
            result = await search_entities("Binance")

        assert isinstance(result, list)
        assert result[0]["name"] == "Binance"

    @pytest.mark.asyncio
    async def test_empty_results_returns_empty_list(self):
        pool, _ = _make_pg_pool(fetch_result=[])

        with patch("src.services.entity_attribution.get_postgres_pool", return_value=pool):
            result = await search_entities("xyznotfound")

        assert result == []


# ---------------------------------------------------------------------------
# sync_all_labels (orchestration)
# ---------------------------------------------------------------------------


class TestSyncAllLabels:
    @pytest.mark.asyncio
    async def test_returns_dict_with_source_keys(self):
        with patch("src.services.entity_attribution.ingest_etherscan_labels",
                   new_callable=AsyncMock, return_value=100), \
             patch("src.services.entity_attribution.ingest_scam_databases",
                   new_callable=AsyncMock, return_value=50), \
             patch("src.services.entity_attribution.ingest_community_labels",
                   new_callable=AsyncMock, return_value=200), \
             patch("src.services.entity_attribution.get_postgres_pool",
                   return_value=_make_pg_pool()[0]):
            result = await sync_all_labels()

        assert isinstance(result, dict)
        # at least one source key present
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_partial_failure_still_returns_results(self):
        """If one ingestor raises, sync_all_labels should still return results."""
        with patch("src.services.entity_attribution.ingest_etherscan_labels",
                   new_callable=AsyncMock, side_effect=Exception("network error")), \
             patch("src.services.entity_attribution.ingest_scam_databases",
                   new_callable=AsyncMock, return_value=50), \
             patch("src.services.entity_attribution.ingest_community_labels",
                   new_callable=AsyncMock, return_value=200), \
             patch("src.services.entity_attribution.get_postgres_pool",
                   return_value=_make_pg_pool()[0]):
            # should not raise
            result = await sync_all_labels()

        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# ingest_etherscan_labels
# ---------------------------------------------------------------------------


class TestIngestEtherscanLabels:
    @pytest.mark.asyncio
    async def test_returns_zero_on_fetch_failure(self):
        with patch("src.services.entity_attribution._fetch_json",
                   new_callable=AsyncMock, return_value=None):
            count = await ingest_etherscan_labels()
        assert count == 0

    @pytest.mark.asyncio
    async def test_returns_zero_on_empty_data(self):
        with patch("src.services.entity_attribution._fetch_json",
                   new_callable=AsyncMock, return_value={}):
            count = await ingest_etherscan_labels()
        assert count == 0

    @pytest.mark.asyncio
    async def test_ingests_records_and_returns_count(self):
        fake_data = {
            "0xabc": {"name": "Binance 1", "labels": ["exchange"]},
            "0xdef": {"name": "Coinbase 1", "labels": ["exchange", "cex"]},
        }
        pool, conn = _make_pg_pool()
        conn.fetchrow = AsyncMock(return_value={"id": "uuid-x"})

        with patch("src.services.entity_attribution._fetch_json",
                   new_callable=AsyncMock, return_value=fake_data), \
             patch("src.services.entity_attribution.get_postgres_pool",
                   return_value=pool):
            count = await ingest_etherscan_labels()

        assert count == 2


# ---------------------------------------------------------------------------
# ingest_scam_databases
# ---------------------------------------------------------------------------


class TestIngestScamDatabases:
    @pytest.mark.asyncio
    async def test_returns_zero_on_fetch_failure(self):
        with patch("src.services.entity_attribution._fetch_json",
                   new_callable=AsyncMock, return_value=None), \
             patch("src.services.entity_attribution._fetch_text",
                   new_callable=AsyncMock, return_value=None):
            count = await ingest_scam_databases()
        assert count == 0
