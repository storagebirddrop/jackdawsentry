"""
Jackdaw Sentry - Report Generator Unit Tests
Tests for forensic report generation and templates
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
import os
import tempfile
from pathlib import Path

from src.forensics.report_generator import (
    ReportGenerator,
    ReportType,
    ReportFormat,
    ReportTemplate,
    ForensicReport,
    ReportStatistics,
)


class TestReportGenerator:
    """Test suite for ReportGenerator"""

    @pytest.fixture
    def mock_db_pool(self):
        """Mock PostgreSQL connection pool"""
        return AsyncMock()

    @pytest.fixture
    def report_generator(self, mock_db_pool):
        """Create ReportGenerator instance with mocked dependencies"""
        with patch("src.forensics.report_generator.get_postgres_connection", return_value=mock_db_pool):
            return ReportGenerator(mock_db_pool)

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for file operations"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    # ---- Initialization Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generator_initializes(self, report_generator, mock_db_pool):
        """Test generator initialization creates required schema"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        await report_generator.initialize()
        
        # Verify schema creation queries were executed
        assert mock_conn.execute.call_count >= 1
        mock_pool.acquire.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generator_shutdown(self, report_generator):
        """Test generator shutdown"""
        report_generator.running = True
        await report_generator.shutdown()
        assert report_generator.running is False

    # ---- Report Creation Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_report_record(self, report_generator, mock_db_pool):
        """Test successful report record creation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {"id": str(uuid4())}
        
        report_data = {
            "case_id": str(uuid4()),
            "report_type": "detailed",
            "title": "Cryptocurrency Fraud Investigation Report",
            "format": "pdf",
            "include_evidence": True,
            "include_chain_of_custody": True,
            "include_analysis": True,
            "custom_sections": [
                {"title": "Executive Summary", "content": "High-level overview"},
                {"title": "Technical Details", "content": "Technical analysis"}
            ],
            "generated_by": "analyst_123"
        }
        
        report = await report_generator.create_report_record(report_data)
        
        assert isinstance(report, ForensicReport)
        assert report.case_id == report_data["case_id"]
        assert report.report_type == ReportType.DETAILED
        assert report.title == "Cryptocurrency Fraud Investigation Report"
        assert report.format == ReportFormat.PDF
        assert report.include_evidence is True
        assert report.include_chain_of_custody is True
        assert report.include_analysis is True
        assert report.generated_by == "analyst_123"
        assert report.status == "generating"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_report_record_invalid_data(self, report_generator):
        """Test report record creation with invalid data"""
        invalid_data = {
            "case_id": "",  # Empty required field
            "report_type": "invalid_type",  # Invalid enum value
            "title": "",  # Empty required field
            "format": "invalid_format"  # Invalid enum value
        }
        
        with pytest.raises(ValueError, match="Case ID is required"):
            await report_generator.create_report_record(invalid_data)

    # ---- Report Generation Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_pdf_report(self, report_generator, mock_db_pool, temp_dir):
        """Test PDF report generation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        report_id = str(uuid4())
        output_path = os.path.join(temp_dir, "test_report.pdf")
        
        # Mock report data
        mock_report = MagicMock(
            id=report_id,
            case_id=str(uuid4()),
            title="Test Report",
            report_type="detailed",
            format="pdf",
            include_evidence=True,
            include_chain_of_custody=True,
            include_analysis=True,
            custom_sections=[],
            generated_by="analyst_123"
        )
        
        # Mock case data
        mock_case = MagicMock(
            id=str(uuid4()),
            title="Test Case",
            description="Test case description",
            case_type="cryptocurrency_fraud",
            status="closed",
            priority="high",
            assigned_investigator="investigator_123",
            created_date=datetime.now(timezone.utc) - timedelta(days=10),
            completion_date=datetime.now(timezone.utc) - timedelta(days=1)
        )
        
        # Mock evidence data
        mock_evidence = [
            MagicMock(
                id=str(uuid4()),
                title="Evidence 1",
                evidence_type="transaction_data",
                collection_date=datetime.now(timezone.utc) - timedelta(days=5),
                integrity_status="verified",
                metadata={"hash": "abc123"}
            ),
            MagicMock(
                id=str(uuid4()),
                title="Evidence 2",
                evidence_type="address_analysis",
                collection_date=datetime.now(timezone.utc) - timedelta(days=3),
                integrity_status="verified",
                metadata={"addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"]}
            )
        ]
        
        # Mock database queries
        mock_conn.fetchrow.side_effect = [mock_report, mock_case]
        mock_conn.fetch.return_value = mock_evidence
        
        # Mock PDF generation
        with patch("reportlab.pdfgen.canvas.Canvas") as mock_canvas, \
             patch("reportlab.platypus.SimpleDocTemplate") as mock_template:
            
            mock_canvas_instance = MagicMock()
            mock_canvas.return_value = mock_canvas_instance
            mock_template_instance = MagicMock()
            mock_template.return_value = mock_template_instance
            
            result = await report_generator.generate_pdf_report(report_id, output_path)
        
        assert result["success"] is True
        assert result["file_path"] == output_path
        assert result["file_size"] > 0
        assert result["checksum"] is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_html_report(self, report_generator, mock_db_pool, temp_dir):
        """Test HTML report generation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        report_id = str(uuid4())
        output_path = os.path.join(temp_dir, "test_report.html")
        
        # Mock report and case data
        mock_report = MagicMock(
            id=report_id,
            case_id=str(uuid4()),
            title="Test HTML Report",
            report_type="summary",
            format="html",
            include_evidence=True,
            include_chain_of_custody=True,
            include_analysis=True,
            custom_sections=[],
            generated_by="analyst_123"
        )
        
        mock_case = MagicMock(
            id=str(uuid4()),
            title="Test Case",
            description="Test case description",
            status="in_progress",
            priority="medium"
        )
        
        mock_evidence = [
            MagicMock(
                id=str(uuid4()),
                title="Evidence 1",
                evidence_type="documents",
                collection_date=datetime.now(timezone.utc) - timedelta(days=2),
                integrity_status="verified"
            )
        ]
        
        mock_conn.fetchrow.side_effect = [mock_report, mock_case]
        mock_conn.fetch.return_value = mock_evidence
        
        result = await report_generator.generate_html_report(report_id, output_path)
        
        assert result["success"] is True
        assert result["file_path"] == output_path
        assert result["file_size"] > 0
        assert os.path.exists(output_path)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_json_report(self, report_generator, mock_db_pool, temp_dir):
        """Test JSON report generation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        report_id = str(uuid4())
        output_path = os.path.join(temp_dir, "test_report.json")
        
        # Mock report and case data
        mock_report = MagicMock(
            id=report_id,
            case_id=str(uuid4()),
            title="Test JSON Report",
            report_type="technical",
            format="json",
            include_evidence=True,
            include_chain_of_custody=True,
            include_analysis=True,
            custom_sections=[],
            generated_by="analyst_123"
        )
        
        mock_case = MagicMock(
            id=str(uuid4()),
            title="Test Case",
            description="Test case description",
            case_type="smart_contract_hack",
            status="analysis"
        )
        
        mock_evidence = [
            MagicMock(
                id=str(uuid4()),
                title="Technical Evidence",
                evidence_type="smart_contract_code",
                collection_date=datetime.now(timezone.utc) - timedelta(days=1),
                integrity_status="verified",
                metadata={"contract_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"}
            )
        ]
        
        mock_conn.fetchrow.side_effect = [mock_report, mock_case]
        mock_conn.fetch.return_value = mock_evidence
        
        result = await report_generator.generate_json_report(report_id, output_path)
        
        assert result["success"] is True
        assert result["file_path"] == output_path
        assert result["file_size"] > 0
        
        # Verify JSON structure
        with open(output_path, 'r') as f:
            json_data = json.load(f)
        
        assert "report_metadata" in json_data
        assert "case_information" in json_data
        assert "evidence" in json_data
        assert json_data["report_metadata"]["title"] == "Test JSON Report"

    # ---- Template Management Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_template(self, report_generator, mock_db_pool):
        """Test successful template creation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {"id": str(uuid4())}
        
        template_data = {
            "name": "Standard Fraud Investigation Template",
            "description": "Template for standard cryptocurrency fraud investigations",
            "report_type": "detailed",
            "format": "pdf",
            "template_content": """
# {title}

## Case Information
**Case ID:** {case_id}
**Investigator:** {investigator}
**Date:** {date}

## Executive Summary
{executive_summary}

## Findings
{findings}

## Evidence
{evidence}

## Conclusion
{conclusion}
            """.strip(),
            "variables": ["title", "case_id", "investigator", "date", "executive_summary", "findings", "evidence", "conclusion"],
            "is_default": False,
            "created_by": "template_creator"
        }
        
        template = await report_generator.create_template(template_data)
        
        assert isinstance(template, ReportTemplate)
        assert template.name == "Standard Fraud Investigation Template"
        assert template.report_type == ReportType.DETAILED
        assert template.format == ReportFormat.PDF
        assert len(template.variables) == 8
        assert template.is_default is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_template(self, report_generator, mock_db_pool):
        """Test successful template retrieval"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        template_id = str(uuid4())
        
        mock_row = {
            "id": template_id,
            "name": "Test Template",
            "description": "Test template description",
            "report_type": "summary",
            "format": "html",
            "template_content": "# {title}\n\n## Summary\n{summary}",
            "variables": ["title", "summary"],
            "is_default": True,
            "created_date": datetime.now(timezone.utc) - timedelta(days=5),
            "last_updated": datetime.now(timezone.utc) - timedelta(days=1),
            "created_by": "template_creator"
        }
        mock_conn.fetchrow.return_value = mock_row
        
        template = await report_generator.get_template(template_id)
        
        assert template is not None
        assert template.id == template_id
        assert template.name == "Test Template"
        assert template.report_type == ReportType.SUMMARY
        assert template.format == ReportFormat.HTML

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_templates(self, report_generator, mock_db_pool):
        """Test template listing with filters"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        filters = {
            "report_type": "detailed",
            "format": "pdf",
            "is_default": True
        }
        
        mock_rows = [
            {
                "id": str(uuid4()),
                "name": "Template 1",
                "report_type": "detailed",
                "format": "pdf",
                "is_default": True,
                "created_date": datetime.now(timezone.utc) - timedelta(days=10)
            },
            {
                "id": str(uuid4()),
                "name": "Template 2",
                "report_type": "detailed",
                "format": "pdf",
                "is_default": True,
                "created_date": datetime.now(timezone.utc) - timedelta(days=5)
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        templates = await report_generator.list_templates(filters)
        
        assert len(templates) == 2
        for template in templates:
            assert template.report_type == ReportType.DETAILED
            assert template.format == ReportFormat.PDF
            assert template.is_default is True

    # ---- Report Retrieval Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_report(self, report_generator, mock_db_pool):
        """Test successful report retrieval"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        report_id = str(uuid4())
        
        mock_row = {
            "id": report_id,
            "case_id": str(uuid4()),
            "title": "Completed Investigation Report",
            "report_type": "court_submission",
            "format": "pdf",
            "status": "completed",
            "file_path": "/reports/report_123.pdf",
            "file_size": 1048576,
            "checksum": "abc123def456",
            "generated_date": datetime.now(timezone.utc) - timedelta(days=2),
            "generated_by": "analyst_456",
            "reviewed_by": "supervisor_789",
            "approved_by": "manager_012",
            "is_court_ready": True,
            "confidence_score": 0.95,
            "total_word_count": 5000,
            "created_date": datetime.now(timezone.utc) - timedelta(days=3),
            "last_updated": datetime.now(timezone.utc) - timedelta(days=2)
        }
        mock_conn.fetchrow.return_value = mock_row
        
        report = await report_generator.get_report(report_id)
        
        assert report is not None
        assert report.id == report_id
        assert report.title == "Completed Investigation Report"
        assert report.report_type == ReportType.COURT_SUBMISSION
        assert report.status == "completed"
        assert report.is_court_ready is True
        assert report.confidence_score == 0.95

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_report_not_found(self, report_generator, mock_db_pool):
        """Test report retrieval when report doesn't exist"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        
        report = await report_generator.get_report("nonexistent_id")
        assert report is None

    # ---- Report Update Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_report_status(self, report_generator, mock_db_pool):
        """Test successful report status update"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        report_id = str(uuid4())
        update_data = {
            "status": "completed",
            "file_path": "/reports/updated_report.pdf",
            "file_size": 2097152,
            "checksum": "updated_checksum_123",
            "is_court_ready": True,
            "confidence_score": 0.9,
            "total_word_count": 7500,
            "reviewed_by": "reviewer_456"
        }
        
        # Mock existing report
        mock_conn.fetchrow.return_value = {"id": report_id}
        
        mock_row = {
            "id": report_id,
            "status": "completed",
            "file_path": "/reports/updated_report.pdf",
            "file_size": 2097152,
            "checksum": "updated_checksum_123",
            "is_court_ready": True,
            "confidence_score": 0.9,
            "total_word_count": 7500,
            "reviewed_by": "reviewer_456",
            "last_updated": datetime.now(timezone.utc)
        }
        mock_conn.fetchrow.return_value = mock_row
        
        updated_report = await report_generator.update_report_status(report_id, update_data)
        
        assert updated_report.status == "completed"
        assert updated_report.file_path == "/reports/updated_report.pdf"
        assert updated_report.is_court_ready is True
        assert updated_report.confidence_score == 0.9
        assert updated_report.reviewed_by == "reviewer_456"

    # ---- Report Statistics Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_statistics(self, report_generator, mock_db_pool):
        """Test report statistics calculation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        days = 30
        
        # Mock statistics query results
        mock_stats = {
            "total_reports": 150,
            "reports_by_type": {
                ReportType.SUMMARY.value: 40,
                ReportType.DETAILED.value: 60,
                ReportType.EXPERT_WITNESS.value: 20,
                ReportType.COURT_SUBMISSION.value: 15,
                ReportType.TECHNICAL.value: 10,
                ReportType.EXECUTIVE.value: 5
            },
            "reports_by_format": {
                ReportFormat.PDF.value: 80,
                ReportFormat.HTML.value: 40,
                ReportFormat.JSON.value: 20,
                ReportFormat.DOCX.value: 10
            },
            "reports_by_status": {
                "generating": 5,
                "completed": 120,
                "reviewed": 20,
                "approved": 5
            },
            "average_word_count": 3500.0,
            "total_word_count": 525000,
            "court_ready_reports": 25,
            "average_generation_time_minutes": 15.5,
            "success_rate": 0.95
        }
        mock_conn.fetchrow.return_value = mock_stats
        
        stats = await report_generator.get_statistics(days)
        
        assert isinstance(stats, ReportStatistics)
        assert stats.total_reports == 150
        assert stats.reports_by_type[ReportType.DETAILED.value] == 60
        assert stats.reports_by_format[ReportFormat.PDF.value] == 80
        assert stats.average_word_count == 3500.0
        assert stats.court_ready_reports == 25
        assert stats.success_rate == 0.95

    # ---- Template Application Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_apply_template(self, report_generator, temp_dir):
        """Test template application with variable substitution"""
        template_content = """
# {title}

## Case Information
- **Case ID:** {case_id}
- **Investigator:** {investigator}
- **Date:** {date}

## Executive Summary
{executive_summary}

## Detailed Findings
{findings}

## Evidence Summary
{evidence_summary}

## Conclusion
{conclusion}
        """.strip()
        
        variables = {
            "title": "Cryptocurrency Fraud Investigation",
            "case_id": "CASE-2023-001",
            "investigator": "John Doe",
            "date": "2023-12-01",
            "executive_summary": "This report details the investigation of a sophisticated cryptocurrency fraud scheme.",
            "findings": "Multiple fraudulent transactions were identified totaling $500,000 in losses.",
            "evidence_summary": "15 pieces of evidence were collected and verified.",
            "conclusion": "The evidence supports the conclusion of fraudulent activity."
        }
        
        output_path = os.path.join(temp_dir, "templated_report.md")
        
        result = await report_generator.apply_template(template_content, variables, output_path)
        
        assert result["success"] is True
        assert result["output_path"] == output_path
        
        # Verify template was applied correctly
        with open(output_path, 'r') as f:
            content = f.read()
        
        assert "Cryptocurrency Fraud Investigation" in content
        assert "CASE-2023-001" in content
        assert "John Doe" in content
        assert "2023-12-01" in content

    # ---- Court Preparation Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_prepare_court_submission(self, report_generator, mock_db_pool, temp_dir):
        """Test court submission preparation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        report_id = str(uuid4())
        jurisdiction = "federal_us"
        court_type = "criminal"
        
        # Mock report data
        mock_report = MagicMock(
            id=report_id,
            title="Court Submission Report",
            report_type="court_submission",
            format="pdf",
            file_path=os.path.join(temp_dir, "report.pdf"),
            is_court_ready=True,
            confidence_score=0.95,
            generated_by="analyst_123"
        )
        
        # Mock case data
        mock_case = MagicMock(
            id=str(uuid4()),
            title="Legal Case",
            legal_standard="beyond_reasonable_doubt",
            jurisdiction="federal_us"
        )
        
        # Mock evidence
        mock_evidence = [
            MagicMock(
                id=str(uuid4()),
                title="Verified Evidence 1",
                integrity_status="verified",
                chain_of_custody_verified=True
            ),
            MagicMock(
                id=str(uuid4()),
                title="Verified Evidence 2",
                integrity_status="verified",
                chain_of_custody_verified=True
            )
        ]
        
        mock_conn.fetchrow.side_effect = [mock_report, mock_case]
        mock_conn.fetch.return_value = mock_evidence
        
        result = await report_generator.prepare_court_submission(
            report_id, jurisdiction, court_type
        )
        
        assert result["success"] is True
        assert result["jurisdiction"] == jurisdiction
        assert result["court_type"] == court_type
        assert result["evidence_compliance"]["verified_evidence"] == 2
        assert result["evidence_compliance"]["total_evidence"] == 2
        assert result["readiness_score"] >= 0.9

    # ---- Error Handling Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_database_connection_error(self, report_generator, mock_db_pool):
        """Test handling of database connection errors"""
        mock_pool.acquire.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            await report_generator.create_report_record({
                "case_id": str(uuid4()),
                "report_type": "summary",
                "title": "Test Report",
                "format": "pdf",
                "generated_by": "test_user"
            })

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_report_type_validation(self, report_generator):
        """Test validation of invalid report types"""
        invalid_data = {
            "case_id": str(uuid4()),
            "report_type": "invalid_type",  # Invalid enum value
            "title": "Test Report",
            "format": "pdf",
            "generated_by": "test_user"
        }
        
        with pytest.raises(ValueError, match="Invalid report type"):
            await report_generator.create_report_record(invalid_data)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_file_generation_error(self, report_generator, mock_db_pool, temp_dir):
        """Test handling of file generation errors"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        report_id = str(uuid4())
        output_path = os.path.join(temp_dir, "test_report.pdf")
        
        # Mock report data
        mock_report = MagicMock(id=report_id)
        mock_case = MagicMock()
        
        mock_conn.fetchrow.side_effect = [mock_report, mock_case]
        mock_conn.fetch.return_value = []
        
        # Mock PDF generation error
        with patch("reportlab.pdfgen.canvas.Canvas", side_effect=Exception("PDF generation failed")):
            result = await report_generator.generate_pdf_report(report_id, output_path)
        
        assert result["success"] is False
        assert "PDF generation failed" in result["error"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_template_variable_missing(self, report_generator, temp_dir):
        """Test template application with missing variables"""
        template_content = "# {title}\n\n## Missing Variable\n{nonexistent_variable}"
        
        variables = {
            "title": "Test Report"
            # Missing "nonexistent_variable"
        }
        
        output_path = os.path.join(temp_dir, "incomplete_report.md")
        
        result = await report_generator.apply_template(template_content, variables, output_path)
        
        assert result["success"] is True
        assert result["warnings"] is not None
        assert "nonexistent_variable" in str(result["warnings"])


class TestForensicReportModel:
    """Test suite for ForensicReport data model"""

    @pytest.mark.unit
    def test_forensic_report_creation(self):
        """Test ForensicReport model creation"""
        report_data = {
            "id": str(uuid4()),
            "case_id": str(uuid4()),
            "title": "Comprehensive Cryptocurrency Investigation Report",
            "report_type": "detailed",
            "format": "pdf",
            "status": "completed",
            "file_path": "/reports/comprehensive_investigation.pdf",
            "file_size": 2097152,
            "checksum": "abc123def456789",
            "generated_date": datetime.now(timezone.utc) - timedelta(days=2),
            "generated_by": "lead_analyst",
            "reviewed_by": "senior_analyst",
            "approved_by": "case_manager",
            "is_court_ready": True,
            "confidence_score": 0.92,
            "total_word_count": 8500,
            "created_date": datetime.now(timezone.utc) - timedelta(days=3),
            "last_updated": datetime.now(timezone.utc) - timedelta(days=2)
        }
        
        report = ForensicReport(**report_data)
        
        assert report.id == report_data["id"]
        assert report.title == "Comprehensive Cryptocurrency Investigation Report"
        assert report.report_type == ReportType.DETAILED
        assert report.format == ReportFormat.PDF
        assert report.status == "completed"
        assert report.is_court_ready is True
        assert report.confidence_score == 0.92
        assert report.total_word_count == 8500

    @pytest.mark.unit
    def test_forensic_report_optional_fields(self):
        """Test ForensicReport with optional fields"""
        report_data = {
            "id": str(uuid4()),
            "case_id": str(uuid4()),
            "title": "Simple Report",
            "report_type": "summary",
            "format": "html",
            "status": "generating",
            "generated_by": "analyst_123",
            "created_date": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc)
        }
        
        report = ForensicReport(**report_data)
        
        assert report.file_path is None
        assert report.file_size is None
        assert report.checksum is None
        assert report.reviewed_by is None
        assert report.approved_by is None
        assert report.is_court_ready is False
        assert report.confidence_score is None
        assert report.total_word_count is None


class TestReportTemplateModel:
    """Test suite for ReportTemplate data model"""

    @pytest.mark.unit
    def test_report_template_creation(self):
        """Test ReportTemplate model creation"""
        template_data = {
            "id": str(uuid4()),
            "name": "Standard Investigation Template",
            "description": "Standard template for forensic investigations",
            "report_type": "detailed",
            "format": "pdf",
            "template_content": "# {title}\n\n## Summary\n{summary}\n\n## Details\n{details}",
            "variables": ["title", "summary", "details"],
            "is_default": False,
            "created_date": datetime.now(timezone.utc) - timedelta(days=10),
            "last_updated": datetime.now(timezone.utc) - timedelta(days=2),
            "created_by": "template_creator"
        }
        
        template = ReportTemplate(**template_data)
        
        assert template.id == template_data["id"]
        assert template.name == "Standard Investigation Template"
        assert template.report_type == ReportType.DETAILED
        assert template.format == ReportFormat.PDF
        assert len(template.variables) == 3
        assert template.is_default is False

    @pytest.mark.unit
    def test_report_template_validation(self):
        """Test ReportTemplate validation"""
        with pytest.raises(ValueError):
            ReportTemplate(
                id=str(uuid4()),
                name="Test Template",
                description="Test description",
                report_type="invalid_type",  # Invalid enum
                format="pdf",
                template_content="# Test",
                variables=[],
                is_default=False,
                created_date=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc),
                created_by="creator"
            )


class TestReportStatisticsModel:
    """Test suite for ReportStatistics data model"""

    @pytest.mark.unit
    def test_report_statistics_creation(self):
        """Test ReportStatistics model creation"""
        stats_data = {
            "total_reports": 200,
            "reports_by_type": {
                ReportType.SUMMARY.value: 50,
                ReportType.DETAILED.value: 80,
                ReportType.EXPERT_WITNESS.value: 30,
                ReportType.COURT_SUBMISSION.value: 25,
                ReportType.TECHNICAL.value: 10,
                ReportType.EXECUTIVE.value: 5
            },
            "reports_by_format": {
                ReportFormat.PDF.value: 100,
                ReportFormat.HTML.value: 60,
                ReportFormat.JSON.value: 30,
                ReportFormat.DOCX.value: 10
            },
            "reports_by_status": {
                "generating": 8,
                "completed": 170,
                "reviewed": 15,
                "approved": 7
            },
            "average_word_count": 3200.0,
            "total_word_count": 640000,
            "court_ready_reports": 35,
            "average_generation_time_minutes": 12.5,
            "success_rate": 0.96
        }
        
        stats = ReportStatistics(**stats_data)
        
        assert stats.total_reports == 200
        assert stats.reports_by_type[ReportType.DETAILED.value] == 80
        assert stats.reports_by_format[ReportFormat.PDF.value] == 100
        assert stats.average_word_count == 3200.0
        assert stats.court_ready_reports == 35
        assert stats.success_rate == 0.96

    @pytest.mark.unit
    def test_report_statistics_calculated_fields(self):
        """Test calculated fields in ReportStatistics"""
        stats = ReportStatistics(
            total_reports=100,
            completed_reports=90,
            total_word_count=300000,
            court_ready_reports=40,
            total_generation_time_minutes=1000
        )
        
        # Test calculated success rate
        expected_rate = 90 / 100  # 0.9
        assert abs(stats.success_rate - expected_rate) < 0.001
        
        # Test calculated average word count
        expected_avg = 300000 / 100  # 3000.0
        assert abs(stats.average_word_count - expected_avg) < 0.001
        
        # Test calculated average generation time
        expected_time = 1000 / 100  # 10.0
        assert abs(stats.average_generation_time_minutes - expected_time) < 0.001
