"""
Jackdaw Sentry - Threat Feeds Unit Tests
Tests for threat intelligence feeds ingestion and management
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
import json

from src.intelligence.threat_feeds import (
    ThreatIntelligenceManager,
    ThreatLevel,
    ThreatType,
    FeedStatus,
    ThreatFeed,
    ThreatIntelligenceItem,
    FeedHealthStatus,
    FeedStatistics,
)


class TestThreatIntelligenceManager:
    """Test suite for ThreatIntelligenceManager"""

    @pytest.fixture
    def mock_db_pool(self):
        """Mock PostgreSQL connection pool"""
        return AsyncMock()

    @pytest.fixture
    def threat_manager(self, mock_db_pool):
        """Create ThreatIntelligenceManager instance with mocked dependencies"""
        with patch("src.intelligence.threat_feeds.get_postgres_connection", return_value=mock_db_pool):
            return ThreatIntelligenceManager(mock_db_pool)

    # ---- Initialization Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_manager_initializes(self, threat_manager, mock_db_pool):
        """Test manager initialization creates required schema"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        await threat_manager.initialize()
        
        # Verify schema creation queries were executed
        assert mock_conn.execute.call_count >= 1
        mock_pool.acquire.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_manager_shutdown(self, threat_manager):
        """Test manager shutdown"""
        threat_manager.running = True
        await threat_manager.shutdown()
        assert threat_manager.running is False

    # ---- Feed Creation Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_feed_success(self, threat_manager, mock_db_pool):
        """Test successful feed creation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {"id": str(uuid4())}
        
        feed_data = {
            "name": "Test Threat Feed",
            "feed_type": "sanctions",
            "source_url": "https://example.com/threat-feed.json",
            "api_key": "test_api_key",
            "sync_interval_minutes": 60,
            "enabled": True,
            "config": {"format": "json", "auth_type": "api_key"},
            "description": "Test threat intelligence feed"
        }
        
        feed = await threat_manager.create_feed(feed_data)
        
        assert isinstance(feed, ThreatFeed)
        assert feed.name == "Test Threat Feed"
        assert feed.feed_type == ThreatType.SANCTIONS
        assert feed.source_url == "https://example.com/threat-feed.json"
        assert feed.enabled is True
        assert feed.status == FeedStatus.INACTIVE

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_feed_invalid_data(self, threat_manager):
        """Test feed creation with invalid data"""
        invalid_data = {
            "name": "Test Feed",
            "feed_type": "invalid_type",  # Invalid enum value
            "source_url": "not_a_url",  # Invalid URL format
            "sync_interval_minutes": 1  # Too short interval
        }
        
        with pytest.raises(ValueError, match="Invalid feed type"):
            await threat_manager.create_feed(invalid_data)

    # ---- Feed Retrieval Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_feed_success(self, threat_manager, mock_db_pool):
        """Test successful feed retrieval"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        feed_id = str(uuid4())
        mock_row = {
            "id": feed_id,
            "name": "Test Feed",
            "feed_type": "scam",
            "source_url": "https://example.com/feed.json",
            "enabled": True,
            "status": "active",
            "sync_interval_minutes": 60,
            "last_sync": datetime.now(timezone.utc),
            "next_sync": datetime.now(timezone.utc) + timedelta(minutes=60),
            "total_items": 150,
            "error_count": 0,
            "config": {"format": "json"},
            "description": "Test description",
            "created_date": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc)
        }
        mock_conn.fetchrow.return_value = mock_row
        
        feed = await threat_manager.get_feed(feed_id)
        
        assert feed is not None
        assert feed.id == feed_id
        assert feed.feed_type == ThreatType.SCAM
        assert feed.status == FeedStatus.ACTIVE

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_feed_not_found(self, threat_manager, mock_db_pool):
        """Test feed retrieval when feed doesn't exist"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        
        feed = await threat_manager.get_feed("nonexistent_id")
        assert feed is None

    # ---- Feed Update Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_feed_success(self, threat_manager, mock_db_pool):
        """Test successful feed update"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        feed_id = str(uuid4())
        update_data = {
            "enabled": False,
            "sync_interval_minutes": 120,
            "description": "Updated description"
        }
        
        mock_row = {
            "id": feed_id,
            "name": "Test Feed",
            "enabled": False,
            "sync_interval_minutes": 120,
            "description": "Updated description",
            "last_updated": datetime.now(timezone.utc)
        }
        mock_conn.fetchrow.return_value = mock_row
        
        updated_feed = await threat_manager.update_feed(feed_id, update_data)
        
        assert updated_feed.enabled is False
        assert updated_feed.sync_interval_minutes == 120
        assert updated_feed.description == "Updated description"

    # ---- Feed Deletion Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_feed_success(self, threat_manager, mock_db_pool):
        """Test successful feed deletion"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.execute.return_value = "DELETE 1"
        
        feed_id = str(uuid4())
        result = await threat_manager.delete_feed(feed_id)
        
        assert result is True
        mock_conn.execute.assert_called_once()

    # ---- Feed Synchronization Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_feed_success(self, threat_manager, mock_db_pool):
        """Test successful feed synchronization"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        feed_id = str(uuid4())
        
        # Mock feed data
        feed_data = {
            "id": feed_id,
            "source_url": "https://example.com/feed.json",
            "api_key": "test_key",
            "config": {"format": "json"}
        }
        mock_conn.fetchrow.return_value = feed_data
        
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "threats": [
                {
                    "id": "threat_1",
                    "type": "scam",
                    "level": "high",
                    "title": "Test Scam",
                    "description": "Test scam description",
                    "indicators": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
                    "first_seen": "2023-01-01T00:00:00Z",
                    "last_seen": "2023-12-01T00:00:00Z",
                    "confidence": 0.9
                }
            ]
        }
        
        with patch("aiohttp.ClientSession.get", return_value=mock_response):
            result = await threat_manager.sync_feed(feed_id)
        
        assert result["synced_items"] == 1
        assert result["errors"] == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_feed_http_error(self, threat_manager, mock_db_pool):
        """Test feed synchronization with HTTP error"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        feed_id = str(uuid4())
        
        # Mock feed data
        feed_data = {
            "id": feed_id,
            "source_url": "https://example.com/feed.json",
            "api_key": "test_key",
            "config": {"format": "json"}
        }
        mock_conn.fetchrow.return_value = feed_data
        
        # Mock HTTP error response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        
        with patch("aiohttp.ClientSession.get", return_value=mock_response):
            result = await threat_manager.sync_feed(feed_id)
        
        assert result["synced_items"] == 0
        assert len(result["errors"]) > 0

    # ---- Intelligence Query Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_query_intelligence_success(self, threat_manager, mock_db_pool):
        """Test successful intelligence query"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        query_type = "address"
        query_value = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        threat_types = ["scam", "fraud"]
        time_range_days = 30
        
        mock_rows = [
            {
                "id": str(uuid4()),
                "feed_id": str(uuid4()),
                "feed_name": "Test Feed",
                "threat_type": "scam",
                "threat_level": "high",
                "title": "Bitcoin Scam",
                "description": "Bitcoin investment scam",
                "indicators": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
                "first_seen": datetime.now(timezone.utc) - timedelta(days=15),
                "last_seen": datetime.now(timezone.utc) - timedelta(days=1),
                "confidence_score": 0.85,
                "source_url": "https://example.com",
                "tags": ["bitcoin", "investment"],
                "metadata": {"blockchain": "bitcoin"}
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        results = await threat_manager.query_intelligence(
            query_type, query_value, threat_types, time_range_days
        )
        
        assert len(results) == 1
        assert results[0].threat_type == ThreatType.SCAM
        assert results[0].threat_level == ThreatLevel.HIGH
        assert query_value in results[0].indicators

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_query_intelligence_no_results(self, threat_manager, mock_db_pool):
        """Test intelligence query with no results"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = []
        
        results = await threat_manager.query_intelligence(
            "address", "nonexistent_address", ["scam"], 30
        )
        
        assert len(results) == 0

    # ---- Health Check Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_feed_health_success(self, threat_manager, mock_db_pool):
        """Test successful feed health check"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        feed_id = str(uuid4())
        
        # Mock feed data
        feed_data = {
            "id": feed_id,
            "name": "Test Feed",
            "status": "active",
            "last_sync": datetime.now(timezone.utc) - timedelta(minutes=30),
            "total_items": 100,
            "error_count": 0
        }
        mock_conn.fetchrow.return_value = feed_data
        
        health = await threat_manager.get_feed_health(feed_id)
        
        assert isinstance(health, FeedHealthStatus)
        assert health.feed_id == feed_id
        assert health.status == "active"
        assert health.consecutive_errors == 0
        assert health.items_last_sync == 100

    # ---- Statistics Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_statistics(self, threat_manager, mock_db_pool):
        """Test statistics calculation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Mock statistics query results
        mock_stats = {
            "total_feeds": 10,
            "active_feeds": 8,
            "total_intelligence_items": 1500,
            "items_by_threat_type": {
                "scam": 500, "fraud": 300, "hack": 200, "phishing": 150,
                "malware": 100, "ransomware": 80, "terrorism": 70, "money_laundering": 60,
                "dark_web": 40, "mixer": 30, "exchange_hack": 20, "defi_exploit": 15,
                "nft_fraud": 10, "social_engineering": 25
            },
            "items_by_threat_level": {
                "low": 300, "medium": 600, "high": 400, "critical": 150, "severe": 50
            },
            "sync_success_rate": 0.95,
            "average_sync_time": 45.5,
            "last_24h_items": 50
        }
        mock_conn.fetchrow.return_value = mock_stats
        
        stats = await threat_manager.get_statistics()
        
        assert isinstance(stats, FeedStatistics)
        assert stats.total_feeds == 10
        assert stats.active_feeds == 8
        assert stats.total_intelligence_items == 1500
        assert stats.sync_success_rate == 0.95

    # ---- Recent Items Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_recent_items(self, threat_manager, mock_db_pool):
        """Test getting recent threat intelligence items"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        hours = 24
        threat_type = "scam"
        threat_level = "high"
        limit = 100
        
        mock_rows = [
            {
                "id": str(uuid4()),
                "feed_id": str(uuid4()),
                "feed_name": "Recent Feed",
                "threat_type": "scam",
                "threat_level": "high",
                "title": "Recent Bitcoin Scam",
                "first_seen": datetime.now(timezone.utc) - timedelta(hours=12),
                "last_seen": datetime.now(timezone.utc) - timedelta(hours=2),
                "confidence_score": 0.9
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        items = await threat_manager.get_recent_items(hours, threat_type, threat_level, limit)
        
        assert len(items) == 1
        assert items[0].threat_type == ThreatType.SCAM
        assert items[0].threat_level == ThreatLevel.HIGH

    # ---- Error Handling Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_database_connection_error(self, threat_manager, mock_db_pool):
        """Test handling of database connection errors"""
        mock_pool.acquire.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            await threat_manager.create_feed({
                "name": "Test Feed",
                "feed_type": "scam",
                "source_url": "https://example.com/feed.json"
            })

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_feed_type_validation(self, threat_manager):
        """Test validation of invalid feed types"""
        invalid_feed_data = {
            "name": "Test Feed",
            "feed_type": "nonexistent_type",  # Invalid enum value
            "source_url": "https://example.com/feed.json"
        }
        
        with pytest.raises(ValueError, match="Invalid feed type"):
            await threat_manager.create_feed(invalid_feed_data)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_sync_interval_validation(self, threat_manager):
        """Test validation of invalid sync intervals"""
        invalid_feed_data = {
            "name": "Test Feed",
            "feed_type": "scam",
            "source_url": "https://example.com/feed.json",
            "sync_interval_minutes": 1  # Too short (minimum 5)
        }
        
        with pytest.raises(ValueError, match="Sync interval must be between"):
            await threat_manager.create_feed(invalid_feed_data)


class TestThreatFeedModel:
    """Test suite for ThreatFeed data model"""

    @pytest.mark.unit
    def test_threat_feed_creation(self):
        """Test ThreatFeed model creation"""
        feed_data = {
            "id": str(uuid4()),
            "name": "Test Threat Feed",
            "feed_type": "sanctions",
            "source_url": "https://example.com/threat-feed.json",
            "enabled": True,
            "status": "active",
            "sync_interval_minutes": 60,
            "last_sync": datetime.now(timezone.utc),
            "next_sync": datetime.now(timezone.utc) + timedelta(minutes=60),
            "total_items": 200,
            "error_count": 0,
            "config": {"format": "json", "auth_type": "api_key"},
            "description": "Test threat intelligence feed",
            "created_date": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc)
        }
        
        feed = ThreatFeed(**feed_data)
        
        assert feed.id == feed_data["id"]
        assert feed.name == "Test Threat Feed"
        assert feed.feed_type == ThreatType.SANCTIONS
        assert feed.enabled is True
        assert feed.status == FeedStatus.ACTIVE
        assert feed.sync_interval_minutes == 60
        assert feed.total_items == 200
        assert feed.error_count == 0

    @pytest.mark.unit
    def test_threat_feed_optional_fields(self):
        """Test ThreatFeed with optional fields"""
        feed_data = {
            "id": str(uuid4()),
            "name": "Minimal Feed",
            "feed_type": "scam",
            "source_url": "https://example.com/feed.json",
            "enabled": True,
            "status": "inactive",
            "sync_interval_minutes": 60,
            "total_items": 0,
            "error_count": 0,
            "created_date": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc)
        }
        
        feed = ThreatFeed(**feed_data)
        
        assert feed.last_sync is None
        assert feed.next_sync is None
        assert feed.config == {}
        assert feed.description is None

    @pytest.mark.unit
    def test_threat_feed_enum_validation(self):
        """Test enum validation in ThreatFeed"""
        with pytest.raises(ValueError):
            ThreatFeed(
                id=str(uuid4()),
                name="Test Feed",
                feed_type="invalid_type",  # Invalid enum
                source_url="https://example.com/feed.json",
                enabled=True,
                status="inactive",
                sync_interval_minutes=60,
                total_items=0,
                error_count=0,
                created_date=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc)
            )


class TestThreatIntelligenceItemModel:
    """Test suite for ThreatIntelligenceItem data model"""

    @pytest.mark.unit
    def test_threat_intelligence_item_creation(self):
        """Test ThreatIntelligenceItem model creation"""
        item_data = {
            "id": str(uuid4()),
            "feed_id": str(uuid4()),
            "feed_name": "Test Feed",
            "threat_type": "scam",
            "threat_level": "high",
            "title": "Bitcoin Investment Scam",
            "description": "Fraudulent Bitcoin investment scheme",
            "indicators": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
            "first_seen": datetime.now(timezone.utc) - timedelta(days=30),
            "last_seen": datetime.now(timezone.utc) - timedelta(days=1),
            "confidence_score": 0.85,
            "source_url": "https://example.com/threat/1",
            "tags": ["bitcoin", "investment", "scam"],
            "metadata": {"blockchain": "bitcoin", "category": "investment"}
        }
        
        item = ThreatIntelligenceItem(**item_data)
        
        assert item.id == item_data["id"]
        assert item.feed_type == ThreatType.SCAM
        assert item.threat_level == ThreatLevel.HIGH
        assert item.title == "Bitcoin Investment Scam"
        assert len(item.indicators) == 1
        assert item.confidence_score == 0.85
        assert len(item.tags) == 3

    @pytest.mark.unit
    def test_threat_intelligence_item_validation(self):
        """Test validation in ThreatIntelligenceItem"""
        with pytest.raises(ValueError):
            ThreatIntelligenceItem(
                id=str(uuid4()),
                feed_id=str(uuid4()),
                feed_name="Test Feed",
                threat_type="invalid_type",  # Invalid enum
                threat_level="high",
                title="Test Threat",
                description="Test description",
                indicators=["test_indicator"],
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc),
                confidence_score=1.5,  # Invalid confidence score (> 1.0)
                source_url="https://example.com",
                tags=[],
                metadata={}
            )
