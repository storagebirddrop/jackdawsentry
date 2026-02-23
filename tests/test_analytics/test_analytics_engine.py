"""
Tests for advanced analytics engine
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.analytics.analytics_engine import AdvancedAnalyticsEngine, get_analytics_engine
from src.analytics.models import (
    AnalyticsRequest, AnalyticsResponse, PathfindingRequest, PathfindingResult,
    SeedAnalysisRequest, SeedAnalysisResult, FingerprintingRequest, FingerprintResult,
    BatchAnalyticsRequest, BatchAnalyticsResponse
)


class TestAdvancedAnalyticsEngine:
    """Test cases for AdvancedAnalyticsEngine"""
    
    @pytest.fixture
    async def analytics_engine(self):
        """Create analytics engine instance"""
        engine = AdvancedAnalyticsEngine()
        await engine.initialize()
        return engine
    
    @pytest.mark.asyncio
    async def test_initialize(self, analytics_engine):
        """Test analytics engine initialization"""
        assert analytics_engine._initialized is True
    
    @pytest.mark.asyncio
    async def test_process_pathfinding_request(self, analytics_engine):
        """Test processing pathfinding request"""
        
        request = AnalyticsRequest(
            request_type="pathfinding",
            parameters={
                "source_address": "0x1234567890123456789012345678901234567890",
                "target_address": "0x0987654321098765432109876543210987654321",
                "blockchain": "ethereum",
                "algorithm": "all_paths"
            }
        )
        
        with patch.object(analytics_engine.pathfinder, 'find_paths') as mock_find:
            mock_result = MagicMock(
                source_address="0x1234567890123456789012345678901234567890",
                target_address="0x0987654321098765432109876543210987654321",
                blockchain="ethereum",
                algorithm="all_paths",
                paths=[],
                total_paths_found=0,
                processing_time_ms=100.0
            )
            mock_find.return_value = mock_result
            
            response = await analytics_engine.process_request(request)
            
            assert response.status == "completed"
            assert response.request_type == "pathfinding"
            assert response.result == mock_result
            assert response.processing_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_process_seed_analysis_request(self, analytics_engine):
        """Test processing seed analysis request"""
        
        request = AnalyticsRequest(
            request_type="seed_analysis",
            parameters={
                "seed_phrase": "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
                "derivation_types": ["bip44"],
                "blockchains": ["bitcoin", "ethereum"],
                "max_derivations": 10
            }
        )
        
        with patch.object(analytics_engine.seed_analyzer, 'analyze_seed_phrase') as mock_analyze:
            mock_result = MagicMock(
                seed_phrase_hash="abc123",
                derivations=[],
                total_wallets=0,
                active_wallets=0,
                total_balance=0.0,
                blockchains=set(),
                processing_time_ms=200.0
            )
            mock_analyze.return_value = mock_result
            
            response = await analytics_engine.process_request(request)
            
            assert response.status == "completed"
            assert response.request_type == "seed_analysis"
            assert response.result == mock_result
            assert response.processing_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_process_fingerprinting_request(self, analytics_engine):
        """Test processing fingerprinting request"""
        
        request = AnalyticsRequest(
            request_type="fingerprinting",
            parameters={
                "query_type": "amount_pattern",
                "query_parameters": {},
                "blockchain": "ethereum",
                "min_confidence": 0.5
            }
        )
        
        with patch.object(analytics_engine.fingerprinter, 'fingerprint_transactions') as mock_fingerprint:
            mock_result = MagicMock(
                query_parameters={},
                matched_patterns=[],
                confidence_score=0.0,
                match_count=0,
                processing_time_ms=150.0
            )
            mock_fingerprint.return_value = mock_result
            
            response = await analytics_engine.process_request(request)
            
            assert response.status == "completed"
            assert response.request_type == "fingerprinting"
            assert response.result == mock_result
            assert response.processing_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_process_batch_request(self, analytics_engine):
        """Test processing batch request"""
        
        request = AnalyticsRequest(
            request_type="batch",
            parameters={
                "requests": [
                    AnalyticsRequest(
                        request_type="pathfinding",
                        parameters={"source_address": "0x123", "target_address": "0x456", "blockchain": "ethereum"}
                    ),
                    AnalyticsRequest(
                        request_type="fingerprinting",
                        parameters={"query_type": "amount_pattern"}
                    )
                ],
                "parallel_processing": True,
                "max_concurrent": 2
            }
        )
        
        with patch.object(analytics_engine, 'process_batch_requests') as mock_batch:
            mock_response = BatchAnalyticsResponse(
                batch_id="test-batch",
                results=[],
                successful_requests=2,
                failed_requests=0,
                total_processing_time_ms=300.0
            )
            mock_batch.return_value = mock_response
            
            response = await analytics_engine.process_request(request)
            
            assert response.status == "completed"
            assert response.request_type == "batch"
            assert isinstance(response.result, BatchAnalyticsResponse)
    
    @pytest.mark.asyncio
    async def test_process_invalid_request_type(self, analytics_engine):
        """Test processing invalid request type"""
        
        request = AnalyticsRequest(
            request_type="invalid_type",
            parameters={}
        )
        
        response = await analytics_engine.process_request(request)
        
        assert response.status == "failed"
        assert "Unsupported request type" in response.error_message
    
    @pytest.mark.asyncio
    async def test_process_batch_requests_parallel(self, analytics_engine):
        """Test batch processing with parallel execution"""
        
        requests = [
            AnalyticsRequest(request_type="pathfinding", parameters={}),
            AnalyticsRequest(request_type="fingerprinting", parameters={})
        ]
        
        batch_request = BatchAnalyticsRequest(
            requests=requests,
            parallel_processing=True,
            max_concurrent=2
        )
        
        with patch.object(analytics_engine, 'process_request') as mock_process:
            # Mock successful responses
            mock_process.side_effect = [
                AnalyticsResponse(
                    request_id="1",
                    request_type="pathfinding",
                    status="completed",
                    processing_time_ms=100.0
                ),
                AnalyticsResponse(
                    request_id="2",
                    request_type="fingerprinting",
                    status="completed",
                    processing_time_ms=150.0
                )
            ]
            
            result = await analytics_engine.process_batch_requests(batch_request)
            
            assert result.successful_requests == 2
            assert result.failed_requests == 0
            assert len(result.results) == 2
            assert result.total_processing_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_process_batch_requests_sequential(self, analytics_engine):
        """Test batch processing with sequential execution"""
        
        requests = [
            AnalyticsRequest(request_type="pathfinding", parameters={}),
            AnalyticsRequest(request_type="fingerprinting", parameters={})
        ]
        
        batch_request = BatchAnalyticsRequest(
            requests=requests,
            parallel_processing=False,
            max_concurrent=1
        )
        
        with patch.object(analytics_engine, 'process_request') as mock_process:
            # Mock successful responses
            mock_process.side_effect = [
                AnalyticsResponse(
                    request_id="1",
                    request_type="pathfinding",
                    status="completed",
                    processing_time_ms=100.0
                ),
                AnalyticsResponse(
                    request_id="2",
                    request_type="fingerprinting",
                    status="completed",
                    processing_time_ms=150.0
                )
            ]
            
            result = await analytics_engine.process_batch_requests(batch_request)
            
            assert result.successful_requests == 2
            assert result.failed_requests == 0
            assert len(result.results) == 2
            assert result.total_processing_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_get_analytics_statistics(self, analytics_engine):
        """Test getting analytics statistics"""
        
        # Add some mock data
        analytics_engine.metrics['total_requests'] = 10
        analytics_engine.metrics['pathfinding_requests'] = 5
        analytics_engine.metrics['avg_processing_time'] = 150.0
        
        stats = await analytics_engine.get_analytics_statistics()
        
        assert stats['total_requests'] == 10
        assert stats['pathfinding_requests'] == 5
        assert stats['avg_processing_time'] == 150.0
        assert 'components_initialized' in stats
        assert 'generated_at' in stats
    
    @pytest.mark.asyncio
    async def test_clear_all_caches(self, analytics_engine):
        """Test clearing all caches"""
        
        # Add some mock cache data
        analytics_engine.cache['test_key'] = 'test_value'
        
        with patch.object(analytics_engine.pathfinder, 'clear_cache') as mock_pathfinder, \
             patch.object(analytics_engine.seed_analyzer, 'clear_cache') as mock_seed, \
             patch.object(analytics_engine.fingerprinter, 'clear_cache') as mock_fingerprint:
            
            await analytics_engine.clear_all_caches()
            
            assert len(analytics_engine.cache) == 0
            mock_pathfinder.assert_called_once()
            mock_seed.assert_called_once()
            mock_fingerprint.assert_called_once()
    
    def test_get_analytics_engine_singleton(self):
        """Test that get_analytics_engine returns singleton instance"""
        engine1 = get_analytics_engine()
        engine2 = get_analytics_engine()
        
        assert engine1 is engine2


@pytest.mark.asyncio
async def test_analytics_engine_integration():
    """Integration test for analytics engine"""
    
    engine = AdvancedAnalyticsEngine()
    
    # Test initialization
    await engine.initialize()
    assert engine._initialized is True
    
    # Test basic functionality with mocked dependencies
    with patch.object(engine.pathfinder, 'find_paths') as mock_pathfinder, \
         patch.object(engine.seed_analyzer, 'analyze_seed_phrase') as mock_seed, \
         patch.object(engine.fingerprinter, 'fingerprint_transactions') as mock_fingerprint:
        
        # Mock all methods to return empty results
        mock_pathfinder.return_value = MagicMock(
            source_address="0x123",
            target_address="0x456",
            blockchain="ethereum",
            paths=[],
            total_paths_found=0
        )
        
        mock_seed.return_value = MagicMock(
            seed_phrase_hash="abc123",
            derivations=[],
            total_wallets=0
        )
        
        mock_fingerprint.return_value = MagicMock(
            query_parameters={},
            matched_patterns=[],
            confidence_score=0.0
        )
        
        # Test pathfinding request
        pathfinding_request = AnalyticsRequest(
            request_type="pathfinding",
            parameters={
                "source_address": "0x123",
                "target_address": "0x456",
                "blockchain": "ethereum"
            }
        )
        
        response = await engine.process_request(pathfinding_request)
        assert isinstance(response, AnalyticsResponse)
        assert response.status == "completed"
        assert response.request_type == "pathfinding"
