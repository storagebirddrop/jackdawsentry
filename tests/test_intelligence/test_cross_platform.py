"""
Jackdaw Sentry - Cross-Platform Attribution Unit Tests
Tests for unified intelligence consolidation and attribution analysis
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from src.intelligence.cross_platform import (
    CrossPlatformAttributionEngine,
    AttributionConfidence,
    AttributionSource,
    CrossPlatformAttribution,
    AttributionConsolidation,
    ConfidenceMetrics,
)


class TestCrossPlatformAttributionEngine:
    """Test suite for CrossPlatformAttributionEngine"""

    @pytest.fixture
    def mock_db_pool(self):
        """Mock PostgreSQL connection pool"""
        return AsyncMock()

    @pytest.fixture
    def attribution_engine(self, mock_db_pool):
        """Create CrossPlatformAttributionEngine instance with mocked dependencies"""
        with patch("src.intelligence.cross_platform.get_postgres_connection", return_value=mock_db_pool):
            return CrossPlatformAttributionEngine(mock_db_pool)

    # ---- Initialization Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_engine_initializes(self, attribution_engine, mock_db_pool):
        """Test engine initialization creates required schema"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        await attribution_engine.initialize()
        
        # Verify schema creation queries were executed
        assert mock_conn.execute.call_count >= 1
        mock_pool.acquire.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_engine_shutdown(self, attribution_engine):
        """Test engine shutdown"""
        attribution_engine.running = True
        await attribution_engine.shutdown()
        assert attribution_engine.running is False

    # ---- Attribution Analysis Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_address_success(self, attribution_engine, mock_db_pool):
        """Test successful address analysis"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        blockchain = "bitcoin"
        sources = ["victim_reports", "threat_intelligence"]
        
        # Mock source data
        mock_rows = [
            {
                "source": "victim_reports",
                "confidence_score": 0.8,
                "entity": "Scam Service",
                "entity_type": "scam",
                "data": {"reports": 5, "verified": True},
                "last_updated": datetime.now(timezone.utc),
                "reliability_score": 0.7,
                "coverage_score": 0.6
            },
            {
                "source": "threat_intelligence",
                "confidence_score": 0.9,
                "entity": "Malicious Actor",
                "entity_type": "criminal",
                "data": {"threat_level": "high"},
                "last_updated": datetime.now(timezone.utc),
                "reliability_score": 0.8,
                "coverage_score": 0.9
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        attribution = await attribution_engine.analyze_address(
            address, blockchain, sources, True, True, 30
        )
        
        assert isinstance(attribution, CrossPlatformAttribution)
        assert attribution.address == address
        assert attribution.blockchain == blockchain
        assert len(attribution.sources) == 2
        assert attribution.confidence_score > 0.8  # Weighted average
        assert attribution.confidence_level in [level.value for level in AttributionConfidence]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_address_no_sources(self, attribution_engine, mock_db_pool):
        """Test address analysis with no matching sources"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = []
        
        address = "nonexistent_address"
        blockchain = "bitcoin"
        sources = ["victim_reports"]
        
        attribution = await attribution_engine.analyze_address(
            address, blockchain, sources, True, True, 30
        )
        
        assert attribution.address == address
        assert attribution.blockchain == blockchain
        assert attribution.entity is None
        assert attribution.confidence_score == 0.0
        assert attribution.confidence_level == AttributionConfidence.VERY_LOW

    # ---- Attribution Retrieval Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_attribution_success(self, attribution_engine, mock_db_pool):
        """Test successful attribution retrieval"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        blockchain = "bitcoin"
        
        mock_row = {
            "id": str(uuid4()),
            "address": address,
            "blockchain": blockchain,
            "entity": "Exchange Service",
            "entity_type": "exchange",
            "confidence_score": 0.85,
            "confidence_level": "high",
            "sources": ["threat_intelligence", "vasp_registry"],
            "source_details": {
                "threat_intelligence": {"confidence": 0.9},
                "vasp_registry": {"confidence": 0.8}
            },
            "first_seen": datetime.now(timezone.utc) - timedelta(days=30),
            "last_seen": datetime.now(timezone.utc) - timedelta(days=1),
            "verification_status": "unverified",
            "created_date": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc)
        }
        mock_conn.fetchrow.return_value = mock_row
        
        attribution = await attribution_engine.get_attribution(address, blockchain)
        
        assert attribution is not None
        assert attribution.address == address
        assert attribution.blockchain == blockchain
        assert attribution.entity == "Exchange Service"
        assert attribution.confidence_score == 0.85
        assert attribution.confidence_level == AttributionConfidence.HIGH

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_attribution_not_found(self, attribution_engine, mock_db_pool):
        """Test attribution retrieval when attribution doesn't exist"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None
        
        attribution = await attribution_engine.get_attribution("nonexistent", "bitcoin")
        assert attribution is None

    # ---- Attribution Consolidation Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_consolidate_attributions_success(self, attribution_engine, mock_db_pool):
        """Test successful attribution consolidation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        addresses = [
            "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
        ]
        blockchain = "ethereum"
        sources = ["all"]
        consolidation_method = "weighted_average"
        min_confidence_threshold = 0.3
        
        # Mock individual attributions
        mock_rows = [
            {
                "id": str(uuid4()),
                "address": addresses[0],
                "entity": "Exchange A",
                "confidence_score": 0.8,
                "sources": ["vasp_registry", "threat_intelligence"]
            },
            {
                "id": str(uuid4()),
                "address": addresses[1],
                "entity": "Exchange B",
                "confidence_score": 0.7,
                "sources": ["vasp_registry"]
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        consolidation = await attribution_engine.consolidate_attributions(
            addresses, blockchain, sources, consolidation_method, min_confidence_threshold
        )
        
        assert isinstance(consolidation, AttributionConsolidation)
        assert consolidation.addresses == addresses
        assert consolidation.blockchain == blockchain
        assert consolidation.consolidation_method == consolidation_method
        assert len(consolidation.individual_attributions) == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_consolidate_attributions_no_agreement(self, attribution_engine, mock_db_pool):
        """Test attribution consolidation with low source agreement"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        addresses = ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"]
        blockchain = "bitcoin"
        
        # Mock conflicting attributions
        mock_rows = [
            {
                "id": str(uuid4()),
                "address": addresses[0],
                "entity": "Exchange A",
                "confidence_score": 0.9,
                "sources": ["vasp_registry"]
            },
            {
                "id": str(uuid4()),
                "address": addresses[0],
                "entity": "Scam Service",
                "confidence_score": 0.8,
                "sources": ["threat_intelligence"]
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        consolidation = await attribution_engine.consolidate_attributions(
            addresses, blockchain, ["all"], "highest_confidence", 0.5
        )
        
        assert consolidation.source_agreement < 0.5  # Low agreement
        assert len(consolidation.gaps_conflicts) > 0

    # ---- Attribution Verification Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_verify_attribution_success(self, attribution_engine, mock_db_pool):
        """Test successful attribution verification"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        attribution_id = str(uuid4())
        verification_data = {
            "verified": True,
            "confidence_adjustment": 0.1,
            "notes": "Verified by analyst",
            "additional_sources": ["manual_investigation"]
        }
        
        # Mock existing attribution
        mock_row = {
            "id": attribution_id,
            "confidence_score": 0.8,
            "verification_status": "unverified"
        }
        mock_conn.fetchrow.return_value = mock_row
        
        updated_attribution = await attribution_engine.verify_attribution(attribution_id, verification_data)
        
        assert updated_attribution.verification_status == "verified"
        assert updated_attribution.confidence_score == 0.9  # 0.8 + 0.1
        assert updated_attribution.notes == "Verified by analyst"

    # ---- Search Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_by_entity(self, attribution_engine, mock_db_pool):
        """Test searching attributions by entity name"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        entity = "Exchange Service"
        
        mock_rows = [
            {
                "id": str(uuid4()),
                "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                "entity": entity,
                "confidence_score": 0.85,
                "blockchain": "bitcoin"
            },
            {
                "id": str(uuid4()),
                "address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
                "entity": entity,
                "confidence_score": 0.75,
                "blockchain": "ethereum"
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        results = await attribution_engine.search_by_entity(entity, None, None, 100)
        
        assert len(results) == 2
        for result in results:
            assert result.entity == entity

    # ---- Batch Processing Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_batch_attributions(self, attribution_engine, mock_db_pool):
        """Test batch attribution retrieval"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        addresses = [
            "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
        ]
        blockchain = "ethereum"
        
        mock_rows = [
            {
                "id": str(uuid4()),
                "address": addresses[0],
                "entity": "Exchange A",
                "confidence_score": 0.8,
                "blockchain": blockchain
            },
            {
                "id": str(uuid4()),
                "address": addresses[1],
                "entity": "Exchange B",
                "confidence_score": 0.7,
                "blockchain": blockchain
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        results = await attribution_engine.get_batch_attributions(addresses, blockchain)
        
        assert len(results) == 2
        assert results[0].address == addresses[0]
        assert results[1].address == addresses[1]

    # ---- Confidence Metrics Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_confidence_metrics(self, attribution_engine, mock_db_pool):
        """Test confidence metrics calculation"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        days = 30
        
        # Mock metrics data
        mock_metrics = {
            "total_attributions": 500,
            "confidence_distribution": {
                AttributionConfidence.VERY_LOW.value: 50,
                AttributionConfidence.LOW.value: 100,
                AttributionConfidence.MEDIUM.value: 150,
                AttributionConfidence.HIGH.value: 150,
                AttributionConfidence.VERY_HIGH.value: 40,
                AttributionConfidence.DEFINITIVE.value: 10
            },
            "source_coverage": {
                "victim_reports": 0.6,
                "threat_intelligence": 0.8,
                "vasp_registry": 0.9,
                "on_chain_analysis": 0.7
            },
            "verification_rate": 0.75,
            "attribution_accuracy": 0.85
        }
        mock_conn.fetchrow.return_value = mock_metrics
        
        metrics = await attribution_engine.get_confidence_metrics(None, days)
        
        assert isinstance(metrics, ConfidenceMetrics)
        assert metrics.total_attributions == 500
        assert metrics.verification_rate == 0.75
        assert metrics.attribution_accuracy == 0.85

    # ---- Source Management Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_available_sources(self, attribution_engine, mock_db_pool):
        """Test getting available attribution sources"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        mock_rows = [
            {
                "source": AttributionSource.VICTIM_REPORTS,
                "description": "Victim report database",
                "total_attributions": 100,
                "average_confidence": 0.7,
                "reliability_score": 0.6,
                "coverage": {"bitcoin": 30, "ethereum": 40, "other": 30}
            },
            {
                "source": AttributionSource.THREAT_INTELLIGENCE,
                "description": "Threat intelligence feeds",
                "total_attributions": 200,
                "average_confidence": 0.8,
                "reliability_score": 0.8,
                "coverage": {"bitcoin": 50, "ethereum": 60, "other": 40}
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        sources = await attribution_engine.get_available_sources()
        
        assert len(sources) == 2
        assert sources[0].source == AttributionSource.VICTIM_REPORTS
        assert sources[1].source == AttributionSource.THREAT_INTELLIGENCE

    # ---- Conflict Detection Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_conflicts(self, attribution_engine, mock_db_pool):
        """Test conflict detection between sources"""
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        min_confidence_gap = 0.3
        
        mock_conflicts = [
            {
                "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                "blockchain": "bitcoin",
                "source1": "victim_reports",
                "source2": "threat_intelligence",
                "entity1": "Exchange A",
                "entity2": "Scam Service",
                "confidence_gap": 0.4,
                "description": "High confidence gap between sources"
            }
        ]
        mock_conn.fetch.return_value = mock_conflicts
        
        conflicts = await attribution_engine.get_conflicts(None, min_confidence_gap)
        
        assert len(conflicts) == 1
        assert conflicts[0]["confidence_gap"] == 0.4
        assert conflicts[0]["entity1"] != conflicts[0]["entity2"]

    # ---- Error Handling Tests ----

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_database_connection_error(self, attribution_engine, mock_db_pool):
        """Test handling of database connection errors"""
        mock_pool.acquire.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            await attribution_engine.analyze_address(
                "test_address", "bitcoin", ["all"], True, True, 30
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_blockchain_validation(self, attribution_engine):
        """Test validation of invalid blockchain names"""
        with pytest.raises(ValueError, match="Invalid blockchain"):
            await attribution_engine.analyze_address(
                "test_address", "invalid_blockchain", ["all"], True, True, 30
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_confidence_threshold(self, attribution_engine):
        """Test validation of invalid confidence thresholds"""
        with pytest.raises(ValueError, match="Confidence threshold must be between"):
            await attribution_engine.consolidate_attributions(
                ["test_address"], "bitcoin", ["all"], "weighted_average", 1.5
            )


class TestCrossPlatformAttributionModel:
    """Test suite for CrossPlatformAttribution data model"""

    @pytest.mark.unit
    def test_cross_platform_attribution_creation(self):
        """Test CrossPlatformAttribution model creation"""
        attribution_data = {
            "id": str(uuid4()),
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "blockchain": "bitcoin",
            "entity": "Exchange Service",
            "entity_type": "exchange",
            "confidence_score": 0.85,
            "confidence_level": "high",
            "sources": ["threat_intelligence", "vasp_registry"],
            "source_details": {
                "threat_intelligence": {
                    "confidence": 0.9,
                    "data": {"threat_level": "high"}
                },
                "vasp_registry": {
                    "confidence": 0.8,
                    "data": {"verified": True}
                }
            },
            "first_seen": datetime.now(timezone.utc) - timedelta(days=30),
            "last_seen": datetime.now(timezone.utc) - timedelta(days=1),
            "verification_status": "verified",
            "verified_by": "analyst_123",
            "verification_date": datetime.now(timezone.utc),
            "created_date": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc)
        }
        
        attribution = CrossPlatformAttribution(**attribution_data)
        
        assert attribution.id == attribution_data["id"]
        assert attribution.address == attribution_data["address"]
        assert attribution.blockchain == "bitcoin"
        assert attribution.entity == "Exchange Service"
        assert attribution.confidence_score == 0.85
        assert attribution.confidence_level == AttributionConfidence.HIGH
        assert len(attribution.sources) == 2
        assert attribution.verification_status == "verified"

    @pytest.mark.unit
    def test_cross_platform_attribution_optional_fields(self):
        """Test CrossPlatformAttribution with optional fields"""
        attribution_data = {
            "id": str(uuid4()),
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "blockchain": "ethereum",
            "confidence_score": 0.5,
            "confidence_level": "medium",
            "sources": ["on_chain_analysis"],
            "source_details": {},
            "verification_status": "unverified",
            "created_date": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc)
        }
        
        attribution = CrossPlatformAttribution(**attribution_data)
        
        assert attribution.entity is None
        assert attribution.entity_type is None
        assert attribution.first_seen is None
        assert attribution.last_seen is None
        assert attribution.verified_by is None
        assert attribution.verification_date is None

    @pytest.mark.unit
    def test_cross_platform_attribution_enum_validation(self):
        """Test enum validation in CrossPlatformAttribution"""
        with pytest.raises(ValueError):
            CrossPlatformAttribution(
                id=str(uuid4()),
                address="test_address",
                blockchain="invalid_blockchain",  # Invalid enum
                confidence_score=0.5,
                confidence_level="invalid_level",  # Invalid enum
                sources=[],
                source_details={},
                verification_status="unverified",
                created_date=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc)
            )


class TestAttributionConsolidationModel:
    """Test suite for AttributionConsolidation data model"""

    @pytest.mark.unit
    def test_attribution_consolidation_creation(self):
        """Test AttributionConsolidation model creation"""
        consolidation_data = {
            "addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"],
            "blockchain": "ethereum",
            "consolidated_entity": "Exchange Cluster",
            "consolidated_confidence": 0.82,
            "individual_attributions": [
                {
                    "id": str(uuid4()),
                    "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                    "entity": "Exchange A",
                    "confidence_score": 0.8
                },
                {
                    "id": str(uuid4()),
                    "address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
                    "entity": "Exchange B",
                    "confidence_score": 0.85
                }
            ],
            "consolidation_method": "weighted_average",
            "source_agreement": 0.8,
            "confidence_distribution": {
                "very_low": 0,
                "low": 10,
                "medium": 20,
                "high": 50,
                "very_high": 20,
                "definitive": 0
            },
            "gaps_conflicts": ["Minor confidence differences"],
            "created_date": datetime.now(timezone.utc)
        }
        
        consolidation = AttributionConsolidation(**consolidation_data)
        
        assert consolidation.addresses == consolidation_data["addresses"]
        assert consolidation.blockchain == "ethereum"
        assert consolidation.consolidated_entity == "Exchange Cluster"
        assert consolidation.consolidated_confidence == 0.82
        assert consolidation.consolidation_method == "weighted_average"
        assert consolidation.source_agreement == 0.8
        assert len(consolidation.individual_attributions) == 2

    @pytest.mark.unit
    def test_confidence_metrics_creation(self):
        """Test ConfidenceMetrics model creation"""
        metrics_data = {
            "total_attributions": 1000,
            "confidence_distribution": {
                AttributionConfidence.VERY_LOW.value: 50,
                AttributionConfidence.LOW.value: 150,
                AttributionConfidence.MEDIUM.value: 300,
                AttributionConfidence.HIGH.value: 350,
                AttributionConfidence.VERY_HIGH.value: 120,
                AttributionConfidence.DEFINITIVE.value: 30
            },
            "source_coverage": {
                AttributionSource.VICTIM_REPORTS.value: 0.6,
                AttributionSource.THREAT_INTELLIGENCE.value: 0.8,
                AttributionSource.VASP_REGISTRY.value: 0.9
            },
            "verification_rate": 0.75,
            "attribution_accuracy": 0.88
        }
        
        metrics = ConfidenceMetrics(**metrics_data)
        
        assert metrics.total_attributions == 1000
        assert metrics.verification_rate == 0.75
        assert metrics.attribution_accuracy == 0.88
        assert metrics.source_coverage[AttributionSource.VASP_REGISTRY.value] == 0.9
