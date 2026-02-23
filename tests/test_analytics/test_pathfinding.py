"""
Tests for multi-route pathfinding
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
import networkx as nx

from src.analytics.pathfinding import MultiRoutePathfinder, get_pathfinder
from src.analytics.models import (
    PathfindingRequest, PathfindingResult, TransactionPath, TransactionEdge,
    PathfindingAlgorithm
)


class TestMultiRoutePathfinder:
    """Test cases for MultiRoutePathfinder"""
    
    @pytest.fixture
    async def pathfinder(self):
        """Create pathfinder instance"""
        pathfinder = MultiRoutePathfinder()
        await pathfinder.initialize()
        return pathfinder
    
    @pytest.mark.asyncio
    async def test_initialize(self, pathfinder):
        """Test pathfinder initialization"""
        assert pathfinder._initialized is True
    
    @pytest.mark.asyncio
    async def test_find_paths_shortest_path(self, pathfinder):
        """Test finding shortest paths"""
        
        request = PathfindingRequest(
            source_address="0x1234567890123456789012345678901234567890",
            target_address="0x0987654321098765432109876543210987654321",
            blockchain="ethereum",
            algorithm=PathfindingAlgorithm.SHORTEST_PATH,
            max_paths=10,
            max_hops=5
        )
        
        with patch.object(pathfinder, '_build_transaction_graph') as mock_build:
            # Create a simple graph
            graph = nx.DiGraph()
            graph.add_edge("0x123", "0x456", amount=1.0, transaction_hash="0xabc", timestamp=datetime.now())
            graph.add_edge("0x456", "0x789", amount=0.5, transaction_hash="0xdef", timestamp=datetime.now())
            graph.add_edge("0x789", "0x098", amount=0.25, transaction_hash="0x123", timestamp=datetime.now())
            
            mock_build.return_value = graph
            
            result = await pathfinder.find_paths(request)
            
            assert result.source_address == request.source_address
            assert result.target_address == request.target_address
            assert result.blockchain == request.blockchain
            assert result.algorithm == PathfindingAlgorithm.SHORTEST_PATH
            assert result.total_paths_found >= 0
            assert isinstance(result.paths, list)
    
    @pytest.mark.asyncio
    async def test_find_paths_all_paths(self, pathfinder):
        """Test finding all paths"""
        
        request = PathfindingRequest(
            source_address="0x1234567890123456789012345678901234567890",
            target_address="0x0987654321098765432109876543210987654321",
            blockchain="ethereum",
            algorithm=PathfindingAlgorithm.ALL_PATHS,
            max_paths=10,
            max_hops=5
        )
        
        with patch.object(pathfinder, '_build_transaction_graph') as mock_build:
            # Create a graph with multiple paths
            graph = nx.DiGraph()
            graph.add_edge("0x123", "0x456", amount=1.0, transaction_hash="0xabc", timestamp=datetime.now())
            graph.add_edge("0x456", "0x789", amount=0.5, transaction_hash="0xdef", timestamp=datetime.now())
            graph.add_edge("0x789", "0x098", amount=0.25, transaction_hash="0x123", timestamp=datetime.now())
            
            # Add alternative path
            graph.add_edge("0x123", "0x555", amount=0.8, transaction_hash="0x555", timestamp=datetime.now())
            graph.add_edge("0x555", "0x098", amount=0.4, transaction_hash="0x666", timestamp=datetime.now())
            
            mock_build.return_value = graph
            
            result = await pathfinder.find_paths(request)
            
            assert result.algorithm == PathfindingAlgorithm.ALL_PATHS
            assert result.total_paths_found >= 0
            assert isinstance(result.paths, list)
    
    @pytest.mark.asyncio
    async def test_find_paths_no_path_exists(self, pathfinder):
        """Test when no path exists between addresses"""
        
        request = PathfindingRequest(
            source_address="0x1234567890123456789012345678901234567890",
            target_address="0x0987654321098765432109876543210987654321",
            blockchain="ethereum",
            algorithm=PathfindingAlgorithm.SHORTEST_PATH
        )
        
        with patch.object(pathfinder, '_build_transaction_graph') as mock_build:
            # Create a disconnected graph
            graph = nx.DiGraph()
            graph.add_node("0x123")
            graph.add_node("0x098")
            # No edges between them
            
            mock_build.return_value = graph
            
            result = await pathfinder.find_paths(request)
            
            assert result.total_paths_found == 0
            assert len(result.paths) == 0
    
    @pytest.mark.asyncio
    async def test_build_transaction_graph(self, pathfinder):
        """Test building transaction graph"""
        
        with patch.object(pathfinder, '_get_address_transactions') as mock_get_txs, \
             patch.object(pathfinder, '_expand_graph_with_intermediates') as mock_expand:
            
            # Mock transactions
            mock_get_txs.return_value = [
                {
                    'from_address': '0x123',
                    'to_address': '0x456',
                    'amount': 1.0,
                    'hash': '0xabc',
                    'timestamp': datetime.now()
                }
            ]
            
            graph = await pathfinder._build_transaction_graph(
                '0x123', '0x456', 'ethereum', 5, 24
            )
            
            assert isinstance(graph, nx.DiGraph)
            assert '0x123' in graph.nodes()
            assert '0x456' in graph.nodes()
            assert graph.has_edge('0x123', '0x456')
            
            mock_get_txs.assert_called()
            mock_expand.assert_called()
    
    @pytest.mark.asyncio
    async def test_create_transaction_path(self, pathfinder):
        """Test creating transaction path from node sequence"""
        
        # Create a graph
        graph = nx.DiGraph()
        graph.add_edge(
            "0x123", "0x456",
            amount=1.0,
            transaction_hash="0xabc",
            timestamp=datetime.now(),
            blockchain="ethereum"
        )
        graph.add_edge(
            "0x456", "0x789",
            amount=0.5,
            transaction_hash="0xdef",
            timestamp=datetime.now(),
            blockchain="ethereum"
        )
        
        request = PathfindingRequest(
            source_address="0x123",
            target_address="0x789",
            blockchain="ethereum"
        )
        
        path = await pathfinder._create_transaction_path(graph, ["0x123", "0x456", "0x789"], request)
        
        assert path is not None
        assert path.addresses == ["0x123", "0x456", "0x789"]
        assert len(path.transactions) == 2
        assert path.hop_count == 2
        assert path.total_amount == 1.5
        assert path.path_type == "standard"
    
    def test_calculate_path_risk_score(self, pathfinder):
        """Test path risk score calculation"""
        
        # Create transactions with different risk factors
        transactions = [
            TransactionEdge(
                from_address="0x123",
                to_address="0x456",
                transaction_hash="0xabc",
                amount=100.0,  # Medium amount
                timestamp=datetime.now(timezone.utc) - timedelta(hours=1),  # Recent
                blockchain="ethereum"
            ),
            TransactionEdge(
                from_address="0x456",
                to_address="0x789",
                transaction_hash="0xdef",
                amount=15000.0,  # High amount
                timestamp=datetime.now(timezone.utc) - timedelta(hours=2),  # Recent
                blockchain="ethereum"
            )
        ]
        
        risk_score = pathfinder._calculate_path_risk_score(transactions)
        
        assert 0.0 <= risk_score <= 1.0
        # Should be higher due to high amount transaction
        assert risk_score > 0.1
    
    def test_filter_paths(self, pathfinder):
        """Test filtering paths based on criteria"""
        
        # Create test paths
        paths = [
            TransactionPath(
                addresses=["0x123", "0x456"],
                transactions=[],
                total_amount=100.0,
                hop_count=1,
                path_length=100.0,
                confidence_score=0.8,
                risk_score=0.3
            ),
            TransactionPath(
                addresses=["0x789", "0x012"],
                transactions=[],
                total_amount=50000.0,  # High amount
                hop_count=1,
                path_length=50000.0,
                confidence_score=0.9,
                risk_score=0.7
            ),
            TransactionPath(
                addresses=["0x345", "0x678"],
                transactions=[],
                total_amount=50.0,
                hop_count=10,  # Too many hops
                path_length=50.0,
                confidence_score=0.4,  # Low confidence
                risk_score=0.2
            )
        ]
        
        request = PathfindingRequest(
            source_address="0x123",
            target_address="0x456",
            blockchain="ethereum",
            min_amount=100.0,
            max_amount=10000.0,
            max_hops=5,
            confidence_threshold=0.6
        )
        
        filtered = pathfinder._filter_paths(paths, request)
        
        # Should include first path (within all criteria)
        # Should exclude second path (amount too high)
        # Should exclude third path (too many hops and low confidence)
        assert len(filtered) == 1
        assert filtered[0].total_amount == 100.0
    
    def test_rank_paths(self, pathfinder):
        """Test ranking paths by relevance"""
        
        # Create test paths with different characteristics
        paths = [
            TransactionPath(
                addresses=["0x123", "0x456"],
                transactions=[],
                total_amount=100.0,
                hop_count=3,  # Longer path
                path_length=100.0,
                confidence_score=0.7,
                risk_score=0.5
            ),
            TransactionPath(
                addresses=["0x789", "0x012"],
                transactions=[],
                total_amount=1000.0,  # Higher amount
                hop_count=1,  # Shorter path
                path_length=1000.0,
                confidence_score=0.9,
                risk_score=0.2
            )
        ]
        
        request = PathfindingRequest(
            source_address="0x123",
            target_address="0x456",
            blockchain="ethereum"
        )
        
        ranked = pathfinder._rank_paths(paths, request)
        
        # Second path should be ranked higher (shorter, higher amount, higher confidence, lower risk)
        assert len(ranked) == 2
        assert ranked[0].hop_count == 1
        assert ranked[1].hop_count == 3
    
    def test_generate_cache_key(self, pathfinder):
        """Test cache key generation"""
        
        request = PathfindingRequest(
            source_address="0x123",
            target_address="0x456",
            blockchain="ethereum",
            algorithm=PathfindingAlgorithm.ALL_PATHS,
            max_hops=10,
            time_window_hours=168,
            confidence_threshold=0.5
        )
        
        cache_key = pathfinder._generate_cache_key(request)
        
        assert isinstance(cache_key, str)
        assert "0x123" in cache_key
        assert "0x456" in cache_key
        assert "ethereum" in cache_key
        assert "all_paths" in cache_key
    
    def test_get_pathfinder_singleton(self):
        """Test that get_pathfinder returns singleton instance"""
        pathfinder1 = get_pathfinder()
        pathfinder2 = get_pathfinder()
        
        assert pathfinder1 is pathfinder2


@pytest.mark.asyncio
async def test_pathfinder_integration():
    """Integration test for pathfinder"""
    
    pathfinder = MultiRoutePathfinder()
    
    # Test initialization
    await pathfinder.initialize()
    assert pathfinder._initialized is True
    
    # Test basic functionality with mocked dependencies
    with patch.object(pathfinder, '_build_transaction_graph') as mock_build:
        # Create a simple test graph
        graph = nx.DiGraph()
        graph.add_edge("0x123", "0x456", amount=1.0, transaction_hash="0xabc", timestamp=datetime.now())
        graph.add_edge("0x456", "0x789", amount=0.5, transaction_hash="0xdef", timestamp=datetime.now())
        
        mock_build.return_value = graph
        
        request = PathfindingRequest(
            source_address="0x123",
            target_address="0x789",
            blockchain="ethereum",
            algorithm=PathfindingAlgorithm.SHORTEST_PATH
        )
        
        result = await pathfinder.find_paths(request)
        
        assert isinstance(result, PathfindingResult)
        assert result.source_address == "0x123"
        assert result.target_address == "0x789"
        assert result.blockchain == "ethereum"
