"""
Unit tests for src/analysis/ml_risk_model.py (M14)
"""
import math
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@dataclass
class FakeAddressFeatures:
    """Minimal stand-in for AddressFeatures dataclass."""
    mixer_usage: bool = False
    privacy_tool_usage: bool = False
    cross_chain_activity: bool = False
    bridge_usage: bool = False
    transaction_count: int = 10
    round_amount_transactions: int = 0
    off_peak_transactions: int = 0
    large_transactions: int = 0
    unique_counterparties: int = 5
    high_frequency_periods: int = 0


# ---------------------------------------------------------------------------
# _sigmoid
# ---------------------------------------------------------------------------


class TestSigmoid:
    def test_zero_returns_half(self):
        from src.analysis.ml_risk_model import _sigmoid
        assert abs(_sigmoid(0) - 0.5) < 1e-9

    def test_large_positive_near_one(self):
        from src.analysis.ml_risk_model import _sigmoid
        assert _sigmoid(100) > 0.9999

    def test_large_negative_near_zero(self):
        from src.analysis.ml_risk_model import _sigmoid
        assert _sigmoid(-100) < 0.0001

    def test_overflow_positive(self):
        from src.analysis.ml_risk_model import _sigmoid
        assert _sigmoid(1e308) == 1.0

    def test_overflow_negative(self):
        from src.analysis.ml_risk_model import _sigmoid
        assert _sigmoid(-1e308) == 0.0


# ---------------------------------------------------------------------------
# FeatureVector.to_dict()
# ---------------------------------------------------------------------------


class TestFeatureVector:
    def test_to_dict_returns_all_twelve_fields(self):
        from src.analysis.ml_risk_model import FeatureVector, _DEFAULT_WEIGHTS
        fv = FeatureVector()
        d = fv.to_dict()
        assert set(d.keys()) == set(_DEFAULT_WEIGHTS.keys())

    def test_default_values_are_zero(self):
        from src.analysis.ml_risk_model import FeatureVector
        fv = FeatureVector()
        assert all(v == 0.0 for v in fv.to_dict().values())


# ---------------------------------------------------------------------------
# extract_features
# ---------------------------------------------------------------------------


class TestExtractFeatures:
    def test_binary_flags_set_to_one(self):
        from src.analysis.ml_risk_model import extract_features
        af = FakeAddressFeatures(mixer_usage=True, bridge_usage=True)
        fv = extract_features(af)
        assert fv.mixer_usage == 1.0
        assert fv.bridge_usage == 1.0

    def test_binary_flags_false_stays_zero(self):
        from src.analysis.ml_risk_model import extract_features
        fv = extract_features(FakeAddressFeatures())
        assert fv.mixer_usage == 0.0
        assert fv.privacy_tool_usage == 0.0

    def test_round_amount_ratio_correct(self):
        from src.analysis.ml_risk_model import extract_features
        af = FakeAddressFeatures(transaction_count=10, round_amount_transactions=5)
        fv = extract_features(af)
        assert abs(fv.round_amount_ratio - 0.5) < 1e-6

    def test_round_amount_ratio_capped_at_one(self):
        from src.analysis.ml_risk_model import extract_features
        af = FakeAddressFeatures(transaction_count=5, round_amount_transactions=10)
        fv = extract_features(af)
        assert fv.round_amount_ratio == 1.0

    def test_high_frequency_normalised(self):
        from src.analysis.ml_risk_model import extract_features
        af = FakeAddressFeatures(high_frequency_periods=5)
        fv = extract_features(af)
        assert abs(fv.high_frequency_periods - 0.5) < 1e-6

    def test_high_frequency_capped_at_one(self):
        from src.analysis.ml_risk_model import extract_features
        af = FakeAddressFeatures(high_frequency_periods=20)
        fv = extract_features(af)
        assert fv.high_frequency_periods == 1.0

    def test_entity_critical_risk_sets_sanctions(self):
        from src.analysis.ml_risk_model import extract_features
        entity = {"risk_level": "critical", "entity_type": "exchange"}
        fv = extract_features(FakeAddressFeatures(), entity_info=entity)
        assert fv.sanctions_entity == 1.0

    def test_entity_darknet_sets_darknet_flag(self):
        from src.analysis.ml_risk_model import extract_features
        entity = {"risk_level": "high", "entity_type": "darknet_market"}
        fv = extract_features(FakeAddressFeatures(), entity_info=entity)
        assert fv.darknet_entity == 1.0

    def test_entity_scam_sets_scam_flag(self):
        from src.analysis.ml_risk_model import extract_features
        entity = {"risk_level": "high", "entity_type": "scam"}
        fv = extract_features(FakeAddressFeatures(), entity_info=entity)
        assert fv.scam_entity == 1.0

    def test_no_entity_info_leaves_entity_signals_zero(self):
        from src.analysis.ml_risk_model import extract_features
        fv = extract_features(FakeAddressFeatures())
        assert fv.sanctions_entity == 0.0
        assert fv.darknet_entity == 0.0
        assert fv.scam_entity == 0.0

    def test_zero_transaction_count_does_not_divide_by_zero(self):
        from src.analysis.ml_risk_model import extract_features
        af = FakeAddressFeatures(transaction_count=0, round_amount_transactions=0)
        fv = extract_features(af)
        assert fv.round_amount_ratio == 0.0

    def test_low_counterparty_ratio_high_when_few_counterparties(self):
        from src.analysis.ml_risk_model import extract_features
        # 100 txs, only 1 unique counterparty → high ratio
        af = FakeAddressFeatures(transaction_count=100, unique_counterparties=1)
        fv = extract_features(af)
        assert fv.low_counterparty_ratio > 0.8


# ---------------------------------------------------------------------------
# score_features
# ---------------------------------------------------------------------------


class TestScoreFeatures:
    def test_all_zero_features_returns_half(self):
        from src.analysis.ml_risk_model import FeatureVector, score_features, _DEFAULT_WEIGHTS
        fv = FeatureVector()
        weights = {k: v[0] for k, v in _DEFAULT_WEIGHTS.items()}
        score = score_features(fv, weights, bias=0.0)
        # z=0 → sigmoid(0) = 0.5
        assert abs(score - 0.5) < 0.01

    def test_critical_feature_produces_high_score(self):
        from src.analysis.ml_risk_model import FeatureVector, score_features, _DEFAULT_WEIGHTS
        fv = FeatureVector(sanctions_entity=1.0)
        weights = {k: v[0] for k, v in _DEFAULT_WEIGHTS.items()}
        score = score_features(fv, weights)
        assert score > 0.80  # sanctions weight 0.40, scaled by 4

    def test_score_in_zero_one(self):
        from src.analysis.ml_risk_model import FeatureVector, score_features, _DEFAULT_WEIGHTS
        fv = FeatureVector(
            mixer_usage=1.0, sanctions_entity=1.0, darknet_entity=1.0,
            scam_entity=1.0, privacy_tool_usage=1.0,
        )
        weights = {k: v[0] for k, v in _DEFAULT_WEIGHTS.items()}
        score = score_features(fv, weights)
        assert 0.0 <= score <= 1.0

    def test_unknown_feature_uses_default_weight(self):
        from src.analysis.ml_risk_model import FeatureVector, score_features
        fv = FeatureVector(mixer_usage=1.0)
        # empty weights dict — should fall back to defaults
        score = score_features(fv, {})
        assert score > 0.5  # mixer weight is 0.30

    def test_result_is_rounded_to_four_places(self):
        from src.analysis.ml_risk_model import FeatureVector, score_features, _DEFAULT_WEIGHTS
        fv = FeatureVector(mixer_usage=0.7)
        weights = {k: v[0] for k, v in _DEFAULT_WEIGHTS.items()}
        score = score_features(fv, weights)
        assert score == round(score, 4)


# ---------------------------------------------------------------------------
# _level
# ---------------------------------------------------------------------------


class TestLevel:
    def test_critical(self):
        from src.analysis.ml_risk_model import _level
        assert _level(0.75) == "critical"
        assert _level(1.0) == "critical"

    def test_high(self):
        from src.analysis.ml_risk_model import _level
        assert _level(0.50) == "high"
        assert _level(0.74) == "high"

    def test_medium(self):
        from src.analysis.ml_risk_model import _level
        assert _level(0.25) == "medium"
        assert _level(0.49) == "medium"

    def test_low(self):
        from src.analysis.ml_risk_model import _level
        assert _level(0.0) == "low"
        assert _level(0.24) == "low"


# ---------------------------------------------------------------------------
# compute_ml_risk_score (async, mocked DB)
# ---------------------------------------------------------------------------


class TestComputeMLRiskScore:
    @pytest.mark.asyncio
    async def test_returns_expected_keys(self):
        from src.analysis.ml_risk_model import compute_ml_risk_score, _DEFAULT_WEIGHTS
        weights = {k: v[0] for k, v in _DEFAULT_WEIGHTS.items()}
        result = await compute_ml_risk_score(
            FakeAddressFeatures(), weights=weights
        )
        assert "score" in result
        assert "risk_level" in result
        assert "feature_vector" in result
        assert "weights_used" in result
        assert result["model"] == "ml_v1"

    @pytest.mark.asyncio
    async def test_loads_weights_from_db_when_not_provided(self):
        from src.analysis.ml_risk_model import compute_ml_risk_score, _DEFAULT_WEIGHTS
        default = {k: v[0] for k, v in _DEFAULT_WEIGHTS.items()}
        with patch("src.analysis.ml_risk_model.load_weights", new_callable=AsyncMock, return_value=default):
            result = await compute_ml_risk_score(FakeAddressFeatures())
        assert 0.0 <= result["score"] <= 1.0

    @pytest.mark.asyncio
    async def test_score_matches_direct_calculation(self):
        from src.analysis.ml_risk_model import (
            compute_ml_risk_score, extract_features, score_features, _DEFAULT_WEIGHTS
        )
        weights = {k: v[0] for k, v in _DEFAULT_WEIGHTS.items()}
        af = FakeAddressFeatures(mixer_usage=True)
        result = await compute_ml_risk_score(af, weights=weights)

        fv = extract_features(af)
        expected = score_features(fv, weights)
        assert abs(result["score"] - expected) < 1e-9


# ---------------------------------------------------------------------------
# _eval_rule_conditions
# ---------------------------------------------------------------------------


class TestEvalRuleConditions:
    def test_exact_feature_match(self):
        from src.analysis.ml_risk_model import _eval_rule_conditions
        fv = {"mixer_usage": 1.0}
        assert _eval_rule_conditions({"mixer_usage": 1.0}, fv, "0xabc", None) is True

    def test_exact_feature_no_match(self):
        from src.analysis.ml_risk_model import _eval_rule_conditions
        fv = {"mixer_usage": 0.0}
        assert _eval_rule_conditions({"mixer_usage": 1.0}, fv, "0xabc", None) is False

    def test_gte_operator_pass(self):
        from src.analysis.ml_risk_model import _eval_rule_conditions
        fv = {"mixer_usage": 0.8}
        cond = {"mixer_usage": {"op": "gte", "value": 0.5}}
        assert _eval_rule_conditions(cond, fv, "0xabc", None) is True

    def test_gte_operator_fail(self):
        from src.analysis.ml_risk_model import _eval_rule_conditions
        fv = {"mixer_usage": 0.3}
        cond = {"mixer_usage": {"op": "gte", "value": 0.5}}
        assert _eval_rule_conditions(cond, fv, "0xabc", None) is False

    def test_lte_operator_pass(self):
        from src.analysis.ml_risk_model import _eval_rule_conditions
        fv = {"mixer_usage": 0.2}
        cond = {"mixer_usage": {"op": "lte", "value": 0.5}}
        assert _eval_rule_conditions(cond, fv, "0xabc", None) is True

    def test_entity_type_match(self):
        from src.analysis.ml_risk_model import _eval_rule_conditions
        entity = {"entity_type": "darknet_market"}
        assert _eval_rule_conditions({"entity_type": "darknet_market"}, {}, "0xabc", entity) is True

    def test_entity_type_no_match(self):
        from src.analysis.ml_risk_model import _eval_rule_conditions
        entity = {"entity_type": "exchange"}
        assert _eval_rule_conditions({"entity_type": "darknet_market"}, {}, "0xabc", entity) is False

    def test_address_prefix_match(self):
        from src.analysis.ml_risk_model import _eval_rule_conditions
        assert _eval_rule_conditions({"address_prefix": "0xdead"}, {}, "0xdeadbeef", None) is True

    def test_address_prefix_no_match(self):
        from src.analysis.ml_risk_model import _eval_rule_conditions
        assert _eval_rule_conditions({"address_prefix": "0xdead"}, {}, "0xabcdef", None) is False

    def test_empty_conditions_always_true(self):
        from src.analysis.ml_risk_model import _eval_rule_conditions
        assert _eval_rule_conditions({}, {}, "0xabc", None) is True
