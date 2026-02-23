"""
Forensics API Router Tests

This module contains comprehensive tests for the forensics API router,
covering case management, evidence handling, report generation, and
court-defensible evidence workflows.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from fastapi import status
from fastapi.testclient import TestClient
from uuid import uuid4

from src.forensics.forensic_engine import (
    ForensicEngine,
    ForensicCase,
    CaseStatus,
    CasePriority,
    CaseStatistics
)
from src.forensics.evidence_manager import (
    EvidenceManager,
    Evidence,
    EvidenceType,
    EvidenceStatus,
    ChainOfCustody,
    EvidenceStatistics
)
from src.forensics.report_generator import (
    ReportGenerator,
    ForensicReport,
    ReportType,
    ReportStatus,
    ReportStatistics
)
from src.forensics.court_defensible import (
    CourtDefensibleEvidence,
    LegalCompliance,
    FoundationRequirements,
    TestimonyPreparation,
    ExhibitPreparation
)


class TestForensicsAPI:
    """Test suite for forensics API endpoints"""

    @pytest.fixture
    def client(self, test_app: TestClient):
        """Test client fixture"""
        return test_app

    @pytest.fixture
    def mock_forensic_engine(self):
        """Mock forensic engine fixture"""
        engine = AsyncMock(spec=ForensicEngine)
        return engine

    @pytest.fixture
    def mock_evidence_manager(self):
        """Mock evidence manager fixture"""
        manager = AsyncMock(spec=EvidenceManager)
        return manager

    @pytest.fixture
    def mock_report_generator(self):
        """Mock report generator fixture"""
        generator = AsyncMock(spec=ReportGenerator)
        return generator

    @pytest.fixture
    def mock_court_defensible(self):
        """Mock court defensible evidence fixture"""
        court = AsyncMock(spec=CourtDefensibleEvidence)
        return court

    @pytest.fixture
    def auth_headers(self):
        """Authentication headers fixture"""
        return {"Authorization": "Bearer test_token"}

    @pytest.fixture
    def sample_case(self):
        """Sample forensic case fixture"""
        return ForensicCase(
            id=uuid4(),
            case_number="CASE-2024-001",
            title="Test Forensic Case",
            description="Test case for API testing",
            status=CaseStatus.OPEN,
            priority=CasePriority.HIGH,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="analyst@example.com",
            assigned_to="forensics@example.com",
            evidence_count=5,
            tags=["test", "api"],
            metadata={"test": True}
        )

    @pytest.fixture
    def sample_evidence(self):
        """Sample evidence fixture"""
        return Evidence(
            id=uuid4(),
            case_id=uuid4(),
            evidence_type=EvidenceType.DIGITAL,
            title="Test Evidence",
            description="Test evidence for API testing",
            status=EvidenceStatus.PROCESSED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            collected_by="analyst@example.com",
            file_path="/path/to/evidence",
            hash_value="sha256:abc123",
            size_bytes=1024,
            metadata={"test": True}
        )

    @pytest.fixture
    def sample_report(self):
        """Sample forensic report fixture"""
        return ForensicReport(
            id=uuid4(),
            case_id=uuid4(),
            title="Test Forensic Report",
            report_type=ReportType.FINAL,
            status=ReportStatus.COMPLETED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            generated_by="analyst@example.com",
            file_path="/path/to/report",
            metadata={"test": True}
        )

    # Case Management Tests
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_create_case_success(self, client, mock_forensic_engine, sample_case, auth_headers):
        """Test successful case creation"""
        case_data = {
            "case_number": "CASE-2024-001",
            "title": "Test Forensic Case",
            "description": "Test case for API testing",
            "priority": "high",
            "assigned_to": "forensics@example.com",
            "tags": ["test", "api"]
        }
        
        mock_forensic_engine.create_case.return_value = sample_case
        
        with patch("src.api.routers.forensics.get_forensic_engine", return_value=mock_forensic_engine):
            response = client.post("/api/v1/forensics/cases", json=case_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["case_number"] == case_data["case_number"]
        assert data["title"] == case_data["title"]
        assert data["status"] == "open"
        assert data["priority"] == "high"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_case_success(self, client, mock_forensic_engine, sample_case, auth_headers):
        """Test successful case retrieval"""
        mock_forensic_engine.get_case.return_value = sample_case
        
        with patch("src.api.routers.forensics.get_forensic_engine", return_value=mock_forensic_engine):
            response = client.get(f"/api/v1/forensics/cases/{sample_case.id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(sample_case.id)
        assert data["case_number"] == sample_case.case_number
        assert data["title"] == sample_case.title

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_update_case_success(self, client, mock_forensic_engine, sample_case, auth_headers):
        """Test successful case update"""
        update_data = {
            "title": "Updated Case Title",
            "description": "Updated description",
            "priority": "medium"
        }
        
        updated_case = sample_case.copy()
        updated_case.title = update_data["title"]
        updated_case.description = update_data["description"]
        updated_case.priority = CasePriority.MEDIUM
        
        mock_forensic_engine.update_case.return_value = updated_case
        
        with patch("src.api.routers.forensics.get_forensic_engine", return_value=mock_forensic_engine):
            response = client.put(f"/api/v1/forensics/cases/{sample_case.id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["description"] == update_data["description"]
        assert data["priority"] == "medium"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_list_cases_success(self, client, mock_forensic_engine, sample_case, auth_headers):
        """Test successful case listing"""
        cases = [sample_case]
        mock_forensic_engine.list_cases.return_value = cases
        
        with patch("src.api.routers.forensics.get_forensic_engine", return_value=mock_forensic_engine):
            response = client.get("/api/v1/forensics/cases", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["cases"]) == 1
        assert data["cases"][0]["id"] == str(sample_case.id)

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_list_cases_with_filters(self, client, mock_forensic_engine, sample_case, auth_headers):
        """Test case listing with filters"""
        cases = [sample_case]
        mock_forensic_engine.list_cases.return_value = cases
        
        filters = {
            "status": "open",
            "priority": "high",
            "assigned_to": "forensics@example.com"
        }
        
        with patch("src.api.routers.forensics.get_forensic_engine", return_value=mock_forensic_engine):
            response = client.get("/api/v1/forensics/cases", params=filters, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        mock_forensic_engine.list_cases.assert_called_with(**filters)

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_delete_case_success(self, client, mock_forensic_engine, sample_case, auth_headers):
        """Test successful case deletion"""
        mock_forensic_engine.delete_case.return_value = True
        
        with patch("src.api.routers.forensics.get_forensic_engine", return_value=mock_forensic_engine):
            response = client.delete(f"/api/v1/forensics/cases/{sample_case.id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_case_not_found(self, client, mock_forensic_engine, auth_headers):
        """Test case not found error"""
        case_id = uuid4()
        mock_forensic_engine.get_case.return_value = None
        
        with patch("src.api.routers.forensics.get_forensic_engine", return_value=mock_forensic_engine):
            response = client.get(f"/api/v1/forensics/cases/{case_id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # Evidence Management Tests
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_create_evidence_success(self, client, mock_evidence_manager, sample_evidence, auth_headers):
        """Test successful evidence creation"""
        evidence_data = {
            "case_id": str(uuid4()),
            "evidence_type": "digital",
            "title": "Test Evidence",
            "description": "Test evidence for API testing",
            "file_path": "/path/to/evidence",
            "collected_by": "analyst@example.com"
        }
        
        mock_evidence_manager.create_evidence.return_value = sample_evidence
        
        with patch("src.api.routers.forensics.get_evidence_manager", return_value=mock_evidence_manager):
            response = client.post("/api/v1/forensics/evidence", json=evidence_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == evidence_data["title"]
        assert data["evidence_type"] == "digital"
        assert data["status"] == "processed"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_evidence_success(self, client, mock_evidence_manager, sample_evidence, auth_headers):
        """Test successful evidence retrieval"""
        mock_evidence_manager.get_evidence.return_value = sample_evidence
        
        with patch("src.api.routers.forensics.get_evidence_manager", return_value=mock_evidence_manager):
            response = client.get(f"/api/v1/forensics/evidence/{sample_evidence.id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(sample_evidence.id)
        assert data["title"] == sample_evidence.title

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_list_evidence_success(self, client, mock_evidence_manager, sample_evidence, auth_headers):
        """Test successful evidence listing"""
        evidence_list = [sample_evidence]
        mock_evidence_manager.list_evidence.return_value = evidence_list
        
        with patch("src.api.routers.forensics.get_evidence_manager", return_value=mock_evidence_manager):
            response = client.get("/api/v1/forensics/evidence", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["evidence"]) == 1

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_list_evidence_by_case(self, client, mock_evidence_manager, sample_evidence, auth_headers):
        """Test evidence listing by case ID"""
        evidence_list = [sample_evidence]
        mock_evidence_manager.list_evidence_by_case.return_value = evidence_list
        
        with patch("src.api.routers.forensics.get_evidence_manager", return_value=mock_evidence_manager):
            response = client.get(f"/api/v1/forensics/cases/{sample_evidence.case_id}/evidence", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["evidence"]) == 1

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_verify_evidence_integrity(self, client, mock_evidence_manager, sample_evidence, auth_headers):
        """Test evidence integrity verification"""
        verification_result = {
            "verified": True,
            "hash_matches": True,
            "integrity_score": 1.0,
            "verification_time": datetime.now(timezone.utc).isoformat()
        }
        
        mock_evidence_manager.verify_integrity.return_value = verification_result
        
        with patch("src.api.routers.forensics.get_evidence_manager", return_value=mock_evidence_manager):
            response = client.post(f"/api/v1/forensics/evidence/{sample_evidence.id}/verify", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["verified"] is True
        assert data["hash_matches"] is True

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_chain_of_custody(self, client, mock_evidence_manager, sample_evidence, auth_headers):
        """Test chain of custody retrieval"""
        chain_records = [
            ChainOfCustody(
                id=uuid4(),
                evidence_id=sample_evidence.id,
                transferred_from="analyst1@example.com",
                transferred_to="analyst2@example.com",
                transfer_reason="Analysis",
                timestamp=datetime.now(timezone.utc),
                location="Secure Lab",
                notes="Evidence transferred for analysis"
            )
        ]
        
        mock_evidence_manager.get_chain_of_custody.return_value = chain_records
        
        with patch("src.api.routers.forensics.get_evidence_manager", return_value=mock_evidence_manager):
            response = client.get(f"/api/v1/forensics/evidence/{sample_evidence.id}/custody", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["chain"]) == 1

    # Report Generation Tests
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_create_report_success(self, client, mock_report_generator, sample_report, auth_headers):
        """Test successful report creation"""
        report_data = {
            "case_id": str(uuid4()),
            "title": "Test Forensic Report",
            "report_type": "final",
            "template": "standard_template"
        }
        
        mock_report_generator.create_report.return_value = sample_report
        
        with patch("src.api.routers.forensics.get_report_generator", return_value=mock_report_generator):
            response = client.post("/api/v1/forensics/reports", json=report_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == report_data["title"]
        assert data["report_type"] == "final"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_generate_report_pdf(self, client, mock_report_generator, sample_report, auth_headers):
        """Test PDF report generation"""
        mock_report_generator.generate_pdf_report.return_value = b"PDF content"
        
        with patch("src.api.routers.forensics.get_report_generator", return_value=mock_report_generator):
            response = client.post(f"/api/v1/forensics/reports/{sample_report.id}/generate/pdf", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/pdf"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_generate_report_html(self, client, mock_report_generator, sample_report, auth_headers):
        """Test HTML report generation"""
        mock_report_generator.generate_html_report.return_value = "<html>Report content</html>"
        
        with patch("src.api.routers.forensics.get_report_generator", return_value=mock_report_generator):
            response = client.post(f"/api/v1/forensics/reports/{sample_report.id}/generate/html", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/html"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_list_reports_success(self, client, mock_report_generator, sample_report, auth_headers):
        """Test successful report listing"""
        reports = [sample_report]
        mock_report_generator.list_reports.return_value = reports
        
        with patch("src.api.routers.forensics.get_report_generator", return_value=mock_report_generator):
            response = client.get("/api/v1/forensics/reports", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["reports"]) == 1

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_list_reports_by_case(self, client, mock_report_generator, sample_report, auth_headers):
        """Test report listing by case ID"""
        reports = [sample_report]
        mock_report_generator.list_reports_by_case.return_value = reports
        
        with patch("src.api.routers.forensics.get_report_generator", return_value=mock_report_generator):
            response = client.get(f"/api/v1/forensics/cases/{sample_report.case_id}/reports", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["reports"]) == 1

    # Court Defensible Evidence Tests
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_assess_legal_compliance(self, client, mock_court_defensible, auth_headers):
        """Test legal compliance assessment"""
        evidence_id = uuid4()
        compliance_result = LegalCompliance(
            evidence_id=evidence_id,
            is_compliant=True,
            compliance_score=0.95,
            issues=[],
            recommendations=[],
            assessed_at=datetime.now(timezone.utc),
            assessed_by="legal@example.com"
        )
        
        mock_court_defensible.assess_legal_compliance.return_value = compliance_result
        
        with patch("src.api.routers.forensics.get_court_defensible", return_value=mock_court_defensible):
            response = client.post(f"/api/v1/forensics/evidence/{evidence_id}/assess-compliance", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_compliant"] is True
        assert data["compliance_score"] == 0.95

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_prepare_foundation_requirements(self, client, mock_court_defensible, auth_headers):
        """Test foundation requirements preparation"""
        evidence_id = uuid4()
        foundation = FoundationRequirements(
            evidence_id=evidence_id,
            authentication_methods=["Hash verification", "Chain of custody"],
            chain_of_custody_complete=True,
            original_evidence_preserved=True,
            collection_method_valid=True,
            requirements_met=True,
            gaps=[],
            prepared_at=datetime.now(timezone.utc)
        )
        
        mock_court_defensible.prepare_foundation_requirements.return_value = foundation
        
        with patch("src.api.routers.forensics.get_court_defensible", return_value=mock_court_defensible):
            response = client.post(f"/api/v1/forensics/evidence/{evidence_id}/prepare-foundation", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["requirements_met"] is True

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_prepare_testimony(self, client, mock_court_defensible, auth_headers):
        """Test testimony preparation"""
        evidence_id = uuid4()
        testimony = TestimonyPreparation(
            evidence_id=evidence_id,
            witness_name="John Doe",
            role="Digital Forensics Analyst",
            qualifications=["CFE", "EnCE"],
            testimony_points=[
                "I collected the evidence using standard forensic procedures",
                "The evidence hash was verified at collection and analysis"
            ],
            potential_questions=[
                "What tools did you use for evidence collection?",
                "How did you ensure evidence integrity?"
            ],
            prepared_at=datetime.now(timezone.utc)
        )
        
        mock_court_defensible.prepare_testimony.return_value = testimony
        
        with patch("src.api.routers.forensics.get_court_defensible", return_value=mock_court_defensible):
            response = client.post(f"/api/v1/forensics/evidence/{evidence_id}/prepare-testimony", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["witness_name"] == "John Doe"
        assert len(data["testimony_points"]) == 2

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_prepare_exhibit(self, client, mock_court_defensible, auth_headers):
        """Test exhibit preparation"""
        evidence_id = uuid4()
        exhibit = ExhibitPreparation(
            evidence_id=evidence_id,
            exhibit_number="EX-001",
            exhibit_title="Digital Evidence Exhibit",
            description="Digital forensic evidence collected from suspect device",
            authentication_summary="Hash verified, chain of custody maintained",
            exhibit_format="Digital",
            prepared_at=datetime.now(timezone.utc)
        )
        
        mock_court_defensible.prepare_exhibit.return_value = exhibit
        
        with patch("src.api.routers.forensics.get_court_defensible", return_value=mock_court_defensible):
            response = client.post(f"/api/v1/forensics/evidence/{evidence_id}/prepare-exhibit", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["exhibit_number"] == "EX-001"
        assert data["exhibit_title"] == "Digital Evidence Exhibit"

    # Statistics Tests
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_case_statistics(self, client, mock_forensic_engine, auth_headers):
        """Test case statistics retrieval"""
        stats = CaseStatistics(
            total_cases=100,
            open_cases=25,
            closed_cases=70,
            high_priority_cases=10,
            medium_priority_cases=40,
            low_priority_cases=50,
            average_case_duration_days=15.5,
            cases_by_status={"open": 25, "closed": 70, "archived": 5},
            cases_by_priority={"high": 10, "medium": 40, "low": 50}
        )
        
        mock_forensic_engine.get_case_statistics.return_value = stats
        
        with patch("src.api.routers.forensics.get_forensic_engine", return_value=mock_forensic_engine):
            response = client.get("/api/v1/forensics/statistics/cases", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_cases"] == 100
        assert data["open_cases"] == 25

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_evidence_statistics(self, client, mock_evidence_manager, auth_headers):
        """Test evidence statistics retrieval"""
        stats = EvidenceStatistics(
            total_evidence=500,
            processed_evidence=450,
            pending_evidence=40,
            failed_evidence=10,
            evidence_by_type={"digital": 300, "physical": 150, "document": 50},
            evidence_by_status={"processed": 450, "pending": 40, "failed": 10},
            average_processing_time_hours=2.5,
            storage_utilization_gb=250.5
        )
        
        mock_evidence_manager.get_evidence_statistics.return_value = stats
        
        with patch("src.api.routers.forensics.get_evidence_manager", return_value=mock_evidence_manager):
            response = client.get("/api/v1/forensics/statistics/evidence", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_evidence"] == 500
        assert data["processed_evidence"] == 450

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_report_statistics(self, client, mock_report_generator, auth_headers):
        """Test report statistics retrieval"""
        stats = ReportStatistics(
            total_reports=200,
            completed_reports=180,
            in_progress_reports=15,
            failed_reports=5,
            reports_by_type={"preliminary": 50, "interim": 80, "final": 70},
            reports_by_status={"completed": 180, "in_progress": 15, "failed": 5},
            average_generation_time_minutes=30.0,
            total_pages_generated=5000
        )
        
        mock_report_generator.get_report_statistics.return_value = stats
        
        with patch("src.api.routers.forensics.get_report_generator", return_value=mock_report_generator):
            response = client.get("/api/v1/forensics/statistics/reports", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_reports"] == 200
        assert data["completed_reports"] == 180

    # Authentication Tests
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client, sample_case):
        """Test unauthorized access to forensics endpoints"""
        response = client.get(f"/api/v1/forensics/cases/{sample_case.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_invalid_token(self, client, sample_case):
        """Test invalid token access"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get(f"/api/v1/forensics/cases/{sample_case.id}", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Error Handling Tests
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_case_creation_validation_error(self, client, mock_forensic_engine, auth_headers):
        """Test case creation with invalid data"""
        invalid_data = {
            "title": "",  # Empty title
            "priority": "invalid_priority"  # Invalid priority
        }
        
        with patch("src.api.routers.forensics.get_forensic_engine", return_value=mock_forensic_engine):
            response = client.post("/api/v1/forensics/cases", json=invalid_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_evidence_creation_validation_error(self, client, mock_evidence_manager, auth_headers):
        """Test evidence creation with invalid data"""
        invalid_data = {
            "evidence_type": "invalid_type",
            "title": "",  # Empty title
            "file_path": ""  # Empty file path
        }
        
        with patch("src.api.routers.forensics.get_evidence_manager", return_value=mock_evidence_manager):
            response = client.post("/api/v1/forensics/evidence", json=invalid_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_server_error_handling(self, client, mock_forensic_engine, auth_headers):
        """Test server error handling"""
        case_id = uuid4()
        mock_forensic_engine.get_case.side_effect = Exception("Database error")
        
        with patch("src.api.routers.forensics.get_forensic_engine", return_value=mock_forensic_engine):
            response = client.get(f"/api/v1/forensics/cases/{case_id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    # Integration Tests
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_case_evidence_workflow(self, client, mock_forensic_engine, mock_evidence_manager, 
                                        sample_case, sample_evidence, auth_headers):
        """Test integrated case-evidence workflow"""
        # Create case
        case_data = {
            "case_number": "CASE-2024-001",
            "title": "Test Case",
            "description": "Test case description",
            "priority": "high"
        }
        
        mock_forensic_engine.create_case.return_value = sample_case
        mock_evidence_manager.create_evidence.return_value = sample_evidence
        
        with patch("src.api.routers.forensics.get_forensic_engine", return_value=mock_forensic_engine), \
             patch("src.api.routers.forensics.get_evidence_manager", return_value=mock_evidence_manager):
            
            # Create case
            case_response = client.post("/api/v1/forensics/cases", json=case_data, headers=auth_headers)
            assert case_response.status_code == status.HTTP_201_CREATED
            
            # Add evidence to case
            evidence_data = {
                "case_id": str(sample_case.id),
                "evidence_type": "digital",
                "title": "Test Evidence",
                "description": "Test evidence description"
            }
            
            evidence_response = client.post("/api/v1/forensics/evidence", json=evidence_data, headers=auth_headers)
            assert evidence_response.status_code == status.HTTP_201_CREATED
            
            # List evidence for case
            mock_evidence_manager.list_evidence_by_case.return_value = [sample_evidence]
            list_response = client.get(f"/api/v1/forensics/cases/{sample_case.id}/evidence", headers=auth_headers)
            assert list_response.status_code == status.HTTP_200_OK
            assert len(list_response.json()["evidence"]) == 1

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_case_report_workflow(self, client, mock_forensic_engine, mock_report_generator, 
                                       sample_case, sample_report, auth_headers):
        """Test integrated case-report workflow"""
        # Create case
        case_data = {
            "case_number": "CASE-2024-001",
            "title": "Test Case",
            "description": "Test case description",
            "priority": "high"
        }
        
        mock_forensic_engine.create_case.return_value = sample_case
        mock_report_generator.create_report.return_value = sample_report
        
        with patch("src.api.routers.forensics.get_forensic_engine", return_value=mock_forensic_engine), \
             patch("src.api.routers.forensics.get_report_generator", return_value=mock_report_generator):
            
            # Create case
            case_response = client.post("/api/v1/forensics/cases", json=case_data, headers=auth_headers)
            assert case_response.status_code == status.HTTP_201_CREATED
            
            # Create report for case
            report_data = {
                "case_id": str(sample_case.id),
                "title": "Test Report",
                "report_type": "final"
            }
            
            report_response = client.post("/api/v1/forensics/reports", json=report_data, headers=auth_headers)
            assert report_response.status_code == status.HTTP_201_CREATED
            
            # List reports for case
            mock_report_generator.list_reports_by_case.return_value = [sample_report]
            list_response = client.get(f"/api/v1/forensics/cases/{sample_case.id}/reports", headers=auth_headers)
            assert list_response.status_code == status.HTTP_200_OK
            assert len(list_response.json()["reports"]) == 1

    # Performance Tests
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_large_case_list_performance(self, client, mock_forensic_engine, auth_headers):
        """Test performance with large case lists"""
        # Mock large number of cases
        large_case_list = [ForensicCase(
            id=uuid4(),
            case_number=f"CASE-2024-{i:03d}",
            title=f"Test Case {i}",
            description=f"Test case description {i}",
            status=CaseStatus.OPEN,
            priority=CasePriority.MEDIUM,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="analyst@example.com",
            assigned_to="forensics@example.com",
            evidence_count=5
        ) for i in range(1000)]
        
        mock_forensic_engine.list_cases.return_value = large_case_list
        
        with patch("src.api.routers.forensics.get_forensic_engine", return_value=mock_forensic_engine):
            response = client.get("/api/v1/forensics/cases", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["cases"]) == 1000

    # Data Validation Tests
    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_uuid_validation(self, client, mock_forensic_engine, auth_headers):
        """Test UUID validation for case IDs"""
        invalid_uuid = "invalid-uuid-format"
        
        with patch("src.api.routers.forensics.get_forensic_engine", return_value=mock_forensic_engine):
            response = client.get(f"/api/v1/forensics/cases/{invalid_uuid}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_datetime_format_validation(self, client, mock_forensic_engine, auth_headers):
        """Test datetime format validation"""
        case_data = {
            "case_number": "CASE-2024-001",
            "title": "Test Case",
            "description": "Test case description",
            "priority": "high",
            "created_at": "invalid-datetime-format"
        }
        
        with patch("src.api.routers.forensics.get_forensic_engine", return_value=mock_forensic_engine):
            response = client.post("/api/v1/forensics/cases", json=case_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
