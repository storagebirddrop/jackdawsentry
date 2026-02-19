"""
Unit tests for compute_risk_score()
"""

import pytest
from src.analysis.risk_scoring import compute_risk_score


class TestComputeRiskScore:
    def test_zero_inputs_returns_zero(self):
        score = compute_risk_score()
        assert score == 0.0

    def test_sanctions_hit_contributes_half(self):
        score = compute_risk_score(sanctions_hits=1)
        assert score == 0.5

    def test_multiple_sanctions_hits_still_caps_at_half(self):
        score = compute_risk_score(sanctions_hits=10)
        assert score == 0.5

    def test_pattern_component_weighted_at_30pct(self):
        patterns = [{"risk_score": 1.0}]
        score = compute_risk_score(pattern_matches=patterns)
        assert abs(score - 0.30) < 1e-6

    def test_pattern_averages_multiple(self):
        patterns = [{"risk_score": 0.0}, {"risk_score": 1.0}]
        score = compute_risk_score(pattern_matches=patterns)
        assert abs(score - 0.15) < 1e-6

    def test_mixer_component_weighted_at_20pct(self):
        score = compute_risk_score(mixer_detected=True, mixer_risk=1.0)
        assert abs(score - 0.20) < 1e-6

    def test_mixer_not_detected_zero_component(self):
        score = compute_risk_score(mixer_detected=False, mixer_risk=0.9)
        assert score == 0.0

    def test_volume_anomaly_additive(self):
        score = compute_risk_score(volume_anomaly=1.0)
        assert abs(score - 0.10) < 1e-6

    def test_all_components_combined(self):
        patterns = [{"risk_score": 1.0}]
        score = compute_risk_score(
            sanctions_hits=1,
            pattern_matches=patterns,
            mixer_detected=True,
            mixer_risk=1.0,
            volume_anomaly=1.0,
        )
        assert score == 1.0  # capped at 1.0

    def test_base_score_used_when_higher(self):
        score = compute_risk_score(base_score=0.9)
        assert score == 0.9

    def test_result_rounds_to_4_decimals(self):
        score = compute_risk_score(sanctions_hits=1, volume_anomaly=1.0)
        str_score = str(score)
        if '.' in str_score:
            assert len(str_score.split('.')[1]) <= 4
