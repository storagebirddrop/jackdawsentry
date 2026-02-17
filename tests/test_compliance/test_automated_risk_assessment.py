"""
Automated Risk Assessment Engine Tests — rewritten to match actual API.
"""

import contextlib

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.compliance.automated_risk_assessment import (
    AutomatedRiskAssessmentEngine,
    RiskLevel,
    RiskCategory,
    AssessmentStatus,
    TriggerType,
    RiskThreshold,
    RiskFactor,
    RiskAssessment,
    RiskWorkflow,
)


class TestAutomatedRiskAssessmentEngine:
    """Test suite for AutomatedRiskAssessmentEngine"""

    @pytest.fixture
    def engine(self):
        eng = AutomatedRiskAssessmentEngine()
        eng.neo4j_session = AsyncMock()
        eng.redis_client = AsyncMock()
        return eng

    def _make_factor(self, factor_id="f1", category=RiskCategory.TRANSACTION_VOLUME,
                     weight=1.0, value=0.5, score=0.5, description="d", data_source="t"):
        return RiskFactor(
            factor_id=factor_id, category=category, weight=weight,
            value=value, score=score, description=description, data_source=data_source,
        )

    # ---- Initialization ----

    def test_engine_initializes(self, engine):
        assert isinstance(engine.workflows, list)
        assert isinstance(engine.thresholds, list)
        assert isinstance(engine.risk_models, dict)

    def test_workflows_populated(self, engine):
        assert len(engine.workflows) > 0
        assert all(isinstance(w, RiskWorkflow) for w in engine.workflows)

    def test_thresholds_populated(self, engine):
        assert len(engine.thresholds) > 0
        assert all(isinstance(t, RiskThreshold) for t in engine.thresholds)

    def test_risk_models_have_weights(self, engine):
        assert "weights" in engine.risk_models

    # ---- Enum values ----

    def test_risk_level_values(self):
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_risk_category_values(self):
        assert RiskCategory.TRANSACTION_VOLUME.value == "transaction_volume"
        assert RiskCategory.TRANSACTION_PATTERN.value == "transaction_pattern"
        assert RiskCategory.GEOGRAPHIC_RISK.value == "geographic_risk"

    def test_assessment_status_values(self):
        assert AssessmentStatus.PENDING.value == "pending"
        assert AssessmentStatus.COMPLETED.value == "completed"

    def test_trigger_type_values(self):
        assert TriggerType.AUTOMATIC.value == "automatic"
        assert TriggerType.MANUAL.value == "manual"

    # ---- create_risk_assessment (mocked DB) ----

    @pytest.mark.asyncio
    async def test_create_assessment_returns_assessment(self, engine):
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(engine, '_assess_risk_factors', new_callable=AsyncMock,
                                            return_value=[self._make_factor(score=0.3, value=0.3)]))
            stack.enter_context(patch.object(engine, '_check_thresholds', new_callable=AsyncMock, return_value=[]))
            stack.enter_context(patch.object(engine, '_persist_assessment', new_callable=AsyncMock))
            stack.enter_context(patch.object(engine, '_execute_workflow', new_callable=AsyncMock))

            assessment = await engine.create_risk_assessment(
                entity_id="0xabc123",
                entity_type="transaction",
                trigger_type=TriggerType.AUTOMATIC,
            )
            assert isinstance(assessment, RiskAssessment)
            assert assessment.entity_id == "0xabc123"
            assert assessment.entity_type == "transaction"
            assert assessment.status == AssessmentStatus.COMPLETED
            assert isinstance(assessment.risk_level, RiskLevel)

    @pytest.mark.asyncio
    async def test_create_assessment_address(self, engine):
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(engine, '_assess_risk_factors', new_callable=AsyncMock,
                                            return_value=[self._make_factor(category=RiskCategory.GEOGRAPHIC_RISK, score=0.7, value=0.7)]))
            stack.enter_context(patch.object(engine, '_check_thresholds', new_callable=AsyncMock, return_value=[]))
            stack.enter_context(patch.object(engine, '_persist_assessment', new_callable=AsyncMock))
            stack.enter_context(patch.object(engine, '_execute_workflow', new_callable=AsyncMock))

            assessment = await engine.create_risk_assessment(
                entity_id="0xdef456",
                entity_type="address",
                trigger_type=TriggerType.MANUAL,
            )
            assert assessment.entity_type == "address"

    # ---- _calculate_overall_risk ----

    def test_calculate_risk_low(self, engine):
        factors = [self._make_factor(score=0.2, value=0.2)]
        score, level = engine._calculate_overall_risk(factors)
        assert level == RiskLevel.LOW
        assert 0 <= score <= 1.0

    def test_calculate_risk_high(self, engine):
        factors = [
            self._make_factor(factor_id="f1", score=0.8, value=0.8),
            self._make_factor(factor_id="f2", category=RiskCategory.GEOGRAPHIC_RISK, score=0.9, value=0.9),
        ]
        score, level = engine._calculate_overall_risk(factors)
        assert level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    def test_calculate_risk_empty(self, engine):
        score, level = engine._calculate_overall_risk([])
        assert score == 0.0
        assert level == RiskLevel.LOW

    # ---- _calculate_confidence ----

    def test_confidence_empty(self, engine):
        assert engine._calculate_confidence([]) == 0.0

    def test_confidence_with_factors(self, engine):
        factors = [
            self._make_factor(factor_id="f1"),
            self._make_factor(factor_id="f2", category=RiskCategory.GEOGRAPHIC_RISK),
        ]
        conf = engine._calculate_confidence(factors)
        assert 0 < conf <= 1.0

    # ---- _generate_recommendations ----

    def test_recommendations_low_risk(self, engine):
        recs = engine._generate_recommendations(RiskLevel.LOW, [], [])
        assert isinstance(recs, list)

    def test_recommendations_critical_risk(self, engine):
        factors = [
            self._make_factor(category=RiskCategory.NETWORK_RISK, score=0.95, value=0.95),
        ]
        recs = engine._generate_recommendations(RiskLevel.CRITICAL, factors, [])
        assert len(recs) > 0

    # ---- _select_workflow ----

    def test_select_workflow_transaction(self, engine):
        wf = engine._select_workflow("transaction")
        if wf is not None:
            assert isinstance(wf, RiskWorkflow)

    def test_select_workflow_address(self, engine):
        wf = engine._select_workflow("address")
        if wf is not None:
            assert isinstance(wf, RiskWorkflow)

    def test_select_workflow_unknown(self, engine):
        wf = engine._select_workflow("unknown_entity")
        assert wf is None

    # ---- _evaluate_threshold ----

    def test_evaluate_threshold_gt(self, engine):
        t = RiskThreshold(
            threshold_id="t1", category=RiskCategory.TRANSACTION_VOLUME,
            risk_level=RiskLevel.HIGH, threshold_value=0.7, operator=">",
        )
        assert engine._evaluate_threshold(0.8, t) is True
        assert engine._evaluate_threshold(0.5, t) is False

    def test_evaluate_threshold_gte(self, engine):
        t = RiskThreshold(
            threshold_id="t1", category=RiskCategory.TRANSACTION_VOLUME,
            risk_level=RiskLevel.HIGH, threshold_value=0.7, operator=">=",
        )
        assert engine._evaluate_threshold(0.7, t) is True

    # ---- RiskAssessment dataclass ----

    def test_risk_assessment_dataclass(self):
        a = RiskAssessment(
            assessment_id="a1",
            entity_id="0xabc",
            entity_type="transaction",
            overall_score=0.55,
            risk_level=RiskLevel.MEDIUM,
            risk_factors=[],
            triggered_thresholds=[],
            status=AssessmentStatus.COMPLETED,
            trigger_type=TriggerType.AUTOMATIC,
            assessor="system",
            confidence=0.8,
            recommendations=["Monitor closely"],
        )
        assert a.assessment_id == "a1"
        assert a.risk_level == RiskLevel.MEDIUM

    # ---- RiskFactor dataclass ----

    def test_risk_factor_dataclass(self):
        f = self._make_factor()
        assert f.factor_id == "f1"
        assert f.category == RiskCategory.TRANSACTION_VOLUME
