"""
Regulatory Reporting Integration Tests

Comprehensive test suite for the regulatory reporting engine including:
- Report creation and lifecycle management
- Multi-jurisdictional support
- Deadline tracking and compliance
- API integration and status updates
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from src.compliance.regulatory_reporting import (
    RegulatoryReportingEngine,
    RegulatoryJurisdiction,
    ReportType,
    ReportStatus,
    RegulatoryRequirement,
    RegulatoryReport
)


class TestRegulatoryReportingEngine:
    """Test suite for RegulatoryReportingEngine"""

    @pytest.fixture
    async def engine(self):
        """Create test engine instance"""
        engine = RegulatoryReportingEngine()
        await engine.initialize()
        yield engine
        # Cleanup if needed

    @pytest.fixture
    def sample_requirement(self):
        """Create sample regulatory requirement"""
        return RegulatoryRequirement(
            requirement_id="req_001",
            jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
            report_type=ReportType.SAR,
            description="Suspicious Activity Report",
            deadline_hours=72,
            template_fields=["transaction_details", "suspicious_activity", "subject_information"],
            active=True
        )

    @pytest.fixture
    def sample_report_data(self):
        """Create sample report data"""
        return {
            "transaction_details": {
                "transaction_hash": "0x1234567890abcdef",
                "amount": 15000.00,
                "currency": "USD",
                "date": "2024-01-15",
                "parties": ["sender_address", "receiver_address"]
            },
            "suspicious_activity": {
                "activity_type": "structuring",
                "description": "Multiple transactions just below reporting threshold",
                "risk_level": "high"
            },
            "subject_information": {
                "name": "John Doe",
                "address": "123 Main St",
                "identification": "ID123456"
            }
        }

    class TestReportCreation:
        """Test report creation functionality"""

        @pytest.mark.asyncio
        async def test_create_sar_report(self, engine, sample_report_data):
            """Test SAR report creation"""
            report = await engine.create_report(
                jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                report_type=ReportType.SAR,
                entity_id="entity_001",
                submitted_by="test_user",
                content=sample_report_data
            )

            assert report.report_id is not None
            assert report.jurisdiction == RegulatoryJurisdiction.USA_FINCEN
            assert report.report_type == ReportType.SAR
            assert report.entity_id == "entity_001"
            assert report.submitted_by == "test_user"
            assert report.status == ReportStatus.DRAFT
            assert report.content == sample_report_data
            assert report.created_at is not None

        @pytest.mark.asyncio
        async def test_create_ctr_report(self, engine):
            """Test CTR report creation"""
            report_data = {
                "transaction_details": {
                    "amount": 15000.00,
                    "currency": "USD",
                    "date": "2024-01-15"
                },
                "subject_information": {
                    "name": "Test Entity",
                    "account_number": "ACC123456"
                }
            }

            report = await engine.create_report(
                jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                report_type=ReportType.CTR,
                entity_id="entity_002",
                submitted_by="test_user",
                content=report_data
            )

            assert report.report_type == ReportType.CTR
            assert report.status == ReportStatus.DRAFT

        @pytest.mark.asyncio
        async def test_create_uk_fca_report(self, engine, sample_report_data):
            """Test UK FCA report creation"""
            report = await engine.create_report(
                jurisdiction=RegulatoryJurisdiction.UK_FCA,
                report_type=ReportType.SAR,
                entity_id="entity_003",
                submitted_by="test_user",
                content=sample_report_data
            )

            assert report.jurisdiction == RegulatoryJurisdiction.UK_FCA
            assert report.report_type == ReportType.SAR

        @pytest.mark.asyncio
        async def test_invalid_jurisdiction(self, engine, sample_report_data):
            """Test error handling for invalid jurisdiction"""
            with pytest.raises(ValueError):
                await engine.create_report(
                    jurisdiction="INVALID_JURISDICTION",
                    report_type=ReportType.SAR,
                    entity_id="entity_001",
                    submitted_by="test_user",
                    content=sample_report_data
                )

        @pytest.mark.asyncio
        async def test_missing_required_fields(self, engine):
            """Test error handling for missing required fields"""
            incomplete_data = {
                "transaction_details": {
                    "amount": 15000.00
                    # Missing required fields
                }
            }

            with pytest.raises(ValueError):
                await engine.create_report(
                    jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                    report_type=ReportType.SAR,
                    entity_id="entity_001",
                    submitted_by="test_user",
                    content=incomplete_data
                )

    class TestReportSubmission:
        """Test report submission functionality"""

        @pytest.mark.asyncio
        async def test_submit_report(self, engine, sample_report_data):
            """Test successful report submission"""
            # Create report first
            report = await engine.create_report(
                jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                report_type=ReportType.SAR,
                entity_id="entity_001",
                submitted_by="test_user",
                content=sample_report_data
            )

            # Submit report
            submitted_report = await engine.submit_report(report.report_id)

            assert submitted_report.status == ReportStatus.SUBMITTED
            assert submitted_report.submitted_at is not None
            assert submitted_report.submitted_by == "test_user"

        @pytest.mark.asyncio
        async def test_submit_nonexistent_report(self, engine):
            """Test error handling for nonexistent report"""
            with pytest.raises(ValueError):
                await engine.submit_report("nonexistent_report_id")

        @pytest.mark.asyncio
        async def test_submit_already_submitted_report(self, engine, sample_report_data):
            """Test error handling for already submitted report"""
            # Create and submit report
            report = await engine.create_report(
                jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                report_type=ReportType.SAR,
                entity_id="entity_001",
                submitted_by="test_user",
                content=sample_report_data
            )
            await engine.submit_report(report.report_id)

            # Try to submit again
            with pytest.raises(ValueError):
                await engine.submit_report(report.report_id)

    class TestReportStatusTracking:
        """Test report status tracking functionality"""

        @pytest.mark.asyncio
        async def test_check_report_status(self, engine, sample_report_data):
            """Test checking report status"""
            # Create report
            report = await engine.create_report(
                jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                report_type=ReportType.SAR,
                entity_id="entity_001",
                submitted_by="test_user",
                content=sample_report_data
            )

            # Check status
            status = await engine.check_report_status(report.report_id)
            assert status == ReportStatus.DRAFT

            # Submit report
            await engine.submit_report(report.report_id)

            # Check status again
            status = await engine.check_report_status(report.report_id)
            assert status == ReportStatus.SUBMITTED

        @pytest.mark.asyncio
        async def test_update_report_status(self, engine, sample_report_data):
            """Test updating report status"""
            # Create report
            report = await engine.create_report(
                jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                report_type=ReportType.SAR,
                entity_id="entity_001",
                submitted_by="test_user",
                content=sample_report_data
            )

            # Update status
            updated_report = await engine.update_report_status(
                report.report_id,
                ReportStatus.UNDER_REVIEW,
                updated_by="regulator"
            )

            assert updated_report.status == ReportStatus.UNDER_REVIEW
            assert updated_report.updated_at is not None

    class TestDeadlineTracking:
        """Test deadline tracking functionality"""

        @pytest.mark.asyncio
        async def test_get_upcoming_deadlines(self, engine, sample_report_data):
            """Test getting upcoming deadlines"""
            # Create report with deadline
            report = await engine.create_report(
                jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                report_type=ReportType.SAR,
                entity_id="entity_001",
                submitted_by="test_user",
                content=sample_report_data
            )

            # Get upcoming deadlines
            deadlines = await engine.get_upcoming_deadlines(hours_ahead=96)
            
            # Should include our report
            report_deadlines = [d for d in deadlines if d["report_id"] == report.report_id]
            assert len(report_deadlines) == 1
            assert report_deadlines[0]["deadline_hours"] == 72

        @pytest.mark.asyncio
        async def test_overdue_deadlines(self, engine, sample_report_data):
            """Test checking overdue deadlines"""
            # Create report
            report = await engine.create_report(
                jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                report_type=ReportType.SAR,
                entity_id="entity_001",
                submitted_by="test_user",
                content=sample_report_data
            )

            # Mock time to be after deadline
            with patch('src.compliance.regulatory_reporting.datetime') as mock_datetime:
                mock_datetime.utcnow.return_value = datetime.utcnow() + timedelta(hours=80)
                
                overdue = await engine.get_overdue_deadlines()
                report_overdue = [d for d in overdue if d["report_id"] == report.report_id]
                assert len(report_overdue) == 1

    class TestReportRetrieval:
        """Test report retrieval functionality"""

        @pytest.mark.asyncio
        async def test_get_report_by_id(self, engine, sample_report_data):
            """Test getting report by ID"""
            # Create report
            original_report = await engine.create_report(
                jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                report_type=ReportType.SAR,
                entity_id="entity_001",
                submitted_by="test_user",
                content=sample_report_data
            )

            # Retrieve report
            retrieved_report = await engine.get_report(original_report.report_id)

            assert retrieved_report.report_id == original_report.report_id
            assert retrieved_report.jurisdiction == original_report.jurisdiction
            assert retrieved_report.report_type == original_report.report_type
            assert retrieved_report.content == original_report.content

        @pytest.mark.asyncio
        async def test_get_nonexistent_report(self, engine):
            """Test getting nonexistent report"""
            report = await engine.get_report("nonexistent_report_id")
            assert report is None

        @pytest.mark.asyncio
        async def test_get_reports_by_jurisdiction(self, engine, sample_report_data):
            """Test getting reports by jurisdiction"""
            # Create reports for different jurisdictions
            us_report = await engine.create_report(
                jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                report_type=ReportType.SAR,
                entity_id="entity_001",
                submitted_by="test_user",
                content=sample_report_data
            )

            uk_report = await engine.create_report(
                jurisdiction=RegulatoryJurisdiction.UK_FCA,
                report_type=ReportType.SAR,
                entity_id="entity_002",
                submitted_by="test_user",
                content=sample_report_data
            )

            # Get US reports
            us_reports = await engine.get_reports_by_jurisdiction(RegulatoryJurisdiction.USA_FINCEN)
            us_report_ids = [r.report_id for r in us_reports]
            assert us_report.report_id in us_report_ids
            assert uk_report.report_id not in us_report_ids

        @pytest.mark.asyncio
        async def test_get_reports_by_status(self, engine, sample_report_data):
            """Test getting reports by status"""
            # Create reports
            draft_report = await engine.create_report(
                jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                report_type=ReportType.SAR,
                entity_id="entity_001",
                submitted_by="test_user",
                content=sample_report_data
            )

            submitted_report = await engine.create_report(
                jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                report_type=ReportType.CTR,
                entity_id="entity_002",
                submitted_by="test_user",
                content=sample_report_data
            )
            await engine.submit_report(submitted_report.report_id)

            # Get draft reports
            draft_reports = await engine.get_reports_by_status(ReportStatus.DRAFT)
            draft_report_ids = [r.report_id for r in draft_reports]
            assert draft_report.report_id in draft_report_ids
            assert submitted_report.report_id not in draft_report_ids

    class TestReportValidation:
        """Test report validation functionality"""

        @pytest.mark.asyncio
        async def test_validate_sar_report(self, engine, sample_report_data):
            """Test SAR report validation"""
            validation_result = await engine.validate_report(
                jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                report_type=ReportType.SAR,
                content=sample_report_data
            )

            assert validation_result["valid"] is True
            assert len(validation_result["errors"]) == 0
            assert len(validation_result["warnings"]) >= 0

        @pytest.mark.asyncio
        async def test_validate_invalid_report(self, engine):
            """Test invalid report validation"""
            invalid_data = {
                "transaction_details": {
                    "amount": 15000.00
                    # Missing required fields
                }
            }

            validation_result = await engine.validate_report(
                jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                report_type=ReportType.SAR,
                content=invalid_data
            )

            assert validation_result["valid"] is False
            assert len(validation_result["errors"]) > 0

    class TestMultiJurisdictionalSupport:
        """Test multi-jurisdictional support"""

        @pytest.mark.asyncio
        async def test_supported_jurisdictions(self, engine):
            """Test getting supported jurisdictions"""
            jurisdictions = await engine.get_supported_jurisdictions()
            
            expected_jurisdictions = [
                RegulatoryJurisdiction.USA_FINCEN,
                RegulatoryJurisdiction.UK_FCA,
                RegulatoryJurisdiction.SINGAPORE_MAS,
                RegulatoryJurisdiction.EU_AMLD
            ]
            
            for jur in expected_jurisdictions:
                assert jur in jurisdictions

        @pytest.mark.asyncio
        async def test_jurisdiction_specific_requirements(self, engine):
            """Test jurisdiction-specific requirements"""
            us_requirements = await engine.get_jurisdiction_requirements(RegulatoryJurisdiction.USA_FINCEN)
            assert len(us_requirements) > 0
            assert all(req.jurisdiction == RegulatoryJurisdiction.USA_FINCEN for req in us_requirements)

            uk_requirements = await engine.get_jurisdiction_requirements(RegulatoryJurisdiction.UK_FCA)
            assert len(uk_requirements) > 0
            assert all(req.jurisdiction == RegulatoryJurisdiction.UK_FCA for req in uk_requirements)

    class TestReportTemplates:
        """Test report template functionality"""

        @pytest.mark.asyncio
        async def test_get_report_template(self, engine):
            """Test getting report template"""
            template = await engine.get_report_template(
                jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                report_type=ReportType.SAR
            )

            assert "required_fields" in template
            assert "optional_fields" in template
            assert "validation_rules" in template
            assert len(template["required_fields"]) > 0

        @pytest.mark.asyncio
        async def test_generate_report_from_template(self, engine, sample_report_data):
            """Test generating report from template"""
            generated_report = await engine.generate_report_from_template(
                jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                report_type=ReportType.SAR,
                data=sample_report_data
            )

            assert "formatted_content" in generated_report
            assert "metadata" in generated_report
            assert generated_report["metadata"]["jurisdiction"] == RegulatoryJurisdiction.USA_FINCEN.value
            assert generated_report["metadata"]["report_type"] == ReportType.SAR.value

    class TestErrorHandling:
        """Test error handling scenarios"""

        @pytest.mark.asyncio
        async def test_database_connection_error(self, engine):
            """Test handling of database connection errors"""
            with patch.object(engine, 'neo4j_session', None):
                with pytest.raises(Exception):
                    await engine.create_report(
                        jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                        report_type=ReportType.SAR,
                        entity_id="entity_001",
                        submitted_by="test_user",
                        content={}
                    )

        @pytest.mark.asyncio
        async def test_api_timeout_error(self, engine, sample_report_data):
            """Test handling of API timeout errors"""
            # Mock API call to timeout
            with patch('aiohttp.ClientSession.post', side_effect=asyncio.TimeoutError()):
                report = await engine.create_report(
                    jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                    report_type=ReportType.SAR,
                    entity_id="entity_001",
                    submitted_by="test_user",
                    content=sample_report_data
                )
                
                # Should handle timeout gracefully
                assert report.status == ReportStatus.DRAFT

    class TestPerformance:
        """Test performance characteristics"""

        @pytest.mark.asyncio
        async def test_bulk_report_creation(self, engine, sample_report_data):
            """Test bulk report creation performance"""
            import time
            
            start_time = time.time()
            
            # Create 10 reports concurrently
            tasks = []
            for i in range(10):
                task = engine.create_report(
                    jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                    report_type=ReportType.SAR,
                    entity_id=f"entity_{i}",
                    submitted_by="test_user",
                    content=sample_report_data
                )
                tasks.append(task)
            
            reports = await asyncio.gather(*tasks)
            
            end_time = time.time()
            duration = end_time - start_time
            
            assert len(reports) == 10
            assert duration < 5.0  # Should complete within 5 seconds
            assert all(r.status == ReportStatus.DRAFT for r in reports)

        @pytest.mark.asyncio
        async def test_report_retrieval_performance(self, engine, sample_report_data):
            """Test report retrieval performance"""
            import time
            
            # Create test reports
            reports = []
            for i in range(5):
                report = await engine.create_report(
                    jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                    report_type=ReportType.SAR,
                    entity_id=f"entity_{i}",
                    submitted_by="test_user",
                    content=sample_report_data
                )
                reports.append(report)
            
            # Test retrieval performance
            start_time = time.time()
            
            tasks = []
            for report in reports:
                task = engine.get_report(report.report_id)
                tasks.append(task)
            
            retrieved_reports = await asyncio.gather(*tasks)
            
            end_time = time.time()
            duration = end_time - start_time
            
            assert len(retrieved_reports) == 5
            assert duration < 2.0  # Should complete within 2 seconds
            assert all(r is not None for r in retrieved_reports)
