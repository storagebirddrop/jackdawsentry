"""
Audit Trail and Compliance Logging Tests

Comprehensive test suite for the audit trail engine including:
- Immutable audit event logging
- Hash chaining for integrity verification
- Compliance category tracking
- Audit report generation
"""

import pytest
import asyncio
import hashlib
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from src.compliance.audit_trail import (
    AuditTrailEngine,
    AuditEventType,
    AuditSeverity,
    ComplianceCategory,
    AuditEvent,
    ComplianceLog,
    AuditReport
)


class TestAuditTrailEngine:
    """Test suite for AuditTrailEngine"""

    @pytest.fixture
    async def engine(self):
        """Create test engine instance"""
        engine = AuditTrailEngine()
        await engine.initialize()
        yield engine
        # Cleanup if needed

    @pytest.fixture
    def sample_event_data(self):
        """Create sample event data"""
        return {
            "user_id": "user_001",
            "action": "case_created",
            "resource_type": "case",
            "resource_id": "case_123",
            "details": {
                "case_title": "Suspicious Activity Investigation",
                "priority": "high",
                "assigned_to": "investigator_001"
            },
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    @pytest.fixture
    def sample_compliance_log_data(self):
        """Create sample compliance log data"""
        return {
            "category": ComplianceCategory.GDPR,
            "action": "data_access",
            "data_subject_id": "subject_001",
            "processing_purpose": "investigation",
            "legal_basis": "legitimate_interest",
            "retention_period": 2555,  # 7 years
            "data_types": ["personal_data", "transaction_data"]
        }

    class TestAuditEventLogging:
        """Test audit event logging functionality"""

        @pytest.mark.asyncio
        async def test_log_user_action_event(self, engine, sample_event_data):
            """Test logging user action events"""
            event = await engine.log_event(
                event_type=AuditEventType.USER_ACTION,
                description="User created new investigation case",
                severity=AuditSeverity.INFO,
                user_id=sample_event_data["user_id"],
                resource_type=sample_event_data["resource_type"],
                resource_id=sample_event_data["resource_id"],
                details=sample_event_data["details"],
                metadata={
                    "ip_address": sample_event_data["ip_address"],
                    "user_agent": sample_event_data["user_agent"]
                }
            )

            assert event.event_id is not None
            assert event.event_type == AuditEventType.USER_ACTION
            assert event.description == "User created new investigation case"
            assert event.severity == AuditSeverity.INFO
            assert event.user_id == sample_event_data["user_id"]
            assert event.resource_type == sample_event_data["resource_type"]
            assert event.resource_id == sample_event_data["resource_id"]
            assert event.details == sample_event_data["details"]
            assert event.timestamp is not None
            assert event.previous_hash is not None  # Should have hash chaining
            assert event.current_hash is not None

        @pytest.mark.asyncio
        async def test_log_security_event(self, engine):
            """Test logging security events"""
            event = await engine.log_event(
                event_type=AuditEventType.SECURITY_BREACH,
                description="Failed login attempt detected",
                severity=AuditSeverity.HIGH,
                user_id="unknown",
                resource_type="authentication",
                details={
                    "login_attempt": "failed",
                    "username": "admin",
                    "ip_address": "192.168.1.200",
                    "failure_reason": "invalid_password"
                },
                metadata={
                    "threat_level": "medium",
                    "requires_action": True
                }
            )

            assert event.event_type == AuditEventType.SECURITY_BREACH
            assert event.severity == AuditSeverity.HIGH
            assert event.details["login_attempt"] == "failed"

        @pytest.mark.asyncio
        async def test_log_system_event(self, engine):
            """Test logging system events"""
            event = await engine.log_event(
                event_type=AuditEventType.SYSTEM_ERROR,
                description="Database connection timeout",
                severity=AuditSeverity.WARNING,
                details={
                    "error_code": "DB_TIMEOUT",
                    "component": "neo4j_client",
                    "duration_ms": 30000,
                    "retry_count": 3
                },
                metadata={
                    "system_component": "database_layer",
                    "impact": "medium"
                }
            )

            assert event.event_type == AuditEventType.SYSTEM_ERROR
            assert event.severity == AuditSeverity.WARNING
            assert "error_code" in event.details

        @pytest.mark.asyncio
        async def test_log_compliance_event(self, engine, sample_compliance_log_data):
            """Test logging compliance events"""
            event = await engine.log_event(
                event_type=AuditEventType.COMPLIANCE_CHECK,
                description="GDPR compliance verification",
                severity=AuditSeverity.INFO,
                user_id="compliance_officer",
                resource_type="data_processing",
                details=sample_compliance_log_data,
                metadata={
                    "compliance_framework": "GDPR",
                    "verification_status": "passed"
                }
            )

            assert event.event_type == AuditEventType.COMPLIANCE_CHECK
            assert event.details["category"] == ComplianceCategory.GDPR
            assert event.details["processing_purpose"] == "investigation"

        @pytest.mark.asyncio
        async def test_invalid_event_type(self, engine, sample_event_data):
            """Test error handling for invalid event type"""
            with pytest.raises(ValueError):
                await engine.log_event(
                    event_type="INVALID_TYPE",
                    description="Test event",
                    severity=AuditSeverity.INFO,
                    user_id=sample_event_data["user_id"]
                )

        @pytest.mark.asyncio
        async def test_missing_required_fields(self, engine):
            """Test error handling for missing required fields"""
            with pytest.raises(ValueError):
                await engine.log_event(
                    event_type=AuditEventType.USER_ACTION,
                    description="",  # Empty description
                    severity=AuditSeverity.INFO,
                    user_id="user_001"
                )

    class TestEventRetrieval:
        """Test event retrieval functionality"""

        @pytest.mark.asyncio
        async def test_get_event_by_id(self, engine, sample_event_data):
            """Test getting event by ID"""
            # Log event
            original_event = await engine.log_event(
                event_type=AuditEventType.USER_ACTION,
                description="User action test",
                severity=AuditSeverity.INFO,
                user_id=sample_event_data["user_id"],
                details=sample_event_data["details"]
            )

            # Retrieve event
            retrieved_event = await engine.get_event(original_event.event_id)

            assert retrieved_event.event_id == original_event.event_id
            assert retrieved_event.event_type == original_event.event_type
            assert retrieved_event.description == original_event.description
            assert retrieved_event.details == original_event.details

        @pytest.mark.asyncio
        async def test_get_nonexistent_event(self, engine):
            """Test getting nonexistent event"""
            event = await engine.get_event("nonexistent_event_id")
            assert event is None

        @pytest.mark.asyncio
        async def test_get_events_by_type(self, engine, sample_event_data):
            """Test getting events by type"""
            # Log different types of events
            user_event = await engine.log_event(
                event_type=AuditEventType.USER_ACTION,
                description="User action",
                severity=AuditSeverity.INFO,
                user_id=sample_event_data["user_id"]
            )

            security_event = await engine.log_event(
                event_type=AuditEventType.SECURITY_BREACH,
                description="Security event",
                severity=AuditSeverity.HIGH,
                user_id="system"
            )

            # Get user action events
            user_events = await engine.get_events_by_type(AuditEventType.USER_ACTION, limit=10)
            user_event_ids = [e.event_id for e in user_events]
            assert user_event.event_id in user_event_ids
            assert security_event.event_id not in user_event_ids

        @pytest.mark.asyncio
        async def test_get_events_by_user(self, engine, sample_event_data):
            """Test getting events by user"""
            # Log events for different users
            user1_event = await engine.log_event(
                event_type=AuditEventType.USER_ACTION,
                description="User 1 action",
                severity=AuditSeverity.INFO,
                user_id="user_001"
            )

            user2_event = await engine.log_event(
                event_type=AuditEventType.USER_ACTION,
                description="User 2 action",
                severity=AuditSeverity.INFO,
                user_id="user_002"
            )

            # Get events for user_001
            user1_events = await engine.get_events_by_user("user_001", limit=10)
            event_ids = [e.event_id for e in user1_events]
            assert user1_event.event_id in event_ids
            assert user2_event.event_id not in event_ids

        @pytest.mark.asyncio
        async def test_get_events_by_severity(self, engine):
            """Test getting events by severity"""
            # Log events with different severities
            info_event = await engine.log_event(
                event_type=AuditEventType.USER_ACTION,
                description="Info event",
                severity=AuditSeverity.INFO,
                user_id="user_001"
            )

            critical_event = await engine.log_event(
                event_type=AuditEventType.SECURITY_BREACH,
                description="Critical event",
                severity=AuditSeverity.CRITICAL,
                user_id="system"
            )

            # Get critical events
            critical_events = await engine.get_events_by_severity(AuditSeverity.CRITICAL, limit=10)
            event_ids = [e.event_id for e in critical_events]
            assert critical_event.event_id in event_ids
            assert info_event.event_id not in event_ids

        @pytest.mark.asyncio
        async def test_get_events_by_date_range(self, engine, sample_event_data):
            """Test getting events by date range"""
            # Log events at different times
            start_time = datetime.utcnow()
            
            event1 = await engine.log_event(
                event_type=AuditEventType.USER_ACTION,
                description="Event 1",
                severity=AuditSeverity.INFO,
                user_id=sample_event_data["user_id"]
            )

            await asyncio.sleep(0.1)  # Small delay

            event2 = await engine.log_event(
                event_type=AuditEventType.USER_ACTION,
                description="Event 2",
                severity=AuditSeverity.INFO,
                user_id=sample_event_data["user_id"]
            )

            end_time = datetime.utcnow()

            # Get events in date range
            events = await engine.get_events_by_date_range(start_time, end_time, limit=10)
            event_ids = [e.event_id for e in events]
            assert event1.event_id in event_ids
            assert event2.event_id in event_ids

        @pytest.mark.asyncio
        async def test_search_events(self, engine, sample_event_data):
            """Test event search functionality"""
            # Log test events
            await engine.log_event(
                event_type=AuditEventType.USER_ACTION,
                description="User created investigation case",
                severity=AuditSeverity.INFO,
                user_id=sample_event_data["user_id"],
                details={"action": "case_created"}
            )

            await engine.log_event(
                event_type=AuditEventType.USER_ACTION,
                description="User updated evidence",
                severity=AuditSeverity.INFO,
                user_id=sample_event_data["user_id"],
                details={"action": "evidence_updated"}
            )

            # Search for "investigation"
            investigation_events = await engine.search_events("investigation", limit=10)
            assert len(investigation_events) == 1
            assert "investigation" in investigation_events[0].description

            # Search by details
            case_events = await engine.search_events("case_created", search_details=True, limit=10)
            assert len(case_events) == 1
            assert case_events[0].details["action"] == "case_created"

    class TestHashChaining:
        """Test hash chaining functionality"""

        @pytest.mark.asyncio
        async def test_hash_chain_integrity(self, engine, sample_event_data):
            """Test hash chain integrity"""
            # Log multiple events
            events = []
            for i in range(5):
                event = await engine.log_event(
                    event_type=AuditEventType.USER_ACTION,
                    description=f"Event {i}",
                    severity=AuditSeverity.INFO,
                    user_id=sample_event_data["user_id"],
                    details={"sequence": i}
                )
                events.append(event)

            # Verify hash chain
            for i in range(1, len(events)):
                current_event = events[i]
                previous_event = events[i-1]
                
                # Current event's previous_hash should match previous event's current_hash
                assert current_event.previous_hash == previous_event.current_hash

        @pytest.mark.asyncio
        async def test_verify_chain_integrity(self, engine, sample_event_data):
            """Test chain integrity verification"""
            # Log events
            events = []
            for i in range(3):
                event = await engine.log_event(
                    event_type=AuditEventType.USER_ACTION,
                    description=f"Event {i}",
                    severity=AuditSeverity.INFO,
                    user_id=sample_event_data["user_id"]
                )
                events.append(event)

            # Verify integrity
            integrity_result = await engine.verify_chain_integrity()
            assert integrity_result["valid"] is True
            assert integrity_result["verified_events"] == 3
            assert len(integrity_result["violations"]) == 0

        @pytest.mark.asyncio
        async def test_detect_tampering(self, engine, sample_event_data):
            """Test tampering detection"""
            # Log events
            events = []
            for i in range(3):
                event = await engine.log_event(
                    event_type=AuditEventType.USER_ACTION,
                    description=f"Event {i}",
                    severity=AuditSeverity.INFO,
                    user_id=sample_event_data["user_id"]
                )
                events.append(event)

            # Simulate tampering by modifying an event hash
            with patch.object(engine, '_calculate_event_hash') as mock_hash:
                mock_hash.return_value = "tampered_hash"
                
                # Update event with tampered hash
                await engine._update_event_hash(events[1].event_id, "tampered_hash")

            # Verify integrity should detect tampering
            integrity_result = await engine.verify_chain_integrity()
            assert integrity_result["valid"] is False
            assert len(integrity_result["violations"]) > 0

        @pytest.mark.asyncio
        async def test_hash_consistency(self, engine, sample_event_data):
            """Test hash calculation consistency"""
            # Log event
            event = await engine.log_event(
                event_type=AuditEventType.USER_ACTION,
                description="Test event",
                severity=AuditSeverity.INFO,
                user_id=sample_event_data["user_id"],
                details={"test": "data"}
            )

            # Calculate hash manually
            event_data = {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "description": event.description,
                "severity": event.severity.value,
                "user_id": event.user_id,
                "timestamp": event.timestamp.isoformat(),
                "details": event.details,
                "previous_hash": event.previous_hash
            }
            
            expected_hash = hashlib.sha256(
                json.dumps(event_data, sort_keys=True).encode()
            ).hexdigest()

            assert event.current_hash == expected_hash

    class TestComplianceLogging:
        """Test compliance logging functionality"""

        @pytest.mark.asyncio
        async def test_log_gdpr_compliance(self, engine, sample_compliance_log_data):
            """Test GDPR compliance logging"""
            compliance_log = await engine.log_compliance_event(
                category=ComplianceCategory.GDPR,
                action="data_access",
                description="Accessed personal data for investigation",
                user_id="compliance_officer",
                data_subject_id=sample_compliance_log_data["data_subject_id"],
                processing_purpose=sample_compliance_log_data["processing_purpose"],
                legal_basis=sample_compliance_log_data["legal_basis"],
                retention_period=sample_compliance_log_data["retention_period"],
                data_types=sample_compliance_log_data["data_types"],
                metadata={
                    "data_volume": "medium",
                    "cross_border": False
                }
            )

            assert compliance_log.log_id is not None
            assert compliance_log.category == ComplianceCategory.GDPR
            assert compliance_log.action == "data_access"
            assert compliance_log.data_subject_id == sample_compliance_log_data["data_subject_id"]
            assert compliance_log.processing_purpose == sample_compliance_log_data["processing_purpose"]
            assert compliance_log.legal_basis == sample_compliance_log_data["legal_basis"]
            assert compliance_log.retention_period == sample_compliance_log_data["retention_period"]
            assert compliance_log.data_types == sample_compliance_log_data["data_types"]

        @pytest.mark.asyncio
        async def test_log_aml_compliance(self, engine):
            """Test AML compliance logging"""
            compliance_log = await engine.log_compliance_event(
                category=ComplianceCategory.AML,
                action="sar_filing",
                description="Filed Suspicious Activity Report",
                user_id="compliance_analyst",
                report_id="SAR_2024_001",
                threshold_amount=10000.00,
                suspicious_activity_patterns=["structuring", "rapid_movement"],
                jurisdiction="USA",
                metadata={
                    "filing_deadline": "2024-01-20",
                    "regulator": "FINCEN"
                }
            )

            assert compliance_log.category == ComplianceCategory.AML
            assert compliance_log.action == "sar_filing"
            assert compliance_log.report_id == "SAR_2024_001"
            assert compliance_log.threshold_amount == 10000.00

        @pytest.mark.asyncio
        async def test_log_sox_compliance(self, engine):
            """Test SOX compliance logging"""
            compliance_log = await engine.log_compliance_event(
                category=ComplianceCategory.SOX,
                action="financial_control",
                description="Financial control verification",
                user_id="auditor",
                control_id="CTRL_001",
                control_type="preventive",
                test_result="passed",
                risk_level="low",
                metadata={
                    "test_date": "2024-01-15",
                    "next_review": "2024-04-15"
                }
            )

            assert compliance_log.category == ComplianceCategory.SOX
            assert compliance_log.action == "financial_control"
            assert compliance_log.control_id == "CTRL_001"
            assert compliance_log.test_result == "passed"

        @pytest.mark.asyncio
        async def test_get_compliance_logs_by_category(self, engine, sample_compliance_log_data):
            """Test getting compliance logs by category"""
            # Log different compliance events
            gdpr_log = await engine.log_compliance_event(
                category=ComplianceCategory.GDPR,
                action="data_processing",
                description="GDPR data processing",
                user_id="user_001",
                data_subject_id="subject_001"
            )

            aml_log = await engine.log_compliance_event(
                category=ComplianceCategory.AML,
                action="transaction_monitoring",
                description="AML transaction monitoring",
                user_id="user_002",
                threshold_amount=5000.00
            )

            # Get GDPR logs
            gdpr_logs = await engine.get_compliance_logs_by_category(ComplianceCategory.GDPR, limit=10)
            log_ids = [l.log_id for l in gdpr_logs]
            assert gdpr_log.log_id in log_ids
            assert aml_log.log_id not in log_ids

        @pytest.mark.asyncio
        async def test_get_compliance_logs_by_data_subject(self, engine, sample_compliance_log_data):
            """Test getting compliance logs by data subject"""
            # Log events for different data subjects
            log1 = await engine.log_compliance_event(
                category=ComplianceCategory.GDPR,
                action="data_access",
                description="Access subject 1 data",
                user_id="user_001",
                data_subject_id="subject_001"
            )

            log2 = await engine.log_compliance_event(
                category=ComplianceCategory.GDPR,
                action="data_access",
                description="Access subject 2 data",
                user_id="user_001",
                data_subject_id="subject_002"
            )

            # Get logs for subject_001
            subject1_logs = await engine.get_compliance_logs_by_data_subject("subject_001", limit=10)
            log_ids = [l.log_id for l in subject1_logs]
            assert log1.log_id in log_ids
            assert log2.log_id not in log_ids

    class TestAuditReportGeneration:
        """Test audit report generation functionality"""

        @pytest.mark.asyncio
        async def test_generate_audit_report(self, engine, sample_event_data):
            """Test generating audit report"""
            # Log test events
            await engine.log_event(
                event_type=AuditEventType.USER_ACTION,
                description="User action 1",
                severity=AuditSeverity.INFO,
                user_id=sample_event_data["user_id"]
            )

            await engine.log_event(
                event_type=AuditEventType.SECURITY_BREACH,
                description="Security event",
                severity=AuditSeverity.HIGH,
                user_id="system"
            )

            # Generate report
            start_date = datetime.utcnow() - timedelta(hours=1)
            end_date = datetime.utcnow()
            
            report = await engine.generate_audit_report(
                start_date=start_date,
                end_date=end_date,
                include_compliance_logs=True,
                include_integrity_check=True
            )

            assert report.report_id is not None
            assert report.start_date == start_date
            assert report.end_date == end_date
            assert len(report.audit_events) >= 2
            assert report.total_events >= 2
            assert report.integrity_check["valid"] is True
            assert report.generated_at is not None

        @pytest.mark.asyncio
        async def test_generate_compliance_report(self, engine, sample_compliance_log_data):
            """Test generating compliance report"""
            # Log compliance events
            await engine.log_compliance_event(
                category=ComplianceCategory.GDPR,
                action="data_access",
                description="GDPR data access",
                user_id="user_001",
                data_subject_id="subject_001"
            )

            await engine.log_compliance_event(
                category=ComplianceCategory.AML,
                action="sar_filing",
                description="AML SAR filing",
                user_id="user_002",
                report_id="SAR_001"
            )

            # Generate compliance report
            start_date = datetime.utcnow() - timedelta(hours=1)
            end_date = datetime.utcnow()
            
            report = await engine.generate_compliance_report(
                start_date=start_date,
                end_date=end_date,
                categories=[ComplianceCategory.GDPR, ComplianceCategory.AML]
            )

            assert report.report_id is not None
            assert len(report.compliance_logs) >= 2
            assert report.compliance_summary[ComplianceCategory.GDPR.value] >= 1
            assert report.compliance_summary[ComplianceCategory.AML.value] >= 1

        @pytest.mark.asyncio
        async def test_generate_summary_report(self, engine):
            """Test generating summary report"""
            # Log various events
            await engine.log_event(
                event_type=AuditEventType.USER_ACTION,
                description="User action",
                severity=AuditSeverity.INFO,
                user_id="user_001"
            )

            await engine.log_event(
                event_type=AuditEventType.SECURITY_BREACH,
                description="Security event",
                severity=AuditSeverity.HIGH,
                user_id="system"
            )

            await engine.log_event(
                event_type=AuditEventType.SYSTEM_ERROR,
                description="System error",
                severity=AuditSeverity.WARNING,
                user_id="system"
            )

            # Generate summary report
            start_date = datetime.utcnow() - timedelta(hours=1)
            end_date = datetime.utcnow()
            
            summary = await engine.generate_summary_report(start_date, end_date)

            assert "total_events" in summary
            assert "events_by_type" in summary
            assert "events_by_severity" in summary
            assert "events_by_user" in summary
            assert "compliance_summary" in summary
            assert summary["total_events"] >= 3

    class TestAuditTrailAnalytics:
        """Test audit trail analytics functionality"""

        @pytest.mark.asyncio
        async def test_get_audit_statistics(self, engine):
            """Test getting audit statistics"""
            # Log various events
            await engine.log_event(
                event_type=AuditEventType.USER_ACTION,
                description="User action",
                severity=AuditSeverity.INFO,
                user_id="user_001"
            )

            await engine.log_event(
                event_type=AuditEventType.SECURITY_BREACH,
                description="Security event",
                severity=AuditSeverity.HIGH,
                user_id="system"
            )

            # Get statistics
            stats = await engine.get_audit_statistics()
            
            assert "total_events" in stats
            assert "events_by_type" in stats
            assert "events_by_severity" in stats
            assert "events_by_user" in stats
            assert "recent_activity" in stats
            assert "chain_integrity" in stats
            
            assert stats["total_events"] >= 2
            assert stats["chain_integrity"]["valid"] is True

        @pytest.mark.asyncio
        async def test_get_compliance_statistics(self, engine, sample_compliance_log_data):
            """Test getting compliance statistics"""
            # Log compliance events
            await engine.log_compliance_event(
                category=ComplianceCategory.GDPR,
                action="data_access",
                description="GDPR access",
                user_id="user_001",
                data_subject_id="subject_001"
            )

            await engine.log_compliance_event(
                category=ComplianceCategory.AML,
                action="sar_filing",
                description="AML filing",
                user_id="user_002",
                report_id="SAR_001"
            )

            # Get compliance statistics
            stats = await engine.get_compliance_statistics()
            
            assert "total_compliance_events" in stats
            assert "events_by_category" in stats
            assert "events_by_action" in stats
            assert "data_subjects_count" in stats
            assert "retention_compliance" in stats
            
            assert stats["total_compliance_events"] >= 2
            assert stats["events_by_category"][ComplianceCategory.GDPR.value] >= 1
            assert stats["events_by_category"][ComplianceCategory.AML.value] >= 1

        @pytest.mark.asyncio
        async def test_detect_anomalies(self, engine):
            """Test anomaly detection in audit logs"""
            # Log normal events
            for i in range(10):
                await engine.log_event(
                    event_type=AuditEventType.USER_ACTION,
                    description=f"Normal action {i}",
                    severity=AuditSeverity.INFO,
                    user_id="user_001"
                )

            # Log anomalous event (high severity security event)
            await engine.log_event(
                event_type=AuditEventType.SECURITY_BREACH,
                description="Critical security breach",
                severity=AuditSeverity.CRITICAL,
                user_id="unknown_user",
                details={"anomaly_indicators": ["unknown_user", "critical_severity"]}
            )

            # Detect anomalies
            anomalies = await engine.detect_audit_anomalies(
                lookback_hours=1,
                severity_threshold=AuditSeverity.HIGH
            )

            assert len(anomalies) >= 1
            assert any("critical_security_breach" in anomaly["description"] for anomaly in anomalies)

    class TestDataRetention:
        """Test data retention functionality"""

        @pytest.mark.asyncio
        async def test_retention_policy_enforcement(self, engine):
            """Test retention policy enforcement"""
            # Create old event (mocked timestamp)
            old_timestamp = datetime.utcnow() - timedelta(days=4000)  # > 7 years
            
            with patch('src.compliance.audit_trail.datetime') as mock_datetime:
                mock_datetime.utcnow.return_value = old_timestamp
                
                old_event = await engine.log_event(
                    event_type=AuditEventType.USER_ACTION,
                    description="Old event",
                    severity=AuditSeverity.INFO,
                    user_id="user_001"
                )

            # Create recent event
            recent_event = await engine.log_event(
                event_type=AuditEventType.USER_ACTION,
                description="Recent event",
                severity=AuditSeverity.INFO,
                user_id="user_001"
            )

            # Check retention status
            retention_status = await engine.check_retention_status()
            assert retention_status["events_past_retention"] >= 1
            assert retention_status["total_events"] >= 2

        @pytest.mark.asyncio
        async def test_data_deletion(self, engine):
            """Test secure data deletion"""
            # Create old event
            old_timestamp = datetime.utcnow() - timedelta(days=4000)
            
            with patch('src.compliance.audit_trail.datetime') as mock_datetime:
                mock_datetime.utcnow.return_value = old_timestamp
                
                old_event = await engine.log_event(
                    event_type=AuditEventType.USER_ACTION,
                    description="Event to delete",
                    severity=AuditSeverity.INFO,
                    user_id="user_001"
                )

            # Delete expired events
            deletion_result = await engine.delete_expired_events()
            
            assert deletion_result["deleted_events"] >= 1
            assert deletion_result["deletion_completed"] is True

            # Verify event is deleted
            deleted_event = await engine.get_event(old_event.event_id)
            assert deleted_event is None

    class TestErrorHandling:
        """Test error handling scenarios"""

        @pytest.mark.asyncio
        async def test_database_connection_error(self, engine):
            """Test handling of database connection errors"""
            with patch.object(engine, 'neo4j_session', None):
                with pytest.raises(Exception):
                    await engine.log_event(
                        event_type=AuditEventType.USER_ACTION,
                        description="Test event",
                        severity=AuditSeverity.INFO,
                        user_id="user_001"
                    )

        @pytest.mark.asyncio
        async def test_hash_calculation_error(self, engine, sample_event_data):
            """Test handling of hash calculation errors"""
            with patch('hashlib.sha256', side_effect=Exception("Hash calculation failed")):
                with pytest.raises(Exception):
                    await engine.log_event(
                        event_type=AuditEventType.USER_ACTION,
                        description="Test event",
                        severity=AuditSeverity.INFO,
                        user_id=sample_event_data["user_id"]
                    )

        @pytest.mark.asyncio
        async def test_invalid_compliance_category(self, engine):
            """Test handling of invalid compliance category"""
            with pytest.raises(ValueError):
                await engine.log_compliance_event(
                    category="INVALID_CATEGORY",
                    action="test_action",
                    description="Test compliance event",
                    user_id="user_001"
                )

    class TestPerformance:
        """Test performance characteristics"""

        @pytest.mark.asyncio
        async def test_bulk_event_logging(self, engine, sample_event_data):
            """Test bulk event logging performance"""
            import time
            
            start_time = time.time()
            
            # Log 50 events concurrently
            tasks = []
            for i in range(50):
                task = engine.log_event(
                    event_type=AuditEventType.USER_ACTION,
                    description=f"Bulk event {i}",
                    severity=AuditSeverity.INFO,
                    user_id=sample_event_data["user_id"],
                    details={"bulk_index": i}
                )
                tasks.append(task)
            
            events = await asyncio.gather(*tasks)
            
            end_time = time.time()
            duration = end_time - start_time
            
            assert len(events) == 50
            assert duration < 10.0  # Should complete within 10 seconds
            assert all(e.event_id is not None for e in events)

        @pytest.mark.asyncio
        async def test_chain_verification_performance(self, engine, sample_event_data):
            """Test chain verification performance"""
            import time
            
            # Create chain of 100 events
            events = []
            for i in range(100):
                event = await engine.log_event(
                    event_type=AuditEventType.USER_ACTION,
                    description=f"Chain event {i}",
                    severity=AuditSeverity.INFO,
                    user_id=sample_event_data["user_id"]
                )
                events.append(event)
            
            # Test verification performance
            start_time = time.time()
            
            integrity_result = await engine.verify_chain_integrity()
            
            end_time = time.time()
            duration = end_time - start_time
            
            assert integrity_result["valid"] is True
            assert integrity_result["verified_events"] == 100
            assert duration < 5.0  # Should complete within 5 seconds

        @pytest.mark.asyncio
        async def test_report_generation_performance(self, engine, sample_event_data):
            """Test report generation performance"""
            import time
            
            # Log test events
            for i in range(20):
                await engine.log_event(
                    event_type=AuditEventType.USER_ACTION,
                    description=f"Report test event {i}",
                    severity=AuditSeverity.INFO,
                    user_id=sample_event_data["user_id"]
                )
            
            # Test report generation performance
            start_time = time.time()
            
            start_date = datetime.utcnow() - timedelta(hours=1)
            end_date = datetime.utcnow()
            
            report = await engine.generate_audit_report(
                start_date=start_date,
                end_date=end_date,
                include_compliance_logs=True,
                include_integrity_check=True
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            assert len(report.audit_events) >= 20
            assert duration < 3.0  # Should complete within 3 seconds
