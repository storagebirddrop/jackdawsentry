"""
Compliance API Integration Tests

Comprehensive test suite for compliance API endpoints including:
- Regulatory reporting endpoints
- Case management endpoints
- Risk assessment endpoints
- Audit trail endpoints
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from typing import Dict, Any, List

from src.api.routers.compliance import router
from src.api.auth import User, check_permissions, PERMISSIONS
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


class TestComplianceAPIIntegration:
    """Test suite for compliance API integration"""

    @pytest.fixture
    def app(self):
        """Create FastAPI app for testing"""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/compliance")
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_user(self):
        """Create mock user for authentication"""
        return User(
            id=1,
            username="test_user",
            email="test@example.com",
            permissions=[PERMISSIONS["read_compliance"], PERMISSIONS["write_compliance"]]
        )

    @pytest.fixture
    def mock_admin_user(self):
        """Create mock admin user"""
        return User(
            id=2,
            username="admin_user",
            email="admin@example.com",
            permissions=[PERMISSIONS["read_compliance"], PERMISSIONS["write_compliance"], PERMISSIONS["admin"]]
        )

    class TestRegulatoryReportingEndpoints:
        """Test regulatory reporting API endpoints"""

        @pytest.mark.asyncio
        async def test_create_regulatory_report(self, client, mock_user):
            """Test POST /api/v1/compliance/regulatory/reports"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.regulatory_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.regulatory_engine, 'create_report', new_callable=AsyncMock) as mock_create:
                        # Mock report creation
                        mock_report = MagicMock()
                        mock_report.report_id = "report_001"
                        mock_report.jurisdiction.value = "usa_finCEN"
                        mock_report.report_type.value = "sar"
                        mock_report.status.value = "draft"
                        mock_report.created_at = datetime.utcnow()
                        mock_create.return_value = mock_report

                        response = client.post(
                            "/api/v1/compliance/regulatory/reports",
                            params={
                                "jurisdiction": "usa",
                                "report_type": "sar",
                                "entity_id": "entity_001"
                            }
                        )

                        assert response.status_code == 200
                        data = response.json()
                        assert data["success"] is True
                        assert data["report"]["report_id"] == "report_001"
                        assert data["report"]["jurisdiction"] == "usa_finCEN"
                        assert data["report"]["report_type"] == "sar"

        @pytest.mark.asyncio
        async def test_get_regulatory_report(self, client, mock_user):
            """Test GET /api/v1/compliance/regulatory/reports/{report_id}"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.regulatory_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.regulatory_engine, 'get_report', new_callable=AsyncMock) as mock_get:
                        # Mock report retrieval
                        mock_report = MagicMock()
                        mock_report.report_id = "report_001"
                        mock_report.jurisdiction.value = "usa_finCEN"
                        mock_report.report_type.value = "sar"
                        mock_report.status.value = "submitted"
                        mock_report.entity_id = "entity_001"
                        mock_report.content = {"test": "data"}
                        mock_report.submitted_at = datetime.utcnow()
                        mock_report.created_at = datetime.utcnow()
                        mock_get.return_value = mock_report

                        response = client.get("/api/v1/compliance/regulatory/reports/report_001")

                        assert response.status_code == 200
                        data = response.json()
                        assert data["success"] is True
                        assert data["report"]["report_id"] == "report_001"
                        assert data["report"]["entity_id"] == "entity_001"

        @pytest.mark.asyncio
        async def test_get_nonexistent_regulatory_report(self, client, mock_user):
            """Test GET nonexistent regulatory report"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.regulatory_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.regulatory_engine, 'get_report', new_callable=AsyncMock) as mock_get:
                        mock_get.return_value = None

                        response = client.get("/api/v1/compliance/regulatory/reports/nonexistent")

                        assert response.status_code == 404

        @pytest.mark.asyncio
        async def test_create_regulatory_report_invalid_jurisdiction(self, client, mock_user):
            """Test creating report with invalid jurisdiction"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                response = client.post(
                    "/api/v1/compliance/regulatory/reports",
                    params={
                        "jurisdiction": "invalid",
                        "report_type": "sar",
                        "entity_id": "entity_001"
                    }
                )

                assert response.status_code == 422  # Validation error

    class TestCaseManagementEndpoints:
        """Test case management API endpoints"""

        @pytest.mark.asyncio
        async def test_create_case(self, client, mock_user):
            """Test POST /api/v1/compliance/cases"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.case_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.case_engine, 'create_case', new_callable=AsyncMock) as mock_create:
                        # Mock case creation
                        mock_case = MagicMock()
                        mock_case.case_id = "case_001"
                        mock_case.title = "Test Case"
                        mock_case.case_type = "suspicious_activity"
                        mock_case.priority.value = "high"
                        mock_case.status.value = "open"
                        mock_case.assigned_to = "investigator"
                        mock_case.created_at = datetime.utcnow()
                        mock_create.return_value = mock_case

                        response = client.post(
                            "/api/v1/compliance/cases",
                            params={
                                "title": "Test Case",
                                "description": "Test description",
                                "case_type": "suspicious_activity",
                                "priority": "high",
                                "assigned_to": "investigator"
                            }
                        )

                        assert response.status_code == 200
                        data = response.json()
                        assert data["success"] is True
                        assert data["case"]["case_id"] == "case_001"
                        assert data["case"]["title"] == "Test Case"
                        assert data["case"]["priority"] == "high"

        @pytest.mark.asyncio
        async def test_get_case(self, client, mock_user):
            """Test GET /api/v1/compliance/cases/{case_id}"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.case_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.case_engine, 'get_case', new_callable=AsyncMock) as mock_get:
                        # Mock case retrieval
                        mock_case = MagicMock()
                        mock_case.case_id = "case_001"
                        mock_case.title = "Test Case"
                        mock_case.description = "Test description"
                        mock_case.case_type = "suspicious_activity"
                        mock_case.priority.value = "high"
                        mock_case.status.value = "open"
                        mock_case.assigned_to = "investigator"
                        mock_case.created_by = "system"
                        mock_case.created_at = datetime.utcnow()
                        mock_case.updated_at = datetime.utcnow()
                        mock_get.return_value = mock_case

                        response = client.get("/api/v1/compliance/cases/case_001")

                        assert response.status_code == 200
                        data = response.json()
                        assert data["success"] is True
                        assert data["case"]["case_id"] == "case_001"
                        assert data["case"]["description"] == "Test description"

        @pytest.mark.asyncio
        async def test_get_nonexistent_case(self, client, mock_user):
            """Test GET nonexistent case"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.case_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.case_engine, 'get_case', new_callable=AsyncMock) as mock_get:
                        mock_get.return_value = None

                        response = client.get("/api/v1/compliance/cases/nonexistent")

                        assert response.status_code == 404

        @pytest.mark.asyncio
        async def test_add_evidence_to_case(self, client, mock_user):
            """Test POST /api/v1/compliance/cases/{case_id}/evidence"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.case_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.case_engine, 'add_evidence', new_callable=AsyncMock) as mock_add:
                        # Mock evidence addition
                        mock_evidence = MagicMock()
                        mock_evidence.evidence_id = "evidence_001"
                        mock_evidence.case_id = "case_001"
                        mock_evidence.evidence_type = "transaction_data"
                        mock_evidence.description = "Test evidence"
                        mock_evidence.status.value = "pending_review"
                        mock_evidence.collected_by = "investigator"
                        mock_evidence.collected_at = datetime.utcnow()
                        mock_add.return_value = mock_evidence

                        evidence_content = {
                            "transaction_hash": "0x1234567890abcdef",
                            "amount": 1000.00,
                            "timestamp": "2024-01-15T10:30:00Z"
                        }

                        response = client.post(
                            "/api/v1/compliance/cases/case_001/evidence",
                            params={
                                "evidence_type": "transaction_data",
                                "description": "Test evidence"
                            },
                            json=evidence_content
                        )

                        assert response.status_code == 200
                        data = response.json()
                        assert data["success"] is True
                        assert data["evidence"]["evidence_id"] == "evidence_001"
                        assert data["evidence"]["evidence_type"] == "transaction_data"

    class TestRiskAssessmentEndpoints:
        """Test risk assessment API endpoints"""

        @pytest.mark.asyncio
        async def test_create_risk_assessment(self, client, mock_user):
            """Test POST /api/v1/compliance/risk/assessments"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.risk_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.risk_engine, 'create_risk_assessment', new_callable=AsyncMock) as mock_create:
                        # Mock assessment creation
                        mock_assessment = MagicMock()
                        mock_assessment.assessment_id = "assessment_001"
                        mock_assessment.entity_id = "entity_001"
                        mock_assessment.entity_type = "address"
                        mock_assessment.overall_score = 0.75
                        mock_assessment.risk_level.value = "high"
                        mock_assessment.status.value = "completed"
                        mock_assessment.trigger_type.value = "automatic"
                        mock_assessment.confidence = 0.85
                        mock_assessment.recommendations = ["Immediate review required"]
                        mock_assessment.created_at = datetime.utcnow()
                        mock_create.return_value = mock_assessment

                        response = client.post(
                            "/api/v1/compliance/risk/assessments",
                            params={
                                "entity_id": "entity_001",
                                "entity_type": "address",
                                "trigger_type": "automatic"
                            }
                        )

                        assert response.status_code == 200
                        data = response.json()
                        assert data["success"] is True
                        assert data["assessment"]["assessment_id"] == "assessment_001"
                        assert data["assessment"]["entity_id"] == "entity_001"
                        assert data["assessment"]["risk_level"] == "high"
                        assert data["assessment"]["overall_score"] == 0.75

        @pytest.mark.asyncio
        async def test_get_risk_assessment(self, client, mock_user):
            """Test GET /api/v1/compliance/risk/assessments/{assessment_id}"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.risk_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.risk_engine, 'get_risk_assessment', new_callable=AsyncMock) as mock_get:
                        # Mock assessment retrieval
                        mock_assessment = MagicMock()
                        mock_assessment.assessment_id = "assessment_001"
                        mock_assessment.entity_id = "entity_001"
                        mock_assessment.entity_type = "address"
                        mock_assessment.overall_score = 0.75
                        mock_assessment.risk_level.value = "high"
                        mock_assessment.status.value = "completed"
                        mock_assessment.trigger_type.value = "automatic"
                        mock_assessment.confidence = 0.85
                        mock_assessment.recommendations = ["Immediate review required"]
                        mock_assessment.created_at = datetime.utcnow()

                        # Mock risk factors
                        mock_factor1 = MagicMock()
                        mock_factor1.category.value = "transaction_volume"
                        mock_factor1.weight = 0.25
                        mock_factor1.score = 0.8
                        mock_factor1.description = "High transaction volume"

                        mock_factor2 = MagicMock()
                        mock_factor2.category.value = "address_risk"
                        mock_factor2.weight = 0.20
                        mock_factor2.score = 0.7
                        mock_factor2.description = "Address risk detected"

                        mock_assessment.risk_factors = [mock_factor1, mock_factor2]
                        mock_get.return_value = mock_assessment

                        response = client.get("/api/v1/compliance/risk/assessments/assessment_001")

                        assert response.status_code == 200
                        data = response.json()
                        assert data["success"] is True
                        assert data["assessment"]["assessment_id"] == "assessment_001"
                        assert len(data["assessment"]["risk_factors"]) == 2
                        assert data["assessment"]["risk_factors"][0]["category"] == "transaction_volume"

        @pytest.mark.asyncio
        async def test_get_nonexistent_risk_assessment(self, client, mock_user):
            """Test GET nonexistent risk assessment"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.risk_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.risk_engine, 'get_risk_assessment', new_callable=AsyncMock) as mock_get:
                        mock_get.return_value = None

                        response = client.get("/api/v1/compliance/risk/assessments/nonexistent")

                        assert response.status_code == 404

        @pytest.mark.asyncio
        async def test_get_risk_summary(self, client, mock_user):
            """Test GET /api/v1/compliance/risk/summary"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.risk_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.risk_engine, 'get_risk_summary', new_callable=AsyncMock) as mock_summary:
                        # Mock summary data
                        mock_summary.return_value = {
                            "total_assessments": 50,
                            "risk_level_distribution": {
                                "low": 20,
                                "medium": 15,
                                "high": 10,
                                "critical": 4,
                                "severe": 1
                            },
                            "average_score": 0.45,
                            "max_score": 0.95,
                            "min_score": 0.1,
                            "period": {
                                "start_date": None,
                                "end_date": None
                            }
                        }

                        response = client.get("/api/v1/compliance/risk/summary")

                        assert response.status_code == 200
                        data = response.json()
                        assert data["success"] is True
                        assert data["summary"]["total_assessments"] == 50
                        assert data["summary"]["risk_level_distribution"]["high"] == 10
                        assert data["summary"]["average_score"] == 0.45

        @pytest.mark.asyncio
        async def test_get_risk_summary_with_date_filter(self, client, mock_user):
            """Test GET risk summary with date filter"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.risk_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.risk_engine, 'get_risk_summary', new_callable=AsyncMock) as mock_summary:
                        start_date = "2024-01-01T00:00:00"
                        end_date = "2024-01-31T23:59:59"

                        mock_summary.return_value = {
                            "total_assessments": 25,
                            "risk_level_distribution": {"low": 10, "medium": 8, "high": 5, "critical": 2, "severe": 0},
                            "average_score": 0.4,
                            "max_score": 0.8,
                            "min_score": 0.15,
                            "period": {
                                "start_date": start_date,
                                "end_date": end_date
                            }
                        }

                        response = client.get(
                            "/api/v1/compliance/risk/summary",
                            params={
                                "start_date": start_date,
                                "end_date": end_date
                            }
                        )

                        assert response.status_code == 200
                        data = response.json()
                        assert data["summary"]["total_assessments"] == 25
                        assert data["summary"]["period"]["start_date"] == start_date

    class TestAuditTrailEndpoints:
        """Test audit trail API endpoints"""

        @pytest.mark.asyncio
        async def test_log_audit_event(self, client, mock_user):
            """Test POST /api/v1/compliance/audit/log"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.audit_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.audit_engine, 'log_event', new_callable=AsyncMock) as mock_log:
                        # Mock event logging
                        mock_event = MagicMock()
                        mock_event.event_id = "event_001"
                        mock_event.event_type = "user_action"
                        mock_event.description = "Test audit event"
                        mock_event.severity = "medium"
                        mock_event.user_id = "test_user"
                        mock_event.timestamp = datetime.utcnow()
                        mock_log.return_value = mock_event

                        response = client.post(
                            "/api/v1/compliance/audit/log",
                            params={
                                "event_type": "user_action",
                                "description": "Test audit event",
                                "severity": "medium"
                            }
                        )

                        assert response.status_code == 200
                        data = response.json()
                        assert data["success"] is True
                        assert data["event"]["event_id"] == "event_001"
                        assert data["event"]["event_type"] == "user_action"
                        assert data["event"]["description"] == "Test audit event"

        @pytest.mark.asyncio
        async def test_log_audit_event_with_metadata(self, client, mock_user):
            """Test POST audit event with metadata"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.audit_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.audit_engine, 'log_event', new_callable=AsyncMock) as mock_log:
                        mock_event = MagicMock()
                        mock_event.event_id = "event_002"
                        mock_event.event_type = "compliance_check"
                        mock_event.description = "Compliance verification"
                        mock_event.severity = "high"
                        mock_event.user_id = "test_user"
                        mock_event.timestamp = datetime.utcnow()
                        mock_log.return_value = mock_event

                        metadata = {
                            "compliance_framework": "GDPR",
                            "verification_status": "passed",
                            "data_types": ["personal_data"]
                        }

                        response = client.post(
                            "/api/v1/compliance/audit/log",
                            params={
                                "event_type": "compliance_check",
                                "description": "Compliance verification",
                                "severity": "high"
                            },
                            json=metadata
                        )

                        assert response.status_code == 200
                        data = response.json()
                        assert data["success"] is True
                        assert data["event"]["severity"] == "high"

        @pytest.mark.asyncio
        async def test_get_audit_events(self, client, mock_user):
            """Test GET /api/v1/compliance/audit/events"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.audit_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.audit_engine, 'get_events', new_callable=AsyncMock) as mock_get:
                        # Mock events retrieval
                        mock_event1 = MagicMock()
                        mock_event1.event_id = "event_001"
                        mock_event1.event_type = "user_action"
                        mock_event1.description = "User action 1"
                        mock_event1.severity = "info"
                        mock_event1.user_id = "user_001"
                        mock_event1.timestamp = datetime.utcnow()

                        mock_event2 = MagicMock()
                        mock_event2.event_id = "event_002"
                        mock_event2.event_type = "security_breach"
                        mock_event2.description = "Security event"
                        mock_event2.severity = "high"
                        mock_event2.user_id = "system"
                        mock_event2.timestamp = datetime.utcnow()

                        mock_get.return_value = [mock_event1, mock_event2]

                        response = client.get("/api/v1/compliance/audit/events")

                        assert response.status_code == 200
                        data = response.json()
                        assert data["success"] is True
                        assert len(data["events"]) == 2
                        assert data["total_count"] == 2
                        assert data["events"][0]["event_type"] == "user_action"
                        assert data["events"][1]["event_type"] == "security_breach"

        @pytest.mark.asyncio
        async def test_get_audit_events_with_filters(self, client, mock_user):
            """Test GET audit events with filters"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.audit_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.audit_engine, 'get_events', new_callable=AsyncMock) as mock_get:
                        mock_event = MagicMock()
                        mock_event.event_id = "event_001"
                        mock_event.event_type = "user_action"
                        mock_event.description = "Filtered event"
                        mock_event.severity = "medium"
                        mock_event.user_id = "user_001"
                        mock_event.timestamp = datetime.utcnow()
                        mock_get.return_value = [mock_event]

                        response = client.get(
                            "/api/v1/compliance/audit/events",
                            params={
                                "event_type": "user_action",
                                "user_id": "user_001",
                                "limit": 10
                            }
                        )

                        assert response.status_code == 200
                        data = response.json()
                        assert len(data["events"]) == 1
                        assert data["events"][0]["event_type"] == "user_action"
                        assert data["events"][0]["user_id"] == "user_001"

    class TestAuthenticationAndAuthorization:
        """Test authentication and authorization"""

        @pytest.mark.asyncio
        async def test_unauthorized_access(self, client):
            """Test unauthorized access to compliance endpoints"""
            # Mock check_permissions to raise exception
            with patch('src.api.routers.compliance.check_permissions') as mock_check:
                mock_check.side_effect = Exception("Unauthorized")

                response = client.post(
                    "/api/v1/compliance/cases",
                    params={
                        "title": "Test Case",
                        "description": "Test description",
                        "case_type": "suspicious_activity",
                        "priority": "high"
                    }
                )

                assert response.status_code == 500  # Internal server error for auth issues

        @pytest.mark.asyncio
        async def test_insufficient_permissions(self, client):
            """Test access with insufficient permissions"""
            # Create user with only read permissions
            read_only_user = User(
                id=3,
                username="read_only_user",
                email="readonly@example.com",
                permissions=[PERMISSIONS["read_compliance"]]  # No write permissions
            )

            with patch('src.api.routers.compliance.check_permissions', return_value=read_only_user):
                response = client.post(
                    "/api/v1/compliance/cases",
                    params={
                        "title": "Test Case",
                        "description": "Test description",
                        "case_type": "suspicious_activity",
                        "priority": "high"
                    }
                )

                # Should fail due to insufficient permissions
                assert response.status_code == 500

    class TestErrorHandling:
        """Test API error handling"""

        @pytest.mark.asyncio
        async def test_database_error_handling(self, client, mock_user):
            """Test handling of database errors"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.case_engine, 'initialize', new_callable=AsyncMock) as mock_init:
                    # Mock database connection error
                    mock_init.side_effect = Exception("Database connection failed")

                    response = client.post(
                        "/api/v1/compliance/cases",
                        params={
                            "title": "Test Case",
                            "description": "Test description",
                            "case_type": "suspicious_activity",
                            "priority": "high"
                        }
                    )

                    assert response.status_code == 500

        @pytest.mark.asyncio
        async def test_validation_error_handling(self, client, mock_user):
            """Test handling of validation errors"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                # Send invalid data
                response = client.post(
                    "/api/v1/compliance/cases",
                    params={
                        "title": "",  # Empty title should fail validation
                        "description": "Test description",
                        "case_type": "invalid_type",  # Invalid case type
                        "priority": "high"
                    }
                )

                # Should return validation error
                assert response.status_code in [422, 400]

        @pytest.mark.asyncio
        async def test_timeout_error_handling(self, client, mock_user):
            """Test handling of timeout errors"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.case_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.case_engine, 'create_case', new_callable=AsyncMock) as mock_create:
                        # Mock timeout
                        mock_create.side_effect = asyncio.TimeoutError("Operation timed out")

                        response = client.post(
                            "/api/v1/compliance/cases",
                            params={
                                "title": "Test Case",
                                "description": "Test description",
                                "case_type": "suspicious_activity",
                                "priority": "high"
                            }
                        )

                        assert response.status_code == 500

    class TestAPIPerformance:
        """Test API performance characteristics"""

        @pytest.mark.asyncio
        async def test_bulk_case_creation_performance(self, client, mock_user):
            """Test bulk case creation performance"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.case_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.case_engine, 'create_case', new_callable=AsyncMock) as mock_create:
                        # Mock fast case creation
                        mock_case = MagicMock()
                        mock_case.case_id = "case_001"
                        mock_case.title = "Test Case"
                        mock_case.case_type = "suspicious_activity"
                        mock_case.priority.value = "medium"
                        mock_case.status.value = "open"
                        mock_case.assigned_to = "investigator"
                        mock_case.created_at = datetime.utcnow()
                        mock_create.return_value = mock_case

                        import time
                        start_time = time.time()

                        # Create multiple cases
                        responses = []
                        for i in range(10):
                            response = client.post(
                                "/api/v1/compliance/cases",
                                params={
                                    "title": f"Test Case {i}",
                                    "description": f"Test description {i}",
                                    "case_type": "suspicious_activity",
                                    "priority": "medium"
                                }
                            )
                            responses.append(response)

                        end_time = time.time()
                        duration = end_time - start_time

                        # All requests should succeed
                        assert all(r.status_code == 200 for r in responses)
                        # Should complete within reasonable time
                        assert duration < 5.0

        @pytest.mark.asyncio
        async def test_large_payload_handling(self, client, mock_user):
            """Test handling of large payloads"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.case_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.case_engine, 'add_evidence', new_callable=AsyncMock) as mock_add:
                        # Mock evidence addition
                        mock_evidence = MagicMock()
                        mock_evidence.evidence_id = "evidence_001"
                        mock_evidence.case_id = "case_001"
                        mock_evidence.evidence_type = "document"
                        mock_evidence.description = "Large evidence"
                        mock_evidence.status.value = "pending_review"
                        mock_evidence.collected_by = "investigator"
                        mock_evidence.collected_at = datetime.utcnow()
                        mock_add.return_value = mock_evidence

                        # Create large evidence content
                        large_content = {
                            "data": "x" * 10000,  # 10KB of data
                            "metadata": {
                                "large_list": list(range(1000)),
                                "nested_dict": {
                                    "deep": {
                                        "nested": {
                                            "value": "test" * 100
                                        }
                                    }
                                }
                            }
                        }

                        response = client.post(
                            "/api/v1/compliance/cases/case_001/evidence",
                            params={
                                "evidence_type": "document",
                                "description": "Large evidence"
                            },
                            json=large_content
                        )

                        assert response.status_code == 200

    class TestAPIResponseFormat:
        """Test API response format consistency"""

        @pytest.mark.asyncio
        async def test_success_response_format(self, client, mock_user):
            """Test consistent success response format"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.case_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.case_engine, 'create_case', new_callable=AsyncMock) as mock_create:
                        mock_case = MagicMock()
                        mock_case.case_id = "case_001"
                        mock_case.title = "Test Case"
                        mock_case.case_type = "suspicious_activity"
                        mock_case.priority.value = "medium"
                        mock_case.status.value = "open"
                        mock_case.assigned_to = "investigator"
                        mock_case.created_at = datetime.utcnow()
                        mock_create.return_value = mock_case

                        response = client.post(
                            "/api/v1/compliance/cases",
                            params={
                                "title": "Test Case",
                                "description": "Test description",
                                "case_type": "suspicious_activity",
                                "priority": "medium"
                            }
                        )

                        assert response.status_code == 200
                        data = response.json()
                        
                        # Check response structure
                        assert "success" in data
                        assert "case" in data
                        assert "timestamp" in data
                        assert data["success"] is True
                        assert isinstance(data["timestamp"], str)

        @pytest.mark.asyncio
        async def test_error_response_format(self, client, mock_user):
            """Test consistent error response format"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.case_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.case_engine, 'create_case', new_callable=AsyncMock) as mock_create:
                        # Mock case creation error
                        mock_create.side_effect = ValueError("Invalid case data")

                        response = client.post(
                            "/api/v1/compliance/cases",
                            params={
                                "title": "Test Case",
                                "description": "Test description",
                                "case_type": "suspicious_activity",
                                "priority": "medium"
                            }
                        )

                        assert response.status_code == 500
                        data = response.json()
                        
                        # Check error response structure
                        assert "detail" in data
                        assert isinstance(data["detail"], str)

    class TestAPIPagination:
        """Test API pagination functionality"""

        @pytest.mark.asyncio
        async def test_events_pagination(self, client, mock_user):
            """Test audit events pagination"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.audit_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.audit_engine, 'get_events', new_callable=AsyncMock) as mock_get:
                        # Mock paginated events
                        events = []
                        for i in range(50):
                            mock_event = MagicMock()
                            mock_event.event_id = f"event_{i:03d}"
                            mock_event.event_type = "user_action"
                            mock_event.description = f"Event {i}"
                            mock_event.severity = "info"
                            mock_event.user_id = "user_001"
                            mock_event.timestamp = datetime.utcnow()
                            events.append(mock_event)
                        
                        mock_get.return_value = events[:20]  # Return first 20

                        response = client.get(
                            "/api/v1/compliance/audit/events",
                            params={"limit": 20}
                        )

                        assert response.status_code == 200
                        data = response.json()
                        assert len(data["events"]) == 20
                        assert data["total_count"] == 20

        @pytest.mark.asyncio
        async def test_pagination_parameters(self, client, mock_user):
            """Test pagination parameter validation"""
            with patch('src.api.routers.compliance.check_permissions', return_value=mock_user):
                with patch.object(router.audit_engine, 'initialize', new_callable=AsyncMock):
                    with patch.object(router.audit_engine, 'get_events', new_callable=AsyncMock) as mock_get:
                        mock_get.return_value = []

                        # Test invalid limit
                        response = client.get(
                            "/api/v1/compliance/audit/events",
                            params={"limit": -1}  # Invalid negative limit
                        )

                        # Should handle invalid parameter
                        assert response.status_code in [422, 400]
