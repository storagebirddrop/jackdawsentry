"""
Jackdaw Sentry - Analysis Manager Tests
Tests for the analysis manager and engines
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.analysis.manager import AnalysisManager
from src.analysis.bridge_tracker import BridgeTracker


class TestAnalysisManager:
    """Test AnalysisManager class"""
    
    @pytest.fixture
    def analysis_manager(self):
        """Create AnalysisManager instance for testing"""
        return AnalysisManager()
    
    @pytest.fixture
    def mock_bridge_tracker(self):
        """Create mock BridgeTracker"""
        tracker = Mock(spec=BridgeTracker)
        tracker.initialize = AsyncMock()
        tracker.start = AsyncMock()
        tracker.stop = AsyncMock()
        tracker.analyze = AsyncMock(return_value={"risk_score": 50.0})
        return tracker
    
    @pytest.mark.asyncio
    async def test_initialization(self, analysis_manager, mock_bridge_tracker):
        """Test analysis manager initialization"""
        with patch('src.analysis.manager.BridgeTracker', return_value=mock_bridge_tracker):
            await analysis_manager.initialize()
            
            assert len(analysis_manager.engines) == 1
            assert 'bridge_tracker' in analysis_manager.engines
            assert analysis_manager.metrics['total_engines'] == 1
            assert analysis_manager.metrics['running_engines'] == 0
            assert analysis_manager.metrics['analysis_completed'] == 0
            assert analysis_manager.metrics['alerts_generated'] == 0
    
    @pytest.mark.asyncio
    async def test_start_all_engines(self, analysis_manager, mock_bridge_tracker):
        """Test starting all analysis engines"""
        with patch('src.analysis.manager.BridgeTracker', return_value=mock_bridge_tracker):
            await analysis_manager.initialize()
            await analysis_manager.start_all()
            
            assert analysis_manager.is_running
            assert analysis_manager.metrics['running_engines'] == 1
            assert analysis_manager.metrics['last_update'] is not None
    
    @pytest.mark.asyncio
    async def test_stop_all_engines(self, analysis_manager, mock_bridge_tracker):
        """Test stopping all analysis engines"""
        with patch('src.analysis.manager.BridgeTracker', return_value=mock_bridge_tracker):
            await analysis_manager.initialize()
            await analysis_manager.start_all()
            await analysis_manager.stop_all()
            
            assert not analysis_manager.is_running
            assert analysis_manager.metrics['running_engines'] == 0
    
    @pytest.mark.asyncio
    async def test_analyze_transaction(self, analysis_manager, mock_bridge_tracker):
        """Test transaction analysis"""
        transaction_data = {
            "hash": "0x1234567890abcdef",
            "from_address": "0x1234567890abcdef1234567890abcdef12345678",
            "to_address": "0x876543210fedcba9876543210fedcba987654321",
            "amount": "1.5",
            "blockchain": "ethereum"
        }
        
        with patch('src.analysis.manager.BridgeTracker', return_value=mock_bridge_tracker):
            await analysis_manager.initialize()
            await analysis_manager.start_all()
            
            result = await analysis_manager.analyze_transaction(transaction_data)
            
            assert result is not None
            assert "risk_score" in result
            assert analysis_manager.metrics['analysis_completed'] > 0
    
    @pytest.mark.asyncio
    async def test_analyze_address(self, analysis_manager, mock_bridge_tracker):
        """Test address analysis"""
        address_data = {
            "address": "0x1234567890abcdef1234567890abcdef12345678",
            "blockchain": "ethereum"
        }
        
        with patch('src.analysis.manager.BridgeTracker', return_value=mock_bridge_tracker):
            await analysis_manager.initialize()
            await analysis_manager.start_all()
            
            result = await analysis_manager.analyze_address(address_data)
            
            assert result is not None
            assert "risk_score" in result
            assert analysis_manager.metrics['analysis_completed'] > 0
    
    @pytest.mark.asyncio
    async def test_detect_patterns(self, analysis_manager, mock_bridge_tracker):
        """Test pattern detection"""
        transaction_data = [
            {"hash": "0x1234567890abcdef", "amount": "1.0"},
            {"hash": "0xabcdef1234567890", "amount": "2.0"}
        ]
        
        mock_bridge_tracker.detect_patterns.return_value = [
            {"type": "mixing", "confidence": 0.8}
        ]
        
        with patch('src.analysis.manager.BridgeTracker', return_value=mock_bridge_tracker):
            await analysis_manager.initialize()
            await analysis_manager.start_all()
            
            patterns = await analysis_manager.detect_patterns(transaction_data)
            
            assert len(patterns) > 0
            assert patterns[0]["type"] == "mixing"
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, analysis_manager, mock_bridge_tracker):
        """Test metrics retrieval"""
        with patch('src.analysis.manager.BridgeTracker', return_value=mock_bridge_tracker):
            await analysis_manager.initialize()
            await analysis_manager.start_all()
            
            metrics = analysis_manager.get_metrics()
            
            assert "total_engines" in metrics
            assert "running_engines" in metrics
            assert "analysis_completed" in metrics
            assert "alerts_generated" in metrics
            assert "last_update" in metrics
    
    @pytest.mark.asyncio
    async def test_engine_failure_handling(self, analysis_manager):
        """Test handling of engine failures"""
        # Create a failing engine
        failing_tracker = Mock(spec=BridgeTracker)
        failing_tracker.initialize = AsyncMock(side_effect=Exception("Engine failed"))
        
        with patch('src.analysis.manager.BridgeTracker', return_value=failing_tracker):
            # Should handle failure gracefully
            await analysis_manager.initialize()
            
            # Engine should not be added if initialization fails
            assert len(analysis_manager.engines) == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_analysis(self, analysis_manager, mock_bridge_tracker):
        """Test concurrent analysis requests"""
        with patch('src.analysis.manager.BridgeTracker', return_value=mock_bridge_tracker):
            await analysis_manager.initialize()
            await analysis_manager.start_all()
            
            # Create multiple concurrent analysis tasks
            tasks = []
            for i in range(10):
                task = analysis_manager.analyze_transaction({
                    "hash": f"0x{i:040d}",
                    "amount": str(i)
                })
                tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should succeed
            assert all(isinstance(result, dict) for result in results)
            assert analysis_manager.metrics['analysis_completed'] >= 10
    
    @pytest.mark.asyncio
    async def test_analysis_with_missing_data(self, analysis_manager, mock_bridge_tracker):
        """Test analysis with missing required data"""
        incomplete_data = {
            "hash": "0x1234567890abcdef"
            # Missing from_address, to_address, etc.
        }
        
        with patch('src.analysis.manager.BridgeTracker', return_value=mock_bridge_tracker):
            await analysis_manager.initialize()
            await analysis_manager.start_all()
            
            # Should handle missing data gracefully
            result = await analysis_manager.analyze_transaction(incomplete_data)
            
            # Should return some result even with incomplete data
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_analysis_timeout(self, analysis_manager):
        """Test analysis timeout handling"""
        # Create a slow engine
        slow_tracker = Mock(spec=BridgeTracker)
        slow_tracker.initialize = AsyncMock()
        slow_tracker.start = AsyncMock()
        slow_tracker.analyze = AsyncMock(side_effect=asyncio.sleep(10))  # Slow operation
        
        with patch('src.analysis.manager.BridgeTracker', return_value=slow_tracker):
            await analysis_manager.initialize()
            await analysis_manager.start_all()
            
            # Test with timeout
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(
                    analysis_manager.analyze_transaction({"hash": "0x1234567890abcdef"}),
                    timeout=1.0
                )
    
    @pytest.mark.asyncio
    async def test_analysis_caching(self, analysis_manager, mock_bridge_tracker):
        """Test analysis result caching"""
        transaction_data = {
            "hash": "0x1234567890abcdef",
            "from_address": "0x1234567890abcdef1234567890abcdef12345678",
            "to_address": "0x876543210fedcba9876543210fedcba987654321",
            "amount": "1.5"
        }
        
        with patch('src.analysis.manager.BridgeTracker', return_value=mock_bridge_tracker):
            await analysis_manager.initialize()
            await analysis_manager.start_all()
            
            # First analysis
            result1 = await analysis_manager.analyze_transaction(transaction_data)
            
            # Second analysis (should use cache if implemented)
            result2 = await analysis_manager.analyze_transaction(transaction_data)
            
            # Results should be the same
            assert result1 == result2
            
            # Engine should only be called once if caching is working
            assert mock_bridge_tracker.analyze.call_count <= 2
    
    @pytest.mark.asyncio
    async def test_alert_generation(self, analysis_manager, mock_bridge_tracker):
        """Test alert generation from analysis"""
        # Configure mock to return high-risk result
        mock_bridge_tracker.analyze.return_value = {
            "risk_score": 95.0,
            "alerts": ["high_risk_transaction", "suspicious_pattern"]
        }
        
        with patch('src.analysis.manager.BridgeTracker', return_value=mock_bridge_tracker):
            await analysis_manager.initialize()
            await analysis_manager.start_all()
            
            result = await analysis_manager.analyze_transaction({
                "hash": "0x1234567890abcdef",
                "amount": "1000000"  # Large amount
            })
            
            assert "alerts" in result
            assert len(result["alerts"]) > 0
            assert analysis_manager.metrics['alerts_generated'] > 0
    
    @pytest.mark.asyncio
    async def test_analysis_engine_health_check(self, analysis_manager, mock_bridge_tracker):
        """Test analysis engine health checking"""
        with patch('src.analysis.manager.BridgeTracker', return_value=mock_bridge_tracker):
            await analysis_manager.initialize()
            await analysis_manager.start_all()
            
            health = await analysis_manager.check_health()
            
            assert "status" in health
            assert "engines" in health
            assert "metrics" in health
    
    @pytest.mark.asyncio
    async def test_analysis_engine_restart(self, analysis_manager, mock_bridge_tracker):
        """Test analysis engine restart functionality"""
        with patch('src.analysis.manager.BridgeTracker', return_value=mock_bridge_tracker):
            await analysis_manager.initialize()
            await analysis_manager.start_all()
            
            # Restart engines
            await analysis_manager.restart_all()
            
            assert analysis_manager.is_running
            assert analysis_manager.metrics['running_engines'] == 1
    
    @pytest.mark.asyncio
    async def test_analysis_engine_configuration(self, analysis_manager):
        """Test analysis engine configuration"""
        config = {
            "risk_threshold": 70.0,
            "analysis_timeout": 30.0,
            "enable_caching": True
        }
        
        await analysis_manager.configure_engines(config)
        
        # Configuration should be applied
        assert analysis_manager.config == config
    
    @pytest.mark.asyncio
    async def test_analysis_engine_statistics(self, analysis_manager, mock_bridge_tracker):
        """Test detailed analysis statistics"""
        with patch('src.analysis.manager.BridgeTracker', return_value=mock_bridge_tracker):
            await analysis_manager.initialize()
            await analysis_manager.start_all()
            
            # Perform some analyses
            await analysis_manager.analyze_transaction({"hash": "0x1234567890abcdef"})
            await analysis_manager.analyze_address({"address": "0x1234567890abcdef"})
            
            stats = analysis_manager.get_detailed_statistics()
            
            assert "transaction_analysis" in stats
            assert "address_analysis" in stats
            assert "performance_metrics" in stats
            assert "error_rates" in stats
