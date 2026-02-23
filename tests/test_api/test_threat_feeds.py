"""
Jackdaw Sentry - Threat Feeds API Tests
Tests for threat intelligence feeds API endpoints
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
import json
from fastapi.testclient import TestClient
from fastapi import status

from src.api.main import app
from src.intelligence.threat_feeds import ThreatFeed, ThreatIntelligenceItem, FeedStatus


class TestThreatFeedsAPI:
    """Test suite for Threat Feeds API endpoints"""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_threat_manager(self):
        """Mock ThreatIntelligenceManager"""
        return AsyncMock()

    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers"""
        return {"Authorization": "Bearer test_token"}

    # ---- Feed Management Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_create_feed_success(self, client, mock_threat_manager, auth_headers):
        """Test successful feed creation"""
        feed_data = {
            "name": "Test Threat Feed",
            "description": "Test threat intelligence feed",
            "feed_type": "blockchain",
            "source_url": "https://example.com/feed",
            "api_key": "test_api_key",
            "update_frequency": 3600,
            "enabled": True,
            "config": {"format": "json", "verify_ssl": True}
        }
        
        mock_feed = ThreatFeed(
            id=str(uuid4()),
            name=feed_data["name"],
            description=feed_data["description"],
            feed_type=feed_data["feed_type"],
            source_url=feed_data["source_url"],
            api_key=feed_data["api_key"],
            update_frequency=feed_data["update_frequency"],
            enabled=feed_data["enabled"],
            config=feed_data["config"],
            status=FeedStatus.ACTIVE,
            last_updated=datetime.now(timezone.utc),
            created_date=datetime.now(timezone.utc)
        )
        mock_threat_manager.create_feed.return_value = mock_feed
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.post("/api/v1/intelligence/threat-feeds", json=feed_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == feed_data["name"]
        assert data["feed_type"] == feed_data["feed_type"]
        assert data["status"] == "active"
        mock_threat_manager.create_feed.assert_called_once()

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_create_feed_invalid_data(self, client, mock_threat_manager, auth_headers):
        """Test feed creation with invalid data"""
        invalid_data = {
            "name": "",  # Empty required field
            "feed_type": "invalid_type",  # Invalid enum
            "source_url": "invalid_url"  # Invalid URL
        }
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.post("/api/v1/intelligence/threat-feeds", json=invalid_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_feed_success(self, client, mock_threat_manager, auth_headers):
        """Test successful feed retrieval"""
        feed_id = str(uuid4())
        
        mock_feed = ThreatFeed(
            id=feed_id,
            name="Test Feed",
            description="Test description",
            feed_type="blockchain",
            source_url="https://example.com",
            status=FeedStatus.ACTIVE,
            last_updated=datetime.now(timezone.utc),
            created_date=datetime.now(timezone.utc)
        )
        mock_threat_manager.get_feed.return_value = mock_feed
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.get(f"/api/v1/intelligence/threat-feeds/{feed_id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == feed_id
        assert data["name"] == "Test Feed"
        assert data["status"] == "active"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_feed_not_found(self, client, mock_threat_manager, auth_headers):
        """Test feed retrieval when feed doesn't exist"""
        feed_id = str(uuid4())
        mock_threat_manager.get_feed.return_value = None
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.get(f"/api/v1/intelligence/threat-feeds/{feed_id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_list_feeds_success(self, client, mock_threat_manager, auth_headers):
        """Test successful feeds listing"""
        mock_feeds = [
            ThreatFeed(
                id=str(uuid4()),
                name="Feed 1",
                description="Description 1",
                feed_type="blockchain",
                status=FeedStatus.ACTIVE,
                created_date=datetime.now(timezone.utc)
            ),
            ThreatFeed(
                id=str(uuid4()),
                name="Feed 2",
                description="Description 2",
                feed_type="malware",
                status=FeedStatus.INACTIVE,
                created_date=datetime.now(timezone.utc)
            )
        ]
        mock_threat_manager.list_feeds.return_value = mock_feeds
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.get("/api/v1/intelligence/threat-feeds", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Feed 1"
        assert data[1]["name"] == "Feed 2"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_list_feeds_with_filters(self, client, mock_threat_manager, auth_headers):
        """Test feeds listing with filters"""
        filters = {
            "feed_type": "blockchain",
            "status": "active",
            "enabled": True
        }
        
        mock_feeds = [
            ThreatFeed(
                id=str(uuid4()),
                name="Filtered Feed",
                feed_type="blockchain",
                status=FeedStatus.ACTIVE,
                enabled=True,
                created_date=datetime.now(timezone.utc)
            )
        ]
        mock_threat_manager.list_feeds.return_value = mock_feeds
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.get("/api/v1/intelligence/threat-feeds", params=filters, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["feed_type"] == "blockchain"
        assert data[0]["status"] == "active"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_update_feed_success(self, client, mock_threat_manager, auth_headers):
        """Test successful feed update"""
        feed_id = str(uuid4())
        update_data = {
            "name": "Updated Feed Name",
            "description": "Updated description",
            "enabled": False,
            "update_frequency": 7200
        }
        
        mock_feed = ThreatFeed(
            id=feed_id,
            name=update_data["name"],
            description=update_data["description"],
            enabled=update_data["enabled"],
            update_frequency=update_data["update_frequency"],
            status=FeedStatus.INACTIVE,
            last_updated=datetime.now(timezone.utc)
        )
        mock_threat_manager.update_feed.return_value = mock_feed
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.put(f"/api/v1/intelligence/threat-feeds/{feed_id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Feed Name"
        assert data["enabled"] is False

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_delete_feed_success(self, client, mock_threat_manager, auth_headers):
        """Test successful feed deletion"""
        feed_id = str(uuid4())
        mock_threat_manager.delete_feed.return_value = True
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.delete(f"/api/v1/intelligence/threat-feeds/{feed_id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_delete_feed_not_found(self, client, mock_threat_manager, auth_headers):
        """Test feed deletion when feed doesn't exist"""
        feed_id = str(uuid4())
        mock_threat_manager.delete_feed.return_value = False
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.delete(f"/api/v1/intelligence/threat-feeds/{feed_id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ---- Feed Operations Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_sync_feed_success(self, client, mock_threat_manager, auth_headers):
        """Test successful feed synchronization"""
        feed_id = str(uuid4())
        
        sync_result = {
            "success": True,
            "items_processed": 25,
            "new_items": 15,
            "updated_items": 10,
            "errors": [],
            "sync_time": datetime.now(timezone.utc)
        }
        mock_threat_manager.sync_feed.return_value = sync_result
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.post(f"/api/v1/intelligence/threat-feeds/{feed_id}/sync", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["items_processed"] == 25
        assert data["new_items"] == 15

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_sync_feed_with_errors(self, client, mock_threat_manager, auth_headers):
        """Test feed synchronization with errors"""
        feed_id = str(uuid4())
        
        sync_result = {
            "success": False,
            "items_processed": 10,
            "new_items": 5,
            "updated_items": 3,
            "errors": ["Connection timeout", "Invalid data format"],
            "sync_time": datetime.now(timezone.utc)
        }
        mock_threat_manager.sync_feed.return_value = sync_result
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.post(f"/api/v1/intelligence/threat-feeds/{feed_id}/sync", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert len(data["errors"]) == 2

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_enable_feed_success(self, client, mock_threat_manager, auth_headers):
        """Test successful feed enablement"""
        feed_id = str(uuid4())
        
        mock_feed = ThreatFeed(
            id=feed_id,
            name="Test Feed",
            enabled=True,
            status=FeedStatus.ACTIVE,
            last_updated=datetime.now(timezone.utc)
        )
        mock_threat_manager.enable_feed.return_value = mock_feed
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.post(f"/api/v1/intelligence/threat-feeds/{feed_id}/enable", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["enabled"] is True
        assert data["status"] == "active"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_disable_feed_success(self, client, mock_threat_manager, auth_headers):
        """Test successful feed disablement"""
        feed_id = str(uuid4())
        
        mock_feed = ThreatFeed(
            id=feed_id,
            name="Test Feed",
            enabled=False,
            status=FeedStatus.INACTIVE,
            last_updated=datetime.now(timezone.utc)
        )
        mock_threat_manager.disable_feed.return_value = mock_feed
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.post(f"/api/v1/intelligence/threat-feeds/{feed_id}/disable", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["enabled"] is False
        assert data["status"] == "inactive"

    # ---- Intelligence Items Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_intelligence_items_success(self, client, mock_threat_manager, auth_headers):
        """Test successful intelligence items retrieval"""
        feed_id = str(uuid4())
        
        mock_items = [
            ThreatIntelligenceItem(
                id=str(uuid4()),
                feed_id=feed_id,
                title="Threat Item 1",
                description="First threat item",
                threat_type="malware",
                severity="high",
                confidence=0.9,
                indicators=["malware.exe", "192.168.1.100"],
                created_date=datetime.now(timezone.utc)
            ),
            ThreatIntelligenceItem(
                id=str(uuid4()),
                feed_id=feed_id,
                title="Threat Item 2",
                description="Second threat item",
                threat_type="phishing",
                severity="medium",
                confidence=0.7,
                indicators=["phishing-site.com"],
                created_date=datetime.now(timezone.utc)
            )
        ]
        mock_threat_manager.get_intelligence_items.return_value = mock_items
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.get(f"/api/v1/intelligence/threat-feeds/{feed_id}/items", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["threat_type"] == "malware"
        assert data[1]["threat_type"] == "phishing"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_intelligence_items_with_filters(self, client, mock_threat_manager, auth_headers):
        """Test intelligence items retrieval with filters"""
        feed_id = str(uuid4())
        filters = {
            "threat_type": "malware",
            "severity": "high",
            "limit": 10,
            "offset": 0
        }
        
        mock_items = [
            ThreatIntelligenceItem(
                id=str(uuid4()),
                feed_id=feed_id,
                title="High Severity Malware",
                threat_type="malware",
                severity="high",
                confidence=0.95,
                indicators=["trojan.exe"],
                created_date=datetime.now(timezone.utc)
            )
        ]
        mock_threat_manager.get_intelligence_items.return_value = mock_items
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.get(f"/api/v1/intelligence/threat-feeds/{feed_id}/items", params=filters, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["threat_type"] == "malware"
        assert data[0]["severity"] == "high"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_search_intelligence_success(self, client, mock_threat_manager, auth_headers):
        """Test successful intelligence search"""
        search_query = "malware"
        
        mock_items = [
            ThreatIntelligenceItem(
                id=str(uuid4()),
                feed_id=str(uuid4()),
                title="Malware Analysis",
                description="Detailed malware analysis",
                threat_type="malware",
                severity="critical",
                confidence=0.98,
                indicators=["malware-sample.exe"],
                created_date=datetime.now(timezone.utc)
            )
        ]
        mock_threat_manager.search_intelligence.return_value = mock_items
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.get(f"/api/v1/intelligence/threat-feeds/search", params={"q": search_query}, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert "malware" in data[0]["title"].lower()

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_intelligence_item_success(self, client, mock_threat_manager, auth_headers):
        """Test successful individual intelligence item retrieval"""
        item_id = str(uuid4())
        
        mock_item = ThreatIntelligenceItem(
            id=item_id,
            feed_id=str(uuid4()),
            title="Specific Threat Item",
            description="Detailed threat description",
            threat_type="ransomware",
            severity="critical",
            confidence=0.99,
            indicators=["ransomware.exe", "encryption-key"],
            created_date=datetime.now(timezone.utc)
        )
        mock_threat_manager.get_intelligence_item.return_value = mock_item
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.get(f"/api/v1/intelligence/threat-feeds/items/{item_id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == item_id
        assert data["threat_type"] == "ransomware"
        assert data["severity"] == "critical"

    # ---- Statistics and Health Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_feed_statistics_success(self, client, mock_threat_manager, auth_headers):
        """Test successful feed statistics retrieval"""
        feed_id = str(uuid4())
        
        stats = {
            "total_items": 150,
            "items_by_type": {"malware": 60, "phishing": 40, "ransomware": 30, "other": 20},
            "items_by_severity": {"low": 30, "medium": 50, "high": 50, "critical": 20},
            "average_confidence": 0.82,
            "last_sync": datetime.now(timezone.utc) - timedelta(hours=2),
            "sync_errors": 0,
            "status": "healthy"
        }
        mock_threat_manager.get_feed_statistics.return_value = stats
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.get(f"/api/v1/intelligence/threat-feeds/{feed_id}/statistics", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_items"] == 150
        assert data["items_by_type"]["malware"] == 60
        assert data["average_confidence"] == 0.82
        assert data["status"] == "healthy"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_overall_statistics_success(self, client, mock_threat_manager, auth_headers):
        """Test successful overall statistics retrieval"""
        stats = {
            "total_feeds": 8,
            "active_feeds": 6,
            "inactive_feeds": 2,
            "total_items": 1250,
            "items_by_feed_type": {
                "blockchain": 300,
                "malware": 400,
                "phishing": 350,
                "ransomware": 200
            },
            "overall_health": "good",
            "last_global_sync": datetime.now(timezone.utc) - timedelta(minutes=30)
        }
        mock_threat_manager.get_overall_statistics.return_value = stats
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.get("/api/v1/intelligence/threat-feeds/statistics", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_feeds"] == 8
        assert data["active_feeds"] == 6
        assert data["total_items"] == 1250
        assert data["overall_health"] == "good"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_health_check_success(self, client, mock_threat_manager, auth_headers):
        """Test successful health check"""
        health_status = {
            "status": "healthy",
            "active_feeds": 6,
            "total_feeds": 8,
            "recent_syncs": 5,
            "sync_errors": 0,
            "last_check": datetime.now(timezone.utc)
        }
        mock_threat_manager.health_check.return_value = health_status
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.get("/api/v1/intelligence/threat-feeds/health", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["active_feeds"] == 6
        assert data["sync_errors"] == 0

    # ---- Authentication and Authorization Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client, mock_threat_manager):
        """Test API access without authentication"""
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.get("/api/v1/intelligence/threat-feeds")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_invalid_token(self, client, mock_threat_manager):
        """Test API access with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.get("/api/v1/intelligence/threat-feeds", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ---- Error Handling Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_database_connection_error(self, client, mock_threat_manager, auth_headers):
        """Test handling of database connection errors"""
        mock_threat_manager.list_feeds.side_effect = Exception("Database connection failed")
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.get("/api/v1/intelligence/threat-feeds", headers=auth_headers)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "error" in data

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_sync_timeout_error(self, client, mock_threat_manager, auth_headers):
        """Test handling of sync timeout errors"""
        feed_id = str(uuid4())
        mock_threat_manager.sync_feed.side_effect = TimeoutError("Sync operation timed out")
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.post(f"/api/v1/intelligence/threat-feeds/{feed_id}/sync", headers=auth_headers)
        
        assert response.status_code == status.HTTP_408_REQUEST_TIMEOUT

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_invalid_feed_id_format(self, client, mock_threat_manager, auth_headers):
        """Test handling of invalid feed ID format"""
        invalid_feed_id = "invalid-uuid-format"
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.get(f"/api/v1/intelligence/threat-feeds/{invalid_feed_id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_missing_required_fields(self, client, mock_threat_manager, auth_headers):
        """Test handling of missing required fields in feed creation"""
        incomplete_data = {
            "description": "Feed without required fields"
        }
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.post("/api/v1/intelligence/threat-feeds", json=incomplete_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # ---- Performance and Rate Limiting Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_large_feeds_list_pagination(self, client, mock_threat_manager, auth_headers):
        """Test handling of large feeds list with pagination"""
        # Mock large number of feeds
        mock_feeds = [
            ThreatFeed(
                id=str(uuid4()),
                name=f"Feed {i}",
                feed_type="blockchain",
                status=FeedStatus.ACTIVE,
                created_date=datetime.now(timezone.utc)
            )
            for i in range(100)
        ]
        mock_threat_manager.list_feeds.return_value = mock_feeds
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            response = client.get("/api/v1/intelligence/threat-feeds?limit=50&offset=0", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 100  # All feeds returned

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_concurrent_sync_requests(self, client, mock_threat_manager, auth_headers):
        """Test handling of concurrent sync requests"""
        feed_id = str(uuid4())
        
        sync_result = {
            "success": True,
            "items_processed": 10,
            "new_items": 5,
            "updated_items": 5,
            "errors": [],
            "sync_time": datetime.now(timezone.utc)
        }
        mock_threat_manager.sync_feed.return_value = sync_result
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            # Simulate multiple concurrent requests
            responses = []
            for _ in range(3):
                response = client.post(f"/api/v1/intelligence/threat-feeds/{feed_id}/sync", headers=auth_headers)
                responses.append(response)
        
        # All requests should succeed (or handle gracefully)
        for response in responses:
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_429_TOO_MANY_REQUESTS]

    # ---- Data Validation Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_feed_url_validation(self, client, mock_threat_manager, auth_headers):
        """Test validation of feed URLs"""
        invalid_urls = [
            "not-a-url",
            "ftp://invalid-protocol.com",
            "http://no-tld",
            "https://"
        ]
        
        for invalid_url in invalid_urls:
            feed_data = {
                "name": "Test Feed",
                "feed_type": "blockchain",
                "source_url": invalid_url,
                "enabled": True
            }
            
            with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
                response = client.post("/api/v1/intelligence/threat-feeds", json=feed_data, headers=auth_headers)
            
            # Should fail validation
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_feed_frequency_validation(self, client, mock_threat_manager, auth_headers):
        """Test validation of update frequency"""
        invalid_frequencies = [
            -1,  # Negative
            0,   # Zero
            30,  # Too frequent (less than 60 seconds)
            86401 * 7  # Too infrequent (more than 7 days)
        ]
        
        for frequency in invalid_frequencies:
            feed_data = {
                "name": "Test Feed",
                "feed_type": "blockchain",
                "source_url": "https://example.com/feed",
                "update_frequency": frequency,
                "enabled": True
            }
            
            with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
                response = client.post("/api/v1/intelligence/threat-feeds", json=feed_data, headers=auth_headers)
            
            # Should fail validation
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_search_query_validation(self, client, mock_threat_manager, auth_headers):
        """Test validation of search queries"""
        invalid_queries = [
            "",  # Empty
            "a" * 1001  # Too long (>1000 characters)
        ]
        
        for query in invalid_queries:
            with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
                response = client.get(f"/api/v1/intelligence/threat-feeds/search", params={"q": query}, headers=auth_headers)
            
            # Should fail validation
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # ---- Integration Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_feed_lifecycle_workflow(self, client, mock_threat_manager, auth_headers):
        """Test complete feed lifecycle workflow"""
        # 1. Create feed
        feed_data = {
            "name": "Lifecycle Test Feed",
            "description": "Feed for lifecycle testing",
            "feed_type": "blockchain",
            "source_url": "https://example.com/feed",
            "enabled": True
        }
        
        mock_feed = ThreatFeed(
            id=str(uuid4()),
            **feed_data,
            status=FeedStatus.ACTIVE,
            created_date=datetime.now(timezone.utc)
        )
        mock_threat_manager.create_feed.return_value = mock_feed
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            create_response = client.post("/api/v1/intelligence/threat-feeds", json=feed_data, headers=auth_headers)
        
        assert create_response.status_code == status.HTTP_201_CREATED
        feed_id = create_response.json()["id"]
        
        # 2. Sync feed
        sync_result = {
            "success": True,
            "items_processed": 20,
            "new_items": 20,
            "updated_items": 0,
            "errors": []
        }
        mock_threat_manager.sync_feed.return_value = sync_result
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            sync_response = client.post(f"/api/v1/intelligence/threat-feeds/{feed_id}/sync", headers=auth_headers)
        
        assert sync_response.status_code == status.HTTP_200_OK
        
        # 3. Get items
        mock_items = [
            ThreatIntelligenceItem(
                id=str(uuid4()),
                feed_id=feed_id,
                title="Test Item",
                threat_type="malware",
                severity="high",
                created_date=datetime.now(timezone.utc)
            )
        ]
        mock_threat_manager.get_intelligence_items.return_value = mock_items
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            items_response = client.get(f"/api/v1/intelligence/threat-feeds/{feed_id}/items", headers=auth_headers)
        
        assert items_response.status_code == status.HTTP_200_OK
        assert len(items_response.json()) == 1
        
        # 4. Update feed
        update_data = {"enabled": False}
        mock_feed.enabled = False
        mock_feed.status = FeedStatus.INACTIVE
        mock_threat_manager.update_feed.return_value = mock_feed
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            update_response = client.put(f"/api/v1/intelligence/threat-feeds/{feed_id}", json=update_data, headers=auth_headers)
        
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["enabled"] is False
        
        # 5. Delete feed
        mock_threat_manager.delete_feed.return_value = True
        
        with patch("src.api.routers.threat_feeds.get_threat_intelligence_manager", return_value=mock_threat_manager):
            delete_response = client.delete(f"/api/v1/intelligence/threat-feeds/{feed_id}", headers=auth_headers)
        
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT
