"""
Regulatory Reporting Engine Tests — rewritten to match actual RegulatoryReportingEngine API.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.compliance.regulatory_reporting import (
    RegulatoryReportingEngine,
    RegulatoryJurisdiction,
    ReportType,
    ReportStatus,
    RegulatoryRequirement,
    RegulatoryReport,
)


class TestRegulatoryReportingEngine:
    """Test suite for RegulatoryReportingEngine"""

    @pytest.fixture
    def engine(self):
        return RegulatoryReportingEngine()

    # ---- Initialization ----

    def test_engine_initializes(self, engine):
        assert isinstance(engine.requirements_cache, dict)
        assert isinstance(engine.report_templates, dict)
        assert engine.cache_ttl == 3600

    def test_requirements_populated(self, engine):
        assert RegulatoryJurisdiction.USA_FINCEN in engine.requirements_cache
        assert RegulatoryJurisdiction.UK_FCA in engine.requirements_cache

    def test_report_templates_populated(self, engine):
        assert len(engine.report_templates) > 0

    # ---- Enum values ----

    def test_jurisdiction_values(self):
        assert RegulatoryJurisdiction.USA_FINCEN.value == "usa_fincen"
        assert RegulatoryJurisdiction.EU_AML.value == "eu_aml"
        assert RegulatoryJurisdiction.UK_FCA.value == "uk_fca"

    def test_report_type_values(self):
        assert ReportType.SAR.value == "sar"
        assert ReportType.CTR.value == "ctr"
        assert ReportType.AML.value == "aml"

    def test_report_status_values(self):
        assert ReportStatus.DRAFT.value == "draft"
        assert ReportStatus.SUBMITTED.value == "submitted"
        assert ReportStatus.ACKNOWLEDGED.value == "acknowledged"

    # ---- create_regulatory_report (mocked DB) ----

    @pytest.mark.asyncio
    async def test_create_regulatory_report_returns_report(self, engine):
        with patch.object(engine, '_store_report', new_callable=AsyncMock):
            with patch.object(engine, '_validate_report_data', new_callable=AsyncMock, return_value={'valid': True}):
                report = await engine.create_regulatory_report(
                    jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                    report_type=ReportType.SAR,
                    case_id="case_123",
                    triggered_by="0xabc123",
                    report_data={"suspicious_activity_details": "test", "transaction_amount": 50000,
                                 "date_range": "2024-01", "involved_parties": ["A"], "suspicion_reasons": ["pattern"]},
                )
                assert isinstance(report, RegulatoryReport)
                assert report.jurisdiction == RegulatoryJurisdiction.USA_FINCEN
                assert report.report_type == ReportType.SAR
                assert report.status == ReportStatus.DRAFT
                assert report.case_id == "case_123"

    @pytest.mark.asyncio
    async def test_create_report_stores_to_db(self, engine):
        mock_store = AsyncMock()
        with patch.object(engine, '_store_report', mock_store):
            with patch.object(engine, '_validate_report_data', new_callable=AsyncMock, return_value={'valid': True}):
                await engine.create_regulatory_report(
                    jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
                    report_type=ReportType.SAR,
                    case_id="case_456",
                    triggered_by="0xdef",
                    report_data={"suspicious_activity_details": "t", "transaction_amount": 1,
                                 "date_range": "d", "involved_parties": ["B"], "suspicion_reasons": ["r"]},
                )
                mock_store.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("jurisdiction", [RegulatoryJurisdiction.USA_FINCEN, RegulatoryJurisdiction.UK_FCA])
    async def test_create_report_with_different_jurisdictions(self, engine, jurisdiction):
        with patch.object(engine, '_store_report', new_callable=AsyncMock):
            with patch.object(engine, '_validate_report_data', new_callable=AsyncMock, return_value={'valid': True}):
                report = await engine.create_regulatory_report(
                    jurisdiction=jurisdiction,
                    report_type=ReportType.SAR,
                    case_id="case_789",
                    triggered_by="0x123",
                    report_data={"suspicious_activity_details": "t", "transaction_amount": 1,
                                 "date_range": "d", "involved_parties": ["C"], "suspicion_reasons": ["r"]},
                )
                assert report.jurisdiction == jurisdiction

    # ---- submit_report (mocked DB) ----

    @pytest.mark.asyncio
    async def test_submit_report_success(self, engine):
        now = datetime.now(timezone.utc)
        mock_report = RegulatoryReport(
            report_id="report_123",
            jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
            report_type=ReportType.SAR,
            status=ReportStatus.DRAFT,
            case_id="case_123",
            triggered_by="0xabc",
            filing_deadline=now + timedelta(days=30),
            submission_deadline=now + timedelta(days=31),
            report_data={"subject": "test"},
        )
        with patch.object(engine, '_get_report', new_callable=AsyncMock, return_value=mock_report):
            with patch.object(engine, '_submit_to_regulatory_body', new_callable=AsyncMock,
                              return_value={"success": True, "reference_number": "REF001"}):
                with patch.object(engine, '_store_report', new_callable=AsyncMock):
                    result = await engine.submit_report("report_123", "analyst_1")
                    assert isinstance(result, dict)
                    assert result.get('success') is True

    @pytest.mark.asyncio
    async def test_submit_nonexistent_report(self, engine):
        with patch.object(engine, '_get_report', new_callable=AsyncMock, return_value=None):
            result = await engine.submit_report("nonexistent", "analyst_1")
            assert result.get('success') is False

    # ---- check_report_status (mocked DB) ----

    @pytest.mark.asyncio
    async def test_check_report_status_success(self, engine):
        now = datetime.now(timezone.utc)
        mock_report = RegulatoryReport(
            report_id="report_123",
            jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
            report_type=ReportType.SAR,
            status=ReportStatus.SUBMITTED,
            case_id="case_123",
            triggered_by="0xabc",
            filing_deadline=now + timedelta(days=30),
            submission_deadline=now + timedelta(days=31),
            report_data={},
            external_reference="REF001",
        )
        with patch.object(engine, '_get_report', new_callable=AsyncMock, return_value=mock_report) as mock_get:
            with patch.object(engine, '_check_regulatory_status', new_callable=AsyncMock,
                              return_value={"success": True, "status": "acknowledged"}) as mock_check:
                with patch.object(engine, '_store_report', new_callable=AsyncMock) as mock_store:
                    result = await engine.check_report_status("report_123")
                    assert isinstance(result, dict)
                    assert result.get("status") == "acknowledged"
                    mock_get.assert_awaited_once_with("report_123")
                    mock_check.assert_awaited_once()
                    mock_store.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_check_status_nonexistent(self, engine):
        with patch.object(engine, '_get_report', new_callable=AsyncMock, return_value=None):
            result = await engine.check_report_status("nonexistent")
            # Engine returns error dict, not a 'success' key
            assert 'error' in result

    # ---- get_upcoming_deadlines (mocked DB) ----

    @pytest.mark.asyncio
    async def test_get_upcoming_deadlines(self, engine):
        result = await engine.get_upcoming_deadlines(days_ahead=30)
        assert isinstance(result, list)

    # ---- helper methods ----

    def test_get_regulatory_requirement(self, engine):
        req = engine._get_regulatory_requirement(
            RegulatoryJurisdiction.USA_FINCEN,
            ReportType.SAR,
        )
        assert req is not None
        assert isinstance(req, RegulatoryRequirement)

    # ---- RegulatoryReport dataclass ----

    def test_report_dataclass(self):
        now = datetime.now(timezone.utc)
        report = RegulatoryReport(
            report_id="r1",
            jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
            report_type=ReportType.SAR,
            status=ReportStatus.DRAFT,
            case_id="c1",
            triggered_by="0xabc",
            filing_deadline=now + timedelta(days=30),
            submission_deadline=now + timedelta(days=31),
            report_data={"test": True},
        )
        assert report.report_id == "r1"
        assert report.completed_at is None

    # ---- RegulatoryRequirement dataclass ----

    def test_requirement_dataclass(self):
        req = RegulatoryRequirement(
            jurisdiction=RegulatoryJurisdiction.USA_FINCEN,
            report_type=ReportType.SAR,
            filing_deadline=timedelta(days=30),
        )
        assert req.jurisdiction == RegulatoryJurisdiction.USA_FINCEN
