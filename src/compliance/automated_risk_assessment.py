"""
Automated Risk Assessment Workflows

This module implements automated risk assessment workflows for compliance
and regulatory reporting, including risk scoring, threshold monitoring,
and automated escalation procedures.
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

import aiohttp
from neo4j import AsyncSession

from src.api.config import settings
from src.api.database import get_neo4j_session
from src.api.database import get_redis_connection

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk assessment levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    SEVERE = "severe"


class RiskCategory(Enum):
    """Risk assessment categories."""

    TRANSACTION_VOLUME = "transaction_volume"
    TRANSACTION_PATTERN = "transaction_pattern"
    ADDRESS_RISK = "address_risk"
    GEOGRAPHIC_RISK = "geographic_risk"
    COUNTERPARTY_RISK = "counterparty_risk"
    TIME_PATTERN_RISK = "time_pattern_risk"
    AMOUNT_ANOMALY = "amount_anomaly"
    FREQUENCY_ANOMALY = "frequency_anomaly"
    NETWORK_RISK = "network_risk"


class AssessmentStatus(Enum):
    """Risk assessment status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    REVIEW_REQUIRED = "review_required"
    CLOSED = "closed"


class TriggerType(Enum):
    """Risk assessment trigger types."""

    AUTOMATIC = "automatic"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    THRESHOLD_BREACH = "threshold_breach"
    PATTERN_DETECTION = "pattern_detection"
    REGULATORY_REQUIREMENT = "regulatory_requirement"


@dataclass
class RiskThreshold:
    """Risk assessment threshold configuration."""

    threshold_id: str
    category: RiskCategory
    risk_level: RiskLevel
    threshold_value: float
    operator: str  # '>', '<', '>=', '<=', '=='
    time_window: Optional[int] = None  # minutes
    description: str = ""
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RiskFactor:
    """Individual risk factor in assessment."""

    factor_id: str
    category: RiskCategory
    weight: float
    value: float
    score: float
    description: str
    data_source: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RiskAssessment:
    """Comprehensive risk assessment result."""

    assessment_id: str
    entity_id: str
    entity_type: str  # 'address', 'transaction', 'wallet', 'user'
    overall_score: float
    risk_level: RiskLevel
    risk_factors: List[RiskFactor]
    triggered_thresholds: List[RiskThreshold]
    status: AssessmentStatus
    trigger_type: TriggerType
    assessor: str
    confidence: float
    recommendations: List[str]
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskWorkflow:
    """Risk assessment workflow definition."""

    workflow_id: str
    name: str
    description: str
    risk_categories: List[RiskCategory]
    assessment_steps: List[str]
    escalation_rules: Dict[str, Any]
    notification_rules: Dict[str, Any]
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WorkflowExecution:
    """Risk workflow execution record."""

    execution_id: str
    workflow_id: str
    assessment_id: str
    status: AssessmentStatus
    current_step: int
    total_steps: int
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    execution_log: List[str] = field(default_factory=list)


class AutomatedRiskAssessmentEngine:
    """
    Automated Risk Assessment Engine

    Provides comprehensive risk assessment workflows with automated
    scoring, threshold monitoring, and escalation procedures.
    """

    def __init__(self):
        self.neo4j_session = None
        self.redis_client = None
        self._initialized = False
        self.workflows = self._initialize_workflows()
        self.thresholds = self._initialize_thresholds()
        self.risk_models = self._initialize_risk_models()

    async def initialize(self):
        """Initialize database connections and load configurations.

        Idempotent: subsequent calls return immediately if already initialized.
        """
        if self._initialized:
            return
        self.neo4j_session = await get_neo4j_session()
        self.redis_client = await get_redis_connection()
        await self._load_configurations()
        self._initialized = True

    async def create_risk_assessment(
        self,
        entity_id: str,
        entity_type: str,
        trigger_type: TriggerType,
        workflow_id: Optional[str] = None,
        assessor: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RiskAssessment:
        """Create a new risk assessment."""
        assessment_id = f"risk_assessment_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{hashlib.sha256(entity_id.encode()).hexdigest()[:8]}"

        # Select workflow
        if workflow_id:
            workflow = next(
                (w for w in self.workflows if w.workflow_id == workflow_id), None
            )
        else:
            workflow = self._select_workflow(entity_type)

        if not workflow:
            raise ValueError(
                f"No suitable workflow found for entity type: {entity_type}"
            )

        # Execute risk assessment
        risk_factors = await self._assess_risk_factors(
            entity_id, entity_type, workflow.risk_categories
        )
        overall_score, risk_level = self._calculate_overall_risk(risk_factors)
        triggered_thresholds = await self._check_thresholds(risk_factors)
        recommendations = self._generate_recommendations(
            risk_level, risk_factors, triggered_thresholds
        )

        assessment = RiskAssessment(
            assessment_id=assessment_id,
            entity_id=entity_id,
            entity_type=entity_type,
            overall_score=overall_score,
            risk_level=risk_level,
            risk_factors=risk_factors,
            triggered_thresholds=triggered_thresholds,
            status=AssessmentStatus.COMPLETED,
            trigger_type=trigger_type,
            assessor=assessor,
            confidence=self._calculate_confidence(risk_factors),
            recommendations=recommendations,
            metadata=metadata or {},
        )

        # Persist assessment
        await self._persist_assessment(assessment)

        # Execute workflow if needed
        if workflow:
            await self._execute_workflow(workflow, assessment)

        # Trigger escalation if needed
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.SEVERE]:
            await self._trigger_escalation(assessment)

        logger.info(
            f"Created risk assessment {assessment_id} for {entity_type} {entity_id} with risk level {risk_level.value}"
        )
        return assessment

    async def get_risk_assessment(self, assessment_id: str) -> Optional[RiskAssessment]:
        """Retrieve a risk assessment by ID."""
        query = """
        MATCH (a:RiskAssessment {assessment_id: $assessment_id})
        OPTIONAL MATCH (a)-[:HAS_FACTOR]->(f:RiskFactor)
        OPTIONAL MATCH (a)-[:TRIGGERED]->(t:RiskThreshold)
        RETURN a, collect(f) as factors, collect(t) as thresholds
        """

        result = await self.neo4j_session.run(query, assessment_id=assessment_id)
        record = await result.single()

        if not record:
            return None

        assessment_data = record["a"]
        factors_data = record["factors"]
        thresholds_data = record["thresholds"]

        risk_factors = [
            RiskFactor(
                factor_id=f["factor_id"],
                category=RiskCategory(f["category"]),
                weight=f["weight"],
                value=f["value"],
                score=f["score"],
                description=f["description"],
                data_source=f["data_source"],
                timestamp=datetime.fromisoformat(f["timestamp"]),
            )
            for f in factors_data
        ]

        triggered_thresholds = [
            RiskThreshold(
                threshold_id=t["threshold_id"],
                category=RiskCategory(t["category"]),
                risk_level=RiskLevel(t["risk_level"]),
                threshold_value=t["threshold_value"],
                operator=t["operator"],
                time_window=t.get("time_window"),
                description=t["description"],
                active=t["active"],
                created_at=datetime.fromisoformat(t["created_at"]),
            )
            for t in thresholds_data
        ]

        return RiskAssessment(
            assessment_id=assessment_data["assessment_id"],
            entity_id=assessment_data["entity_id"],
            entity_type=assessment_data["entity_type"],
            overall_score=assessment_data["overall_score"],
            risk_level=RiskLevel(assessment_data["risk_level"]),
            risk_factors=risk_factors,
            triggered_thresholds=triggered_thresholds,
            status=AssessmentStatus(assessment_data["status"]),
            trigger_type=TriggerType(assessment_data["trigger_type"]),
            assessor=assessment_data["assessor"],
            confidence=assessment_data["confidence"],
            recommendations=assessment_data["recommendations"],
            created_at=datetime.fromisoformat(assessment_data["created_at"]),
            updated_at=datetime.fromisoformat(assessment_data["updated_at"]),
            metadata=assessment_data["metadata"],
        )

    async def update_assessment_status(
        self,
        assessment_id: str,
        status: AssessmentStatus,
        updated_by: str,
        notes: Optional[str] = None,
    ) -> bool:
        """Update risk assessment status."""
        query = """
        MATCH (a:RiskAssessment {assessment_id: $assessment_id})
        SET a.status = $status, a.updated_at = $updated_at
        WITH a
        CREATE (u:Update {
            update_id: $update_id,
            status: $status,
            updated_by: $updated_by,
            notes: $notes,
            timestamp: $timestamp
        })
        CREATE (a)-[:HAS_UPDATE]->(u)
        RETURN a
        """

        now = datetime.now(timezone.utc)
        update_id = f"update_{now.strftime('%Y%m%d_%H%M%S')}_{hashlib.sha256(assessment_id.encode()).hexdigest()[:8]}"

        result = await self.neo4j_session.run(
            query,
            assessment_id=assessment_id,
            status=status.value,
            updated_at=now.isoformat(),
            update_id=update_id,
            updated_by=updated_by,
            notes=notes or "",
            timestamp=now.isoformat(),
        )

        record = await result.single()
        success = record is not None

        if success:
            logger.info(
                f"Updated assessment {assessment_id} status to {status.value} by {updated_by}"
            )

        return success

    async def get_risk_history(
        self,
        entity_id: str,
        entity_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        risk_level: Optional[RiskLevel] = None,
    ) -> List[RiskAssessment]:
        """Get risk assessment history for an entity."""
        query = """
        MATCH (a:RiskAssessment {entity_id: $entity_id})
        """

        params = {"entity_id": entity_id}

        if entity_type:
            query += " WHERE a.entity_type = $entity_type"
            params["entity_type"] = entity_type

        if start_date:
            query += " AND a.created_at >= $start_date"
            params["start_date"] = start_date.isoformat()

        if end_date:
            query += " AND a.created_at <= $end_date"
            params["end_date"] = end_date.isoformat()

        if risk_level:
            query += " AND a.risk_level = $risk_level"
            params["risk_level"] = risk_level.value

        query += " ORDER BY a.created_at DESC"

        result = await self.neo4j_session.run(query, **params)
        records = await result.data()

        assessments = []
        for record in records:
            assessment_data = record["a"]
            assessments.append(
                RiskAssessment(
                    assessment_id=assessment_data["assessment_id"],
                    entity_id=assessment_data["entity_id"],
                    entity_type=assessment_data["entity_type"],
                    overall_score=assessment_data["overall_score"],
                    risk_level=RiskLevel(assessment_data["risk_level"]),
                    risk_factors=[],  # Simplified for history
                    triggered_thresholds=[],
                    status=AssessmentStatus(assessment_data["status"]),
                    trigger_type=TriggerType(assessment_data["trigger_type"]),
                    assessor=assessment_data["assessor"],
                    confidence=assessment_data["confidence"],
                    recommendations=assessment_data["recommendations"],
                    created_at=datetime.fromisoformat(assessment_data["created_at"]),
                    updated_at=datetime.fromisoformat(assessment_data["updated_at"]),
                    metadata=assessment_data["metadata"],
                )
            )

        return assessments

    async def create_threshold(
        self,
        category: RiskCategory,
        risk_level: RiskLevel,
        threshold_value: float,
        operator: str,
        time_window: Optional[int] = None,
        description: str = "",
    ) -> RiskThreshold:
        """Create a new risk threshold."""
        threshold_id = f"threshold_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{hashlib.sha256(f'{category.value}_{risk_level.value}'.encode()).hexdigest()[:8]}"

        threshold = RiskThreshold(
            threshold_id=threshold_id,
            category=category,
            risk_level=risk_level,
            threshold_value=threshold_value,
            operator=operator,
            time_window=time_window,
            description=description,
        )

        query = """
        CREATE (t:RiskThreshold {
            threshold_id: $threshold_id,
            category: $category,
            risk_level: $risk_level,
            threshold_value: $threshold_value,
            operator: $operator,
            time_window: $time_window,
            description: $description,
            active: $active,
            created_at: $created_at
        })
        RETURN t
        """

        await self.neo4j_session.run(
            query,
            threshold_id=threshold.threshold_id,
            category=threshold.category.value,
            risk_level=threshold.risk_level.value,
            threshold_value=threshold.threshold_value,
            operator=threshold.operator,
            time_window=threshold.time_window,
            description=threshold.description,
            active=threshold.active,
            created_at=threshold.created_at.isoformat(),
        )

        self.thresholds.append(threshold)
        logger.info(
            f"Created risk threshold {threshold_id} for {category.value} {risk_level.value}"
        )
        return threshold

    async def get_risk_summary(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get risk assessment summary statistics."""
        query = """
        MATCH (a:RiskAssessment)
        """

        params = {}

        if start_date:
            query += " WHERE a.created_at >= $start_date"
            params["start_date"] = start_date.isoformat()

        if end_date:
            if start_date:
                query += " AND a.created_at <= $end_date"
            else:
                query += " WHERE a.created_at <= $end_date"
            params["end_date"] = end_date.isoformat()

        query += """
        RETURN 
            count(a) as total_assessments,
            a.risk_level as risk_level,
            count(*) as count_by_level,
            avg(a.overall_score) as avg_score,
            max(a.overall_score) as max_score,
            min(a.overall_score) as min_score
        ORDER BY risk_level
        """

        result = await self.neo4j_session.run(query, **params)
        records = await result.data()

        summary = {
            "total_assessments": 0,
            "risk_level_distribution": {},
            "average_score": 0.0,
            "max_score": 0.0,
            "min_score": 0.0,
            "period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            },
        }

        for record in records:
            summary["total_assessments"] += record["count_by_level"]
            summary["risk_level_distribution"][record["risk_level"]] = record[
                "count_by_level"
            ]
            summary["average_score"] = record["avg_score"] or 0.0
            summary["max_score"] = record["max_score"] or 0.0
            summary["min_score"] = record["min_score"] or 0.0

        return summary

    def _initialize_workflows(self) -> List[RiskWorkflow]:
        """Initialize default risk assessment workflows."""
        return [
            RiskWorkflow(
                workflow_id="transaction_risk_workflow",
                name="Transaction Risk Assessment",
                description="Comprehensive risk assessment for blockchain transactions",
                risk_categories=[
                    RiskCategory.TRANSACTION_VOLUME,
                    RiskCategory.TRANSACTION_PATTERN,
                    RiskCategory.AMOUNT_ANOMALY,
                    RiskCategory.ADDRESS_RISK,
                    RiskCategory.GEOGRAPHIC_RISK,
                ],
                assessment_steps=[
                    "collect_transaction_data",
                    "analyze_patterns",
                    "check_address_risk",
                    "calculate_volume_metrics",
                    "assess_geographic_risk",
                    "generate_score",
                    "create_recommendations",
                ],
                escalation_rules={
                    "high_risk": {"threshold": 0.7, "action": "manual_review"},
                    "critical_risk": {"threshold": 0.8, "action": "immediate_alert"},
                    "severe_risk": {"threshold": 0.9, "action": "emergency_response"},
                },
                notification_rules={
                    "medium": {"channels": ["email"], "delay": 300},
                    "high": {"channels": ["email", "sms"], "delay": 60},
                    "critical": {"channels": ["email", "sms", "slack"], "delay": 0},
                    "severe": {
                        "channels": ["email", "sms", "slack", "phone"],
                        "delay": 0,
                    },
                },
            ),
            RiskWorkflow(
                workflow_id="address_risk_workflow",
                name="Address Risk Assessment",
                description="Risk assessment for blockchain addresses and wallets",
                risk_categories=[
                    RiskCategory.ADDRESS_RISK,
                    RiskCategory.COUNTERPARTY_RISK,
                    RiskCategory.NETWORK_RISK,
                    RiskCategory.TRANSACTION_PATTERN,
                    RiskCategory.FREQUENCY_ANOMALY,
                ],
                assessment_steps=[
                    "collect_address_history",
                    "analyze_counterparties",
                    "check_blacklist_status",
                    "analyze_network_connections",
                    "assess_transaction_patterns",
                    "calculate_risk_score",
                    "generate_recommendations",
                ],
                escalation_rules={
                    "high_risk": {"threshold": 0.6, "action": "enhanced_monitoring"},
                    "critical_risk": {"threshold": 0.75, "action": "freeze_review"},
                    "severe_risk": {"threshold": 0.85, "action": "immediate_freeze"},
                },
                notification_rules={
                    "medium": {"channels": ["email"], "delay": 600},
                    "high": {"channels": ["email", "sms"], "delay": 300},
                    "critical": {"channels": ["email", "sms", "slack"], "delay": 60},
                    "severe": {
                        "channels": ["email", "sms", "slack", "phone"],
                        "delay": 0,
                    },
                },
            ),
        ]

    def _initialize_thresholds(self) -> List[RiskThreshold]:
        """Initialize default risk thresholds."""
        return [
            RiskThreshold(
                threshold_id="high_volume_threshold",
                category=RiskCategory.TRANSACTION_VOLUME,
                risk_level=RiskLevel.HIGH,
                threshold_value=100000.0,
                operator=">",
                time_window=1440,  # 24 hours
                description="High transaction volume threshold",
            ),
            RiskThreshold(
                threshold_id="critical_amount_threshold",
                category=RiskCategory.AMOUNT_ANOMALY,
                risk_level=RiskLevel.CRITICAL,
                threshold_value=1000000.0,
                operator=">",
                description="Critical transaction amount threshold",
            ),
            RiskThreshold(
                threshold_id="high_frequency_threshold",
                category=RiskCategory.FREQUENCY_ANOMALY,
                risk_level=RiskLevel.HIGH,
                threshold_value=100,
                operator=">",
                time_window=60,  # 1 hour
                description="High transaction frequency threshold",
            ),
        ]

    def _initialize_risk_models(self) -> Dict[str, Any]:
        """Initialize risk assessment models and configurations."""
        return {
            "weights": {
                RiskCategory.TRANSACTION_VOLUME: 0.25,
                RiskCategory.TRANSACTION_PATTERN: 0.20,
                RiskCategory.ADDRESS_RISK: 0.20,
                RiskCategory.GEOGRAPHIC_RISK: 0.15,
                RiskCategory.COUNTERPARTY_RISK: 0.10,
                RiskCategory.AMOUNT_ANOMALY: 0.10,
            },
            "scoring_functions": {
                RiskCategory.TRANSACTION_VOLUME: "logarithmic",
                RiskCategory.TRANSACTION_PATTERN: "pattern_match",
                RiskCategory.ADDRESS_RISK: "blacklist_check",
                RiskCategory.GEOGRAPHIC_RISK: "sanction_check",
                RiskCategory.COUNTERPARTY_RISK: "network_analysis",
                RiskCategory.AMOUNT_ANOMALY: "statistical_outlier",
            },
        }

    async def _load_configurations(self):
        """Load configurations from database."""
        # Load workflows
        query = "MATCH (w:RiskWorkflow {active: true}) RETURN w"
        result = await self.neo4j_session.run(query)
        records = await result.data()

        for record in records:
            workflow_data = record["w"]
            workflow = RiskWorkflow(
                workflow_id=workflow_data["workflow_id"],
                name=workflow_data["name"],
                description=workflow_data["description"],
                risk_categories=[
                    RiskCategory(cat) for cat in workflow_data["risk_categories"]
                ],
                assessment_steps=workflow_data["assessment_steps"],
                escalation_rules=workflow_data["escalation_rules"],
                notification_rules=workflow_data["notification_rules"],
                active=workflow_data["active"],
                created_at=datetime.fromisoformat(workflow_data["created_at"]),
            )
            self.workflows.append(workflow)

        # Load thresholds
        query = "MATCH (t:RiskThreshold {active: true}) RETURN t"
        result = await self.neo4j_session.run(query)
        records = await result.data()

        for record in records:
            threshold_data = record["t"]
            threshold = RiskThreshold(
                threshold_id=threshold_data["threshold_id"],
                category=RiskCategory(threshold_data["category"]),
                risk_level=RiskLevel(threshold_data["risk_level"]),
                threshold_value=threshold_data["threshold_value"],
                operator=threshold_data["operator"],
                time_window=threshold_data.get("time_window"),
                description=threshold_data["description"],
                active=threshold_data["active"],
                created_at=datetime.fromisoformat(threshold_data["created_at"]),
            )
            self.thresholds.append(threshold)

    def _select_workflow(self, entity_type: str) -> Optional[RiskWorkflow]:
        """Select appropriate workflow based on entity type."""
        if entity_type == "transaction":
            return next(
                (
                    w
                    for w in self.workflows
                    if w.workflow_id == "transaction_risk_workflow"
                ),
                None,
            )
        elif entity_type in ["address", "wallet"]:
            return next(
                (w for w in self.workflows if w.workflow_id == "address_risk_workflow"),
                None,
            )
        return None

    async def _assess_risk_factors(
        self, entity_id: str, entity_type: str, categories: List[RiskCategory]
    ) -> List[RiskFactor]:
        """Assess risk factors for given categories."""
        risk_factors = []

        for category in categories:
            factor = await self._assess_single_risk_factor(
                entity_id, entity_type, category
            )
            if factor:
                risk_factors.append(factor)

        return risk_factors

    async def _assess_single_risk_factor(
        self, entity_id: str, entity_type: str, category: RiskCategory
    ) -> Optional[RiskFactor]:
        """Assess a single risk factor."""
        factor_id = f"factor_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{category.value}_{hashlib.sha256(entity_id.encode()).hexdigest()[:8]}"

        # Simulate risk factor assessment
        if category == RiskCategory.TRANSACTION_VOLUME:
            value = await self._get_transaction_volume(entity_id, entity_type)
            weight = self.risk_models["weights"][category]
            score = self._calculate_volume_score(value)
            description = f"Transaction volume analysis: {value:.2f} units"
            data_source = "blockchain_analysis"

        elif category == RiskCategory.ADDRESS_RISK:
            value = await self._get_address_risk_score(entity_id)
            weight = self.risk_models["weights"][category]
            score = value
            description = f"Address risk score: {value:.2f}"
            data_source = "risk_database"

        elif category == RiskCategory.AMOUNT_ANOMALY:
            value = await self._get_amount_anomaly_score(entity_id, entity_type)
            weight = self.risk_models["weights"][category]
            score = value
            description = f"Amount anomaly detection: {value:.2f}"
            data_source = "statistical_analysis"

        else:
            # Default assessment for other categories
            value = 0.5  # Neutral value
            weight = self.risk_models["weights"].get(category, 0.1)
            score = value
            description = f"{category.value} assessment: {value:.2f}"
            data_source = "default_model"

        return RiskFactor(
            factor_id=factor_id,
            category=category,
            weight=weight,
            value=value,
            score=score,
            description=description,
            data_source=data_source,
        )

    def _calculate_overall_risk(
        self, risk_factors: List[RiskFactor]
    ) -> Tuple[float, RiskLevel]:
        """Calculate overall risk score and level."""
        if not risk_factors:
            return 0.0, RiskLevel.LOW

        weighted_score = sum(factor.score * factor.weight for factor in risk_factors)
        total_weight = sum(factor.weight for factor in risk_factors)

        if total_weight > 0:
            overall_score = weighted_score / total_weight
        else:
            overall_score = 0.0

        # Determine risk level
        if overall_score >= 0.9:
            risk_level = RiskLevel.SEVERE
        elif overall_score >= 0.8:
            risk_level = RiskLevel.CRITICAL
        elif overall_score >= 0.7:
            risk_level = RiskLevel.HIGH
        elif overall_score >= 0.4:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        return overall_score, risk_level

    async def _check_thresholds(
        self, risk_factors: List[RiskFactor]
    ) -> List[RiskThreshold]:
        """Check which thresholds are triggered by risk factors."""
        triggered_thresholds = []

        for factor in risk_factors:
            for threshold in self.thresholds:
                if threshold.category == factor.category:
                    if self._evaluate_threshold(factor.value, threshold):
                        triggered_thresholds.append(threshold)

        return triggered_thresholds

    def _evaluate_threshold(self, value: float, threshold: RiskThreshold) -> bool:
        """Evaluate if a threshold is triggered."""
        if threshold.operator == ">":
            return value > threshold.threshold_value
        elif threshold.operator == "<":
            return value < threshold.threshold_value
        elif threshold.operator == ">=":
            return value >= threshold.threshold_value
        elif threshold.operator == "<=":
            return value <= threshold.threshold_value
        elif threshold.operator == "==":
            return value == threshold.threshold_value
        return False

    def _generate_recommendations(
        self,
        risk_level: RiskLevel,
        risk_factors: List[RiskFactor],
        triggered_thresholds: List[RiskThreshold],
    ) -> List[str]:
        """Generate risk mitigation recommendations."""
        recommendations = []

        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.SEVERE]:
            recommendations.append("Immediate manual review required")
            recommendations.append("Enhanced monitoring recommended")

        # Category-specific recommendations
        for factor in risk_factors:
            if (
                factor.category == RiskCategory.TRANSACTION_VOLUME
                and factor.score > 0.7
            ):
                recommendations.append("Consider transaction limits")
            elif factor.category == RiskCategory.ADDRESS_RISK and factor.score > 0.6:
                recommendations.append("Verify address legitimacy")
            elif factor.category == RiskCategory.AMOUNT_ANOMALY and factor.score > 0.8:
                recommendations.append("Investigate unusual transaction amounts")

        # Threshold-specific recommendations
        for threshold in triggered_thresholds:
            if threshold.risk_level in [RiskLevel.CRITICAL, RiskLevel.SEVERE]:
                recommendations.append(
                    f"Critical threshold breached: {threshold.description}"
                )

        return list(set(recommendations))  # Remove duplicates

    def _calculate_confidence(self, risk_factors: List[RiskFactor]) -> float:
        """Calculate confidence score for the assessment."""
        if not risk_factors:
            return 0.0

        # Confidence based on number of factors and data quality
        factor_count = len(risk_factors)
        data_quality_bonus = sum(
            0.1 for factor in risk_factors if factor.data_source != "default_model"
        )

        confidence = min(0.5 + (factor_count * 0.1) + data_quality_bonus, 1.0)
        return confidence

    async def _persist_assessment(self, assessment: RiskAssessment):
        """Persist risk assessment to database."""
        query = """
        CREATE (a:RiskAssessment {
            assessment_id: $assessment_id,
            entity_id: $entity_id,
            entity_type: $entity_type,
            overall_score: $overall_score,
            risk_level: $risk_level,
            status: $status,
            trigger_type: $trigger_type,
            assessor: $assessor,
            confidence: $confidence,
            recommendations: $recommendations,
            created_at: $created_at,
            updated_at: $updated_at,
            metadata: $metadata
        })
        """

        await self.neo4j_session.run(
            query,
            assessment_id=assessment.assessment_id,
            entity_id=assessment.entity_id,
            entity_type=assessment.entity_type,
            overall_score=assessment.overall_score,
            risk_level=assessment.risk_level.value,
            status=assessment.status.value,
            trigger_type=assessment.trigger_type.value,
            assessor=assessment.assessor,
            confidence=assessment.confidence,
            recommendations=assessment.recommendations,
            created_at=assessment.created_at.isoformat(),
            updated_at=assessment.updated_at.isoformat(),
            metadata=assessment.metadata,
        )

        # Persist risk factors
        for factor in assessment.risk_factors:
            factor_query = """
            CREATE (f:RiskFactor {
                factor_id: $factor_id,
                category: $category,
                weight: $weight,
                value: $value,
                score: $score,
                description: $description,
                data_source: $data_source,
                timestamp: $timestamp
            })
            WITH f
            MATCH (a:RiskAssessment {assessment_id: $assessment_id})
            CREATE (a)-[:HAS_FACTOR]->(f)
            """

            await self.neo4j_session.run(
                factor_query,
                factor_id=factor.factor_id,
                category=factor.category.value,
                weight=factor.weight,
                value=factor.value,
                score=factor.score,
                description=factor.description,
                data_source=factor.data_source,
                timestamp=factor.timestamp.isoformat(),
                assessment_id=assessment.assessment_id,
            )

        # Persist triggered thresholds
        for threshold in assessment.triggered_thresholds:
            threshold_query = """
            MATCH (a:RiskAssessment {assessment_id: $assessment_id})
            MATCH (t:RiskThreshold {threshold_id: $threshold_id})
            CREATE (a)-[:TRIGGERED]->(t)
            """

            await self.neo4j_session.run(
                threshold_query,
                assessment_id=assessment.assessment_id,
                threshold_id=threshold.threshold_id,
            )

    async def _execute_workflow(
        self, workflow: RiskWorkflow, assessment: RiskAssessment
    ):
        """Execute risk assessment workflow."""
        execution_id = f"execution_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{hashlib.sha256(assessment.assessment_id.encode()).hexdigest()[:8]}"

        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow.workflow_id,
            assessment_id=assessment.assessment_id,
            status=AssessmentStatus.IN_PROGRESS,
            current_step=0,
            total_steps=len(workflow.assessment_steps),
        )

        # Persist workflow execution
        query = """
        CREATE (e:WorkflowExecution {
            execution_id: $execution_id,
            workflow_id: $workflow_id,
            assessment_id: $assessment_id,
            status: $status,
            current_step: $current_step,
            total_steps: $total_steps,
            started_at: $started_at,
            execution_log: $execution_log
        })
        """

        await self.neo4j_session.run(
            query,
            execution_id=execution.execution_id,
            workflow_id=execution.workflow_id,
            assessment_id=execution.assessment_id,
            status=execution.status.value,
            current_step=execution.current_step,
            total_steps=execution.total_steps,
            started_at=execution.started_at.isoformat(),
            execution_log=execution.execution_log,
        )

        # Execute workflow steps (simplified)
        for i, step in enumerate(workflow.assessment_steps):
            await asyncio.sleep(0.1)  # Simulate step execution
            execution.current_step = i + 1
            execution.execution_log.append(f"Completed step: {step}")

        execution.status = AssessmentStatus.COMPLETED
        execution.completed_at = datetime.now(timezone.utc)

        # Update execution record
        update_query = """
        MATCH (e:WorkflowExecution {execution_id: $execution_id})
        SET e.status = $status, e.current_step = $current_step, 
            e.completed_at = $completed_at, e.execution_log = $execution_log
        """

        await self.neo4j_session.run(
            update_query,
            execution_id=execution.execution_id,
            status=execution.status.value,
            current_step=execution.current_step,
            completed_at=execution.completed_at.isoformat(),
            execution_log=execution.execution_log,
        )

    async def _trigger_escalation(self, assessment: RiskAssessment):
        """Trigger escalation procedures for high-risk assessments."""
        escalation_key = f"escalation:{assessment.assessment_id}"

        escalation_data = {
            "assessment_id": assessment.assessment_id,
            "entity_id": assessment.entity_id,
            "entity_type": assessment.entity_type,
            "risk_level": assessment.risk_level.value,
            "overall_score": assessment.overall_score,
            "triggered_at": datetime.now(timezone.utc).isoformat(),
            "recommendations": assessment.recommendations,
        }

        # Store escalation in Redis for immediate processing
        await self.redis_client.setex(
            escalation_key, 86400, json.dumps(escalation_data)  # 24 hours TTL
        )

        logger.warning(
            f"Escalation triggered for assessment {assessment.assessment_id} with risk level {assessment.risk_level.value}"
        )

    # Helper methods for risk factor calculations
    async def _get_transaction_volume(self, entity_id: str, entity_type: str) -> float:
        """Get transaction volume for risk assessment."""
        # Simulate transaction volume calculation
        await asyncio.sleep(0.01)
        return hash(entity_id) % 1000000 / 1000  # Random value between 0-1000

    async def _get_address_risk_score(self, address: str) -> float:
        """Get address risk score from database."""
        # Simulate address risk lookup
        await asyncio.sleep(0.01)
        return (hash(address) % 100) / 100  # Random value between 0-1

    async def _get_amount_anomaly_score(
        self, entity_id: str, entity_type: str
    ) -> float:
        """Calculate amount anomaly score."""
        # Simulate anomaly detection
        await asyncio.sleep(0.01)
        return (hash(entity_id) % 80) / 100  # Random value between 0-0.8

    def _calculate_volume_score(self, volume: float) -> float:
        """Calculate risk score based on transaction volume."""
        # Logarithmic scaling for volume
        if volume <= 0:
            return 0.0
        elif volume < 1000:
            return 0.2
        elif volume < 10000:
            return 0.4
        elif volume < 100000:
            return 0.6
        elif volume < 1000000:
            return 0.8
        else:
            return 1.0
