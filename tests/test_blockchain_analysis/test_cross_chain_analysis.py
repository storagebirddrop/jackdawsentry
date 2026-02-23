"""
Cross-Chain Analysis Testing
Tests cross-chain transaction tracking, bridge detection, and entity linking
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import json
from datetime import datetime, timezone, timedelta


class TestCrossChainAnalysis:
    """Test cross-chain analysis functionality"""

    @pytest.mark.parametrize("bridge_type,from_chain,to_chain,test_addresses", [
        ("bitcoin_ethereum", "bitcoin", "ethereum", ["1...btc", "0x...eth"]),
        ("ethereum_solana", "ethereum", "solana", ["0x...eth", "9Wz...sol"]),
        ("ethereum_bsc", "ethereum", "bsc", ["0x...eth", "0x...bsc"]),
        ("stablecoin_bridge", "ethereum", "polygon", ["0x...eth", "0x...poly"]),
    ])
    def test_bridge_detection_basic(self, client, bridge_type, from_chain, to_chain, test_addresses):
        """Test basic bridge transaction detection"""
        response = client.post("/api/v1/analysis/cross-chain", json={
            "addresses": test_addresses,
            "bridge_type": bridge_type,
            "from_blockchain": from_chain,
            "to_blockchain": to_chain,
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "bridge_transactions" in data
        assert "cross_chain_analysis" in data
        assert "bridge_type" in data
        assert "from_blockchain" in data
        assert "to_blockchain" in data
        
        # Verify bridge type matches
        assert data["bridge_type"] == bridge_type
        assert data["from_blockchain"] == from_chain
        assert data["to_blockchain"] == to_chain
        
        # Should have bridge transactions
        assert isinstance(data["bridge_transactions"], list)

    def test_stablecoin_flow_tracking(self, client):
        """Test stablecoin flow tracking across chains"""
        response = client.post("/api/v1/analysis/stablecoin-flows", json={
            "stablecoin": "USDC",
            "addresses": [
                "0x...eth_usdc",  # Ethereum USDC
                "9Wz...sol_usdc",  # Solana USDC
                "0x...poly_usdc"   # Polygon USDC
            ],
            "blockchains": ["ethereum", "solana", "polygon"],
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "stablecoin_flows" in data
        assert "total_volume" in data
        assert "cross_chain_transfers" in data
        assert "flow_analysis" in data
        
        # Should have flow data
        assert isinstance(data["stablecoin_flows"], list)
        assert isinstance(data["cross_chain_transfers"], list)
        
        # Validate flow structure
        if data["stablecoin_flows"]:
            flow = data["stablecoin_flows"][0]
            assert "from_blockchain" in flow
            assert "to_blockchain" in flow
            assert "amount" in flow
            assert "timestamp" in flow
            assert flow["amount"] > 0

    def test_entity_linking_across_chains(self, client):
        """Test entity attribution across multiple blockchains"""
        response = client.post("/api/v1/analysis/entity-linking", json={
            "addresses": [
                {"address": "1...btc", "blockchain": "bitcoin"},
                {"address": "0x...eth", "blockchain": "ethereum"},
                {"address": "9Wz...sol", "blockchain": "solana"}
            ],
            "linking_type": "same_entity",
            "confidence_threshold": 0.7
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "entity_links" in data
        assert "linked_addresses" in data
        assert "confidence_scores" in data
        assert "entity_attribution" in data
        
        # Should have linking results
        assert isinstance(data["entity_links"], list)
        assert isinstance(data["linked_addresses"], list)
        
        # Validate link structure
        if data["entity_links"]:
            link = data["entity_links"][0]
            assert "address_1" in link
            assert "address_2" in link
            assert "blockchain_1" in link
            assert "blockchain_2" in link
            assert "confidence" in link
            assert "link_type" in link
            assert 0.0 <= link["confidence"] <= 1.0

    def test_bridge_hop_detection(self, client):
        """Test detection of multiple bridge hops"""
        response = client.post("/api/v1/analysis/bridge-hopping", json={
            "addresses": [
                "1...btc_start",
                "0x...eth_bridge1", 
                "9Wz...sol_bridge2",
                "0x...poly_end"
            ],
            "hop_analysis": True,
            "min_hops": 2
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "bridge_hops" in data
        assert "hop_count" in data
        assert "total_hops" in data
        assert "hop_sequence" in data
        
        # Should detect hops
        assert data["hop_count"] >= 0
        assert isinstance(data["hop_sequence"], list)
        
        # Validate hop structure
        if data["bridge_hops"]:
            hop = data["bridge_hops"][0]
            assert "from_blockchain" in hop
            assert "to_blockchain" in hop
            assert "bridge_contract" in hop
            assert "amount" in hop
            assert "timestamp" in hop

    def test_cross_chain_risk_assessment(self, client):
        """Test cross-chain risk assessment"""
        response = client.post("/api/v1/analysis/cross-chain-risk", json={
            "addresses": [
                {"address": "1...btc", "blockchain": "bitcoin"},
                {"address": "0x...eth", "blockchain": "ethereum"}
            ],
            "risk_factors": ["bridge_usage", "privacy_tools", "high_frequency"],
            "include_attribution": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "cross_chain_risk_score" in data
        assert "risk_factors" in data
        assert "risk_breakdown" in data
        assert "recommendations" in data
        
        # Validate risk score
        assert 0.0 <= data["cross_chain_risk_score"] <= 1.0
        
        # Should have risk breakdown
        assert isinstance(data["risk_breakdown"], dict)
        assert isinstance(data["recommendations"], list)

    def test_value_tracking_across_bridges(self, client):
        """Test value preservation tracking across bridges"""
        response = client.post("/api/v1/analysis/value-tracking", json={
            "initial_amount": 1.0,
            "initial_blockchain": "bitcoin",
            "initial_token": "BTC",
            "target_blockchains": ["ethereum", "solana", "polygon"],
            "track_fees": True,
            "track_slippage": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "value_tracking" in data
        assert "final_amounts" in data
        assert "total_fees" in data
        assert "total_slippage" in data
        assert "preservation_rate" in data
        
        # Should have tracking data
        assert isinstance(data["value_tracking"], list)
        assert isinstance(data["final_amounts"], dict)
        
        # Validate value preservation
        assert 0.0 <= data["preservation_rate"] <= 1.0
        assert data["total_fees"] >= 0
        assert data["total_slippage"] >= 0

    def test_multi_chain_investigation(self, client):
        """Test multi-chain investigation workflow"""
        response = client.post("/api/v1/analysis/multi-chain-investigation", json={
            "investigation_id": "inv_123456",
            "addresses": [
                {"address": "1...btc", "blockchain": "bitcoin"},
                {"address": "0x...eth", "blockchain": "ethereum"},
                {"address": "9Wz...sol", "blockchain": "solana"}
            ],
            "analysis_types": ["bridge_tracking", "entity_linking", "pattern_detection"],
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "investigation_id" in data
        assert "cross_chain_findings" in data
        assert "entity_connections" in data
        assert "suspicious_activities" in data
        assert "investigation_summary" in data
        
        # Verify investigation ID
        assert data["investigation_id"] == "inv_123456"
        
        # Should have findings
        assert isinstance(data["cross_chain_findings"], list)
        assert isinstance(data["entity_connections"], list)

    @patch('src.analysis.bridge_tracker.BridgeTracker')
    def test_bridge_detection_with_mock_tracker(self, mock_tracker, client):
        """Test bridge detection with mocked tracker"""
        # Mock bridge detection results
        mock_bridge_tx = MagicMock()
        mock_bridge_tx.from_blockchain = "bitcoin"
        mock_bridge_tx.to_blockchain = "ethereum"
        mock_bridge_tx.amount = 1.0
        mock_bridge_tx.token_symbol = "WBTC"
        mock_bridge_tx.bridge_contract = "0x...bridge"
        mock_bridge_tx.timestamp = datetime.now(timezone.utc)
        
        mock_tracker_instance = MagicMock()
        mock_tracker_instance.detect_bridge_transactions.return_value = [mock_bridge_tx]
        mock_tracker.return_value = mock_tracker_instance
        
        response = client.post("/api/v1/analysis/cross-chain", json={
            "addresses": ["1...btc", "0x...eth"],
            "bridge_type": "bitcoin_ethereum",
            "from_blockchain": "bitcoin",
            "to_blockchain": "ethereum"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have bridge transactions
        assert "bridge_transactions" in data

    def test_cross_chain_analysis_performance(self, client):
        """Test cross-chain analysis performance"""
        import time
        
        start_time = time.time()
        response = client.post("/api/v1/analysis/cross-chain", json={
            "addresses": ["1...btc", "0x...eth"],
            "bridge_type": "bitcoin_ethereum",
            "from_blockchain": "bitcoin",
            "to_blockchain": "ethereum"
        })
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 200
        # Should complete within 3 seconds for basic cross-chain analysis
        assert response_time < 3.0

    def test_cross_chain_analysis_invalid_blockchain(self, client):
        """Test cross-chain analysis with invalid blockchain"""
        response = client.post("/api/v1/analysis/cross-chain", json={
            "addresses": ["1...btc", "0x...eth"],
            "bridge_type": "invalid_ethereum",
            "from_blockchain": "invalid_chain",
            "to_blockchain": "ethereum"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    @pytest.mark.integration
    def test_cross_chain_analysis_with_real_data(self, client):
        """Test cross-chain analysis with real blockchain data (integration test)"""
        response = client.post("/api/v1/analysis/cross-chain", json={
            "addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "0x742d35Cc6634C0532925a3b8D4E7E0E0e9e0dF3"],
            "bridge_type": "bitcoin_ethereum",
            "from_blockchain": "bitcoin",
            "to_blockchain": "ethereum",
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have analyzed real addresses
        assert "bridge_transactions" in data
        assert "cross_chain_analysis" in data


class TestStablecoinAnalysis:
    """Test stablecoin-specific cross-chain analysis"""

    @pytest.mark.parametrize("stablecoin,supported_chains", [
        ("USDC", ["ethereum", "solana", "polygon", "base", "arbitrum"]),
        ("USDT", ["ethereum", "tron", "bsc", "polygon"]),
        ("DAI", ["ethereum", "polygon", "arbitrum"]),
        ("BUSD", ["ethereum", "bsc"]),
    ])
    def test_stablecoin_multi_chain_support(self, client, stablecoin, supported_chains):
        """Test stablecoin support across multiple chains"""
        response = client.post("/api/v1/analysis/stablecoin-support", json={
            "stablecoin": stablecoin,
            "check_chains": supported_chains
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "stablecoin" in data
        assert "supported_chains" in data
        assert "chain_details" in data
        
        # Verify stablecoin
        assert data["stablecoin"] == stablecoin
        
        # Should have chain details
        assert isinstance(data["chain_details"], dict)
        for chain in supported_chains:
            assert chain in data["chain_details"]

    def test_stablecoin_large_transfer_detection(self, client):
        """Test detection of large stablecoin transfers"""
        response = client.post("/api/v1/analysis/stablecoin-large-transfers", json={
            "stablecoin": "USDC",
            "threshold_usd": 100000,  # $100k threshold
            "blockchains": ["ethereum", "solana"],
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "large_transfers" in data
        assert "total_volume" in data
        assert "transfer_count" in data
        assert "average_amount" in data
        
        # Should have transfer data
        assert isinstance(data["large_transfers"], list)
        assert data["total_volume"] >= 0
        assert data["transfer_count"] >= 0

    def test_stablecoin_exchange_flow_analysis(self, client):
        """Test stablecoin flow to/from exchanges"""
        response = client.post("/api/v1/analysis/stablecoin-exchange-flows", json={
            "stablecoin": "USDT",
            "exchanges": ["binance", "coinbase", "kraken"],
            "flow_type": "both",  # inflow and outflow
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "exchange_flows" in data
        assert "inflow_volume" in data
        assert "outflow_volume" in data
        assert "net_flow" in data
        
        # Should have flow data
        assert isinstance(data["exchange_flows"], list)
        assert isinstance(data["inflow_volume"], dict)
        assert isinstance(data["outflow_volume"], dict)

    def test_stablecoin_compliance_reporting(self, client):
        """Test stablecoin compliance reporting"""
        response = client.post("/api/v1/analysis/stablecoin-compliance-report", json={
            "stablecoin": "USDC",
            "report_type": "aml",
            "jurisdictions": ["US", "EU", "UK"],
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            },
            "include_suspicious_activity": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "report_id" in data
        assert "compliance_summary" in data
        assert "suspicious_transactions" in data
        assert "risk_assessment" in data
        
        # Should have compliance data
        assert isinstance(data["suspicious_transactions"], list)
        assert data["report_id"] is not None


class TestBridgeAnalysis:
    """Test bridge-specific analysis"""

    def test_known_bridge_detection(self, client):
        """Test detection of known bridge contracts"""
        response = client.post("/api/v1/analysis/known-bridges", json={
            "bridge_types": ["wormhole", "layerzero", "multichain"],
            "blockchains": ["ethereum", "solana", "bsc"],
            "include_contract_details": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "known_bridges" in data
        assert "bridge_contracts" in data
        assert "supported_tokens" in data
        
        # Should have bridge data
        assert isinstance(data["known_bridges"], list)
        assert isinstance(data["bridge_contracts"], dict)

    def test_bridge_security_analysis(self, client):
        """Test bridge security and risk analysis"""
        response = client.post("/api/v1/analysis/bridge-security", json={
            "bridge_contracts": [
                "0x...wormhole",
                "0x...layerzero"
            ],
            "security_checks": ["audit_status", "vulnerability_scan", "historical_incidents"],
            "risk_threshold": 0.7
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "security_analysis" in data
        assert "risk_scores" in data
        assert "security_recommendations" in data
        
        # Should have security data
        assert isinstance(data["security_analysis"], list)
        assert isinstance(data["risk_scores"], dict)

    def test_bridge_volume_analysis(self, client):
        """Test bridge volume and liquidity analysis"""
        response = client.post("/api/v1/analysis/bridge-volume", json={
            "bridge_type": "wormhole",
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            },
            "token_analysis": ["WBTC", "WETH", "USDC"],
            "include_liquidity_metrics": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "volume_metrics" in data
        assert "liquidity_analysis" in data
        assert "token_breakdown" in data
        
        # Should have volume data
        assert isinstance(data["volume_metrics"], dict)
        assert isinstance(data["token_breakdown"], dict)


class TestCrossChainEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_address_list(self, client):
        """Test cross-chain analysis with empty addresses"""
        response = client.post("/api/v1/analysis/cross-chain", json={
            "addresses": [],
            "bridge_type": "bitcoin_ethereum",
            "from_blockchain": "bitcoin",
            "to_blockchain": "ethereum"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_single_blockchain_analysis(self, client):
        """Test cross-chain analysis with single blockchain"""
        response = client.post("/api/v1/analysis/cross-chain", json={
            "addresses": ["1...btc"],
            "bridge_type": "bitcoin_ethereum",
            "from_blockchain": "bitcoin",
            "to_blockchain": "ethereum"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle single blockchain gracefully
        assert "bridge_transactions" in data

    def test_invalid_bridge_type(self, client):
        """Test with invalid bridge type"""
        response = client.post("/api/v1/analysis/cross-chain", json={
            "addresses": ["1...btc", "0x...eth"],
            "bridge_type": "invalid_bridge",
            "from_blockchain": "bitcoin",
            "to_blockchain": "ethereum"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_same_blockchain_bridge(self, client):
        """Test bridge analysis with same source and target blockchain"""
        response = client.post("/api/v1/analysis/cross-chain", json={
            "addresses": ["1...btc", "1...btc2"],
            "bridge_type": "bitcoin_bitcoin",
            "from_blockchain": "bitcoin",
            "to_blockchain": "bitcoin"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_very_large_amount_tracking(self, client):
        """Test value tracking with very large amounts"""
        response = client.post("/api/v1/analysis/value-tracking", json={
            "initial_amount": 1000000.0,  # 1M BTC
            "initial_blockchain": "bitcoin",
            "initial_token": "BTC",
            "target_blockchains": ["ethereum", "solana"]
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle large amounts
        assert "value_tracking" in data
        assert "final_amounts" in data

    def test_negative_amount_tracking(self, client):
        """Test value tracking with negative amounts"""
        response = client.post("/api/v1/analysis/value-tracking", json={
            "initial_amount": -1.0,
            "initial_blockchain": "bitcoin",
            "initial_token": "BTC"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_future_timeframe_cross_chain(self, client):
        """Test cross-chain analysis with future timeframe"""
        future_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        response = client.post("/api/v1/analysis/cross-chain", json={
            "addresses": ["1...btc", "0x...eth"],
            "bridge_type": "bitcoin_ethereum",
            "from_blockchain": "bitcoin",
            "to_blockchain": "ethereum",
            "timeframe": {
                "start": future_date,
                "end": future_date
            }
        })
        
        # Should handle future dates gracefully
        assert response.status_code in [200, 400]

    def test_null_values_cross_chain(self, client):
        """Test cross-chain analysis with null values"""
        response = client.post("/api/v1/analysis/cross-chain", json={
            "addresses": None,
            "bridge_type": "bitcoin_ethereum",
            "from_blockchain": "bitcoin",
            "to_blockchain": "ethereum"
        })
        
        assert response.status_code == 422


class TestCrossChainPerformance:
    """Test performance characteristics"""

    def test_cross_chain_scalability(self, client):
        """Test cross-chain analysis scalability"""
        import time
        
        # Test with increasing address counts
        address_counts = [10, 50, 100]
        response_times = []
        
        for count in address_counts:
            addresses = [f"1...btc{i}" for i in range(count)]
            
            start_time = time.time()
            response = client.post("/api/v1/analysis/cross-chain", json={
                "addresses": addresses,
                "bridge_type": "bitcoin_ethereum",
                "from_blockchain": "bitcoin",
                "to_blockchain": "ethereum"
            })
            end_time = time.time()
            
            assert response.status_code == 200
            response_times.append(end_time - start_time)
        
        # Response time should scale reasonably
        assert response_times[2] < response_times[0] * 10  # Not more than 10x slower

    def test_concurrent_cross_chain_analysis(self, client):
        """Test concurrent cross-chain analysis requests"""
        import threading
        import time
        
        results = []
        
        def analyze_cross_chain():
            response = client.post("/api/v1/analysis/cross-chain", json={
                "addresses": ["1...btc", "0x...eth"],
                "bridge_type": "bitcoin_ethereum",
                "from_blockchain": "bitcoin",
                "to_blockchain": "ethereum"
            })
            results.append(response.status_code)
        
        # Start 5 concurrent requests
        threads = []
        start_time = time.time()
        
        for _ in range(5):
            thread = threading.Thread(target=analyze_cross_chain)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        # Should complete within reasonable time
        assert total_time < 10.0
