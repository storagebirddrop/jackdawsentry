"""
Jackdaw Sentry - Forensic Engine Unit Tests
Tests for forensic case management and analysis
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from src.forensics.forensic_engine import (
    ForensicEngine,
    ForensicCaseStatus,
    EvidenceType,
    EvidenceIntegrity,
    ForensicCase,
    CaseStatistics,
)


class TestForensicEngine:
    """Test suite for ForensicEngine"""

    @pytest.fixture
    def mock_db_pool(self):
        """Mock PostgreSQL connection pool"""
        return AsyncMock()

    @pytest.fixture
    def forensic_engine(self, mock_db_pool):
        """Create ForensicEngine instance with mocked dependencies"""
        with patch("src.forensics.forensic_engine.get_postgres_connection", return_value=mock_db_pool):
            return ForensicEngine(mock_db_pool)

    # ---- Initialization Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_engine_initializes(self, forensic_engine, mock_db_pool):
        """Test engine initialization creates required schema"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        await forensic_engine.initialize()
        
        # Verify schema creation queries were executed
        assert mock_conn.execute.call_count >= 1
        mock_pool.acquire.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_engine_shutdown(self, forensic_engine):
        """Test engine shutdown"""
        forensic_engine.running = True
        await forensic_engine.shutdown()
        assert forensic_engine.running is False

    # ---- Case Creation Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_case_success(self, forensic_engine, mock_db_pool):
        """Test successful case creation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {"id": str(uuid4())}
        
        case_data = {
            "title": "Bitcoin Fraud Investigation",
            "description": "Investigation of cryptocurrency fraud involving Bitcoin",
            "case_type": "cryptocurrency_fraud",
            "priority": "high",
            "assigned_investigator": "investigator_123",
            "jurisdiction": "federal_us",
            "legal_standard": "preponderance",
            "related_cases": [],
            "tags": ["bitcoin", "fraud", "cryptocurrency"],
            "estimated_completion_date": datetime.now(timezone.utc) + timedelta(days=30)
        }
        
        case = await forensic_engine.create_case(case_data)
        
        assert isinstance(case, ForensicCase)
        assert case.title == "Bitcoin Fraud Investigation"
        assert case.case_type == "cryptocurrency_fraud"
        assert case.priority == "high"
        assert case.status == ForensicCaseStatus.OPEN
        assert case.assigned_investigator == "investigator_123"
        assert case.jurisdiction == "federal_us"
        assert case.legal_standard == "preponderance"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_case_invalid_data(self, forensic_engine):
        """Test case creation with invalid data"""
        invalid_data = {
            "title": "",  # Empty required field
            "description": "Test case",
            "case_type": "invalid_type",  # Invalid enum value
            "priority": "invalid_priority",  # Invalid priority
            "legal_standard": "invalid_standard"  # Invalid legal standard
        }
        
        with pytest.raises(ValueError, match="Title is required"):
            await forensic_engine.create_case(invalid_data)

    # ---- Case Retrieval Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_case_success(self, forensic_engine, mock_db_pool):
        """Test successful case retrieval"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        case_id = str(uuid4())
        mock_row = {
            "id": case_id,
            "title": "Ethereum Smart Contract Hack",
            "description": "Investigation of smart contract vulnerability exploitation",
            "case_type": "smart_contract_hack",
            "status": "in_progress",
            "priority": "critical",
            "assigned_investigator": "investigator_456",
            "jurisdiction": "state_california",
            "legal_standard": "clear_and_convincing",
            "related_cases": [],
            "tags": ["ethereum", "smart_contract", "hack"],
            "evidence_count": 15,
            "created_date": datetime.now(timezone.utc) - timedelta(days=10),
            "last_updated": datetime.now(timezone.utc) - timedelta(days=2),
            "estimated_completion_date": datetime.now(timezone.utc) + timedelta(days=20),
            "actual_completion_date": None,
            "notes": "Complex case involving DeFi protocol"
        }
        mock_conn.fetchrow.return_value = mock_row
        
        case = await forensic_engine.get_case(case_id)
        
        assert case is not None
        assert case.id == case_id
        assert case.title == "Ethereum Smart Contract Hack"
        assert case.status == ForensicCaseStatus.IN_PROGRESS
        assert case.priority == "critical"
        assert case.evidence_count == 15

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_case_not_found(self, forensic_engine, mock_db_pool):
        """Test case retrieval when case doesn't exist"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        
        case = await forensic_engine.get_case("nonexistent_id")
        assert case is None

    # ---- Case Update Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_case_success(self, forensic_engine, mock_db_pool):
        """Test successful case update"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        case_id = str(uuid4())
        update_data = {
            "status": "analysis",
            "priority": "medium",
            "notes": "Case progressing well, key evidence collected",
            "estimated_completion_date": datetime.now(timezone.utc) + timedelta(days=15)
        }
        
        mock_row = {
            "id": case_id,
            "status": "analysis",
            "priority": "medium",
            "notes": "Case progressing well, key evidence collected",
            "estimated_completion_date": datetime.now(timezone.utc) + timedelta(days=15),
            "last_updated": datetime.now(timezone.utc)
        }
        mock_conn.fetchrow.return_value = mock_row
        
        updated_case = await forensic_engine.update_case(case_id, update_data)
        
        assert updated_case.status == ForensicCaseStatus.ANALYSIS
        assert updated_case.priority == "medium"
        assert updated_case.notes == "Case progressing well, key evidence collected"

    # ---- Case List Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_cases_with_filters(self, forensic_engine, mock_db_pool):
        """Test getting cases with multiple filters"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        filters = {
            "status": "in_progress",
            "priority": "high",
            "assigned_investigator": "investigator_123",
            "jurisdiction": "federal_us"
        }
        
        mock_rows = [
            {
                "id": str(uuid4()),
                "title": "Case 1",
                "status": "in_progress",
                "priority": "high",
                "assigned_investigator": "investigator_123",
                "jurisdiction": "federal_us",
                "created_date": datetime.now(timezone.utc) - timedelta(days=5),
                "evidence_count": 10
            },
            {
                "id": str(uuid4()),
                "title": "Case 2",
                "status": "in_progress",
                "priority": "high",
                "assigned_investigator": "investigator_123",
                "jurisdiction": "federal_us",
                "created_date": datetime.now(timezone.utc) - timedelta(days=3),
                "evidence_count": 8
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        cases = await forensic_engine.get_cases(filters, limit=100, offset=0)
        
        assert len(cases) == 2
        for case in cases:
            assert case.status == ForensicCaseStatus.IN_PROGRESS
            assert case.priority == "high"
            assert case.assigned_investigator == "investigator_123"
            assert case.jurisdiction == "federal_us"

    # ---- Evidence Count Management Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_increment_evidence_count(self, forensic_engine, mock_db_pool):
        """Test incrementing evidence count for a case"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        case_id = str(uuid4())
        
        # Mock current case with evidence count
        mock_conn.fetchrow.return_value = {
            "id": case_id,
            "evidence_count": 5
        }
        
        # Mock update result
        mock_conn.execute.return_value = "UPDATE 1"
        
        result = await forensic_engine.increment_evidence_count(case_id)
        
        assert result is True
        mock_conn.execute.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_decrement_evidence_count(self, forensic_engine, mock_db_pool):
        """Test decrementing evidence count for a case"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        case_id = str(uuid4())
        
        # Mock current case with evidence count
        mock_conn.fetchrow.return_value = {
            "id": case_id,
            "evidence_count": 10
        }
        
        # Mock update result
        mock_conn.execute.return_value = "UPDATE 1"
        
        result = await forensic_engine.decrement_evidence_count(case_id)
        
        assert result is True
        mock_conn.execute.assert_called_once()

    # ---- Statistics Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_statistics(self, forensic_engine, mock_db_pool):
        """Test statistics calculation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        days = 30
        
        # Mock statistics query results
        mock_stats = {
            "total_cases": 50,
            "cases_by_status": {
                ForensicCaseStatus.OPEN.value: 10,
                ForensicCaseStatus.IN_PROGRESS.value: 20,
                ForensicCaseStatus.EVIDENCE_COLLECTION.value: 8,
                ForensicCaseStatus.ANALYSIS.value: 7,
                ForensicCaseStatus.REVIEW.value: 3,
                ForensicCaseStatus.CLOSED.value: 2
            },
            "cases_by_priority": {
                "low": 5,
                "medium": 20,
                "high": 20,
                "critical": 5
            },
            "cases_by_type": {
                "cryptocurrency_fraud": 15,
                "smart_contract_hack": 10,
                "money_laundering": 12,
                "terrorism_financing": 8,
                "other": 5
            },
            "average_case_duration_days": 25.5,
            "total_evidence_items": 750,
            "cases_with_court_preparation": 8,
            "completion_rate": 0.85
        }
        mock_conn.fetchrow.return_value = mock_stats
        
        stats = await forensic_engine.get_statistics(days)
        
        assert isinstance(stats, CaseStatistics)
        assert stats.total_cases == 50
        assert stats.average_case_duration_days == 25.5
        assert stats.total_evidence_items == 750
        assert stats.completion_rate == 0.85

    # ---- Case Search Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_cases_by_title(self, forensic_engine, mock_db_pool):
        """Test searching cases by title"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        search_term = "bitcoin"
        
        mock_rows = [
            {
                "id": str(uuid4()),
                "title": "Bitcoin Fraud Investigation",
                "description": "Investigation of Bitcoin-related fraud",
                "status": "in_progress",
                "created_date": datetime.now(timezone.utc) - timedelta(days=5)
            },
            {
                "id": str(uuid4()),
                "title": "Bitcoin Money Laundering Case",
                "description": "Money laundering using Bitcoin",
                "status": "evidence_collection",
                "created_date": datetime.now(timezone.utc) - timedelta(days=3)
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        cases = await forensic_engine.search_cases("title", search_term, limit=50)
        
        assert len(cases) == 2
        for case in cases:
            assert "bitcoin" in case.title.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_cases_by_tags(self, forensic_engine, mock_db_pool):
        """Test searching cases by tags"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        search_term = "cryptocurrency"
        
        mock_rows = [
            {
                "id": str(uuid4()),
                "title": "Crypto Fraud Case",
                "tags": ["cryptocurrency", "fraud", "bitcoin"],
                "status": "in_progress",
                "created_date": datetime.now(timezone.utc) - timedelta(days=7)
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        cases = await forensic_engine.search_cases("tags", search_term, limit=50)
        
        assert len(cases) == 1
        assert "cryptocurrency" in cases[0].tags

    # ---- Case Lifecycle Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_case_lifecycle_transitions(self, forensic_engine, mock_db_pool):
        """Test case status transitions through lifecycle"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        case_id = str(uuid4())
        
        # Create case
        case_data = {
            "title": "Test Case",
            "description": "Test description",
            "case_type": "test_type",
            "priority": "medium"
        }
        
        mock_conn.fetchrow.return_value = {"id": case_id}
        case = await forensic_engine.create_case(case_data)
        assert case.status == ForensicCaseStatus.OPEN
        
        # Transition to evidence collection
        update_data = {"status": "evidence_collection"}
        mock_conn.fetchrow.return_value = {
            "id": case_id,
            "status": "evidence_collection",
            "last_updated": datetime.now(timezone.utc)
        }
        
        updated_case = await forensic_engine.update_case(case_id, update_data)
        assert updated_case.status == ForensicCaseStatus.EVIDENCE_COLLECTION
        
        # Transition to analysis
        update_data = {"status": "analysis"}
        mock_conn.fetchrow.return_value = {
            "id": case_id,
            "status": "analysis",
            "last_updated": datetime.now(timezone.utc)
        }
        
        updated_case = await forensic_engine.update_case(case_id, update_data)
        assert updated_case.status == ForensicCaseStatus.ANALYSIS
        
        # Transition to review
        update_data = {"status": "review"}
        mock_conn.fetchrow.return_value = {
            "id": case_id,
            "status": "review",
            "last_updated": datetime.now(timezone.utc)
        }
        
        updated_case = await forensic_engine.update_case(case_id, update_data)
        assert updated_case.status == ForensicCaseStatus.REVIEW
        
        # Transition to closed
        update_data = {"status": "closed"}
        mock_conn.fetchrow.return_value = {
            "id": case_id,
            "status": "closed",
            "last_updated": datetime.now(timezone.utc),
            "actual_completion_date": datetime.now(timezone.utc)
        }
        
        updated_case = await forensic_engine.update_case(case_id, update_data)
        assert updated_case.status == ForensicCaseStatus.CLOSED
        assert updated_case.actual_completion_date is not None

    # ---- Error Handling Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_database_connection_error(self, forensic_engine, mock_db_pool):
        """Test handling of database connection errors"""
        mock_pool.acquire.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            await forensic_engine.create_case({
                "title": "Test Case",
                "description": "Test description",
                "case_type": "test_type"
            })

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_case_status_validation(self, forensic_engine):
        """Test validation of invalid case status"""
        invalid_update_data = {
            "status": "invalid_status"  # Invalid enum value
        }
        
        with pytest.raises(ValueError, match="Invalid status"):
            await forensic_engine.update_case("case_id", invalid_update_data)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_priority_validation(self, forensic_engine):
        """Test validation of invalid priority"""
        invalid_case_data = {
            "title": "Test Case",
            "description": "Test description",
            "case_type": "test_type",
            "priority": "invalid_priority"  # Invalid enum value
        }
        
        with pytest.raises(ValueError, match="Invalid priority"):
            await forensic_engine.create_case(invalid_case_data)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_legal_standard_validation(self, forensic_engine):
        """Test validation of invalid legal standard"""
        invalid_case_data = {
            "title": "Test Case",
            "description": "Test description",
            "case_type": "test_type",
            "legal_standard": "invalid_standard"  # Invalid enum value
        }
        
        with pytest.raises(ValueError, match="Invalid legal standard"):
            await forensic_engine.create_case(invalid_case_data)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_case_not_found_error(self, forensic_engine, mock_db_pool):
        """Test handling of case not found error"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        
        update_data = {"status": "analysis"}
        
        with pytest.raises(ValueError, match="Case not found"):
            await forensic_engine.update_case("nonexistent_id", update_data)


class TestForensicCaseModel:
    """Test suite for ForensicCase data model"""

    @pytest.mark.unit
    def test_forensic_case_creation(self):
        """Test ForensicCase model creation"""
        case_data = {
            "id": str(uuid4()),
            "title": "Major Cryptocurrency Investigation",
            "description": "Comprehensive investigation of major cryptocurrency fraud scheme",
            "case_type": "cryptocurrency_fraud",
            "status": "in_progress",
            "priority": "critical",
            "assigned_investigator": "lead_investigator_123",
            "jurisdiction": "federal_us",
            "legal_standard": "beyond_reasonable_doubt",
            "related_cases": ["case_456", "case_789"],
            "tags": ["cryptocurrency", "fraud", "bitcoin", "ethereum"],
            "evidence_count": 25,
            "created_date": datetime.now(timezone.utc) - timedelta(days=15),
            "last_updated": datetime.now(timezone.utc) - timedelta(days=2),
            "estimated_completion_date": datetime.now(timezone.utc) + timedelta(days=45),
            "actual_completion_date": None,
            "notes": "Complex multi-jurisdictional case"
        }
        
        case = ForensicCase(**case_data)
        
        assert case.id == case_data["id"]
        assert case.title == "Major Cryptocurrency Investigation"
        assert case.case_type == "cryptocurrency_fraud"
        assert case.status == ForensicCaseStatus.IN_PROGRESS
        assert case.priority == "critical"
        assert case.assigned_investigator == "lead_investigator_123"
        assert case.jurisdiction == "federal_us"
        assert case.legal_standard == "beyond_reasonable_doubt"
        assert case.evidence_count == 25
        assert len(case.related_cases) == 2
        assert len(case.tags) == 4

    @pytest.mark.unit
    def test_forensic_case_optional_fields(self):
        """Test ForensicCase with optional fields"""
        case_data = {
            "id": str(uuid4()),
            "title": "Simple Case",
            "description": "Simple investigation case",
            "case_type": "simple_type",
            "status": "open",
            "priority": "medium",
            "jurisdiction": "state_default",
            "legal_standard": "preponderance",
            "related_cases": [],
            "tags": [],
            "evidence_count": 0,
            "created_date": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc)
        }
        
        case = ForensicCase(**case_data)
        
        assert case.assigned_investigator is None
        assert case.estimated_completion_date is None
        assert case.actual_completion_date is None
        assert case.notes is None

    @pytest.mark.unit
    def test_forensic_case_enum_validation(self):
        """Test enum validation in ForensicCase"""
        with pytest.raises(ValueError):
            ForensicCase(
                id=str(uuid4()),
                title="Test Case",
                description="Test description",
                case_type="test_type",
                status="invalid_status",  # Invalid enum
                priority="medium",
                jurisdiction="state_default",
                legal_standard="preponderance",
                related_cases=[],
                tags=[],
                evidence_count=0,
                created_date=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc)
            )


class TestCaseStatisticsModel:
    """Test suite for CaseStatistics data model"""

    @pytest.mark.unit
    def test_case_statistics_creation(self):
        """Test CaseStatistics model creation"""
        stats_data = {
            "total_cases": 100,
            "cases_by_status": {
                ForensicCaseStatus.OPEN.value: 15,
                ForensicCaseStatus.IN_PROGRESS.value: 35,
                ForensicCaseStatus.EVIDENCE_COLLECTION.value: 20,
                ForensicCaseStatus.ANALYSIS.value: 15,
                ForensicCaseStatus.REVIEW.value: 10,
                ForensicCaseStatus.CLOSED.value: 5
            },
            "cases_by_priority": {
                "low": 10,
                "medium": 50,
                "high": 30,
                "critical": 10
            },
            "cases_by_type": {
                "cryptocurrency_fraud": 30,
                "smart_contract_hack": 25,
                "money_laundering": 20,
                "terrorism_financing": 15,
                "other": 10
            },
            "average_case_duration_days": 22.5,
            "total_evidence_items": 1500,
            "cases_with_court_preparation": 12,
            "completion_rate": 0.88
        }
        
        stats = CaseStatistics(**stats_data)
        
        assert stats.total_cases == 100
        assert stats.cases_by_status[ForensicCaseStatus.IN_PROGRESS.value] == 35
        assert stats.cases_by_priority["high"] == 30
        assert stats.cases_by_type["cryptocurrency_fraud"] == 30
        assert stats.average_case_duration_days == 22.5
        assert stats.total_evidence_items == 1500
        assert stats.cases_with_court_preparation == 12
        assert stats.completion_rate == 0.88

    @pytest.mark.unit
    def test_case_statistics_calculated_fields(self):
        """Test calculated fields in CaseStatistics"""
        stats = CaseStatistics(
            total_cases=200,
            completed_cases=170,
            total_evidence_items=2000,
            total_case_duration_days=4000
        )
        
        # Test calculated completion rate
        expected_rate = 170 / 200  # 0.85
        assert abs(stats.completion_rate - expected_rate) < 0.001
        
        # Test calculated average duration
        expected_avg = 4000 / 200  # 20.0
        assert abs(stats.average_case_duration_days - expected_avg) < 0.001
