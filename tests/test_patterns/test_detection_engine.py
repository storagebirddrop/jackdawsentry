"""
Tests for pattern detection engine
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from src.patterns.detection_engine import AdvancedPatternDetector, get_pattern_detector
from src.patterns.models import (
    PatternRequest, PatternAnalysisResult, PatternResult,
    PatternType, PatternSeverity, PatternEvidence
)


class TestAdvancedPatternDetector:
    """Test cases for AdvancedPatternDetector"""
    
    @pytest.fixture
    async def pattern_detector(self):
        """Create pattern detector instance"""
        detector = AdvancedPatternDetector()
        await detector.initialize()
        return detector
    
    @pytest.fixture
    def sample_transactions(self):
        """Create sample transactions for testing"""
        from src.patterns.algorithms.peeling_chain import Transaction
        
        base_time = datetime.now(timezone.utc)
        
        return [
            Transaction(
                hash="0x1",
                address="0x1234567890123456789012345678901234567890",
                amount=1.0,
                timestamp=base_time,
                recipient="0x1111111111111111111111111111111111111111",
                sender="0x1234567890123456789012345678901234567890",
                blockchain="ethereum"
            ),
            Transaction(
                hash="0x2",
                address="0x1234567890123456789012345678901234567890",
                amount=0.5,
                timestamp=base_time + timedelta(hours=1),
                recipient="0x2222222222222222222222222222222222222222",
                sender="0x1234567890123456789012345678901234567890",
                blockchain="ethereum"
            ),
            Transaction(
                hash="0x3",
                address="0x1234567890123456789012345678901234567890",
                amount=0.25,
                timestamp=base_time + timedelta(hours=2),
                recipient="0x3333333333333333333333333333333333333333",
                sender="0x1234567890123456789012345678901234567890",
                blockchain="ethereum"
            )
        ]
    
    @pytest.mark.asyncio
    async def test_initialize(self, pattern_detector):
        """Test pattern detector initialization"""
        assert pattern_detector._initialized is True
    
    @pytest.mark.asyncio
    async def test_analyze_address_patterns_no_transactions(self, pattern_detector):
        """Test pattern analysis with no transactions"""
        
        with patch.object(pattern_detector, '_get_transaction_history') as mock_history:
            mock_history.return_value = []
            
            result = await pattern_detector.analyze_address_patterns(
                address="0x1234567890123456789012345678901234567890",
                blockchain="ethereum"
            )
            
            assert result.address == "0x1234567890123456789012345678901234567890"
            assert result.blockchain == "ethereum"
            assert len(result.patterns) == 0
            assert result.overall_risk_score == 0.0
    
    @pytest.mark.asyncio
    async def test_analyze_address_patterns_with_transactions(self, pattern_detector, sample_transactions):
        """Test pattern analysis with transactions"""
        
        with patch.object(pattern_detector, '_get_transaction_history') as mock_history:
            mock_history.return_value = sample_transactions
            
            # Mock peeling chain detection
            with patch.object(pattern_detector.detectors[PatternType.PEELING_CHAIN], 'detect_peeling_chain') as mock_peeling:
                mock_peeling.return_value = PatternResult(
                    pattern_id="peeling_chain",
                    pattern_name="Peeling Chain Detection",
                    detected=True,
                    confidence_score=0.85,
                    severity=PatternSeverity.HIGH,
                    evidence=[],
                    indicators_met=["sequential_decreasing_amounts"],
                    indicators_missed=[],
                    transaction_count=3,
                    time_window_hours=24
                )
                
                result = await pattern_detector.analyze_address_patterns(
                    address="0x1234567890123456789012345678901234567890",
                    blockchain="ethereum"
                )
                
                assert result.address == "0x1234567890123456789012345678901234567890"
                assert result.blockchain == "ethereum"
                assert len(result.patterns) == 1
                assert result.overall_risk_score > 0.0
                assert result.total_transactions_analyzed == len(sample_transactions)
    
    @pytest.mark.asyncio
    async def test_analyze_address_patterns_cache_hit(self, pattern_detector):
        """Test pattern analysis cache functionality"""
        
        address = "0x1234567890123456789012345678901234567890"
        blockchain = "ethereum"
        
        # Create cached result
        cached_result = PatternAnalysisResult(
            address=address,
            blockchain=blockchain,
            patterns=[],
            overall_risk_score=0.0,
            total_transactions_analyzed=0,
            analysis_timestamp=datetime.now(timezone.utc)
        )
        
        cache_key = f"{address}:{blockchain}:24:0.5"
        pattern_detector.cache[cache_key] = {
            'result': cached_result,
            'timestamp': datetime.now(timezone.utc)
        }
        
        result = await pattern_detector.analyze_address_patterns(
            address=address,
            blockchain=blockchain
        )
        
        assert result == cached_result
        assert pattern_detector.metrics['cache_hit_rate'] > 0.0
    
    @pytest.mark.asyncio
    async def test_batch_analyze_patterns(self, pattern_detector):
        """Test batch pattern analysis"""
        
        request = PatternRequest(
            addresses=[
                "0x1234567890123456789012345678901234567890",
                "0x0987654321098765432109876543210987654321"
            ],
            blockchain="ethereum",
            min_confidence=0.5
        )
        
        with patch.object(pattern_detector, 'analyze_address_patterns') as mock_analyze:
            mock_result = MagicMock(
                address="0x1234567890123456789012345678901234567890",
                blockchain="ethereum",
                patterns=[],
                overall_risk_score=0.0
            )
            mock_analyze.return_value = mock_result
            
            results = await pattern_detector.batch_analyze_patterns(request)
            
            assert len(results) == 2
            assert "0x1234567890123456789012345678901234567890" in results
            assert "0x0987654321098765432109876543210987654321" in results
            assert mock_analyze.call_count == 2
    
    def test_calculate_overall_risk_score(self, pattern_detector):
        """Test overall risk score calculation"""
        
        # Create pattern results with different severities
        patterns = [
            PatternResult(
                pattern_id="test1",
                pattern_name="Test Pattern 1",
                detected=True,
                confidence_score=0.8,
                severity=PatternSeverity.HIGH,
                evidence=[],
                indicators_met=[],
                indicators_missed=[],
                transaction_count=1,
                time_window_hours=24
            ),
            PatternResult(
                pattern_id="test2",
                pattern_name="Test Pattern 2",
                detected=True,
                confidence_score=0.6,
                severity=PatternSeverity.MEDIUM,
                evidence=[],
                indicators_met=[],
                indicators_missed=[],
                transaction_count=1,
                time_window_hours=24
            )
        ]
        
        risk_score = pattern_detector._calculate_overall_risk_score(patterns)
        
        # Should be weighted by severity (HIGH = 0.6, MEDIUM = 0.3)
        expected_high = 0.8 * 0.6  # 0.48
        expected_medium = 0.6 * 0.3  # 0.18
        expected_max = max(expected_high, expected_medium)  # 0.48
        
        assert abs(risk_score - expected_max) < 0.01
    
    def test_get_pattern_detector_singleton(self):
        """Test that get_pattern_detector returns singleton instance"""
        detector1 = get_pattern_detector()
        detector2 = get_pattern_detector()
        
        assert detector1 is detector2
    
    def test_get_metrics(self, pattern_detector):
        """Test metrics collection"""
        
        # Add some mock data
        pattern_detector.metrics['total_detections'] = 10
        pattern_detector.metrics['patterns_detected'] = {'peeling_chain': 5}
        pattern_detector.metrics['avg_processing_time'] = 150.0
        
        metrics = pattern_detector.get_metrics()
        
        assert metrics['total_detections'] == 10
        assert metrics['patterns_detected']['peeling_chain'] == 5
        assert metrics['avg_processing_time'] == 150.0
        assert 'enabled_patterns' in metrics
        assert 'total_algorithms' in metrics
        assert 'generated_at' in metrics
    
    def test_clear_cache(self, pattern_detector):
        """Test cache clearing"""
        
        # Add some cached data
        pattern_detector.cache['test_key'] = {'result': 'test'}
        
        assert len(pattern_detector.cache) == 1
        
        pattern_detector.clear_cache()
        
        assert len(pattern_detector.cache) == 0


@pytest.mark.asyncio
async def test_pattern_detector_integration():
    """Integration test for pattern detector"""
    
    detector = AdvancedPatternDetector()
    
    # Test initialization
    await detector.initialize()
    assert detector._initialized is True
    
    # Test basic functionality with mocked dependencies
    with patch.object(detector, '_get_transaction_history', return_value=[]):
        
        result = await detector.analyze_address_patterns(
            address="0x1234567890123456789012345678901234567890",
            blockchain="ethereum"
        )
        
        assert isinstance(result, PatternAnalysisResult)
        assert result.address == "0x1234567890123456789012345678901234567890"
        assert result.blockchain == "ethereum"
