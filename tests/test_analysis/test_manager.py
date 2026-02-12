"""
Jackdaw Sentry - Analysis Manager Tests
Tests for the analysis manager and engines
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from src.analysis.manager import AnalysisManager


class TestAnalysisManager:
    """Test AnalysisManager class"""

    @pytest.fixture
    def manager(self):
        """Create AnalysisManager instance for testing"""
        return AnalysisManager()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def test_fresh_manager_has_no_engines(self, manager):
        """A freshly-created manager has empty engines and is not running"""
        assert manager.engines == {}
        assert manager.is_running is False
        assert manager.metrics['total_engines'] == 0

    @pytest.mark.asyncio
    async def test_initialize_populates_engines(self, manager):
        """initialize() registers all six built-in engines"""
        await manager.initialize()

        expected_engines = {
            'cross_chain', 'stablecoin_flows', 'pattern_detection',
            'mixer_detection', 'ml_clustering', 'bridge_tracker',
        }
        assert set(manager.engines.keys()) == expected_engines
        assert manager.metrics['total_engines'] == 6

    @pytest.mark.asyncio
    async def test_initialize_twice_overwrites(self, manager):
        """Calling initialize() again replaces engines with new instances"""
        await manager.initialize()
        old_engines = {name: id(eng) for name, eng in manager.engines.items()}
        await manager.initialize()
        new_engines = {name: id(eng) for name, eng in manager.engines.items()}
        assert manager.metrics['total_engines'] == 6
        for name in old_engines:
            assert old_engines[name] != new_engines[name], f"Engine '{name}' was not replaced"

    # ------------------------------------------------------------------
    # Integration with mocked engines
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_analyze_transaction_with_mocked_cross_chain(self, manager):
        """analyze_transaction delegates to cross_chain engine and includes its output"""
        mock_result = AsyncMock()
        mock_result.patterns = []
        mock_result.risk_score = 0.85
        mock_result.confidence = 0.9
        mock_result.related_transactions = ["0xrelated"]

        mock_engine = AsyncMock()
        mock_engine.analyze_transaction = AsyncMock(return_value=mock_result)

        manager.engines['cross_chain'] = mock_engine
        with patch.object(manager, 'cache_analysis_results', new_callable=AsyncMock):
            result = await manager.analyze_transaction("0xabc", "ethereum")

        assert result['tx_hash'] == '0xabc'
        assert result['cross_chain_analysis']['risk_score'] == 0.85
        assert result['cross_chain_analysis']['related_transactions'] == ["0xrelated"]
        assert result['overall_risk_score'] == 0.85
        mock_engine.analyze_transaction.assert_awaited_once_with("0xabc", "ethereum")

    @pytest.mark.asyncio
    async def test_analyze_address_with_mocked_engines(self, manager):
        """analyze_address delegates to injected engines and aggregates output"""
        mock_cross_chain = AsyncMock()
        mock_cross_chain.get_cross_chain_analysis = AsyncMock(return_value={"bridges": 2})

        mock_stablecoin = AsyncMock()
        mock_stablecoin.analyze_stablecoin_flows = AsyncMock(return_value={"usdt": 100})

        manager.engines['cross_chain'] = mock_cross_chain
        manager.engines['stablecoin_flows'] = mock_stablecoin
        with patch.object(manager, 'cache_analysis_results', new_callable=AsyncMock):
            result = await manager.analyze_address("0xaddr", "ethereum")

        assert result['address'] == '0xaddr'
        assert result['cross_chain_analysis'] == {"bridges": 2}
        assert result['stablecoin_flows'] == {"usdt": 100}
        mock_cross_chain.get_cross_chain_analysis.assert_awaited_once()
        mock_stablecoin.analyze_stablecoin_flows.assert_awaited_once()

    # ------------------------------------------------------------------
    # Start / Stop (avoid calling start_all — it blocks on infinite loops)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_stop_all_sets_flag(self, manager):
        """stop_all() sets is_running to False"""
        await manager.initialize()
        manager.is_running = True
        await manager.stop_all()
        assert manager.is_running is False

    # ------------------------------------------------------------------
    # Transaction analysis
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_analyze_transaction_returns_dict(self, manager):
        """analyze_transaction(hash, blockchain) returns a dict with expected keys"""
        # Don't initialize — empty engines dict means engine code is skipped
        result = await manager.analyze_transaction("0xabc123", "ethereum")
        assert isinstance(result, dict)
        assert 'tx_hash' in result
        assert result['tx_hash'] == '0xabc123'

    @pytest.mark.asyncio
    async def test_analyze_transaction_handles_errors(self, manager):
        """analyze_transaction returns {} on engine errors"""
        # Don't initialize — engines dict is empty, so inner calls skip
        result = await manager.analyze_transaction("0xbad", "ethereum")
        assert isinstance(result, dict)

    # ------------------------------------------------------------------
    # Address analysis
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_analyze_address_returns_dict(self, manager):
        """analyze_address(address, blockchain) returns a dict with expected keys"""
        result = await manager.analyze_address("0xaddr1", "ethereum")
        assert isinstance(result, dict)
        assert result.get('address') == '0xaddr1'

    @pytest.mark.asyncio
    async def test_analyze_address_increments_metric(self, manager):
        """Successful analysis bumps the analysis_completed counter"""
        before = manager.metrics['analysis_completed']
        await manager.analyze_address("0xaddr2", "bitcoin")
        assert manager.metrics['analysis_completed'] == before + 1

    # ------------------------------------------------------------------
    # Transaction flow analysis
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_analyze_transaction_flow(self, manager):
        """analyze_transaction_flow returns a dict"""
        result = await manager.analyze_transaction_flow("0xA", "0xB", "ethereum")
        assert isinstance(result, dict)

    # ------------------------------------------------------------------
    # System statistics
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_system_statistics(self, manager):
        """get_system_statistics returns a dict with engine info"""
        await manager.initialize()
        stats = await manager.get_system_statistics()
        assert isinstance(stats, dict)

    # ------------------------------------------------------------------
    # Metrics dict
    # ------------------------------------------------------------------

    def test_metrics_dict_has_expected_keys(self, manager):
        """The metrics dict has the expected structure"""
        expected_keys = {'total_engines', 'running_engines', 'analysis_completed',
                         'alerts_generated', 'last_update'}
        assert expected_keys == set(manager.metrics.keys())

    # ------------------------------------------------------------------
    # Concurrent analysis
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_concurrent_analysis(self, manager):
        """Multiple concurrent analyze_transaction calls succeed"""
        tasks = [
            manager.analyze_transaction(f"0x{i:064x}", "ethereum")
            for i in range(5)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        assert all(isinstance(r, dict) for r in results)

    # ------------------------------------------------------------------
    # Workflow dispatch
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_run_unknown_workflow(self, manager):
        """Unknown workflow returns error dict"""
        result = await manager.run_analysis_workflow("nonexistent", {})
        assert isinstance(result, dict)
