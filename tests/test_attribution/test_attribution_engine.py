"""
Tests for attribution engine
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.attribution.attribution_engine import AttributionEngine, get_attribution_engine
from src.attribution.models import (
    AttributionRequest, AttributionResult, AddressAttribution,
    VASP, AttributionSource, VerificationStatus, EntityType, RiskLevel
)


class TestAttributionEngine:
    """Test cases for AttributionEngine"""
    
    @pytest.fixture
    async def attribution_engine(self):
        """Create attribution engine instance"""
        engine = AttributionEngine()
        await engine.initialize()
        return engine
    
    @pytest.fixture
    def sample_vasp(self):
        """Create sample VASP for testing"""
        return VASP(
            id=1,
            name="Test Exchange",
            entity_type=EntityType.EXCHANGE,
            risk_level=RiskLevel.LOW,
            jurisdictions=["US"],
            website="https://test.com",
            supported_blockchains=["ethereum", "bitcoin"]
        )
    
    @pytest.fixture
    def sample_source(self):
        """Create sample attribution source"""
        return AttributionSource(
            id=1,
            name="Test Source",
            source_type="on_chain",
            reliability_score=0.85,
            description="Test attribution source"
        )
    
    @pytest.fixture
    def sample_attribution(self):
        """Create sample address attribution"""
        return AddressAttribution(
            address="0x1234567890123456789012345678901234567890",
            blockchain="ethereum",
            vasp_id=1,
            confidence_score=0.85,
            attribution_source_id=1,
            verification_status=VerificationStatus.VERIFIED,
            evidence={"pattern": "exchange_deposit"}
        )
    
    @pytest.mark.asyncio
    async def test_initialize(self, attribution_engine):
        """Test attribution engine initialization"""
        assert attribution_engine._initialized is True
    
    @pytest.mark.asyncio
    async def test_attribute_address_exact_match(self, attribution_engine, sample_attribution):
        """Test address attribution with exact match"""
        
        # Mock database query to return exact match
        with patch.object(attribution_engine, '_find_exact_matches') as mock_exact:
            mock_exact.return_value = [sample_attribution]
            
            with patch.object(attribution_engine, '_find_cluster_attributions') as mock_cluster:
                mock_cluster.return_value = []
                
                with patch.object(attribution_engine, '_analyze_on_chain_patterns') as mock_patterns:
                    mock_patterns.return_value = []
                    
                    with patch.object(attribution_engine, '_consolidate_attributions') as mock_consolidate:
                        mock_consolidate.return_value = MagicMock(
                            attributions=[sample_attribution],
                            confidence_score=0.85,
                            evidence={}
                        )
                        
                        result = await attribution_engine.attribute_address(
                            address="0x1234567890123456789012345678901234567890",
                            blockchain="ethereum"
                        )
                        
                        assert result.address == "0x1234567890123456789012345678901234567890"
                        assert result.blockchain == "ethereum"
                        assert len(result.attributions) == 1
                        assert result.confidence_score == 0.85
    
    @pytest.mark.asyncio
    async def test_attribute_address_no_matches(self, attribution_engine):
        """Test address attribution with no matches"""
        
        with patch.object(attribution_engine, '_find_exact_matches') as mock_exact:
            mock_exact.return_value = []
            
            with patch.object(attribution_engine, '_find_cluster_attributions') as mock_cluster:
                mock_cluster.return_value = []
                
                with patch.object(attribution_engine, '_analyze_on_chain_patterns') as mock_patterns:
                    mock_patterns.return_value = []
                    
                    with patch.object(attribution_engine, '_consolidate_attributions') as mock_consolidate:
                        mock_consolidate.return_value = MagicMock(
                            attributions=[],
                            confidence_score=0.0,
                            evidence={}
                        )
                        
                        result = await attribution_engine.attribute_address(
                            address="0x1234567890123456789012345678901234567890",
                            blockchain="ethereum"
                        )
                        
                        assert result.address == "0x1234567890123456789012345678901234567890"
                        assert result.blockchain == "ethereum"
                        assert len(result.attributions) == 0
                        assert result.confidence_score == 0.0
    
    @pytest.mark.asyncio
    async def test_batch_attribute_addresses(self, attribution_engine):
        """Test batch address attribution"""
        
        request = AttributionRequest(
            addresses=[
                "0x1234567890123456789012345678901234567890",
                "0x0987654321098765432109876543210987654321"
            ],
            blockchain="ethereum",
            min_confidence=0.5
        )
        
        with patch.object(attribution_engine, 'attribute_address') as mock_attribute:
            mock_result = MagicMock(
                address="0x1234567890123456789012345678901234567890",
                blockchain="ethereum",
                attributions=[],
                confidence_score=0.0
            )
            mock_attribute.return_value = mock_result
            
            results = await attribution_engine.batch_attribute_addresses(request)
            
            assert len(results) == 2
            assert "0x1234567890123456789012345678901234567890" in results
            assert "0x0987654321098765432109876543210987654321" in results
            assert mock_attribute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, attribution_engine):
        """Test caching functionality"""
        
        address = "0x1234567890123456789012345678901234567890"
        blockchain = "ethereum"
        
        # First call should populate cache
        with patch.object(attribution_engine, '_find_exact_matches') as mock_exact:
            mock_exact.return_value = []
            
            with patch.object(attribution_engine, '_find_cluster_attributions') as mock_cluster:
                mock_cluster.return_value = []
                
                with patch.object(attribution_engine, '_analyze_on_chain_patterns') as mock_patterns:
                    mock_patterns.return_value = []
                    
                    with patch.object(attribution_engine, '_consolidate_attributions') as mock_consolidate:
                        mock_consolidate.return_value = MagicMock(
                            attributions=[],
                            confidence_score=0.0,
                            evidence={}
                        )
                        
                        # First call
                        result1 = await attribution_engine.attribute_address(address, blockchain)
                        
                        # Second call should use cache
                        result2 = await attribution_engine.attribute_address(address, blockchain)
                        
                        # Should only call the underlying methods once
                        assert mock_exact.call_count == 1
                        assert mock_cluster.call_count == 1
                        assert mock_patterns.call_count == 1
                        assert mock_consolidate.call_count == 1
    
    @pytest.mark.asyncio
    async def test_add_attribution(self, attribution_engine, sample_attribution):
        """Test adding new attribution"""
        
        with patch('src.api.database.get_postgres_connection') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            # Mock successful insert
            mock_conn.fetchrow.return_value = {
                'id': '123e4567-e89b-12d3-a456-426614174000',
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
            
            result = await attribution_engine.add_attribution(sample_attribution)
            
            assert result.id is not None
            assert result.created_at is not None
            assert result.updated_at is not None
            mock_conn.execute.assert_called()
            mock_conn.commit.assert_called()
    
    def test_get_attribution_engine_singleton(self):
        """Test that get_attribution_engine returns singleton instance"""
        engine1 = get_attribution_engine()
        engine2 = get_attribution_engine()
        
        assert engine1 is engine2


@pytest.mark.asyncio
async def test_attribution_engine_integration():
    """Integration test for attribution engine"""
    
    engine = AttributionEngine()
    
    # Test initialization
    await engine.initialize()
    assert engine._initialized is True
    
    # Test basic functionality with mocked dependencies
    with patch.object(engine, '_find_exact_matches', return_value=[]), \
         patch.object(engine, '_find_cluster_attributions', return_value=[]), \
         patch.object(engine, '_analyze_on_chain_patterns', return_value=[]), \
         patch.object(engine, '_consolidate_attributions') as mock_consolidate:
        
        mock_consolidate.return_value = MagicMock(
            attributions=[],
            confidence_score=0.0,
            evidence={}
        )
        
        result = await engine.attribute_address(
            address="0x1234567890123456789012345678901234567890",
            blockchain="ethereum"
        )
        
        assert isinstance(result, AttributionResult)
        assert result.address == "0x1234567890123456789012345678901234567890"
        assert result.blockchain == "ethereum"
