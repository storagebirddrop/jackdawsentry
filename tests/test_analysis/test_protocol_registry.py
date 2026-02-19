"""
Unit tests for the M13 protocol registry and DeFi decoder.
"""

import pytest

from src.analysis.protocol_registry import (
    classify_address,
    get_all_protocols,
    get_high_risk_addresses,
    get_known_bridge_addresses,
    get_known_dex_addresses,
    get_known_mixer_addresses,
    get_protocol_by_address,
    get_protocols_by_type,
    protocol_count,
)
from src.analysis.defi_decoder import (
    _extract_selector,
    decode_transaction,
    decode_transactions_bulk,
)


# ---------------------------------------------------------------------------
# Protocol registry
# ---------------------------------------------------------------------------


class TestProtocolCount:
    def test_at_least_50_protocols(self):
        assert protocol_count() >= 50

    def test_returns_int(self):
        assert isinstance(protocol_count(), int)


class TestGetAllProtocols:
    def test_returns_list(self):
        protocols = get_all_protocols()
        assert isinstance(protocols, list)
        assert len(protocols) >= 50

    def test_each_has_required_fields(self):
        for p in get_all_protocols():
            assert p.name
            assert p.protocol_type
            assert isinstance(p.chains, list)
            assert isinstance(p.addresses, dict)
            assert p.risk_level in {"low", "medium", "high", "critical"}


class TestGetProtocolsByType:
    def test_bridges_exist(self):
        bridges = get_protocols_by_type("bridge")
        assert len(bridges) >= 5

    def test_dexes_exist(self):
        dexes = get_protocols_by_type("dex")
        assert len(dexes) >= 5

    def test_lending_exists(self):
        lending = get_protocols_by_type("lending")
        assert len(lending) >= 4

    def test_staking_exists(self):
        staking = get_protocols_by_type("staking")
        assert len(staking) >= 2

    def test_yield_farming_exists(self):
        yield_protocols = get_protocols_by_type("yield_farming")
        assert len(yield_protocols) >= 2

    def test_mixers_exist(self):
        mixers = get_protocols_by_type("mixer")
        assert len(mixers) >= 1

    def test_unknown_type_returns_empty(self):
        result = get_protocols_by_type("notatype")
        assert result == []


class TestGetProtocolByAddress:
    def test_finds_uniswap_v2(self):
        # Uniswap V2 router on Ethereum
        proto = get_protocol_by_address("0x7a250d5630b4cf539739df2c5dacb4c659f2488d")
        assert proto is not None
        assert proto.protocol_type == "dex"

    def test_finds_tornado_cash(self):
        proto = get_protocol_by_address("0x12d66f87a04a9e220c9d6d34deef7eb5dbbf4b22")
        assert proto is not None
        assert proto.protocol_type == "mixer"
        assert proto.risk_level == "critical"

    def test_case_insensitive_lookup(self):
        proto_lower = get_protocol_by_address("0x7a250d5630b4cf539739df2c5dacb4c659f2488d")
        proto_upper = get_protocol_by_address("0x7A250D5630B4CF539739DF2C5DACB4C659F2488D")
        assert proto_lower is not None
        assert proto_upper is not None
        assert proto_lower.name == proto_upper.name

    def test_returns_none_for_unknown(self):
        result = get_protocol_by_address("0x0000000000000000000000000000000000000000")
        assert result is None


class TestClassifyAddress:
    def test_classifies_known_contract(self):
        result = classify_address("0x7a250d5630b4cf539739df2c5dacb4c659f2488d")
        assert result is not None
        assert result["protocol_type"] == "dex"
        assert "protocol_name" in result
        assert "risk_level" in result

    def test_returns_none_for_unknown(self):
        result = classify_address("0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef")
        assert result is None


class TestAddressSets:
    def test_bridge_addresses_not_empty(self):
        addrs = get_known_bridge_addresses()
        assert len(addrs) > 0
        # All should be lowercase
        assert all(a == a.lower() for a in addrs)

    def test_dex_addresses_not_empty(self):
        addrs = get_known_dex_addresses()
        assert len(addrs) > 0

    def test_mixer_addresses_not_empty(self):
        addrs = get_known_mixer_addresses()
        assert len(addrs) > 0

    def test_high_risk_includes_tornado(self):
        high_risk = get_high_risk_addresses()
        tornado = "0x12d66f87a04a9e220c9d6d34deef7eb5dbbf4b22"
        assert tornado in high_risk

    def test_sets_contain_lowercase_addresses(self):
        for addr in get_known_bridge_addresses():
            assert addr == addr.lower(), f"Bridge address not lowercase: {addr}"
        for addr in get_known_mixer_addresses():
            assert addr == addr.lower(), f"Mixer address not lowercase: {addr}"


# ---------------------------------------------------------------------------
# DeFi decoder
# ---------------------------------------------------------------------------


class TestExtractSelector:
    def test_extracts_4_bytes(self):
        result = _extract_selector("0x38ed1739abcdef1234567890")
        assert result == "0x38ed1739"

    def test_returns_none_for_empty(self):
        assert _extract_selector(None) is None
        assert _extract_selector("") is None
        assert _extract_selector("0x") is None

    def test_returns_none_for_too_short(self):
        assert _extract_selector("0xaabb") is None

    def test_lowercase_output(self):
        result = _extract_selector("0xABCDEF123456")
        assert result == result.lower()


class TestDecodeTransaction:
    def test_uniswap_v2_swap(self):
        result = decode_transaction(
            to_address="0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
            input_data="0x38ed17390000000000000000000000000000000000000000000000000000000000000001",
        )
        assert result["interaction_type"] == "dex_swap"
        assert result["protocol_name"] is not None
        assert result["confidence"] >= 0.8

    def test_tornado_cash_deposit(self):
        result = decode_transaction(
            to_address="0x12d66f87a04a9e220c9d6d34deef7eb5dbbf4b22",
            input_data="0xb214faa5" + "00" * 32,
        )
        assert result["interaction_type"] == "mixer_deposit"
        assert result["risk_level"] == "critical"

    def test_plain_transfer_no_input(self):
        result = decode_transaction(
            to_address="0x1234567890abcdef1234567890abcdef12345678",
            input_data=None,
        )
        assert result["interaction_type"] == "transfer"
        assert result["confidence"] >= 0.7

    def test_plain_transfer_0x_input(self):
        result = decode_transaction(
            to_address="0x1234567890abcdef1234567890abcdef12345678",
            input_data="0x",
        )
        assert result["interaction_type"] == "transfer"

    def test_unknown_address_unknown_selector(self):
        result = decode_transaction(
            to_address="0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
            input_data="0xffffffff0000000000000000000000000000000000000000000000000000000000000000",
        )
        assert result["interaction_type"] == "unknown"

    def test_protocol_matched_by_address_fallback(self):
        # Lido address but unknown selector → should still identify as staking
        result = decode_transaction(
            to_address="0xae7ab96520de3a18e5e111b5eaab095312d7fe84",
            input_data="0xdeadbeef12345678",
        )
        assert result["protocol_name"] == "Lido Finance"
        assert result["protocol_type"] == "staking"

    def test_aave_supply(self):
        result = decode_transaction(
            to_address="0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2",
            input_data="0x617ba0370000000000000000000000000000000000000000000000000000000000000001",
        )
        assert result["interaction_type"] == "lending_deposit"

    def test_result_has_all_keys(self):
        result = decode_transaction("0xanything")
        for key in ("interaction_type", "protocol_name", "protocol_type", "risk_level", "function_selector", "confidence"):
            assert key in result


class TestBulkDecodeTransactions:
    def test_returns_list_of_same_length(self):
        txs = [
            {"to": "0x7a250d5630b4cf539739df2c5dacb4c659f2488d", "input": "0x38ed1739"},
            {"to": "0xunknownaddress"},
        ]
        results = decode_transactions_bulk(txs)
        assert len(results) == 2

    def test_empty_list_returns_empty(self):
        assert decode_transactions_bulk([]) == []

    def test_uses_to_field(self):
        txs = [{"to": "0x7a250d5630b4cf539739df2c5dacb4c659f2488d"}]
        results = decode_transactions_bulk(txs)
        assert results[0]["protocol_name"] is not None


# ---------------------------------------------------------------------------
# Tracing API endpoint tests
# ---------------------------------------------------------------------------


class TestTracingEndpoints:
    def test_protocols_list_requires_auth(self, client):
        resp = client.get("/api/v1/tracing/protocols")
        assert resp.status_code == 403

    def test_protocols_list_returns_50_plus(self, client, auth_headers):
        resp = client.get("/api/v1/tracing/protocols", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["total_in_registry"] >= 50
        assert body["count"] >= 50

    def test_protocols_filter_by_type(self, client, auth_headers):
        resp = client.get("/api/v1/tracing/protocols?protocol_type=bridge", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert all(p["protocol_type"] == "bridge" for p in body["protocols"])

    def test_lookup_by_address_found(self, client, auth_headers):
        resp = client.get(
            "/api/v1/tracing/protocols/address/0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["protocol"]["protocol_type"] == "dex"

    def test_lookup_by_address_404(self, client, auth_headers):
        resp = client.get(
            "/api/v1/tracing/protocols/address/0x0000000000000000000000000000000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_decode_endpoint(self, client, auth_headers):
        resp = client.post("/api/v1/tracing/decode", json={
            "to_address": "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
            "input_data": "0x38ed1739",
        }, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "decode" in body
        assert body["decode"]["interaction_type"] == "dex_swap"

    def test_bulk_decode_endpoint(self, client, auth_headers):
        resp = client.post("/api/v1/tracing/decode/bulk", json={
            "transactions": [
                {"to": "0x7a250d5630b4cf539739df2c5dacb4c659f2488d", "input": "0x38ed1739"},
                {"to": "0xunknown"},
            ]
        }, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 2

    def test_bulk_decode_rejects_empty(self, client, auth_headers):
        resp = client.post("/api/v1/tracing/decode/bulk", json={
            "transactions": []
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_trace_requires_auth(self, client):
        resp = client.post("/api/v1/tracing/trace", json={
            "address": "0xabc",
            "blockchain": "ethereum",
        })
        assert resp.status_code == 403

    def test_trace_rejects_unsupported_chain(self, client, auth_headers):
        resp = client.post("/api/v1/tracing/trace", json={
            "address": "0xabc",
            "blockchain": "notachain",
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_trace_rejects_empty_address(self, client, auth_headers):
        resp = client.post("/api/v1/tracing/trace", json={
            "address": "",
            "blockchain": "ethereum",
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_trace_rejects_depth_over_10(self, client, auth_headers):
        resp = client.post("/api/v1/tracing/trace", json={
            "address": "0xabc",
            "blockchain": "ethereum",
            "max_depth": 11,
        }, headers=auth_headers)
        assert resp.status_code == 422
