"""
End-to-End Compliance Workflow Tests — rewritten to match actual engine APIs.

Tests cross-engine workflows by mocking DB calls and verifying that
the engines can be used together in realistic scenarios.
"""

import contextlib

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from src.compliance.audit_trail import (
    AuditTrailEngine, AuditEventType, AuditSeverity, ComplianceCategory,
)
from src.compliance.case_management import (
    CaseManagementEngine, CaseType, CasePriority, CaseStatus,
    EvidenceType, Case,
)
from src.compliance.regulatory_reporting import (
    RegulatoryReportingEngine, RegulatoryJurisdiction, ReportType, ReportStatus,
    RegulatoryReport,
)
from src.compliance.automated_risk_assessment import (
    AutomatedRiskAssessmentEngine, RiskLevel, TriggerType, RiskFactor,
    RiskCategory, RiskAssessment, AssessmentStatus,
)


def _make_factor(factor_id="f1", category=RiskCategory.TRANSACTION_VOLUME,
                 weight=1.0, value=0.5, score=0.5, description="d", data_source="t"):
    return RiskFactor(
        factor_id=factor_id, category=category, weight=weight,
        value=value, score=score, description=description, data_source=data_source,
    )


class TestComplianceWorkflows:
    """Test suite for end-to-end compliance workflows"""

    @pytest.fixture
    def engines(self):
        """Create all compliance engines for workflow testing"""
        return {
            "regulatory": RegulatoryReportingEngine(),
            "case": CaseManagementEngine(),
            "audit": AuditTrailEngine(),
            "risk": AutomatedRiskAssessmentEngine(),
        }

    # ---- Workflow: Risk Assessment → Case Creation ----

    @pytest.mark.asyncio
    async def test_risk_to_case_workflow(self, engines):
        """High risk assessment triggers case creation"""
        risk_engine = engines["risk"]
        case_engine = engines["case"]

        # Step 1: Create risk assessment (mocked)
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(risk_engine, '_assess_risk_factors', new_callable=AsyncMock, return_value=[
                _make_factor(category=RiskCategory.NETWORK_RISK, score=0.9, value=0.9),
            ]))
            stack.enter_context(patch.object(risk_engine, '_check_thresholds', new_callable=AsyncMock, return_value=[]))
            stack.enter_context(patch.object(risk_engine, '_persist_assessment', new_callable=AsyncMock))
            stack.enter_context(patch.object(risk_engine, '_execute_workflow', new_callable=AsyncMock))
            stack.enter_context(patch.object(risk_engine, '_trigger_escalation', new_callable=AsyncMock))
            assessment = await risk_engine.create_risk_assessment(
                entity_id="0xsuspect",
                entity_type="address",
                trigger_type=TriggerType.AUTOMATIC,
            )

        assert assessment.risk_level in (RiskLevel.HIGH, RiskLevel.SEVERE, RiskLevel.CRITICAL)

        # Step 2: Create case based on assessment
        with patch.object(case_engine, '_store_case', new_callable=AsyncMock):
            case = await case_engine.create_case(
                title=f"High Risk: {assessment.entity_id}",
                description=f"Automated case from risk assessment {assessment.assessment_id}",
                case_type=CaseType.SUSPICIOUS_ACTIVITY,
                priority=CasePriority.HIGH,
                assigned_to="investigator_1",
                created_by="system",
                targets=[assessment.entity_id],
                metadata={"assessment_id": assessment.assessment_id},
            )

        assert isinstance(case, Case)
        assert case.targets == ["0xsuspect"]

    # ---- Workflow: Case → Audit Trail ----

    @pytest.mark.asyncio
    async def test_case_audit_trail_workflow(self, engines):
        """Case creation is logged in audit trail"""
        case_engine = engines["case"]
        audit_engine = engines["audit"]

        # Step 1: Create case
        with patch.object(case_engine, '_store_case', new_callable=AsyncMock):
            case = await case_engine.create_case(
                title="AML Investigation",
                description="Potential money laundering",
                case_type=CaseType.MONEY_LAUNDERING,
                priority=CasePriority.URGENT,
                assigned_to="inv_1",
                created_by="analyst_1",
            )

        # Step 2: Log to audit trail
        with patch.object(audit_engine, '_store_audit_event', new_callable=AsyncMock):
            with patch.object(audit_engine, '_get_latest_event', new_callable=AsyncMock, return_value=None):
                with patch.object(audit_engine, '_update_compliance_logs', new_callable=AsyncMock):
                    event_id = await audit_engine.log_event(
                        event_type=AuditEventType.CASE_CREATED,
                        severity=AuditSeverity.MEDIUM,
                        user_id="analyst_1",
                        session_id="sess_1",
                        ip_address="10.0.0.1",
                        user_agent="Chrome",
                        action="case_created",
                        description=f"Created case {case.case_id}",
                        resource_id=case.case_id,
                        resource_type="case",
                    )

        assert event_id is not None
        assert event_id.startswith("audit_")

    # ---- Workflow: Case → Regulatory Report ----

    @pytest.mark.asyncio
    async def test_case_to_report_workflow(self, engines):
        """Case investigation leads to regulatory report"""
        case_engine = engines["case"]
        reg_engine = engines["regulatory"]

        # Step 1: Create case
        with patch.object(case_engine, '_store_case', new_callable=AsyncMock):
            case = await case_engine.create_case(
                title="SAR Filing Required",
                description="Suspicious activity requiring SAR",
                case_type=CaseType.SUSPICIOUS_ACTIVITY,
                priority=CasePriority.HIGH,
                assigned_to="inv_1",
                created_by="system",
            )

        # Step 2: Generate regulatory report
        with patch.object(reg_engine, '_store_report', new_callable=AsyncMock):
            with patch.object(reg_engine, '_validate_report_data', new_callable=AsyncMock, return_value={'valid': True}):
                report = await reg_engine.create_regulatory_report(
                    jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                    report_type=ReportType.SAR,
                    case_id=case.case_id,
                    triggered_by="0xabc",
                    report_data={"suspicious_activity_details": case.title, "transaction_amount": 1,
                                 "date_range": "d", "involved_parties": ["A"], "suspicion_reasons": ["pattern"]},
                )

        assert isinstance(report, RegulatoryReport)
        assert report.case_id == case.case_id
        assert report.report_type == ReportType.SAR

    # ---- Workflow: Full pipeline ----

    @pytest.mark.asyncio
    async def test_full_compliance_pipeline(self, engines):
        """Complete pipeline: Risk → Case → Evidence → Audit → Report"""
        risk_engine = engines["risk"]
        case_engine = engines["case"]
        audit_engine = engines["audit"]
        reg_engine = engines["regulatory"]

        # 1. Risk assessment
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(risk_engine, '_assess_risk_factors', new_callable=AsyncMock, return_value=[
                _make_factor(category=RiskCategory.TRANSACTION_PATTERN, score=0.85, value=0.85),
            ]))
            stack.enter_context(patch.object(risk_engine, '_check_thresholds', new_callable=AsyncMock, return_value=[]))
            stack.enter_context(patch.object(risk_engine, '_persist_assessment', new_callable=AsyncMock))
            stack.enter_context(patch.object(risk_engine, '_execute_workflow', new_callable=AsyncMock))
            stack.enter_context(patch.object(risk_engine, '_trigger_escalation', new_callable=AsyncMock))
            assessment = await risk_engine.create_risk_assessment(
                entity_id="0xtarget", entity_type="address",
                trigger_type=TriggerType.AUTOMATIC,
            )

        # 2. Create case
        with patch.object(case_engine, '_store_case', new_callable=AsyncMock):
            case = await case_engine.create_case(
                title="Investigation", description="Auto-generated",
                case_type=CaseType.SUSPICIOUS_ACTIVITY, priority=CasePriority.HIGH,
                assigned_to="inv_1", created_by="system",
                metadata={"assessment_id": assessment.assessment_id},
            )

        # 3. Add evidence
        with patch.object(case_engine, '_store_evidence', new_callable=AsyncMock):
            with patch.object(case_engine, '_update_case_evidence_count', new_callable=AsyncMock):
                evidence = await case_engine.add_evidence(
                    case_id=case.case_id,
                    evidence_type=EvidenceType.ADDRESS_ANALYSIS,
                    title="Risk Assessment",
                    description=f"Risk score: {assessment.overall_score}",
                    source="risk_engine",
                    collected_by="system",
                    data={"risk_score": assessment.overall_score},
                )

        # 4. Audit log
        with patch.object(audit_engine, '_store_audit_event', new_callable=AsyncMock):
            with patch.object(audit_engine, '_get_latest_event', new_callable=AsyncMock, return_value=None):
                with patch.object(audit_engine, '_update_compliance_logs', new_callable=AsyncMock):
                    await audit_engine.log_event(
                        event_type=AuditEventType.CASE_CREATED,
                        severity=AuditSeverity.MEDIUM,
                        user_id="system", session_id="auto",
                        ip_address="127.0.0.1", user_agent="system",
                        resource_id=case.case_id, resource_type="case",
                    )

        # 5. Regulatory report
        with patch.object(reg_engine, '_store_report', new_callable=AsyncMock):
            with patch.object(reg_engine, '_validate_report_data', new_callable=AsyncMock, return_value={'valid': True}):
                report = await reg_engine.create_regulatory_report(
                    jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                    report_type=ReportType.SAR,
                    case_id=case.case_id,
                    triggered_by="0xtarget",
                    report_data={"suspicious_activity_details": "auto", "transaction_amount": 1,
                                 "date_range": "d", "involved_parties": ["A"], "suspicion_reasons": ["r"]},
                )

        # Verify full pipeline
        assert assessment.risk_level in (RiskLevel.HIGH, RiskLevel.SEVERE, RiskLevel.CRITICAL)
        assert case.status == CaseStatus.OPEN
        assert evidence.case_id == case.case_id
        assert report.case_id == case.case_id
        assert report.status == ReportStatus.DRAFT

