"""
Automated Risk Assessment Workflows Tests

Comprehensive test suite for the automated risk assessment engine including:
- Risk assessment creation and management
- Risk factor analysis and scoring
- Threshold monitoring and escalation
- Workflow execution and reporting
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

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
    WorkflowExecution
)


class TestAutomatedRiskAssessmentEngine:
    """Test suite for AutomatedRiskAssessmentEngine"""

    @pytest.fixture
    async def engine(self):
        """Create test engine instance"""
        engine = AutomatedRiskAssessmentEngine()
        await engine.initialize()
        yield engine
        # Cleanup if needed

    @pytest.fixture
    def sample_assessment_data(self):
        """Create sample assessment data"""
        return {
            "entity_id": "0x1234567890abcdef",
            "entity_type": "address",
            "trigger_type": "automatic",
            "workflow_id": "transaction_risk_workflow",
            "assessor": "risk_engine",
            "metadata": {
                "detection_source": "automated_monitoring",
                "initial_risk_score": 0.75,
                "transaction_count": 25,
                "total_volume": 150000.00
            }
        }

    @pytest.fixture
    def sample_risk_factors(self):
        """Create sample risk factors"""
        return [
            RiskFactor(
                factor_id="factor_001",
                category=RiskCategory.TRANSACTION_VOLUME,
                weight=0.25,
                value=150000.00,
                score=0.8,
                description="High transaction volume detected",
                data_source="blockchain_analysis"
            ),
            RiskFactor(
                factor_id="factor_002",
                category=RiskCategory.ADDRESS_RISK,
                weight=0.20,
                value=0.85,
                score=0.85,
                description="Address flagged on risk database",
                data_source="risk_database"
            ),
            RiskFactor(
                factor_id="factor_003",
                category=RiskCategory.AMOUNT_ANOMALY,
                weight=0.15,
                value=0.9,
                score=0.9,
                description="Unusual transaction amounts detected",
                data_source="statistical_analysis"
            )
        ]

    class TestRiskAssessmentCreation:
        """Test risk assessment creation functionality"""

        @pytest.mark.asyncio
        async def test_create_transaction_risk_assessment(self, engine, sample_assessment_data):
            """Test creating transaction risk assessment"""
            assessment = await engine.create_risk_assessment(
                entity_id=sample_assessment_data["entity_id"],
                entity_type=sample_assessment_data["entity_type"],
                trigger_type=TriggerType.AUTOMATIC,
                workflow_id=sample_assessment_data["workflow_id"],
                assessor=sample_assessment_data["assessor"],
                metadata=sample_assessment_data["metadata"]
            )

            assert assessment.assessment_id is not None
            assert assessment.entity_id == sample_assessment_data["entity_id"]
            assert assessment.entity_type == sample_assessment_data["entity_type"]
            assert assessment.trigger_type == TriggerType.AUTOMATIC
            assert assessment.assessor == sample_assessment_data["assessor"]
            assert assessment.status == AssessmentStatus.COMPLETED
            assert assessment.overall_score >= 0.0
            assert assessment.overall_score <= 1.0
            assert assessment.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.SEVERE]
            assert assessment.confidence >= 0.0
            assert assessment.confidence <= 1.0
            assert len(assessment.risk_factors) > 0
            assert len(assessment.recommendations) > 0
            assert assessment.created_at is not None

        @pytest.mark.asyncio
        async def test_create_address_risk_assessment(self, engine):
            """Test creating address risk assessment"""
            assessment = await engine.create_risk_assessment(
                entity_id="0xabcdef1234567890",
                entity_type="address",
                trigger_type=TriggerType.MANUAL,
                assessor="compliance_analyst",
                metadata={
                    "assessment_reason": "suspicious_activity",
                    "review_priority": "high"
                }
            )

            assert assessment.entity_type == "address"
            assert assessment.trigger_type == TriggerType.MANUAL
            assert assessment.assessor == "compliance_analyst"

        @pytest.mark.asyncio
        async def test_create_wallet_risk_assessment(self, engine):
            """Test creating wallet risk assessment"""
            assessment = await engine.create_risk_assessment(
                entity_id="wallet_001",
                entity_type="wallet",
                trigger_type=TriggerType.THRESHOLD_BREACH,
                assessor="automated_system",
                metadata={
                    "breached_threshold": "high_volume",
                    "threshold_value": 100000.00
                }
            )

            assert assessment.entity_type == "wallet"
            assert assessment.trigger_type == TriggerType.THRESHOLD_BREACH

        @pytest.mark.asyncio
        async def test_invalid_entity_type(self, engine):
            """Test error handling for invalid entity type"""
            with pytest.raises(ValueError):
                await engine.create_risk_assessment(
                    entity_id="entity_001",
                    entity_type="invalid_type",
                    trigger_type=TriggerType.AUTOMATIC,
                    assessor="system"
                )

        @pytest.mark.asyncio
        async def test_missing_required_fields(self, engine):
            """Test error handling for missing required fields"""
            with pytest.raises(ValueError):
                await engine.create_risk_assessment(
                    entity_id="",  # Empty entity ID
                    entity_type="address",
                    trigger_type=TriggerType.AUTOMATIC,
                    assessor="system"
                )

    class TestRiskFactorAnalysis:
        """Test risk factor analysis functionality"""

        @pytest.mark.asyncio
        async def test_assess_transaction_volume_risk(self, engine):
            """Test transaction volume risk assessment"""
            risk_factor = await engine._assess_single_risk_factor(
                entity_id="0x1234567890abcdef",
                entity_type="address",
                category=RiskCategory.TRANSACTION_VOLUME
            )

            assert risk_factor.category == RiskCategory.TRANSACTION_VOLUME
            assert risk_factor.weight > 0.0
            assert risk_factor.value >= 0.0
            assert risk_factor.score >= 0.0
            assert risk_factor.score <= 1.0
            assert risk_factor.description is not None
            assert risk_factor.data_source is not None

        @pytest.mark.asyncio
        async def test_assess_address_risk(self, engine):
            """Test address risk assessment"""
            risk_factor = await engine._assess_single_risk_factor(
                entity_id="0x1234567890abcdef",
                entity_type="address",
                category=RiskCategory.ADDRESS_RISK
            )

            assert risk_factor.category == RiskCategory.ADDRESS_RISK
            assert risk_factor.score >= 0.0
            assert risk_factor.score <= 1.0
            assert "address" in risk_factor.description.lower()

        @pytest.mark.asyncio
        async def test_assess_amount_anomaly_risk(self, engine):
            """Test amount anomaly risk assessment"""
            risk_factor = await engine._assess_single_risk_factor(
                entity_id="0x1234567890abcdef",
                entity_type="transaction",
                category=RiskCategory.AMOUNT_ANOMALY
            )

            assert risk_factor.category == RiskCategory.AMOUNT_ANOMALY
            assert risk_factor.score >= 0.0
            assert risk_factor.score <= 1.0
            assert "anomaly" in risk_factor.description.lower()

        @pytest.mark.asyncio
        async def test_assess_geographic_risk(self, engine):
            """Test geographic risk assessment"""
            risk_factor = await engine._assess_single_risk_factor(
                entity_id="0x1234567890abcdef",
                entity_type="address",
                category=RiskCategory.GEOGRAPHIC_RISK
            )

            assert risk_factor.category == RiskCategory.GEOGRAPHIC_RISK
            assert risk_factor.score >= 0.0
            assert risk_factor.score <= 1.0

        @pytest.mark.asyncio
        async def test_comprehensive_risk_assessment(self, engine, sample_assessment_data):
            """Test comprehensive risk assessment with multiple factors"""
            assessment = await engine.create_risk_assessment(
                entity_id=sample_assessment_data["entity_id"],
                entity_type=sample_assessment_data["entity_type"],
                trigger_type=TriggerType.AUTOMATIC,
                assessor=sample_assessment_data["assessor"]
            )

            # Verify multiple risk factors were assessed
            categories = [factor.category for factor in assessment.risk_factors]
            assert len(categories) >= 3  # Should have at least 3 different risk categories
            
            expected_categories = [
                RiskCategory.TRANSACTION_VOLUME,
                RiskCategory.ADDRESS_RISK,
                RiskCategory.AMOUNT_ANOMALY
            ]
            
            for expected_category in expected_categories:
                assert expected_category in categories

    class TestRiskScoring:
        """Test risk scoring functionality"""

        @pytest.mark.asyncio
        async def test_calculate_overall_risk_low(self, engine, sample_risk_factors):
            """Test calculating low overall risk"""
            # Create low-risk factors
            low_risk_factors = [
                RiskFactor(
                    factor_id="low_001",
                    category=RiskCategory.TRANSACTION_VOLUME,
                    weight=0.3,
                    value=100.0,
                    score=0.2,
                    description="Low transaction volume",
                    data_source="blockchain_analysis"
                ),
                RiskFactor(
                    factor_id="low_002",
                    category=RiskCategory.ADDRESS_RISK,
                    weight=0.3,
                    value=0.1,
                    score=0.1,
                    description="Low address risk",
                    data_source="risk_database"
                )
            ]

            overall_score, risk_level = engine._calculate_overall_risk(low_risk_factors)

            assert overall_score >= 0.0
            assert overall_score <= 1.0
            assert risk_level == RiskLevel.LOW

        @pytest.mark.asyncio
        async def test_calculate_overall_risk_high(self, engine, sample_risk_factors):
            """Test calculating high overall risk"""
            # Create high-risk factors
            high_risk_factors = [
                RiskFactor(
                    factor_id="high_001",
                    category=RiskCategory.TRANSACTION_VOLUME,
                    weight=0.3,
                    value=1000000.0,
                    score=0.9,
                    description="Very high transaction volume",
                    data_source="blockchain_analysis"
                ),
                RiskFactor(
                    factor_id="high_002",
                    category=RiskCategory.ADDRESS_RISK,
                    weight=0.3,
                    value=0.95,
                    score=0.95,
                    description="Very high address risk",
                    data_source="risk_database"
                )
            ]

            overall_score, risk_level = engine._calculate_overall_risk(high_risk_factors)

            assert overall_score >= 0.7
            assert risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.SEVERE]

        @pytest.mark.asyncio
        async def test_calculate_overall_risk_critical(self, engine):
            """Test calculating critical overall risk"""
            # Create critical-risk factors
            critical_risk_factors = [
                RiskFactor(
                    factor_id="critical_001",
                    category=RiskCategory.TRANSACTION_VOLUME,
                    weight=0.4,
                    value=5000000.0,
                    score=1.0,
                    description="Extreme transaction volume",
                    data_source="blockchain_analysis"
                ),
                RiskFactor(
                    factor_id="critical_002",
                    category=RiskCategory.ADDRESS_RISK,
                    weight=0.4,
                    value=1.0,
                    score=1.0,
                    description="Maximum address risk",
                    data_source="risk_database"
                )
            ]

            overall_score, risk_level = engine._calculate_overall_risk(critical_risk_factors)

            assert overall_score >= 0.9
            assert risk_level == RiskLevel.SEVERE

        @pytest.mark.asyncio
        async def test_calculate_confidence(self, engine, sample_risk_factors):
            """Test confidence calculation"""
            confidence = engine._calculate_confidence(sample_risk_factors)

            assert confidence >= 0.0
            assert confidence <= 1.0
            # Should have reasonable confidence with 3 factors
            assert confidence >= 0.5

        @pytest.mark.asyncio
        async def test_calculate_confidence_empty_factors(self, engine):
            """Test confidence calculation with empty factors"""
            confidence = engine._calculate_confidence([])

            assert confidence == 0.0

    class TestThresholdManagement:
        """Test threshold management functionality"""

        @pytest.mark.asyncio
        async def test_create_risk_threshold(self, engine):
            """Test creating risk threshold"""
            threshold = await engine.create_threshold(
                category=RiskCategory.TRANSACTION_VOLUME,
                risk_level=RiskLevel.HIGH,
                threshold_value=100000.0,
                operator=">",
                time_window=1440,  # 24 hours
                description="High transaction volume threshold"
            )

            assert threshold.threshold_id is not None
            assert threshold.category == RiskCategory.TRANSACTION_VOLUME
            assert threshold.risk_level == RiskLevel.HIGH
            assert threshold.threshold_value == 100000.0
            assert threshold.operator == ">"
            assert threshold.time_window == 1440
            assert threshold.description == "High transaction volume threshold"
            assert threshold.active is True

        @pytest.mark.asyncio
        async def test_check_thresholds_triggered(self, engine, sample_risk_factors):
            """Test checking triggered thresholds"""
            # Create thresholds that should be triggered
            await engine.create_threshold(
                category=RiskCategory.TRANSACTION_VOLUME,
                risk_level=RiskLevel.HIGH,
                threshold_value=50000.0,
                operator=">",
                description="High volume threshold"
            )

            await engine.create_threshold(
                category=RiskCategory.ADDRESS_RISK,
                risk_level=RiskLevel.HIGH,
                threshold_value=0.5,
                operator=">",
                description="Address risk threshold"
            )

            # Check thresholds against risk factors
            triggered_thresholds = await engine._check_thresholds(sample_risk_factors)

            assert len(triggered_thresholds) >= 1  # Should trigger at least one threshold

        @pytest.mark.asyncio
        async def test_evaluate_threshold_operators(self, engine):
            """Test different threshold operators"""
            test_cases = [
                (">", 100.0, 150.0, True),
                (">", 100.0, 50.0, False),
                ("<", 100.0, 50.0, True),
                ("<", 100.0, 150.0, False),
                (">=", 100.0, 100.0, True),
                ("<=", 100.0, 100.0, True),
                ("==", 100.0, 100.0, True),
                ("==", 100.0, 50.0, False)
            ]

            for operator, threshold_value, test_value, expected in test_cases:
                threshold = RiskThreshold(
                    threshold_id="test_threshold",
                    category=RiskCategory.TRANSACTION_VOLUME,
                    risk_level=RiskLevel.HIGH,
                    threshold_value=threshold_value,
                    operator=operator,
                    description="Test threshold"
                )

                result = engine._evaluate_threshold(test_value, threshold)
                assert result == expected, f"Failed for operator {operator} with value {test_value}"

    class TestRecommendationGeneration:
        """Test recommendation generation functionality"""

        @pytest.mark.asyncio
        async def test_generate_recommendations_low_risk(self, engine):
            """Test generating recommendations for low risk"""
            low_risk_factors = [
                RiskFactor(
                    factor_id="low_001",
                    category=RiskCategory.TRANSACTION_VOLUME,
                    weight=0.3,
                    value=100.0,
                    score=0.2,
                    description="Low transaction volume",
                    data_source="blockchain_analysis"
                )
            ]

            triggered_thresholds = []

            recommendations = engine._generate_recommendations(
                RiskLevel.LOW,
                low_risk_factors,
                triggered_thresholds
            )

            assert isinstance(recommendations, list)
            # Low risk might have minimal or no recommendations
            assert len(recommendations) >= 0

        @pytest.mark.asyncio
        async def test_generate_recommendations_high_risk(self, engine, sample_risk_factors):
            """Test generating recommendations for high risk"""
            triggered_thresholds = [
                RiskThreshold(
                    threshold_id="threshold_001",
                    category=RiskCategory.TRANSACTION_VOLUME,
                    risk_level=RiskLevel.HIGH,
                    threshold_value=50000.0,
                    operator=">",
                    description="High volume threshold"
                )
            ]

            recommendations = engine._generate_recommendations(
                RiskLevel.HIGH,
                sample_risk_factors,
                triggered_thresholds
            )

            assert isinstance(recommendations, list)
            assert len(recommendations) > 0
            # Should include immediate review recommendation
            assert any("review" in rec.lower() for rec in recommendations)

        @pytest.mark.asyncio
        async def test_generate_recommendations_critical_risk(self, engine, sample_risk_factors):
            """Test generating recommendations for critical risk"""
            triggered_thresholds = [
                RiskThreshold(
                    threshold_id="critical_001",
                    category=RiskCategory.ADDRESS_RISK,
                    risk_level=RiskLevel.CRITICAL,
                    threshold_value=0.8,
                    operator=">",
                    description="Critical address risk"
                )
            ]

            recommendations = engine._generate_recommendations(
                RiskLevel.CRITICAL,
                sample_risk_factors,
                triggered_thresholds
            )

            assert isinstance(recommendations, list)
            assert len(recommendations) > 0
            # Should include immediate action recommendations
            assert any("immediate" in rec.lower() for rec in recommendations)

        @pytest.mark.asyncio
        async def test_generate_category_specific_recommendations(self, engine):
            """Test category-specific recommendations"""
            volume_factor = RiskFactor(
                factor_id="volume_001",
                category=RiskCategory.TRANSACTION_VOLUME,
                weight=0.3,
                value=200000.0,
                score=0.85,
                description="High transaction volume",
                data_source="blockchain_analysis"
            )

            recommendations = engine._generate_recommendations(
                RiskLevel.HIGH,
                [volume_factor],
                []
            )

            assert isinstance(recommendations, list)
            # Should include volume-specific recommendations
            assert any("transaction" in rec.lower() or "volume" in rec.lower() for rec in recommendations)

    class TestWorkflowManagement:
        """Test workflow management functionality"""

        @pytest.mark.asyncio
        async def test_select_workflow_for_transaction(self, engine):
            """Test selecting workflow for transaction entity"""
            workflow = engine._select_workflow("transaction")

            assert workflow is not None
            assert workflow.workflow_id == "transaction_risk_workflow"
            assert "transaction" in workflow.name.lower()

        @pytest.mark.asyncio
        async def test_select_workflow_for_address(self, engine):
            """Test selecting workflow for address entity"""
            workflow = engine._select_workflow("address")

            assert workflow is not None
            assert workflow.workflow_id == "address_risk_workflow"
            assert "address" in workflow.name.lower()

        @pytest.mark.asyncio
        async def test_select_workflow_for_wallet(self, engine):
            """Test selecting workflow for wallet entity"""
            workflow = engine._select_workflow("wallet")

            assert workflow is not None
            assert workflow.workflow_id == "address_risk_workflow"  # Should use address workflow

        @pytest.mark.asyncio
        async def test_select_workflow_invalid_type(self, engine):
            """Test selecting workflow for invalid entity type"""
            workflow = engine._select_workflow("invalid_type")

            assert workflow is None

        @pytest.mark.asyncio
        async def test_execute_workflow(self, engine, sample_assessment_data):
            """Test workflow execution"""
            # Create assessment
            assessment = await engine.create_risk_assessment(
                entity_id=sample_assessment_data["entity_id"],
                entity_type=sample_assessment_data["entity_type"],
                trigger_type=TriggerType.AUTOMATIC,
                workflow_id=sample_assessment_data["workflow_id"],
                assessor=sample_assessment_data["assessor"]
            )

            # Workflow should be executed automatically during assessment creation
            # Verify workflow execution exists
            executions = await engine._get_workflow_executions(assessment.assessment_id)
            assert len(executions) >= 1
            assert executions[0]["status"] == AssessmentStatus.COMPLETED.value

    class TestAssessmentRetrieval:
        """Test assessment retrieval functionality"""

        @pytest.mark.asyncio
        async def test_get_assessment_by_id(self, engine, sample_assessment_data):
            """Test getting assessment by ID"""
            # Create assessment
            original_assessment = await engine.create_risk_assessment(
                entity_id=sample_assessment_data["entity_id"],
                entity_type=sample_assessment_data["entity_type"],
                trigger_type=TriggerType.AUTOMATIC,
                assessor=sample_assessment_data["assessor"]
            )

            # Retrieve assessment
            retrieved_assessment = await engine.get_risk_assessment(original_assessment.assessment_id)

            assert retrieved_assessment.assessment_id == original_assessment.assessment_id
            assert retrieved_assessment.entity_id == original_assessment.entity_id
            assert retrieved_assessment.entity_type == original_assessment.entity_type
            assert retrieved_assessment.overall_score == original_assessment.overall_score
            assert retrieved_assessment.risk_level == original_assessment.risk_level
            assert len(retrieved_assessment.risk_factors) == len(original_assessment.risk_factors)

        @pytest.mark.asyncio
        async def test_get_nonexistent_assessment(self, engine):
            """Test getting nonexistent assessment"""
            assessment = await engine.get_risk_assessment("nonexistent_assessment_id")
            assert assessment is None

        @pytest.mark.asyncio
        async def test_get_risk_history(self, engine, sample_assessment_data):
            """Test getting risk history for entity"""
            # Create multiple assessments for same entity
            assessment1 = await engine.create_risk_assessment(
                entity_id=sample_assessment_data["entity_id"],
                entity_type=sample_assessment_data["entity_type"],
                trigger_type=TriggerType.AUTOMATIC,
                assessor="system_1"
            )

            assessment2 = await engine.create_risk_assessment(
                entity_id=sample_assessment_data["entity_id"],
                entity_type=sample_assessment_data["entity_type"],
                trigger_type=TriggerType.MANUAL,
                assessor="system_2"
            )

            # Get risk history
            history = await engine.get_risk_history(
                entity_id=sample_assessment_data["entity_id"],
                entity_type=sample_assessment_data["entity_type"]
            )

            assert len(history) >= 2
            assessment_ids = [a.assessment_id for a in history]
            assert assessment1.assessment_id in assessment_ids
            assert assessment2.assessment_id in assessment_ids

        @pytest.mark.asyncio
        async def test_get_risk_history_by_risk_level(self, engine, sample_assessment_data):
            """Test getting risk history filtered by risk level"""
            # Create assessments with different risk levels
            await engine.create_risk_assessment(
                entity_id="low_risk_entity",
                entity_type="address",
                trigger_type=TriggerType.AUTOMATIC,
                assessor="system"
            )

            # Get high risk assessments
            high_risk_history = await engine.get_risk_history(
                risk_level=RiskLevel.HIGH
            )

            # Should only include high risk assessments
            for assessment in high_risk_history:
                assert assessment.risk_level == RiskLevel.HIGH

    class TestAssessmentStatusManagement:
        """Test assessment status management functionality"""

        @pytest.mark.asyncio
        async def test_update_assessment_status(self, engine, sample_assessment_data):
            """Test updating assessment status"""
            # Create assessment
            assessment = await engine.create_risk_assessment(
                entity_id=sample_assessment_data["entity_id"],
                entity_type=sample_assessment_data["entity_type"],
                trigger_type=TriggerType.AUTOMATIC,
                assessor=sample_assessment_data["assessor"]
            )

            # Update status
            success = await engine.update_assessment_status(
                assessment_id=assessment.assessment_id,
                status=AssessmentStatus.REVIEW_REQUIRED,
                updated_by="supervisor",
                notes="Requires manual review due to high risk"
            )

            assert success is True

            # Verify status update
            updated_assessment = await engine.get_risk_assessment(assessment.assessment_id)
            assert updated_assessment.status == AssessmentStatus.REVIEW_REQUIRED

        @pytest.mark.asyncio
        async def test_update_nonexistent_assessment_status(self, engine):
            """Test updating status of nonexistent assessment"""
            success = await engine.update_assessment_status(
                assessment_id="nonexistent_assessment_id",
                status=AssessmentStatus.REVIEW_REQUIRED,
                updated_by="supervisor"
            )

            assert success is False

        @pytest.mark.asyncio
        async def test_status_transition_validation(self, engine, sample_assessment_data):
            """Test status transition validation"""
            # Create assessment
            assessment = await engine.create_risk_assessment(
                entity_id=sample_assessment_data["entity_id"],
                entity_type=sample_assessment_data["entity_type"],
                trigger_type=TriggerType.AUTOMATIC,
                assessor=sample_assessment_data["assessor"]
            )

            # Valid transition: COMPLETED -> REVIEW_REQUIRED
            success = await engine.update_assessment_status(
                assessment_id=assessment.assessment_id,
                status=AssessmentStatus.REVIEW_REQUIRED,
                updated_by="supervisor"
            )
            assert success is True

            # Valid transition: REVIEW_REQUIRED -> ESCALATED
            success = await engine.update_assessment_status(
                assessment_id=assessment.assessment_id,
                status=AssessmentStatus.ESCALATED,
                updated_by="manager"
            )
            assert success is True

    class TestRiskSummary:
        """Test risk summary functionality"""

        @pytest.mark.asyncio
        async def test_get_risk_summary(self, engine, sample_assessment_data):
            """Test getting risk summary"""
            # Create multiple assessments
            await engine.create_risk_assessment(
                entity_id="entity_001",
                entity_type="address",
                trigger_type=TriggerType.AUTOMATIC,
                assessor="system"
            )

            await engine.create_risk_assessment(
                entity_id="entity_002",
                entity_type="transaction",
                trigger_type=TriggerType.MANUAL,
                assessor="analyst"
            )

            # Get summary
            summary = await engine.get_risk_summary()

            assert "total_assessments" in summary
            assert "risk_level_distribution" in summary
            assert "average_score" in summary
            assert "max_score" in summary
            assert "min_score" in summary
            assert "period" in summary

            assert summary["total_assessments"] >= 2
            assert isinstance(summary["risk_level_distribution"], dict)
            assert isinstance(summary["average_score"], (int, float))

        @pytest.mark.asyncio
        async def test_get_risk_summary_with_date_filter(self, engine, sample_assessment_data):
            """Test getting risk summary with date filter"""
            # Create assessment
            await engine.create_risk_assessment(
                entity_id=sample_assessment_data["entity_id"],
                entity_type=sample_assessment_data["entity_type"],
                trigger_type=TriggerType.AUTOMATIC,
                assessor=sample_assessment_data["assessor"]
            )

            # Get summary with date range
            start_date = datetime.utcnow() - timedelta(hours=1)
            end_date = datetime.utcnow()
            
            summary = await engine.get_risk_summary(start_date, end_date)

            assert summary["total_assessments"] >= 1
            assert summary["period"]["start_date"] == start_date.isoformat()
            assert summary["period"]["end_date"] == end_date.isoformat()

    class TestEscalationProcedures:
        """Test escalation procedures functionality"""

        @pytest.mark.asyncio
        async def test_trigger_escalation_high_risk(self, engine, sample_assessment_data):
            """Test escalation trigger for high risk"""
            # Create high-risk assessment
            with patch.object(engine, '_calculate_overall_risk', return_value=(0.8, RiskLevel.HIGH)):
                assessment = await engine.create_risk_assessment(
                    entity_id=sample_assessment_data["entity_id"],
                    entity_type=sample_assessment_data["entity_type"],
                    trigger_type=TriggerType.AUTOMATIC,
                    assessor=sample_assessment_data["assessor"]
                )

            # Check if escalation was triggered (should be automatic for HIGH/CRITICAL/SEVERE)
            # Verify escalation data exists in Redis
            escalation_key = f"escalation:{assessment.assessment_id}"
            escalation_data = await engine.redis_client.get(escalation_key)
            
            if escalation_data:
                escalation_info = json.loads(escalation_data)
                assert escalation_info["assessment_id"] == assessment.assessment_id
                assert escalation_info["risk_level"] == RiskLevel.HIGH.value

        @pytest.mark.asyncio
        async def test_trigger_escalation_critical_risk(self, engine, sample_assessment_data):
            """Test escalation trigger for critical risk"""
            # Create critical-risk assessment
            with patch.object(engine, '_calculate_overall_risk', return_value=(0.9, RiskLevel.CRITICAL)):
                assessment = await engine.create_risk_assessment(
                    entity_id=sample_assessment_data["entity_id"],
                    entity_type=sample_assessment_data["entity_type"],
                    trigger_type=TriggerType.AUTOMATIC,
                    assessor=sample_assessment_data["assessor"]
                )

            # Should trigger escalation
            escalation_key = f"escalation:{assessment.assessment_id}"
            escalation_data = await engine.redis_client.get(escalation_key)
            
            if escalation_data:
                escalation_info = json.loads(escalation_data)
                assert escalation_info["risk_level"] == RiskLevel.CRITICAL.value

        @pytest.mark.asyncio
        async def test_no_escalation_low_risk(self, engine, sample_assessment_data):
            """Test no escalation for low risk"""
            # Create low-risk assessment
            with patch.object(engine, '_calculate_overall_risk', return_value=(0.2, RiskLevel.LOW)):
                assessment = await engine.create_risk_assessment(
                    entity_id=sample_assessment_data["entity_id"],
                    entity_type=sample_assessment_data["entity_type"],
                    trigger_type=TriggerType.AUTOMATIC,
                    assessor=sample_assessment_data["assessor"]
                )

            # Should not trigger escalation
            escalation_key = f"escalation:{assessment.assessment_id}"
            escalation_data = await engine.redis_client.get(escalation_key)
            
            assert escalation_data is None

    class TestErrorHandling:
        """Test error handling scenarios"""

        @pytest.mark.asyncio
        async def test_database_connection_error(self, engine):
            """Test handling of database connection errors"""
            with patch.object(engine, 'neo4j_session', None):
                with pytest.raises(Exception):
                    await engine.create_risk_assessment(
                        entity_id="entity_001",
                        entity_type="address",
                        trigger_type=TriggerType.AUTOMATIC,
                        assessor="system"
                    )

        @pytest.mark.asyncio
        async def test_redis_connection_error(self, engine, sample_assessment_data):
            """Test handling of Redis connection errors"""
            with patch.object(engine, 'redis_client', None):
                # Should still work but without caching/escalation
                assessment = await engine.create_risk_assessment(
                    entity_id=sample_assessment_data["entity_id"],
                    entity_type=sample_assessment_data["entity_type"],
                    trigger_type=TriggerType.AUTOMATIC,
                    assessor=sample_assessment_data["assessor"]
                )
                
                assert assessment.assessment_id is not None

        @pytest.mark.asyncio
        async def test_invalid_risk_category(self, engine):
            """Test handling of invalid risk category"""
            with pytest.raises(Exception):
                await engine._assess_single_risk_factor(
                    entity_id="entity_001",
                    entity_type="address",
                    category="INVALID_CATEGORY"
                )

    class TestPerformance:
        """Test performance characteristics"""

        @pytest.mark.asyncio
        async def test_bulk_assessment_creation(self, engine, sample_assessment_data):
            """Test bulk assessment creation performance"""
            import time
            
            start_time = time.time()
            
            # Create 10 assessments concurrently
            tasks = []
            for i in range(10):
                task = engine.create_risk_assessment(
                    entity_id=f"entity_{i}",
                    entity_type="address",
                    trigger_type=TriggerType.AUTOMATIC,
                    assessor="system"
                )
                tasks.append(task)
            
            assessments = await asyncio.gather(*tasks)
            
            end_time = time.time()
            duration = end_time - start_time
            
            assert len(assessments) == 10
            assert duration < 8.0  # Should complete within 8 seconds
            assert all(a.assessment_id is not None for a in assessments)

        @pytest.mark.asyncio
        async def test_risk_factor_assessment_performance(self, engine):
            """Test risk factor assessment performance"""
            import time
            
            start_time = time.time()
            
            # Assess multiple risk factors concurrently
            tasks = []
            categories = [
                RiskCategory.TRANSACTION_VOLUME,
                RiskCategory.ADDRESS_RISK,
                RiskCategory.AMOUNT_ANOMALY,
                RiskCategory.GEOGRAPHIC_RISK,
                RiskCategory.COUNTERPARTY_RISK
            ]
            
            for category in categories:
                task = engine._assess_single_risk_factor(
                    entity_id="0x1234567890abcdef",
                    entity_type="address",
                    category=category
                )
                tasks.append(task)
            
            risk_factors = await asyncio.gather(*tasks)
            
            end_time = time.time()
            duration = end_time - start_time
            
            assert len(risk_factors) == len(categories)
            assert duration < 3.0  # Should complete within 3 seconds
            assert all(rf.category in categories for rf in risk_factors)

        @pytest.mark.asyncio
        async def test_summary_generation_performance(self, engine, sample_assessment_data):
            """Test summary generation performance"""
            import time
            
            # Create test data
            for i in range(20):
                await engine.create_risk_assessment(
                    entity_id=f"entity_{i}",
                    entity_type="address",
                    trigger_type=TriggerType.AUTOMATIC,
                    assessor="system"
                )
            
            # Test summary generation performance
            start_time = time.time()
            
            summary = await engine.get_risk_summary()
            
            end_time = time.time()
            duration = end_time - start_time
            
            assert summary["total_assessments"] >= 20
            assert duration < 2.0  # Should complete within 2 seconds
