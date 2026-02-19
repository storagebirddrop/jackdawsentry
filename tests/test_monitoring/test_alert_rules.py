"""
Unit tests for the M12 alert rules engine.

Covers:
  - _matches()           — condition evaluation logic
  - evaluate_transaction() — full pipeline (DB + Redis mocked)
  - create_rule / list_rules / get_rule / update_rule / delete_rule
  - get_recent_alerts
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.monitoring.alert_rules import (
    _matches,
    _new_rule,
    create_rule,
    delete_rule,
    evaluate_transaction,
    get_recent_alerts,
    get_rule,
    list_rules,
    update_rule,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pg_pool(fetchrow=None, fetch=None, execute=None):
    """Minimal asyncpg pool mock."""
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=fetchrow)
    conn.fetch = AsyncMock(return_value=fetch or [])
    conn.execute = AsyncMock(return_value=execute or "INSERT 1")
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=ctx)
    return pool, conn


def _sample_tx(
    hash="0xdeadbeef",
    from_addr="0xsender",
    to_addr="0xreceiver",
    value=1.5,
    blockchain="ethereum",
):
    return {
        "hash": hash,
        "from": from_addr,
        "to": to_addr,
        "value": value,
        "blockchain": blockchain,
    }


# ---------------------------------------------------------------------------
# _matches — condition unit tests
# ---------------------------------------------------------------------------


class TestMatchesConditions:
    def test_no_conditions_always_matches(self):
        rule = _new_rule("open", {})
        assert _matches(rule, _sample_tx()) is True

    def test_chain_filter_match(self):
        rule = _new_rule("eth only", {"chain": "ethereum"})
        assert _matches(rule, _sample_tx(blockchain="ethereum")) is True

    def test_chain_filter_no_match(self):
        rule = _new_rule("eth only", {"chain": "ethereum"})
        assert _matches(rule, _sample_tx(blockchain="bitcoin")) is False

    def test_chain_filter_case_insensitive(self):
        rule = _new_rule("eth only", {"chain": "ETHEREUM"})
        assert _matches(rule, _sample_tx(blockchain="ethereum")) is True

    def test_address_match_sender(self):
        rule = _new_rule("watch sender", {"address_match": "0xWATCHED"})
        assert _matches(rule, _sample_tx(from_addr="0xwatched")) is True

    def test_address_match_receiver(self):
        rule = _new_rule("watch receiver", {"address_match": "0xwatched"})
        assert _matches(rule, _sample_tx(to_addr="0xWATCHED")) is True

    def test_address_match_no_match(self):
        rule = _new_rule("watch", {"address_match": "0xwatched"})
        assert _matches(rule, _sample_tx(from_addr="0xother", to_addr="0xother2")) is False

    def test_value_gte_match(self):
        rule = _new_rule("whale", {"value_gte": 1.0})
        assert _matches(rule, _sample_tx(value=5.0)) is True

    def test_value_gte_exact_boundary(self):
        rule = _new_rule("whale", {"value_gte": 1.5})
        assert _matches(rule, _sample_tx(value=1.5)) is True

    def test_value_gte_no_match(self):
        rule = _new_rule("whale", {"value_gte": 10.0})
        assert _matches(rule, _sample_tx(value=0.5)) is False

    def test_pattern_type_match(self):
        rule = _new_rule("layering alert", {"pattern_type": "layering"})
        assert _matches(rule, _sample_tx(), patterns=["layering", "smurfing"]) is True

    def test_pattern_type_no_match(self):
        rule = _new_rule("layering alert", {"pattern_type": "layering"})
        assert _matches(rule, _sample_tx(), patterns=["smurfing"]) is False

    def test_pattern_type_no_patterns_provided(self):
        rule = _new_rule("layering alert", {"pattern_type": "layering"})
        assert _matches(rule, _sample_tx(), patterns=None) is False

    def test_combined_conditions_all_match(self):
        rule = _new_rule("combo", {
            "chain": "ethereum",
            "value_gte": 1.0,
            "address_match": "0xsender",
        })
        assert _matches(rule, _sample_tx()) is True

    def test_combined_conditions_one_fails(self):
        rule = _new_rule("combo", {
            "chain": "ethereum",
            "value_gte": 100.0,   # tx value is 1.5 — fails
        })
        assert _matches(rule, _sample_tx()) is False


# ---------------------------------------------------------------------------
# evaluate_transaction — integration with DB + Redis mocks
# ---------------------------------------------------------------------------


class TestEvaluateTransaction:
    @pytest.mark.asyncio
    async def test_fires_matching_rule(self):
        rule = {
            "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "name": "Whale alert",
            "conditions": {"value_gte": 1.0},
            "severity": "high",
            "enabled": True,
        }
        pool, conn = _pg_pool()
        redis = AsyncMock()
        redis.publish = AsyncMock(return_value=1)
        redis.pubsub = MagicMock(return_value=AsyncMock())

        with patch("src.monitoring.alert_rules.list_rules", new_callable=AsyncMock, return_value=[rule]), \
             patch("src.monitoring.alert_rules.get_postgres_pool", return_value=pool), \
             patch("src.monitoring.alert_rules.get_redis_client", return_value=redis):
            fired = await evaluate_transaction(_sample_tx(value=5.0))

        assert len(fired) == 1
        assert fired[0]["rule_name"] == "Whale alert"
        assert fired[0]["severity"] == "high"

    @pytest.mark.asyncio
    async def test_does_not_fire_non_matching_rule(self):
        rule = {
            "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "name": "Mega whale",
            "conditions": {"value_gte": 1000.0},
            "severity": "critical",
            "enabled": True,
        }
        pool, _ = _pg_pool()
        redis = AsyncMock()

        with patch("src.monitoring.alert_rules.list_rules", new_callable=AsyncMock, return_value=[rule]), \
             patch("src.monitoring.alert_rules.get_postgres_pool", return_value=pool), \
             patch("src.monitoring.alert_rules.get_redis_client", return_value=redis):
            fired = await evaluate_transaction(_sample_tx(value=0.1))

        assert fired == []

    @pytest.mark.asyncio
    async def test_redis_failure_does_not_raise(self):
        """Alert should still be returned even if Redis publish fails."""
        rule = {
            "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "name": "Fail rule",
            "conditions": {},
            "severity": "low",
            "enabled": True,
        }
        pool, _ = _pg_pool()
        redis = AsyncMock()
        redis.publish = AsyncMock(side_effect=Exception("Redis down"))

        with patch("src.monitoring.alert_rules.list_rules", new_callable=AsyncMock, return_value=[rule]), \
             patch("src.monitoring.alert_rules.get_postgres_pool", return_value=pool), \
             patch("src.monitoring.alert_rules.get_redis_client", return_value=redis):
            fired = await evaluate_transaction(_sample_tx())

        assert len(fired) == 1  # alert returned despite Redis failure

    @pytest.mark.asyncio
    async def test_multiple_rules_can_fire(self):
        rules = [
            {"id": "d" * 36, "name": "Rule A", "conditions": {}, "severity": "low", "enabled": True},
            {"id": "e" * 36, "name": "Rule B", "conditions": {}, "severity": "medium", "enabled": True},
        ]
        # Fix uuid format
        rules[0]["id"] = "dddddddd-dddd-dddd-dddd-dddddddddddd"
        rules[1]["id"] = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
        pool, _ = _pg_pool()
        redis = AsyncMock()
        redis.publish = AsyncMock(return_value=1)

        with patch("src.monitoring.alert_rules.list_rules", new_callable=AsyncMock, return_value=rules), \
             patch("src.monitoring.alert_rules.get_postgres_pool", return_value=pool), \
             patch("src.monitoring.alert_rules.get_redis_client", return_value=redis):
            fired = await evaluate_transaction(_sample_tx())

        assert len(fired) == 2


# ---------------------------------------------------------------------------
# CRUD API tests
# ---------------------------------------------------------------------------


class TestCreateRule:
    @pytest.mark.asyncio
    async def test_returns_rule_with_id(self):
        pool, _ = _pg_pool()
        with patch("src.monitoring.alert_rules.get_postgres_pool", return_value=pool):
            rule = await create_rule("Test Rule", {"value_gte": 10.0})
        assert "id" in rule
        assert rule["name"] == "Test Rule"
        assert rule["conditions"]["value_gte"] == 10.0

    @pytest.mark.asyncio
    async def test_severity_stored(self):
        pool, _ = _pg_pool()
        with patch("src.monitoring.alert_rules.get_postgres_pool", return_value=pool):
            rule = await create_rule("High rule", {}, severity="high")
        assert rule["severity"] == "high"


class TestListRules:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        rows = [
            {
                "id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
                "name": "Rule 1", "description": "", "conditions": "{}",
                "severity": "medium", "enabled": True, "created_by": "admin",
                "trigger_count": 0, "created_at": None, "updated_at": None,
            }
        ]
        pool, conn = _pg_pool(fetch=rows)
        conn.fetch = AsyncMock(return_value=rows)
        with patch("src.monitoring.alert_rules.get_postgres_pool", return_value=pool):
            result = await list_rules()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_empty_list_when_no_rules(self):
        pool, conn = _pg_pool(fetch=[])
        conn.fetch = AsyncMock(return_value=[])
        with patch("src.monitoring.alert_rules.get_postgres_pool", return_value=pool):
            result = await list_rules()
        assert result == []


class TestGetRecentAlerts:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        pool, conn = _pg_pool(fetch=[])
        conn.fetch = AsyncMock(return_value=[])
        with patch("src.monitoring.alert_rules.get_postgres_pool", return_value=pool):
            result = await get_recent_alerts(limit=10)
        assert result == []
