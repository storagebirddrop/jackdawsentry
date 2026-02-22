"""
Tests for VASP registry
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.attribution.vasp_registry import VASPRegistry, get_vasp_registry
from src.attribution.models import VASP, EntityType, RiskLevel, AttributionSearchFilters


class TestVASPRegistry:
    """Test cases for VASPRegistry"""
    
    @pytest.fixture
    async def vasp_registry(self):
        """Create VASP registry instance"""
        registry = VASPRegistry()
        await registry.initialize()
        return registry
    
    @pytest.fixture
    def sample_vasp(self):
        """Create sample VASP for testing"""
        return VASP(
            name="Test Exchange",
            entity_type=EntityType.EXCHANGE,
            risk_level=RiskLevel.LOW,
            jurisdictions=["US"],
            website="https://test.com",
            supported_blockchains=["ethereum", "bitcoin"]
        )
    
    @pytest.mark.asyncio
    async def test_initialize(self, vasp_registry):
        """Test VASP registry initialization"""
        assert vasp_registry._initialized is True
    
    @pytest.mark.asyncio
    async def test_search_vasps_no_filters(self, vasp_registry):
        """Test VASP search without filters"""
        
        with patch('src.api.database.get_postgres_connection') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            # Mock database response
            mock_conn.fetch.return_value = [
                {
                    'id': 1,
                    'name': 'Test Exchange',
                    'entity_type': 'exchange',
                    'risk_level': 'low',
                    'jurisdictions': ['US'],
                    'registration_numbers': {},
                    'website': 'https://test.com',
                    'description': 'Test exchange',
                    'founded_year': 2020,
                    'active_countries': ['US'],
                    'supported_blockchains': ['ethereum'],
                    'compliance_program': True,
                    'regulatory_licenses': ['FINCEN'],
                    'created_at': '2024-01-01T00:00:00Z',
                    'updated_at': '2024-01-01T00:00:00Z'
                }
            ]
            
            results = await vasp_registry.search_vasps()
            
            assert len(results) == 1
            vasp = results[0]
            assert isinstance(vasp, VASP)
            assert vasp.name == 'Test Exchange'
            assert vasp.entity_type == EntityType.EXCHANGE
            assert vasp.risk_level == RiskLevel.LOW
    
    @pytest.mark.asyncio
    async def test_search_vasps_with_query(self, vasp_registry):
        """Test VASP search with query parameter"""
        
        with patch('src.api.database.get_postgres_connection') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            mock_conn.fetch.return_value = []
            
            filters = AttributionSearchFilters()
            results = await vasp_registry.search_vasps(query="binance", filters=filters)
            
            # Verify query was called with correct parameters
            mock_conn.fetch.assert_called_once()
            call_args = mock_conn.fetch.call_args
            assert '%binance%' in str(call_args[0])  # Query should be in SQL
    
    @pytest.mark.asyncio
    async def test_search_vasps_with_filters(self, vasp_registry):
        """Test VASP search with filters"""
        
        with patch('src.api.database.get_postgres_connection') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            mock_conn.fetch.return_value = []
            
            filters = AttributionSearchFilters(
                entity_types=[EntityType.EXCHANGE],
                risk_levels=[RiskLevel.LOW, RiskLevel.MEDIUM],
                jurisdictions=["US", "GB"]
            )
            
            results = await vasp_registry.search_vasps(filters=filters)
            
            # Verify query was called with filter parameters
            mock_conn.fetch.assert_called_once()
            call_args = mock_conn.fetch.call_args
            
            # Check that filter parameters were included
            query = call_args[0]
            assert 'entity_type' in query
            assert 'risk_level' in query
    
    @pytest.mark.asyncio
    async def test_get_vasp_by_id(self, vasp_registry):
        """Test getting VASP by ID"""
        
        with patch('src.api.database.get_postgres_connection') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            # Mock successful lookup
            mock_conn.fetchrow.return_value = {
                'id': 1,
                'name': 'Test Exchange',
                'entity_type': 'exchange',
                'risk_level': 'low',
                'jurisdictions': ['US'],
                'registration_numbers': {},
                'website': 'https://test.com',
                'description': 'Test exchange',
                'founded_year': 2020,
                'active_countries': ['US'],
                'supported_blockchains': ['ethereum'],
                'compliance_program': True,
                'regulatory_licenses': ['FINCEN'],
                'created_at': '2024-01-01T00:00:00Z',
                'updated_at': '2024-01-01T00:00:00Z'
            }
            
            vasp = await vasp_registry.get_vasp_by_id(1)
            
            assert vasp is not None
            assert vasp.id == 1
            assert vasp.name == 'Test Exchange'
            assert isinstance(vasp, VASP)
    
    @pytest.mark.asyncio
    async def test_get_vasp_by_id_not_found(self, vasp_registry):
        """Test getting VASP by ID when not found"""
        
        with patch('src.api.database.get_postgres_connection') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            # Mock not found
            mock_conn.fetchrow.return_value = None
            
            vasp = await vasp_registry.get_vasp_by_id(999)
            
            assert vasp is None
    
    @pytest.mark.asyncio
    async def test_add_vasp(self, vasp_registry, sample_vasp):
        """Test adding a new VASP"""
        
        with patch('src.api.database.get_postgres_connection') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            # Mock successful insert
            mock_conn.fetchrow.return_value = {
                'id': 2,
                'created_at': '2024-01-01T00:00:00Z',
                'updated_at': '2024-01-01T00:00:00Z'
            }
            
            result = await vasp_registry.add_vasp(sample_vasp)
            
            assert result.id == 2
            assert result.created_at is not None
            assert result.updated_at is not None
            mock_conn.execute.assert_called()
            mock_conn.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_attribution_sources(self, vasp_registry):
        """Test getting attribution sources"""
        
        with patch('src.api.database.get_postgres_connection') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_get_conn.return_value.__aenter__.return_value = mock_conn
            
            # Mock sources data
            mock_conn.fetch.return_value = [
                {
                    'id': 1,
                    'name': 'On-Chain Analysis',
                    'source_type': 'on_chain',
                    'reliability_score': 0.85,
                    'description': 'Direct blockchain analysis',
                    'url': None,
                    'api_endpoint': None,
                    'authentication_required': False,
                    'rate_limit_per_hour': None,
                    'last_updated': '2024-01-01T00:00:00Z'
                }
            ]
            
            sources = await vasp_registry.get_attribution_sources()
            
            assert len(sources) == 1
            source = sources[0]
            assert source['name'] == 'On-Chain Analysis'
            assert source['source_type'] == 'on_chain'
            assert source['reliability_score'] == 0.85
    
    def test_get_vasp_registry_singleton(self):
        """Test that get_vasp_registry returns singleton instance"""
        registry1 = get_vasp_registry()
        registry2 = get_vasp_registry()
        
        assert registry1 is registry2


@pytest.mark.asyncio
async def test_vasp_registry_integration():
    """Integration test for VASP registry"""
    
    registry = VASPRegistry()
    
    # Test initialization
    await registry.initialize()
    assert registry._initialized is True
    
    # Test search with mocked database
    with patch('src.api.database.get_postgres_connection') as mock_get_conn:
        mock_conn = AsyncMock()
        mock_get_conn.return_value.__aenter__.return_value = mock_conn
        
        mock_conn.fetch.return_value = []
        
        results = await registry.search_vasps()
        
        # Should return empty list when no VASPs found
        assert results == []
        
        # Verify database was queried
        mock_conn.fetch.assert_called()
