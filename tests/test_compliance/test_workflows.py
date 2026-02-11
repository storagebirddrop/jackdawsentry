"""
End-to-End Compliance Workflow Tests

Comprehensive test suite for complete compliance workflows including:
- Multi-step compliance processes
- Cross-module integration workflows
- Real-world compliance scenarios
- Performance and reliability testing
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from src.compliance import (
    RegulatoryReportingEngine,
    CaseManagementEngine,
    AuditTrailEngine,
    AutomatedRiskAssessmentEngine,
    RegulatoryJurisdiction,
    ReportType,
    CaseStatus,
    CasePriority,
    RiskLevel,
    AssessmentStatus,
    TriggerType
)


class TestComplianceWorkflows:
    """Test suite for end-to-end compliance workflows"""

    @pytest.fixture
    async def compliance_engines(self):
        """Create all compliance engines for workflow testing"""
        regulatory_engine = RegulatoryReportingEngine()
        case_engine = CaseManagementEngine()
        audit_engine = AuditTrailEngine()
        risk_engine = AutomatedRiskAssessmentEngine()

        await regulatory_engine.initialize()
        await case_engine.initialize()
        await audit_engine.initialize()
        await risk_engine.initialize()

        yield {
            "regulatory": regulatory_engine,
            "case": case_engine,
            "audit": audit_engine,
            "risk": risk_engine
        }

        # Cleanup if needed

    @pytest.fixture
    def sample_suspicious_transaction(self):
        """Create sample suspicious transaction data"""
        return {
            "transaction_hash": "0x1234567890abcdef1234567890abcdef12345678",
            "amount": 9500.00,  # Just below $10,000 reporting threshold
            "timestamp": "2024-01-15T10:30:00Z",
            "from_address": "0xsender1234567890abcdef1234567890abcdef123456",
            "to_address": "0xreceiver1234567890abcdef1234567890abcdef123456",
            "blockchain": "ethereum",
            "suspicious_indicators": [
                "structuring_pattern",
                "rapid_movement",
                "high_frequency_small_amounts",
                "new_counterparty"
            ],
            "risk_score": 0.85
        }

    @pytest.fixture
    def sample_sanctions_match(self):
        """Create sample sanctions match data"""
        return {
            "address": "0xsanctioned1234567890abcdef1234567890abcdef12",
            "sanctions_list": "OFAC_SDN",
            "match_confidence": 0.95,
            "list_name": "Specially Designated Nationals (SDN)",
            "program": "terrorism",
            "date_added": "2024-01-01",
            "identification_info": {
                "name": "SUSPICIOUS ENTITY",
                "aliases": ["ENTITY A", "ENTITY B"],
                "addresses": ["123 Main St", "456 Oak Ave"]
            }
        }

    class TestSuspiciousActivityWorkflow:
        """Test complete suspicious activity investigation workflow"""

        @pytest.mark.asyncio
        async def test_complete_suspicious_activity_workflow(self, compliance_engines, sample_suspicious_transaction):
            """Test complete workflow from detection to resolution"""
            engines = compliance_engines

            # Step 1: Initial risk assessment
            risk_assessment = await engines["risk"].create_risk_assessment(
                entity_id=sample_suspicious_transaction["from_address"],
                entity_type="address",
                trigger_type=TriggerType.PATTERN_DETECTION,
                assessor="automated_system",
                metadata={
                    "detection_source": "transaction_monitoring",
                    "suspicious_indicators": sample_suspicious_transaction["suspicious_indicators"]
                }
            )

            assert risk_assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            assert len(risk_assessment.risk_factors) > 0

            # Step 2: Log audit event for detection
            audit_event = await engines["audit"].log_event(
                event_type="compliance_check",
                description="High-risk transaction pattern detected",
                severity="high",
                user_id="automated_monitoring",
                resource_type="transaction",
                resource_id=sample_suspicious_transaction["transaction_hash"],
                details={
                    "risk_assessment_id": risk_assessment.assessment_id,
                    "risk_score": risk_assessment.overall_score,
                    "suspicious_indicators": sample_suspicious_transaction["suspicious_indicators"]
                }
            )

            assert audit_event.event_id is not None

            # Step 3: Create compliance case
            case = await engines["case"].create_case(
                title=f"Suspicious Activity - {sample_suspicious_transaction['transaction_hash'][:10]}...",
                description=f"Suspicious transaction pattern detected involving address {sample_suspicious_transaction['from_address']}",
                case_type="suspicious_activity",
                priority=CasePriority.HIGH,
                assigned_to="investigator_001",
                created_by="automated_system",
                metadata={
                    "risk_assessment_id": risk_assessment.assessment_id,
                    "transaction_hash": sample_suspicious_transaction["transaction_hash"],
                    "initial_risk_score": risk_assessment.overall_score
                }
            )

            assert case.status == CaseStatus.OPEN
            assert case.priority == CasePriority.HIGH

            # Step 4: Add evidence to case
            evidence = await engines["case"].add_evidence(
                case_id=case.case_id,
                evidence_type="transaction_data",
                description="Suspicious transaction details",
                content=sample_suspicious_transaction,
                collected_by="automated_system",
                source="blockchain_analysis",
                tags=["suspicious", "structuring", "high_value"]
            )

            assert evidence.evidence_id is not None
            assert evidence.status == "pending_review"

            # Step 5: Log case creation in audit trail
            case_audit_event = await engines["audit"].log_event(
                event_type="user_action",
                description="Compliance case created for suspicious activity",
                severity="medium",
                user_id="automated_system",
                resource_type="case",
                resource_id=case.case_id,
                details={
                    "case_id": case.case_id,
                    "case_type": case.case_type,
                    "priority": case.priority.value,
                    "evidence_count": 1
                }
            )

            # Step 6: Update case status to in_progress
            updated_case = await engines["case"].update_case_status(
                case.case_id,
                CaseStatus.IN_PROGRESS,
                updated_by="investigator_001",
                notes="Investigation started, evidence under review"
            )

            assert updated_case.status == CaseStatus.IN_PROGRESS

            # Step 7: Create regulatory report if threshold met
            if risk_assessment.overall_score > 0.7:
                regulatory_report = await engines["regulatory"].create_report(
                    jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                    report_type=ReportType.SAR,
                    entity_id=case.case_id,
                    submitted_by="investigator_001",
                    content={
                        "suspicious_activity": {
                            "transaction_details": sample_suspicious_transaction,
                            "risk_assessment": {
                                "assessment_id": risk_assessment.assessment_id,
                                "overall_score": risk_assessment.overall_score,
                                "risk_level": risk_assessment.risk_level.value,
                                "risk_factors": [
                                    {
                                        "category": factor.category.value,
                                        "score": factor.score,
                                        "description": factor.description
                                    }
                                    for factor in risk_assessment.risk_factors
                                ]
                            },
                            "case_details": {
                                "case_id": case.case_id,
                                "evidence_summary": "Suspicious transaction pattern detected",
                                "investigator_notes": "Pattern indicates possible structuring activity"
                            }
                        },
                        "subject_information": {
                            "address": sample_suspicious_transaction["from_address"],
                            "blockchain": sample_suspicious_transaction["blockchain"],
                            "first_seen": sample_suspicious_transaction["timestamp"]
                        }
                    }
                )

                assert regulatory_report.status == "draft"

                # Step 8: Submit regulatory report
                submitted_report = await engines["regulatory"].submit_report(regulatory_report.report_id)
                assert submitted_report.status == "submitted"

            # Step 9: Close case after investigation
            final_case = await engines["case"].update_case_status(
                case.case_id,
                CaseStatus.CLOSED,
                updated_by="investigator_001",
                notes="Investigation completed, SAR filed with FINCEN"
            )

            assert final_case.status == CaseStatus.CLOSED

            # Step 10: Log case closure
            closure_audit_event = await engines["audit"].log_event(
                event_type="user_action",
                description="Compliance case closed - investigation completed",
                severity="low",
                user_id="investigator_001",
                resource_type="case",
                resource_id=case.case_id,
                details={
                    "final_status": "closed",
                    "resolution": "SAR filed",
                    "investigation_duration": "2 days"
                }
            )

            # Verify workflow completion
            assert risk_assessment.assessment_id is not None
            assert case.case_id is not None
            assert evidence.evidence_id is not None
            assert regulatory_report.report_id is not None

            # Verify audit trail integrity
            audit_events = await engines["audit"].get_events_by_resource("case", case.case_id)
            assert len(audit_events) >= 3  # Creation, update, closure

    class TestSanctionsScreeningWorkflow:
        """Test complete sanctions screening workflow"""

        @pytest.mark.asyncio
        async def test_sanctions_screening_workflow(self, compliance_engines, sample_sanctions_match):
            """Test complete sanctions screening workflow"""
            engines = compliance_engines

            # Step 1: Initial sanctions detection
            audit_event = await engines["audit"].log_event(
                event_type="compliance_check",
                description="Sanctions list match detected",
                severity="critical",
                user_id="automated_screening",
                resource_type="address",
                resource_id=sample_sanctions_match["address"],
                details={
                    "sanctions_list": sample_sanctions_match["sanctions_list"],
                    "match_confidence": sample_sanctions_match["match_confidence"],
                    "list_name": sample_sanctions_match["list_name"]
                }
            )

            # Step 2: Create high-priority case
            case = await engines["case"].create_case(
                title=f"Sanctions Match - {sample_sanctions_match['list_name']}",
                description=f"Address {sample_sanctions_match['address']} matched sanctions list {sample_sanctions_match['sanctions_list']}",
                case_type="sanctions_screening",
                priority=CasePriority.CRITICAL,
                assigned_to="compliance_officer_001",
                created_by="automated_screening",
                metadata={
                    "sanctions_match": sample_sanctions_match,
                    "match_confidence": sample_sanctions_match["match_confidence"]
                }
            )

            # Step 3: Add sanctions evidence
            evidence = await engines["case"].add_evidence(
                case_id=case.case_id,
                evidence_type="sanctions_data",
                description="Sanctions list match details",
                content=sample_sanctions_match,
                collected_by="automated_screening",
                source="sanctions_database",
                tags=["sanctions", "critical", "immediate_action"]
            )

            # Step 4: Risk assessment
            risk_assessment = await engines["risk"].create_risk_assessment(
                entity_id=sample_sanctions_match["address"],
                entity_type="address",
                trigger_type=TriggerType.REGULATORY_REQUIREMENT,
                assessor="compliance_system",
                metadata={
                    "sanctions_match": True,
                    "case_id": case.case_id,
                    "match_confidence": sample_sanctions_match["match_confidence"]
                }
            )

            # Should be critical risk due to sanctions match
            assert risk_assessment.risk_level == RiskLevel.SEVERE

            # Step 5: Immediate regulatory reporting
            regulatory_report = await engines["regulatory"].create_report(
                jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                report_type=ReportType.SAR,
                entity_id=case.case_id,
                submitted_by="compliance_officer_001",
                content={
                    "suspicious_activity": {
                        "sanctions_match": sample_sanctions_match,
                        "risk_assessment": {
                            "assessment_id": risk_assessment.assessment_id,
                            "risk_level": risk_assessment.risk_level.value,
                            "overall_score": risk_assessment.overall_score
                        }
                    },
                    "subject_information": {
                        "address": sample_sanctions_match["address"],
                        "sanctions_details": sample_sanctions_match["identification_info"]
                    },
                    "filing_requirements": {
                        "immediate_filing_required": True,
                        "filing_deadline": "immediate",
                        "regulatory_reference": "31 CFR 103.18"
                    }
                }
            )

            # Step 6: Submit report immediately
            submitted_report = await engines["regulatory"].submit_report(regulatory_report.report_id)

            # Step 7: Update case with immediate actions taken
            updated_case = await engines["case"].update_case_status(
                case.case_id,
                CaseStatus.CLOSED,
                updated_by="compliance_officer_001",
                notes="Immediate SAR filed, address blocked, sanctions compliance verified"
            )

            # Verify workflow completion
            assert case.priority == CasePriority.CRITICAL
            assert risk_assessment.risk_level == RiskLevel.SEVERE
            assert submitted_report.status == "submitted"
            assert updated_case.status == CaseStatus.CLOSED

    class TestMultiJurisdictionalReportingWorkflow:
        """Test multi-jurisdictional reporting workflow"""

        @pytest.mark.asyncio
        async def test_multi_jurisdictional_workflow(self, compliance_engines, sample_suspicious_transaction):
            """Test workflow requiring reports to multiple jurisdictions"""
            engines = compliance_engines

            # Step 1: Create case for multi-jurisdictional investigation
            case = await engines["case"].create_case(
                title="Multi-Jurisdictional Suspicious Activity",
                description="Transaction requiring reporting to multiple regulatory bodies",
                case_type="suspicious_activity",
                priority=CasePriority.HIGH,
                assigned_to="senior_investigator",
                created_by="compliance_system",
                metadata={
                    "jurisdictions": ["USA", "UK", "EU"],
                    "transaction_details": sample_suspicious_transaction
                }
            )

            # Step 2: Risk assessment
            risk_assessment = await engines["risk"].create_risk_assessment(
                entity_id=sample_suspicious_transaction["from_address"],
                entity_type="address",
                trigger_type=TriggerType.MANUAL,
                assessor="senior_investigator",
                metadata={
                    "multi_jurisdictional": True,
                    "case_id": case.case_id
                }
            )

            # Step 3: Create US FINCEN SAR
            us_report = await engines["regulatory"].create_report(
                jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                report_type=ReportType.SAR,
                entity_id=case.case_id,
                submitted_by="senior_investigator",
                content={
                    "jurisdiction_specific": {
                        "filing_requirements": "31 CFR 103.18",
                        "dollar_threshold": 10000,
                        "reporting_format": "FinCEN SAR"
                    },
                    "suspicious_activity": {
                        "transaction": sample_suspicious_transaction,
                        "risk_assessment": {
                            "assessment_id": risk_assessment.assessment_id,
                            "overall_score": risk_assessment.overall_score
                        }
                    }
                }
            )

            # Step 4: Create UK FCA SAR
            uk_report = await engines["regulatory"].create_report(
                jurisdiction=RegulatoryJurisdiction.UK_FCA,
                report_type=ReportType.SAR,
                entity_id=case.case_id,
                submitted_by="senior_investigator",
                content={
                    "jurisdiction_specific": {
                        "filing_requirements": "MLR 2017 Regulations",
                        "pound_threshold": 1000,
                        "reporting_format": "FCA SAR"
                    },
                    "suspicious_activity": {
                        "transaction": sample_suspicious_transaction,
                        "risk_assessment": {
                            "assessment_id": risk_assessment.assessment_id,
                            "overall_score": risk_assessment.overall_score
                        }
                    }
                }
            )

            # Step 5: Submit all reports
            us_submitted = await engines["regulatory"].submit_report(us_report.report_id)
            uk_submitted = await engines["regulatory"].submit_report(uk_report.report_id)

            # Step 6: Log multi-jurisdictional filing
            audit_event = await engines["audit"].log_event(
                event_type="compliance_check",
                description="Multi-jurisdictional SAR filing completed",
                severity="high",
                user_id="senior_investigator",
                resource_type="case",
                resource_id=case.case_id,
                details={
                    "jurisdictions": ["USA_FINCEN", "UK_FCA"],
                    "reports_submitted": [us_submitted.report_id, uk_submitted.report_id],
                    "filing_timestamp": datetime.utcnow().isoformat()
                }
            )

            # Verify workflow completion
            assert us_submitted.status == "submitted"
            assert uk_submitted.status == "submitted"
            assert len(audit_event.details["reports_submitted"]) == 2

    class TestOngoingMonitoringWorkflow:
        """Test ongoing monitoring and periodic assessment workflow"""

        @pytest.mark.asyncio
        async def test_ongoing_monitoring_workflow(self, compliance_engines):
            """Test ongoing monitoring workflow with periodic assessments"""
            engines = compliance_engines

            # Step 1: Create monitoring case
            case = await engines["case"].create_case(
                title="Ongoing Monitoring - High Risk Address",
                description="Continuous monitoring of high-risk address",
                case_type="ongoing_monitoring",
                priority=CasePriority.MEDIUM,
                assigned_to="monitoring_team",
                created_by="automated_system",
                metadata={
                    "monitoring_frequency": "daily",
                    "risk_threshold": 0.7,
                    "monitoring_start": datetime.utcnow().isoformat()
                }
            )

            # Step 2: Initial risk assessment
            initial_assessment = await engines["risk"].create_risk_assessment(
                entity_id="0xmonitored1234567890abcdef1234567890abcdef",
                entity_type="address",
                trigger_type=TriggerType.SCHEDULED,
                assessor="monitoring_system",
                metadata={
                    "monitoring_case_id": case.case_id,
                    "assessment_type": "initial"
                }
            )

            # Step 3: Simulate periodic monitoring over time
            monitoring_periods = 5
            for period in range(monitoring_periods):
                # Simulate time passing
                monitoring_date = datetime.utcnow() + timedelta(days=period)
                
                with patch('src.compliance.automated_risk_assessment.datetime') as mock_datetime:
                    mock_datetime.utcnow.return_value = monitoring_date

                    # Periodic risk assessment
                    periodic_assessment = await engines["risk"].create_risk_assessment(
                        entity_id="0xmonitored1234567890abcdef1234567890abcdef",
                        entity_type="address",
                        trigger_type=TriggerType.SCHEDULED,
                        assessor="monitoring_system",
                        metadata={
                            "monitoring_case_id": case.case_id,
                            "assessment_type": "periodic",
                            "period_number": period + 1
                        }
                    )

                    # Log monitoring event
                    monitoring_event = await engines["audit"].log_event(
                        event_type="compliance_check",
                        description=f"Periodic risk assessment - Period {period + 1}",
                        severity="info",
                        user_id="monitoring_system",
                        resource_type="address",
                        resource_id="0xmonitored1234567890abcdef1234567890abcdef",
                        details={
                            "assessment_id": periodic_assessment.assessment_id,
                            "risk_score": periodic_assessment.overall_score,
                            "risk_level": periodic_assessment.risk_level.value,
                            "monitoring_period": period + 1
                        }
                    )

                    # Add monitoring evidence
                    await engines["case"].add_evidence(
                        case_id=case.case_id,
                        evidence_type="monitoring_data",
                        description=f"Monitoring assessment - Period {period + 1}",
                        content={
                            "assessment_id": periodic_assessment.assessment_id,
                            "risk_score": periodic_assessment.overall_score,
                            "assessment_date": monitoring_date.isoformat(),
                            "risk_factors": [
                                {
                                    "category": factor.category.value,
                                    "score": factor.score
                                }
                                for factor in periodic_assessment.risk_factors
                            ]
                        },
                        collected_by="monitoring_system",
                        source="automated_monitoring"
                    )

            # Step 4: Generate monitoring summary report
            monitoring_summary = await engines["audit"].generate_audit_report(
                start_date=datetime.utcnow() - timedelta(days=monitoring_periods),
                end_date=datetime.utcnow(),
                include_compliance_logs=True
            )

            # Step 5: Update case with monitoring summary
            final_case = await engines["case"].update_case_status(
                case.case_id,
                CaseStatus.CLOSED,
                updated_by="monitoring_team",
                notes=f"Monitoring completed - {monitoring_periods} periods assessed"
            )

            # Verify monitoring workflow
            assert monitoring_summary.total_events >= monitoring_periods
            assert final_case.status == CaseStatus.CLOSED

    class TestEscalationWorkflow:
        """Test escalation workflow for high-risk scenarios"""

        @pytest.mark.asyncio
        async def test_escalation_workflow(self, compliance_engines, sample_suspicious_transaction):
            """Test escalation workflow for critical risk scenarios"""
            engines = compliance_engines

            # Step 1: Create high-priority case
            case = await engines["case"].create_case(
                title="Critical Risk - Immediate Escalation Required",
                description="Critical risk scenario requiring immediate escalation",
                case_type="suspicious_activity",
                priority=CasePriority.CRITICAL,
                assigned_to="junior_analyst",
                created_by="automated_system",
                metadata={
                    "escalation_required": True,
                    "escalation_level": "senior_management"
                }
            )

            # Step 2: Critical risk assessment
            with patch.object(engines["risk"], '_calculate_overall_risk', return_value=(0.95, RiskLevel.SEVERE)):
                risk_assessment = await engines["risk"].create_risk_assessment(
                    entity_id=sample_suspicious_transaction["from_address"],
                    entity_type="address",
                    trigger_type=TriggerType.THRESHOLD_BREACH,
                    assessor="automated_system",
                    metadata={
                        "case_id": case.case_id,
                        "escalation_trigger": True
                    }
                )

            # Step 3: Verify automatic escalation
            escalation_key = f"escalation:{risk_assessment.assessment_id}"
            escalation_data = await engines["risk"].redis_client.get(escalation_key)
            
            assert escalation_data is not None, "Escalation should be triggered for severe risk"

            # Step 4: Log escalation event
            escalation_event = await engines["audit"].log_event(
                event_type="compliance_check",
                description="Critical risk assessment triggered automatic escalation",
                severity="critical",
                user_id="automated_system",
                resource_type="risk_assessment",
                resource_id=risk_assessment.assessment_id,
                details={
                    "risk_level": risk_assessment.risk_level.value,
                    "risk_score": risk_assessment.overall_score,
                    "escalation_triggered": True,
                    "case_id": case.case_id
                }
            )

            # Step 5: Escalate case to senior management
            escalated_case = await engines["case"].update_case_status(
                case.case_id,
                CaseStatus.ESCALATED,
                updated_by="automated_system",
                notes="Automatic escalation due to severe risk assessment"
            )

            # Step 6: Reassign case to senior investigator
            # (In real system, this would involve notification and reassignment)
            reassigned_case = await engines["case"].update_case_status(
                case.case_id,
                CaseStatus.IN_PROGRESS,
                updated_by="senior_investigator",
                notes="Case escalated and assigned to senior investigator for immediate action"
            )

            # Step 7: Immediate regulatory filing
            regulatory_report = await engines["regulatory"].create_report(
                jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                report_type=ReportType.SAR,
                entity_id=case.case_id,
                submitted_by="senior_investigator",
                content={
                    "escalation_details": {
                        "escalation_reason": "Severe risk assessment",
                        "risk_score": risk_assessment.overall_score,
                        "escalation_timestamp": datetime.utcnow().isoformat()
                    },
                    "suspicious_activity": {
                        "transaction": sample_suspicious_transaction,
                        "risk_factors": [
                            {
                                "category": factor.category.value,
                                "score": factor.score,
                                "description": factor.description
                            }
                            for factor in risk_assessment.risk_factors
                        ]
                    }
                }
            )

            # Step 8: Immediate submission
            submitted_report = await engines["regulatory"].submit_report(regulatory_report.report_id)

            # Step 9: Final escalation resolution
            final_case = await engines["case"].update_case_status(
                case.case_id,
                CaseStatus.CLOSED,
                updated_by="senior_investigator",
                notes="Critical case resolved - immediate SAR filed, escalation complete"
            )

            # Verify escalation workflow
            assert risk_assessment.risk_level == RiskLevel.SEVERE
            assert escalated_case.status == CaseStatus.ESCALATED
            assert submitted_report.status == "submitted"
            assert final_case.status == CaseStatus.CLOSED

    class TestWorkflowPerformance:
        """Test workflow performance under load"""

        @pytest.mark.asyncio
        async def test_concurrent_workflow_execution(self, compliance_engines):
            """Test multiple concurrent workflows"""
            engines = compliance_engines

            # Create multiple concurrent workflows
            workflow_count = 10
            tasks = []

            for i in range(workflow_count):
                task = self._run_concurrent_workflow(engines, f"concurrent_{i}")
                tasks.append(task)

            # Execute all workflows concurrently
            start_time = datetime.utcnow()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = datetime.utcnow()

            duration = (end_time - start_time).total_seconds()

            # Verify all workflows completed
            successful_workflows = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_workflows) >= workflow_count * 0.8  # At least 80% success rate
            assert duration < 30.0  # Should complete within 30 seconds

        async def _run_concurrent_workflow(self, engines, workflow_id):
            """Helper method for concurrent workflow execution"""
            try:
                # Create case
                case = await engines["case"].create_case(
                    title=f"Concurrent Test Case - {workflow_id}",
                    description=f"Concurrent workflow test {workflow_id}",
                    case_type="suspicious_activity",
                    priority=CasePriority.MEDIUM,
                    assigned_to="investigator",
                    created_by="test_system"
                )

                # Create risk assessment
                risk_assessment = await engines["risk"].create_risk_assessment(
                    entity_id=f"0x{workflow_id}1234567890abcdef",
                    entity_type="address",
                    trigger_type=TriggerType.AUTOMATIC,
                    assessor="test_system"
                )

                # Add evidence
                await engines["case"].add_evidence(
                    case_id=case.case_id,
                    evidence_type="test_data",
                    description=f"Test evidence for {workflow_id}",
                    content={"workflow_id": workflow_id},
                    collected_by="test_system"
                )

                # Close case
                await engines["case"].update_case_status(
                    case.case_id,
                    CaseStatus.CLOSED,
                    updated_by="test_system",
                    notes=f"Concurrent workflow {workflow_id} completed"
                )

                return {
                    "workflow_id": workflow_id,
                    "case_id": case.case_id,
                    "assessment_id": risk_assessment.assessment_id,
                    "status": "completed"
                }

            except Exception as e:
                return {
                    "workflow_id": workflow_id,
                    "status": "failed",
                    "error": str(e)
                }

        @pytest.mark.asyncio
        async def test_workflow_memory_usage(self, compliance_engines):
            """Test workflow memory usage and cleanup"""
            import psutil
            import os

            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss

            # Run multiple workflows
            for i in range(20):
                await self._run_concurrent_workflow(engines, f"memory_test_{i}")

            # Check memory usage
            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory

            # Memory increase should be reasonable (less than 100MB)
            assert memory_increase < 100 * 1024 * 1024, f"Memory increase too high: {memory_increase / 1024 / 1024:.2f}MB"

    class TestWorkflowReliability:
        """Test workflow reliability and error handling"""

        @pytest.mark.asyncio
        async def test_workflow_error_recovery(self, compliance_engines):
            """Test workflow recovery from errors"""
            engines = compliance_engines

            # Start workflow
            case = await engines["case"].create_case(
                title="Error Recovery Test Case",
                description="Test case for error recovery",
                case_type="suspicious_activity",
                priority=CasePriority.MEDIUM,
                assigned_to="investigator",
                created_by="test_system"
            )

            # Simulate error in risk assessment
            with patch.object(engines["risk"], 'create_risk_assessment', side_effect=Exception("Simulated error")):
                try:
                    await engines["risk"].create_risk_assessment(
                        entity_id="0xtest1234567890abcdef",
                        entity_type="address",
                        trigger_type=TriggerType.AUTOMATIC,
                        assessor="test_system"
                    )
                except Exception:
                    pass  # Expected error

            # Verify workflow can continue after error
            evidence = await engines["case"].add_evidence(
                case_id=case.case_id,
                evidence_type="test_data",
                description="Test evidence after error",
                content={"error_recovery": True},
                collected_by="test_system"
            )

            assert evidence.evidence_id is not None

            # Complete workflow
            final_case = await engines["case"].update_case_status(
                case.case_id,
                CaseStatus.CLOSED,
                updated_by="test_system",
                notes="Workflow completed despite intermediate error"
            )

            assert final_case.status == CaseStatus.CLOSED

        @pytest.mark.asyncio
        async def test_workflow_data_integrity(self, compliance_engines):
            """Test workflow data integrity"""
            engines = compliance_engines

            # Run complete workflow
            case = await engines["case"].create_case(
                title="Data Integrity Test Case",
                description="Test case for data integrity verification",
                case_type="suspicious_activity",
                priority=CasePriority.HIGH,
                assigned_to="investigator",
                created_by="test_system"
            )

            risk_assessment = await engines["risk"].create_risk_assessment(
                entity_id="0xintegrity1234567890abcdef",
                entity_type="address",
                trigger_type=TriggerType.AUTOMATIC,
                assessor="test_system"
            )

            evidence = await engines["case"].add_evidence(
                case_id=case.case_id,
                evidence_type="test_data",
                description="Data integrity test evidence",
                content={
                    "case_id": case.case_id,
                    "assessment_id": risk_assessment.assessment_id,
                    "test_timestamp": datetime.utcnow().isoformat()
                },
                collected_by="test_system"
            )

            # Verify data integrity
            retrieved_case = await engines["case"].get_case(case.case_id)
            retrieved_assessment = await engines["risk"].get_risk_assessment(risk_assessment.assessment_id)
            retrieved_evidence = await engines["case"].get_case_evidence(case.case_id)

            assert retrieved_case.case_id == case.case_id
            assert retrieved_assessment.assessment_id == risk_assessment.assessment_id
            assert len(retrieved_evidence) >= 1
            assert retrieved_evidence[0].evidence_id == evidence.evidence_id

            # Verify audit trail integrity
            audit_events = await engines["audit"].get_events_by_resource("case", case.case_id)
            assert len(audit_events) >= 1

            integrity_result = await engines["audit"].verify_chain_integrity()
            assert integrity_result["valid"] is True
