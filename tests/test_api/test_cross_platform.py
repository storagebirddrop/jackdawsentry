"""
Jackdaw Sentry - Cross Platform Attribution API Tests
Tests for cross-platform attribution consolidation API endpoints
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
import json
from fastapi.testclient import TestClient
from fastapi import status

from src.api.main import app
from src.intelligence.cross_platform import (
    CrossPlatformAttribution,
    AttributionConsolidation,
    ConfidenceMetrics,
    AttributionSource
)


class TestCrossPlatformAPI:
    """Test suite for Cross Platform Attribution API endpoints"""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_attribution_engine(self):
        """Mock CrossPlatformAttributionEngine"""
        return AsyncMock()

    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers"""
        return {"Authorization": "Bearer test_token"}

    # ---- Address Analysis Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_analyze_address_success(self, client, mock_attribution_engine, auth_headers):
        """Test successful address analysis"""
        address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        
        mock_attribution = CrossPlatformAttribution(
            id=str(uuid4()),
            address=address,
            blockchain="bitcoin",
            attributions=[
                {
                    "source": "chainalysis",
                    "entity": "Exchange",
                    "confidence": 0.85,
                    "last_seen": datetime.now(timezone.utc) - timedelta(days=1)
                },
                {
                    "source": "elliptic",
                    "entity": "Exchange",
                    "confidence": 0.78,
                    "last_seen": datetime.now(timezone.utc) - timedelta(days=2)
                }
            ],
            consolidated_entity="Exchange",
            overall_confidence=0.82,
            risk_level="high",
            analysis_date=datetime.now(timezone.utc)
        )
        mock_attribution_engine.analyze_address.return_value = mock_attribution
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            response = client.post(
                "/api/v1/intelligence/cross-platform/analyze",
                json={"address": address},
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["address"] == address
        assert data["blockchain"] == "bitcoin"
        assert data["consolidated_entity"] == "Exchange"
        assert data["overall_confidence"] == 0.82
        assert data["risk_level"] == "high"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_analyze_address_invalid_format(self, client, mock_attribution_engine, auth_headers):
        """Test address analysis with invalid address format"""
        invalid_address = "invalid_address_format"
        
        mock_attribution_engine.analyze_address.side_effect = ValueError("Invalid address format")
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            response = client.post(
                "/api/v1/intelligence/cross-platform/analyze",
                json={"address": invalid_address},
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Invalid address format" in data["detail"]

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_analyze_address_not_found(self, client, mock_attribution_engine, auth_headers):
        """Test address analysis when no attribution found"""
        address = "unknown_address"
        mock_attribution_engine.analyze_address.return_value = None
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            response = client.post(
                "/api/v1/intelligence/cross-platform/analyze",
                json={"address": address},
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_batch_analyze_addresses_success(self, client, mock_attribution_engine, auth_headers):
        """Test successful batch address analysis"""
        addresses = [
            "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "1FeexV6bxbbs4rUABp77iYjB3nqPeKUW1n"
        ]
        
        mock_results = []
        for address in addresses:
            attribution = CrossPlatformAttribution(
                id=str(uuid4()),
                address=address,
                blockchain="bitcoin",
                attributions=[{
                    "source": "chainalysis",
                    "entity": "Exchange",
                    "confidence": 0.85
                }],
                consolidated_entity="Exchange",
                overall_confidence=0.85,
                risk_level="medium",
                analysis_date=datetime.now(timezone.utc)
            )
            mock_results.append(attribution)
        
        mock_attribution_engine.batch_analyze_addresses.return_value = mock_results
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            response = client.post(
                "/api/v1/intelligence/cross-platform/batch-analyze",
                json={"addresses": addresses},
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["address"] == addresses[0]
        assert data[1]["address"] == addresses[1]

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_batch_analyze_addresses_too_many(self, client, mock_attribution_engine, auth_headers):
        """Test batch analysis with too many addresses"""
        addresses = [f"address_{i}" for i in range(101)]  # Exceeds limit of 100
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            response = client.post(
                "/api/v1/intelligence/cross-platform/batch-analyze",
                json={"addresses": addresses},
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "Maximum 100 addresses" in data["detail"]

    # ---- Attribution Consolidation Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_consolidate_attributions_success(self, client, mock_attribution_engine, auth_headers):
        """Test successful attribution consolidation"""
        address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        
        mock_consolidation = AttributionConsolidation(
            id=str(uuid4()),
            address=address,
            blockchain="bitcoin",
            source_attributions=[
                {
                    "source": "chainalysis",
                    "entity": "Exchange",
                    "confidence": 0.85,
                    "evidence": ["transaction patterns", "volume analysis"],
                    "last_updated": datetime.now(timezone.utc) - timedelta(hours=6)
                },
                {
                    "source": "elliptic",
                    "entity": "Exchange",
                    "confidence": 0.78,
                    "evidence": ["address clustering", "behavioral analysis"],
                    "last_updated": datetime.now(timezone.utc) - timedelta(hours=12)
                }
            ],
            consolidated_entity="Exchange",
            confidence_metrics=ConfidenceMetrics(
                overall_confidence=0.82,
                source_agreement=0.85,
                evidence_strength=0.80,
                temporal_consistency=0.75,
                confidence_interval=[0.75, 0.89]
            ),
            conflicts=[],
            consolidation_date=datetime.now(timezone.utc)
        )
        mock_attribution_engine.consolidate_attributions.return_value = mock_consolidation
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            response = client.post(
                "/api/v1/intelligence/cross-platform/consolidate",
                json={"address": address},
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["address"] == address
        assert data["consolidated_entity"] == "Exchange"
        assert data["confidence_metrics"]["overall_confidence"] == 0.82
        assert len(data["source_attributions"]) == 2

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_consolidate_with_conflicts(self, client, mock_attribution_engine, auth_headers):
        """Test attribution consolidation with conflicts"""
        address = "conflict_address"
        
        mock_consolidation = AttributionConsolidation(
            id=str(uuid4()),
            address=address,
            blockchain="ethereum",
            source_attributions=[
                {
                    "source": "chainalysis",
                    "entity": "Exchange",
                    "confidence": 0.85
                },
                {
                    "source": "elliptic",
                    "entity": "Mixing Service",
                    "confidence": 0.80
                }
            ],
            consolidated_entity="Unknown",
            confidence_metrics=ConfidenceMetrics(
                overall_confidence=0.45,
                source_agreement=0.20,
                evidence_strength=0.60,
                temporal_consistency=0.50
            ),
            conflicts=[
                {
                    "type": "entity_disagreement",
                    "sources": ["chainalysis", "elliptic"],
                    "entities": ["Exchange", "Mixing Service"],
                    "severity": "high"
                }
            ],
            consolidation_date=datetime.now(timezone.utc)
        )
        mock_attribution_engine.consolidate_attributions.return_value = mock_consolidation
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            response = client.post(
                "/api/v1/intelligence/cross-platform/consolidate",
                json={"address": address},
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["consolidated_entity"] == "Unknown"
        assert data["confidence_metrics"]["overall_confidence"] == 0.45
        assert len(data["conflicts"]) == 1
        assert data["conflicts"][0]["type"] == "entity_disagreement"

    # ---- Source Management Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_available_sources_success(self, client, mock_attribution_engine, auth_headers):
        """Test successful available sources retrieval"""
        mock_sources = [
            AttributionSource(
                name="chainalysis",
                display_name="Chainalysis",
                description="Leading blockchain analysis platform",
                supported_blockchains=["bitcoin", "ethereum", "litecoin"],
                confidence_reliability=0.85,
                update_frequency="hourly",
                last_updated=datetime.now(timezone.utc) - timedelta(minutes=30),
                status="active"
            ),
            AttributionSource(
                name="elliptic",
                display_name="Elliptic",
                description="Cryptocurrency intelligence and compliance platform",
                supported_blockchains=["bitcoin", "ethereum", "ripple"],
                confidence_reliability=0.82,
                update_frequency="daily",
                last_updated=datetime.now(timezone.utc) - timedelta(hours=2),
                status="active"
            )
        ]
        mock_attribution_engine.get_available_sources.return_value = mock_sources
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            response = client.get("/api/v1/intelligence/cross-platform/sources", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "chainalysis"
        assert data[1]["name"] == "elliptic"
        assert data[0]["status"] == "active"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_source_details_success(self, client, mock_attribution_engine, auth_headers):
        """Test successful source details retrieval"""
        source_name = "chainalysis"
        
        mock_source = AttributionSource(
            name=source_name,
            display_name="Chainalysis",
            description="Leading blockchain analysis platform",
            supported_blockchains=["bitcoin", "ethereum", "litecoin", "bitcoin-cash"],
            confidence_reliability=0.85,
            update_frequency="hourly",
            api_endpoint="https://api.chainalysis.com",
            rate_limit=1000,
            last_updated=datetime.now(timezone.utc) - timedelta(minutes=30),
            status="active",
            statistics={
                "total_addresses": 5000000,
                "attributed_addresses": 3500000,
                "average_confidence": 0.82,
                "coverage_percentage": 70.0
            }
        )
        mock_attribution_engine.get_source_details.return_value = mock_source
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            response = client.get(f"/api/v1/intelligence/cross-platform/sources/{source_name}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == source_name
        assert data["display_name"] == "Chainalysis"
        assert len(data["supported_blockchains"]) == 4
        assert data["confidence_reliability"] == 0.85
        assert data["statistics"]["total_addresses"] == 5000000

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_source_details_not_found(self, client, mock_attribution_engine, auth_headers):
        """Test source details retrieval when source doesn't exist"""
        source_name = "nonexistent_source"
        mock_attribution_engine.get_source_details.return_value = None
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            response = client.get(f"/api/v1/intelligence/cross-platform/sources/{source_name}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ---- Search and Filtering Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_search_attributions_success(self, client, mock_attribution_engine, auth_headers):
        """Test successful attribution search"""
        search_params = {
            "entity": "Exchange",
            "blockchain": "bitcoin",
            "risk_level": "high",
            "limit": 50,
            "offset": 0
        }
        
        mock_results = [
            CrossPlatformAttribution(
                id=str(uuid4()),
                address="address_1",
                blockchain="bitcoin",
                consolidated_entity="Exchange",
                overall_confidence=0.85,
                risk_level="high",
                analysis_date=datetime.now(timezone.utc)
            ),
            CrossPlatformAttribution(
                id=str(uuid4()),
                address="address_2",
                blockchain="bitcoin",
                consolidated_entity="Exchange",
                overall_confidence=0.78,
                risk_level="high",
                analysis_date=datetime.now(timezone.utc)
            )
        ]
        mock_attribution_engine.search_attributions.return_value = mock_results
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            response = client.get("/api/v1/intelligence/cross-platform/search", params=search_params, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        for result in data:
            assert result["consolidated_entity"] == "Exchange"
            assert result["risk_level"] == "high"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_search_by_entity_success(self, client, mock_attribution_engine, auth_headers):
        """Test search by entity type"""
        entity = "Exchange"
        
        mock_results = [
            CrossPlatformAttribution(
                id=str(uuid4()),
                address="exchange_addr_1",
                blockchain="bitcoin",
                consolidated_entity=entity,
                overall_confidence=0.90,
                risk_level="medium"
            ),
            CrossPlatformAttribution(
                id=str(uuid4()),
                address="exchange_addr_2",
                blockchain="ethereum",
                consolidated_entity=entity,
                overall_confidence=0.85,
                risk_level="low"
            )
        ]
        mock_attribution_engine.search_by_entity.return_value = mock_results
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            response = client.get(f"/api/v1/intelligence/cross-platform/entity/{entity}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert all(result["consolidated_entity"] == entity for result in data)

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_attribution_history_success(self, client, mock_attribution_engine, auth_headers):
        """Test successful attribution history retrieval"""
        address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        
        mock_history = [
            {
                "date": datetime.now(timezone.utc) - timedelta(days=7),
                "consolidated_entity": "Unknown",
                "overall_confidence": 0.45,
                "sources_count": 1
            },
            {
                "date": datetime.now(timezone.utc) - timedelta(days=3),
                "consolidated_entity": "Exchange",
                "overall_confidence": 0.72,
                "sources_count": 2
            },
            {
                "date": datetime.now(timezone.utc) - timedelta(days=1),
                "consolidated_entity": "Exchange",
                "overall_confidence": 0.85,
                "sources_count": 3
            }
        ]
        mock_attribution_engine.get_attribution_history.return_value = mock_history
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            response = client.get(f"/api/v1/intelligence/cross-platform/history/{address}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3
        assert data[0]["consolidated_entity"] == "Unknown"
        assert data[2]["consolidated_entity"] == "Exchange"
        assert data[2]["overall_confidence"] == 0.85

    # ---- Statistics and Analytics Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_statistics_success(self, client, mock_attribution_engine, auth_headers):
        """Test successful statistics retrieval"""
        days = 30
        
        mock_stats = {
            "total_analyses": 15000,
            "successful_analyses": 14250,
            "failed_analyses": 750,
            "success_rate": 0.95,
            "attributions_by_blockchain": {
                "bitcoin": 6000,
                "ethereum": 4500,
                "litecoin": 2000,
                "ripple": 1500,
                "other": 1000
            },
            "attributions_by_entity": {
                "Exchange": 4000,
                "Mixing Service": 2500,
                "Gambling": 2000,
                "Market": 1800,
                "Unknown": 4700
            },
            "attributions_by_risk_level": {
                "low": 5000,
                "medium": 6000,
                "high": 3500,
                "critical": 500
            },
            "average_confidence_by_source": {
                "chainalysis": 0.85,
                "elliptic": 0.82,
                "ciphertrace": 0.78,
                "glassnode": 0.75
            },
            "conflict_rate": 0.15,
            "average_processing_time_ms": 250
        }
        mock_attribution_engine.get_statistics.return_value = mock_stats
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            response = client.get(f"/api/v1/intelligence/cross-platform/statistics?days={days}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_analyses"] == 15000
        assert data["success_rate"] == 0.95
        assert data["attributions_by_blockchain"]["bitcoin"] == 6000
        assert data["conflict_rate"] == 0.15

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_get_confidence_metrics_success(self, client, mock_attribution_engine, auth_headers):
        """Test successful confidence metrics retrieval"""
        mock_metrics = {
            "overall_average_confidence": 0.78,
            "confidence_distribution": {
                "0.0-0.2": 500,
                "0.2-0.4": 1200,
                "0.4-0.6": 2800,
                "0.6-0.8": 4500,
                "0.8-1.0": 6000
            },
            "source_reliability_scores": {
                "chainalysis": 0.85,
                "elliptic": 0.82,
                "ciphertrace": 0.78,
                "glassnode": 0.75
            },
            "confidence_trends": [
                {"date": "2023-11-01", "average_confidence": 0.75},
                {"date": "2023-11-02", "average_confidence": 0.76},
                {"date": "2023-11-03", "average_confidence": 0.78}
            ],
            "high_confidence_threshold": 0.8,
            "high_confidence_percentage": 40.0
        }
        mock_attribution_engine.get_confidence_metrics.return_value = mock_metrics
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            response = client.get("/api/v1/intelligence/cross-platform/confidence-metrics", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["overall_average_confidence"] == 0.78
        assert data["high_confidence_percentage"] == 40.0
        assert len(data["confidence_trends"]) == 3

    # ---- Conflict Detection Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_detect_conflicts_success(self, client, mock_attribution_engine, auth_headers):
        """Test successful conflict detection"""
        address = "conflict_test_address"
        
        mock_conflicts = [
            {
                "type": "entity_disagreement",
                "severity": "high",
                "sources": ["chainalysis", "elliptic"],
                "entities": ["Exchange", "Mixing Service"],
                "confidence_gap": 0.15,
                "description": "Sources disagree on entity classification"
            },
            {
                "type": "confidence_variance",
                "severity": "medium",
                "sources": ["chainalysis", "ciphertrace"],
                "confidence_values": [0.85, 0.65],
                "variance": 0.20,
                "description": "Significant confidence score variance"
            }
        ]
        mock_attribution_engine.detect_conflicts.return_value = mock_conflicts
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            response = client.post(
                "/api/v1/intelligence/cross-platform/detect-conflicts",
                json={"address": address},
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["type"] == "entity_disagreement"
        assert data[0]["severity"] == "high"
        assert data[1]["type"] == "confidence_variance"

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_resolve_conflict_success(self, client, mock_attribution_engine, auth_headers):
        """Test successful conflict resolution"""
        conflict_id = str(uuid4())
        resolution_data = {
            "resolution_type": "manual_override",
            "selected_entity": "Exchange",
            "selected_confidence": 0.80,
            "reason": "Manual investigation confirms Exchange classification",
            "resolver": "analyst_123"
        }
        
        resolution_result = {
            "success": True,
            "conflict_id": conflict_id,
            "resolution_applied": True,
            "new_consolidated_entity": "Exchange",
            "new_confidence": 0.80,
            "resolution_date": datetime.now(timezone.utc)
        }
        mock_attribution_engine.resolve_conflict.return_value = resolution_result
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            response = client.post(
                f"/api/v1/intelligence/cross-platform/resolve-conflict/{conflict_id}",
                json=resolution_data,
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["resolution_applied"] is True
        assert data["new_consolidated_entity"] == "Exchange"

    # ---- Authentication and Authorization Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client, mock_attribution_engine):
        """Test API access without authentication"""
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            response = client.get("/api/v1/intelligence/cross-platform/sources")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_invalid_token(self, client, mock_attribution_engine):
        """Test API access with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            response = client.get("/api/v1/intelligence/cross-platform/sources", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ---- Error Handling Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_database_connection_error(self, client, mock_attribution_engine, auth_headers):
        """Test handling of database connection errors"""
        mock_attribution_engine.analyze_address.side_effect = Exception("Database connection failed")
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            response = client.post(
                "/api/v1/intelligence/cross-platform/analyze",
                json={"address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"},
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "error" in data

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_source_api_timeout_error(self, client, mock_attribution_engine, auth_headers):
        """Test handling of source API timeout errors"""
        mock_attribution_engine.analyze_address.side_effect = TimeoutError("Source API timeout")
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            response = client.post(
                "/api/v1/intelligence/cross-platform/analyze",
                json={"address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"},
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_408_REQUEST_TIMEOUT

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_invalid_address_format(self, client, mock_attribution_engine, auth_headers):
        """Test handling of invalid address format"""
        invalid_addresses = [
            "",
            "too_short",
            "invalid_characters_!@#$%",
            "way_too_long_address_that_exceeds_maximum_length_for_any_blockchain_format"
        ]
        
        for address in invalid_addresses:
            with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
                response = client.post(
                    "/api/v1/intelligence/cross-platform/analyze",
                    json={"address": address},
                    headers=auth_headers
                )
            
            # Should fail validation
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # ---- Performance and Rate Limiting Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_batch_analysis_performance(self, client, mock_attribution_engine, auth_headers):
        """Test batch analysis performance with large address sets"""
        addresses = [f"test_address_{i}" for i in range(50)]  # Within limits
        
        mock_results = []
        for address in addresses:
            attribution = CrossPlatformAttribution(
                id=str(uuid4()),
                address=address,
                blockchain="bitcoin",
                consolidated_entity="Exchange",
                overall_confidence=0.80,
                analysis_date=datetime.now(timezone.utc)
            )
            mock_results.append(attribution)
        
        mock_attribution_engine.batch_analyze_addresses.return_value = mock_results
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            response = client.post(
                "/api/v1/intelligence/cross-platform/batch-analyze",
                json={"addresses": addresses},
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 50

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_concurrent_analysis_requests(self, client, mock_attribution_engine, auth_headers):
        """Test handling of concurrent analysis requests"""
        address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        
        mock_attribution = CrossPlatformAttribution(
            id=str(uuid4()),
            address=address,
            blockchain="bitcoin",
            consolidated_entity="Exchange",
            overall_confidence=0.85,
            analysis_date=datetime.now(timezone.utc)
        )
        mock_attribution_engine.analyze_address.return_value = mock_attribution
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            # Simulate multiple concurrent requests
            responses = []
            for _ in range(5):
                response = client.post(
                    "/api/v1/intelligence/cross-platform/analyze",
                    json={"address": address},
                    headers=auth_headers
                )
                responses.append(response)
        
        # All requests should succeed (or handle gracefully)
        for response in responses:
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_429_TOO_MANY_REQUESTS]

    # ---- Data Validation Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_blockchain_validation(self, client, mock_attribution_engine, auth_headers):
        """Test validation of supported blockchains"""
        invalid_blockchains = [
            "invalid_blockchain",
            "unsupported_chain",
            "test_chain"
        ]
        
        for blockchain in invalid_blockchains:
            with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
                response = client.post(
                    "/api/v1/intelligence/cross-platform/analyze",
                    json={"address": "test_address", "blockchain": blockchain},
                    headers=auth_headers
                )
            
            # Should fail validation
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_search_parameters_validation(self, client, mock_attribution_engine, auth_headers):
        """Test validation of search parameters"""
        invalid_params = [
            {"limit": -1},  # Negative limit
            {"limit": 1001},  # Exceeds max limit
            {"offset": -1},  # Negative offset
            {"risk_level": "invalid_risk"}  # Invalid risk level
        ]
        
        for params in invalid_params:
            with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
                response = client.get("/api/v1/intelligence/cross-platform/search", params=params, headers=auth_headers)
            
            # Should fail validation
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # ---- Integration Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    async def test_complete_attribution_workflow(self, client, mock_attribution_engine, auth_headers):
        """Test complete attribution analysis workflow"""
        address = "workflow_test_address"
        
        # 1. Analyze address
        mock_attribution = CrossPlatformAttribution(
            id=str(uuid4()),
            address=address,
            blockchain="bitcoin",
            consolidated_entity="Exchange",
            overall_confidence=0.85,
            risk_level="medium",
            analysis_date=datetime.now(timezone.utc)
        )
        mock_attribution_engine.analyze_address.return_value = mock_attribution
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            analyze_response = client.post(
                "/api/v1/intelligence/cross-platform/analyze",
                json={"address": address},
                headers=auth_headers
            )
        
        assert analyze_response.status_code == status.HTTP_200_OK
        attribution_data = analyze_response.json()
        
        # 2. Get attribution history
        mock_history = [
            {
                "date": datetime.now(timezone.utc) - timedelta(days=7),
                "consolidated_entity": "Unknown",
                "overall_confidence": 0.45
            },
            {
                "date": datetime.now(timezone.utc),
                "consolidated_entity": "Exchange",
                "overall_confidence": 0.85
            }
        ]
        mock_attribution_engine.get_attribution_history.return_value = mock_history
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            history_response = client.get(f"/api/v1/intelligence/cross-platform/history/{address}", headers=auth_headers)
        
        assert history_response.status_code == status.HTTP_200_OK
        history_data = history_response.json()
        assert len(history_data) == 2
        
        # 3. Detect conflicts
        mock_conflicts = []  # No conflicts in this case
        mock_attribution_engine.detect_conflicts.return_value = mock_conflicts
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            conflict_response = client.post(
                "/api/v1/intelligence/cross-platform/detect-conflicts",
                json={"address": address},
                headers=auth_headers
            )
        
        assert conflict_response.status_code == status.HTTP_200_OK
        conflicts_data = conflict_response.json()
        assert len(conflicts_data) == 0
        
        # 4. Search similar entities
        mock_similar = [
            CrossPlatformAttribution(
                id=str(uuid4()),
                address="similar_address_1",
                blockchain="bitcoin",
                consolidated_entity="Exchange",
                overall_confidence=0.82,
                risk_level="medium"
            ),
            CrossPlatformAttribution(
                id=str(uuid4()),
                address="similar_address_2",
                blockchain="bitcoin",
                consolidated_entity="Exchange",
                overall_confidence=0.78,
                risk_level="low"
            )
        ]
        mock_attribution_engine.search_by_entity.return_value = mock_similar
        
        with patch("src.api.routers.cross_platform.get_attribution_engine", return_value=mock_attribution_engine):
            similar_response = client.get("/api/v1/intelligence/cross-platform/entity/Exchange", headers=auth_headers)
        
        assert similar_response.status_code == status.HTTP_200_OK
        similar_data = similar_response.json()
        assert len(similar_data) == 2
        assert all(item["consolidated_entity"] == "Exchange" for item in similar_data)
