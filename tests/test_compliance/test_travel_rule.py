"""
Unit tests for src/compliance/travel_rule.py (M16)
"""
import pytest
from src.compliance.travel_rule import (
    lookup_vasp,
    requires_travel_rule,
    build_travel_rule_record,
    validate_vasp_info,
    _THRESHOLD_USD,
)


# ---------------------------------------------------------------------------
# requires_travel_rule
# ---------------------------------------------------------------------------


class TestRequiresTravelRule:
    def test_above_threshold_returns_true(self):
        assert requires_travel_rule(1500.0) is True

    def test_at_threshold_returns_true(self):
        assert requires_travel_rule(1000.0) is True

    def test_below_threshold_returns_false(self):
        assert requires_travel_rule(999.99) is False

    def test_zero_returns_false(self):
        assert requires_travel_rule(0.0) is False

    def test_threshold_constant(self):
        assert _THRESHOLD_USD == 1000.0


# ---------------------------------------------------------------------------
# lookup_vasp
# ---------------------------------------------------------------------------


class TestLookupVasp:
    def test_known_prefix_returns_vasp(self):
        vasp = lookup_vasp("0x1111abcdef")
        assert vasp is not None
        assert vasp["name"] == "Coinbase"

    def test_known_prefix_case_insensitive(self):
        vasp = lookup_vasp("0X1111ABCDEF")
        assert vasp is not None

    def test_unknown_address_returns_none(self):
        vasp = lookup_vasp("0xdeadbeef1234567890")
        assert vasp is None

    def test_empty_string_returns_none(self):
        assert lookup_vasp("") is None

    def test_vasp_has_required_fields(self):
        vasp = lookup_vasp("0x2222aabbcc")
        assert vasp is not None
        assert "name" in vasp
        assert "jurisdiction" in vasp
        assert "lei" in vasp


# ---------------------------------------------------------------------------
# build_travel_rule_record
# ---------------------------------------------------------------------------


class TestBuildTravelRuleRecord:
    def test_below_threshold_not_required(self):
        record = build_travel_rule_record(
            "0xtx1", "0xabc", "0xdef", 500.0
        )
        assert record["travel_rule_required"] is False
        assert record["compliance_status"] == "not_required"

    def test_above_threshold_required(self):
        record = build_travel_rule_record(
            "0xtx2", "0xabc", "0xdef", 2000.0
        )
        assert record["travel_rule_required"] is True

    def test_known_vasp_both_sides_compliant(self):
        record = build_travel_rule_record(
            "0xtx3",
            "0x1111originator",
            "0x2222beneficiary",
            5000.0,
            originator_name="Alice",
            beneficiary_name="Bob",
        )
        assert record["compliance_status"] == "compliant"
        assert record["missing_fields"] == []

    def test_no_vasp_non_compliant(self):
        record = build_travel_rule_record(
            "0xtx4", "0xunknown1", "0xunknown2", 5000.0
        )
        assert record["compliance_status"] == "non_compliant"

    def test_partial_vasp_partial_status(self):
        # originator is known VASP; beneficiary unknown
        record = build_travel_rule_record(
            "0xtx5", "0x1111abc", "0xunknown", 5000.0
        )
        assert record["compliance_status"] == "partial"

    def test_missing_fields_listed_when_triggered(self):
        record = build_travel_rule_record(
            "0xtx6", "0xunknown1", "0xunknown2", 5000.0
        )
        mf = record["missing_fields"]
        assert "originator_name" in mf
        assert "beneficiary_name" in mf
        assert "originator_vasp" in mf
        assert "beneficiary_vasp" in mf

    def test_no_missing_fields_below_threshold(self):
        record = build_travel_rule_record(
            "0xtx7", "0xabc", "0xdef", 100.0
        )
        assert record["missing_fields"] == []

    def test_record_has_required_keys(self):
        record = build_travel_rule_record("0xtx8", "0xa", "0xb", 0.0)
        for key in ("tx_hash", "amount_usd", "threshold_usd",
                    "travel_rule_required", "originator", "beneficiary",
                    "compliance_status", "missing_fields"):
            assert key in record

    def test_originator_name_in_record(self):
        record = build_travel_rule_record(
            "0xtx9", "0xa", "0xb", 100.0, originator_name="Alice"
        )
        assert record["originator"]["name"] == "Alice"


# ---------------------------------------------------------------------------
# validate_vasp_info
# ---------------------------------------------------------------------------


class TestValidateVaspInfo:
    def test_complete_vasp_no_errors(self):
        errors = validate_vasp_info({
            "name": "Coinbase",
            "jurisdiction": "US",
            "lei": "KGCEPHLVVKVRZYO1",
        })
        assert errors == []

    def test_missing_name_returns_error(self):
        errors = validate_vasp_info({"name": "", "jurisdiction": "US", "lei": "ABC123"})
        assert any("name" in e for e in errors)

    def test_missing_jurisdiction_returns_error(self):
        errors = validate_vasp_info({"name": "Test", "jurisdiction": "", "lei": "ABC123"})
        assert any("jurisdiction" in e for e in errors)

    def test_missing_lei_returns_error(self):
        errors = validate_vasp_info({"name": "Test", "jurisdiction": "US", "lei": ""})
        assert any("lei" in e for e in errors)

    def test_long_jurisdiction_returns_error(self):
        errors = validate_vasp_info({
            "name": "Test",
            "jurisdiction": "UNITED_STATES",  # > 3 chars
            "lei": "ABC123",
        })
        assert any("jurisdiction" in e.lower() or "ISO" in e for e in errors)

    def test_empty_dict_returns_three_errors(self):
        errors = validate_vasp_info({})
        assert len(errors) >= 3
