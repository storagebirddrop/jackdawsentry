"""
Jackdaw Sentry - Victim Reports Unit Tests
Tests for victim reports database integration and management
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from src.intelligence.victim_reports import (
    VictimReportsDatabase,
    ReportType,
    ReportStatus,
    Severity,
    VictimReport,
    ReportStatistics,
)


class TestVictimReportsDatabase:
    """Test suite for VictimReportsDatabase"""

    @pytest.fixture
    def mock_db_pool(self):
        """Mock PostgreSQL connection pool"""
        return AsyncMock()

    @pytest.fixture
    def victim_reports_db(self, mock_db_pool):
        """Create VictimReportsDatabase instance with mocked dependencies"""
        with patch("src.intelligence.victim_reports.get_postgres_connection", return_value=mock_db_pool):
            return VictimReportsDatabase(mock_db_pool)

    # ---- Initialization Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_database_initializes(self, victim_reports_db, mock_db_pool):
        """Test database initialization creates required schema"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        await victim_reports_db.initialize()
        
        # Verify schema creation queries were executed
        assert mock_conn.execute.call_count >= 1
        mock_pool.acquire.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_database_shutdown(self, victim_reports_db):
        """Test database shutdown"""
        victim_reports_db.running = True
        await victim_reports_db.shutdown()
        assert victim_reports_db.running is False

    # ---- Report Creation Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_report_success(self, victim_reports_db, mock_db_pool):
        """Test successful report creation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {"id": str(uuid4())}
        
        report_data = {
            "report_type": "scam",
            "victim_contact": "victim@example.com",
            "incident_date": datetime.now(timezone.utc),
            "amount_lost": 1000.0,
            "currency": "BTC",
            "description": "Test scam report",
            "related_addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
            "severity": "high"
        }
        
        report = await victim_reports_db.create_report(report_data)
        
        assert isinstance(report, VictimReport)
        assert report.report_type == "scam"
        assert report.victim_contact == "victim@example.com"
        assert report.amount_lost == 1000.0
        assert report.status == "pending"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_report_invalid_data(self, victim_reports_db):
        """Test report creation with invalid data"""
        invalid_data = {
            "report_type": "invalid_type",  # Invalid enum value
            "victim_contact": "",  # Empty required field
            "incident_date": "not_a_datetime"  # Invalid date format
        }
        
        with pytest.raises(ValueError, match="Invalid report type"):
            await victim_reports_db.create_report(invalid_data)

    # ---- Report Retrieval Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_report_success(self, victim_reports_db, mock_db_pool):
        """Test successful report retrieval"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        report_id = str(uuid4())
        mock_row = {
            "id": report_id,
            "report_type": "fraud",
            "victim_contact": "victim@example.com",
            "incident_date": datetime.now(timezone.utc),
            "amount_lost": 500.0,
            "currency": "ETH",
            "description": "Test fraud report",
            "related_addresses": ["0x742d35Cc6634C0532925a3b844Bc454e4438f44e"],
            "severity": "medium",
            "status": "verified",
            "created_date": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc)
        }
        mock_conn.fetchrow.return_value = mock_row
        
        report = await victim_reports_db.get_report(report_id)
        
        assert report is not None
        assert report.id == report_id
        assert report.report_type == "fraud"
        assert report.status == "verified"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_report_not_found(self, victim_reports_db, mock_db_pool):
        """Test report retrieval when report doesn't exist"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        
        report = await victim_reports_db.get_report("nonexistent_id")
        assert report is None

    # ---- Report Update Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_report_success(self, victim_reports_db, mock_db_pool):
        """Test successful report update"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        report_id = str(uuid4())
        update_data = {
            "status": "verified",
            "notes": "Investigation completed"
        }
        
        mock_row = {
            "id": report_id,
            "report_type": "scam",
            "victim_contact": "victim@example.com",
            "status": "verified",
            "notes": "Investigation completed",
            "last_updated": datetime.now(timezone.utc)
        }
        mock_conn.fetchrow.return_value = mock_row
        
        updated_report = await victim_reports_db.update_report(report_id, update_data)
        
        assert updated_report.status == "verified"
        assert updated_report.notes == "Investigation completed"

    # ---- Report Deletion Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_report_success(self, victim_reports_db, mock_db_pool):
        """Test successful report deletion"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.execute.return_value = "DELETE 1"
        
        report_id = str(uuid4())
        result = await victim_reports_db.delete_report(report_id)
        
        assert result is True
        mock_conn.execute.assert_called_once()

    # ---- Search and Filter Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_by_address(self, victim_reports_db, mock_db_pool):
        """Test searching reports by blockchain address"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        mock_rows = [
            {
                "id": str(uuid4()),
                "report_type": "scam",
                "related_addresses": [address],
                "status": "verified"
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        reports = await victim_reports_db.search_by_address(address)
        
        assert len(reports) == 1
        assert address in reports[0].related_addresses

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_by_transaction(self, victim_reports_db, mock_db_pool):
        """Test searching reports by transaction hash"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        tx_hash = "a1b2c3d4e5f6789012345678901234567890abcdef"
        mock_rows = [
            {
                "id": str(uuid4()),
                "report_type": "theft",
                "related_transactions": [tx_hash],
                "status": "investigating"
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        reports = await victim_reports_db.search_by_transaction(tx_hash)
        
        assert len(reports) == 1
        assert tx_hash in reports[0].related_transactions

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_reports_with_filters(self, victim_reports_db, mock_db_pool):
        """Test getting reports with multiple filters"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        filters = {
            "status": "verified",
            "report_type": "scam",
            "severity": "high",
            "start_date": datetime.now(timezone.utc) - timedelta(days=30),
            "end_date": datetime.now(timezone.utc)
        }
        
        mock_rows = [
            {
                "id": str(uuid4()),
                "status": "verified",
                "report_type": "scam",
                "severity": "high",
                "created_date": datetime.now(timezone.utc) - timedelta(days=15)
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        reports = await victim_reports_db.get_reports(filters, limit=100, offset=0)
        
        assert len(reports) == 1
        assert reports[0].status == "verified"
        assert reports[0].report_type == "scam"
        assert reports[0].severity == "high"

    # ---- Statistics Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_statistics(self, victim_reports_db, mock_db_pool):
        """Test statistics calculation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Mock statistics query results
        mock_stats = {
            "total_reports": 150,
            "reports_by_status": {"pending": 50, "verified": 80, "false_positive": 20},
            "reports_by_type": {"scam": 60, "fraud": 40, "theft": 30, "phishing": 20},
            "reports_by_severity": {"low": 30, "medium": 60, "high": 40, "critical": 20},
            "total_amount_lost": 150000.0,
            "average_amount_lost": 1000.0,
            "verification_rate": 0.8
        }
        mock_conn.fetchrow.return_value = mock_stats
        
        stats = await victim_reports_db.get_statistics(start_date)
        
        assert isinstance(stats, ReportStatistics)
        assert stats.total_reports == 150
        assert stats.total_amount_lost == 150000.0
        assert stats.verification_rate == 0.8

    # ---- Verification Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_verify_report_success(self, victim_reports_db, mock_db_pool):
        """Test successful report verification"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        report_id = str(uuid4())
        verification_data = {
            "status": "verified",
            "verified_by": "analyst_123",
            "verification_date": datetime.now(timezone.utc),
            "notes": "Evidence verified"
        }
        
        mock_row = {
            "id": report_id,
            "status": "verified",
            "verified_by": "analyst_123",
            "verification_date": datetime.now(timezone.utc),
            "notes": "Evidence verified",
            "last_updated": datetime.now(timezone.utc)
        }
        mock_conn.fetchrow.return_value = mock_row
        
        verified_report = await victim_reports_db.verify_report(report_id, verification_data)
        
        assert verified_report.status == "verified"
        assert verified_report.verified_by == "analyst_123"
        assert verified_report.notes == "Evidence verified"

    # ---- Error Handling Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_database_connection_error(self, victim_reports_db, mock_db_pool):
        """Test handling of database connection errors"""
        mock_pool.acquire.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            await victim_reports_db.create_report({
                "report_type": "scam",
                "victim_contact": "test@example.com",
                "incident_date": datetime.now(timezone.utc),
                "description": "Test report"
            })

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_report_type_validation(self, victim_reports_db):
        """Test validation of invalid report types"""
        invalid_report_data = {
            "report_type": "nonexistent_type",
            "victim_contact": "test@example.com",
            "incident_date": datetime.now(timezone.utc),
            "description": "Test report"
        }
        
        with pytest.raises(ValueError, match="Invalid report type"):
            await victim_reports_db.create_report(invalid_report_data)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_required_fields_validation(self, victim_reports_db):
        """Test validation of empty required fields"""
        invalid_report_data = {
            "report_type": "scam",
            "victim_contact": "",  # Empty required field
            "incident_date": datetime.now(timezone.utc),
            "description": "Test report"
        }
        
        with pytest.raises(ValueError, match="Victim contact is required"):
            await victim_reports_db.create_report(invalid_report_data)


class TestVictimReportModel:
    """Test suite for VictimReport data model"""

    @pytest.mark.unit
    def test_victim_report_creation(self):
        """Test VictimReport model creation"""
        report_data = {
            "id": str(uuid4()),
            "report_type": "scam",
            "victim_contact": "victim@example.com",
            "incident_date": datetime.now(timezone.utc),
            "amount_lost": 1000.0,
            "currency": "BTC",
            "description": "Test scam report",
            "related_addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
            "related_transactions": ["a1b2c3d4e5f6789012345678901234567890abcdef"],
            "evidence_files": ["evidence1.pdf", "evidence2.jpg"],
            "severity": "high",
            "status": "pending",
            "created_date": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc)
        }
        
        report = VictimReport(**report_data)
        
        assert report.id == report_data["id"]
        assert report.report_type == ReportType.SCAM
        assert report.victim_contact == "victim@example.com"
        assert report.amount_lost == 1000.0
        assert report.currency == "BTC"
        assert report.severity == Severity.HIGH
        assert report.status == ReportStatus.PENDING
        assert len(report.related_addresses) == 1
        assert len(report.related_transactions) == 1
        assert len(report.evidence_files) == 2

    @pytest.mark.unit
    def test_victim_report_optional_fields(self):
        """Test VictimReport with optional fields"""
        report_data = {
            "id": str(uuid4()),
            "report_type": "fraud",
            "victim_contact": "victim@example.com",
            "incident_date": datetime.now(timezone.utc),
            "description": "Test fraud report",
            "status": "investigating",
            "created_date": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc)
        }
        
        report = VictimReport(**report_data)
        
        assert report.amount_lost is None
        assert report.currency is None
        assert report.related_addresses == []
        assert report.related_transactions == []
        assert report.evidence_files == []
        assert report.severity == Severity.MEDIUM  # Default value

    @pytest.mark.unit
    def test_victim_report_enum_validation(self):
        """Test enum validation in VictimReport"""
        with pytest.raises(ValueError):
            VictimReport(
                id=str(uuid4()),
                report_type="invalid_type",  # Invalid enum
                victim_contact="test@example.com",
                incident_date=datetime.now(timezone.utc),
                description="Test",
                status="pending",
                created_date=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc)
            )


class TestReportStatisticsModel:
    """Test suite for ReportStatistics data model"""

    @pytest.mark.unit
    def test_report_statistics_creation(self):
        """Test ReportStatistics model creation"""
        stats_data = {
            "total_reports": 100,
            "reports_by_status": {"pending": 30, "verified": 50, "false_positive": 20},
            "reports_by_type": {"scam": 40, "fraud": 30, "theft": 20, "phishing": 10},
            "reports_by_severity": {"low": 20, "medium": 40, "high": 30, "critical": 10},
            "reports_by_timeframe": {"last_24h": 5, "last_7d": 25, "last_30d": 70},
            "total_amount_lost": 50000.0,
            "average_amount_lost": 500.0,
            "verification_rate": 0.85
        }
        
        stats = ReportStatistics(**stats_data)
        
        assert stats.total_reports == 100
        assert stats.reports_by_status["verified"] == 50
        assert stats.reports_by_type["scam"] == 40
        assert stats.reports_by_severity["high"] == 30
        assert stats.total_amount_lost == 50000.0
        assert stats.average_amount_lost == 500.0
        assert stats.verification_rate == 0.85

    @pytest.mark.unit
    def test_report_statistics_calculated_fields(self):
        """Test calculated fields in ReportStatistics"""
        stats = ReportStatistics(
            total_reports=200,
            verified_reports=150,
            total_amount_lost=100000.0
        )
        
        # Test calculated verification rate
        expected_rate = 150 / 200  # 0.75
        assert abs(stats.verification_rate - expected_rate) < 0.001
        
        # Test calculated average amount
        expected_avg = 100000.0 / 200  # 500.0
        assert abs(stats.average_amount_lost - expected_avg) < 0.001
