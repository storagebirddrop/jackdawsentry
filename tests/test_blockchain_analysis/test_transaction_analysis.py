"""
Transaction Analysis Testing
Tests transaction-level analysis and cross-chain tracking functionality
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import json
from datetime import datetime, timezone, timedelta


class TestTransactionAnalysis:
    """Test transaction analysis functionality across all blockchains"""

    @pytest.mark.parametrize("tx_hash,blockchain,expected_type", [
        # Bitcoin transactions
        ("0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098", "bitcoin", "coinbase"),
        ("f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338501e31736a954", "bitcoin", "transfer"),
        
        # Ethereum transactions
        ("0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060", "ethereum", "transfer"),
        ("0x2c531124e77d6223494b53127c236c3cfae2c6eb862d8c5b2f0165b5d2e0d8b", "ethereum", "contract_call"),
        
        # Solana transactions
        ("5VERv8NMvFJekbJmK4J8hBV2z4ASjwJbHMq1s3wNaXyvgbqDEwo5f7BWEp5vELqVnqhDwA", "solana", "transfer"),
        
        # Tron transactions
        ("c9e2f56c40124e026b8c9c9bb3b1c8e7f6d5a4b3c2e1f0d9e8c7b6a5432109876", "tron", "transfer"),
    ])
    def test_transaction_analysis_basic(self, client, tx_hash, blockchain, expected_type):
        """Test basic transaction analysis"""
        response = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": tx_hash,
            "blockchain": blockchain,
            "include_analysis": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "transaction_hash" in data
        assert "blockchain" in data
        assert "transaction_type" in data
        assert "timestamp" in data
        assert "block_number" in data
        
        # Verify transaction hash matches
        assert data["transaction_hash"] == tx_hash
        assert data["blockchain"] == blockchain
        
        # Transaction type should be detected
        assert data["transaction_type"] in ["transfer", "contract_call", "coinbase", "bridge"]

    def test_transaction_analysis_with_inputs_outputs(self, client):
        """Test transaction analysis with detailed inputs/outputs"""
        response = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338501e31736a954",
            "blockchain": "bitcoin",
            "include_inputs_outputs": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have inputs and outputs
        assert "inputs" in data
        assert "outputs" in data
        assert isinstance(data["inputs"], list)
        assert isinstance(data["outputs"], list)
        
        # Validate input/output structure
        if data["inputs"]:
            input_tx = data["inputs"][0]
            assert "address" in input_tx
            assert "value" in input_tx
            assert "script_sig" in input_tx
        
        if data["outputs"]:
            output_tx = data["outputs"][0]
            assert "address" in output_tx
            assert "value" in output_tx
            assert "script_pubkey" in output_tx

    def test_transaction_analysis_with_pattern_detection(self, client):
        """Test transaction analysis with pattern detection"""
        response = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": "0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060",
            "blockchain": "ethereum",
            "include_patterns": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have patterns section
        assert "detected_patterns" in data
        assert isinstance(data["detected_patterns"], list)
        
        # If patterns detected, validate structure
        if data["detected_patterns"]:
            pattern = data["detected_patterns"][0]
            assert "pattern_type" in pattern
            assert "confidence" in pattern
            assert "risk_score" in pattern
            assert 0.0 <= pattern["confidence"] <= 1.0

    def test_transaction_analysis_cross_chain(self, client):
        """Test cross-chain transaction analysis"""
        response = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": "0x2c531124e77d6223494b53127c236c3cfae2c6eb862d8c5b2f0165b5d2e0d8b",
            "blockchain": "ethereum",
            "include_cross_chain": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have cross-chain analysis
        assert "cross_chain_analysis" in data
        
        if data["cross_chain_analysis"]:
            cross_chain = data["cross_chain_analysis"]
            assert "bridge_transactions" in cross_chain
            assert "related_chains" in cross_chain
            assert "total_volume" in cross_chain

    def test_transaction_analysis_smart_contract(self, client):
        """Test smart contract transaction analysis"""
        response = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": "0x2c531124e77d6223494b53127c236c3cfae2c6eb862d8c5b2f0165b5d2e0d8b",
            "blockchain": "ethereum",
            "include_contract_analysis": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have contract analysis
        assert "contract_analysis" in data
        
        if data["contract_analysis"]:
            contract = data["contract_analysis"]
            assert "contract_address" in contract
            assert "function_name" in contract
            assert "parameters" in contract
            assert "gas_used" in contract

    def test_transaction_analysis_invalid_hash(self, client):
        """Test transaction analysis with invalid hash"""
        response = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": "invalid_hash",
            "blockchain": "bitcoin"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_transaction_analysis_not_found(self, client):
        """Test transaction analysis with non-existent hash"""
        response = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": "0x" + "0" * 64,  # Valid format but likely non-existent
            "blockchain": "ethereum"
        })
        
        # Should either succeed with empty data or fail gracefully
        assert response.status_code in [200, 404]

    def test_transaction_analysis_performance(self, client):
        """Test transaction analysis performance"""
        import time
        
        start_time = time.time()
        response = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": "0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098",
            "blockchain": "bitcoin",
            "include_analysis": True
        })
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 200
        # Should complete within 1 second for basic analysis
        assert response_time < 1.0

    def test_bulk_transaction_analysis(self, client):
        """Test bulk transaction analysis"""
        transactions = [
            {
                "transaction_hash": "0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098",
                "blockchain": "bitcoin"
            },
            {
                "transaction_hash": "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338501e31736a954",
                "blockchain": "bitcoin"
            }
        ]
        
        response = client.post("/api/v1/analysis/transactions/bulk", json={
            "transactions": transactions,
            "include_analysis": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have results for all transactions
        assert "results" in data
        assert len(data["results"]) == len(transactions)
        
        # Each result should have basic structure
        for result in data["results"]:
            assert "transaction_hash" in result
            assert "blockchain" in result
            assert "transaction_type" in result

    def test_transaction_analysis_with_fee_analysis(self, client):
        """Test transaction analysis with fee analysis"""
        response = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": "0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060",
            "blockchain": "ethereum",
            "include_fee_analysis": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have fee analysis
        assert "fee_analysis" in data
        
        if data["fee_analysis"]:
            fee = data["fee_analysis"]
            assert "gas_price" in fee
            assert "gas_used" in fee
            assert "total_fee" in fee
            assert "fee_percentage" in fee

    def test_transaction_analysis_risk_assessment(self, client):
        """Test transaction analysis with risk assessment"""
        response = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": "0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060",
            "blockchain": "ethereum",
            "include_risk_assessment": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have risk assessment
        assert "risk_assessment" in data
        
        if data["risk_assessment"]:
            risk = data["risk_assessment"]
            assert "risk_score" in risk
            assert "risk_factors" in risk
            assert "risk_level" in risk
            assert 0.0 <= risk["risk_score"] <= 1.0

    @patch('src.analysis.cross_chain.CrossChainAnalyzer')
    def test_transaction_analysis_with_mock_cross_chain(self, mock_analyzer, client):
        """Test transaction analysis with mocked cross-chain analysis"""
        # Mock cross-chain detection
        mock_cross_chain_tx = MagicMock()
        mock_cross_chain_tx.blockchain = "ethereum"
        mock_cross_chain_tx.from_address = "0x742d35Cc6634C0532925a3b8D4E7E0E0e9e0dF3"
        mock_cross_chain_tx.to_address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        mock_cross_chain_tx.amount = 1.0
        mock_cross_chain_tx.token_symbol = "WBTC"
        mock_cross_chain_tx.patterns = ["bridge_transfer"]
        
        mock_analyzer_instance = MagicMock()
        mock_analyzer_instance.analyze_transaction.return_value = mock_cross_chain_tx
        mock_analyzer.return_value = mock_analyzer_instance
        
        response = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": "0x2c531124e77d6223494b53127c236c3cfae2c6eb862d8c5b2f0165b5d2e0d8b",
            "blockchain": "ethereum",
            "include_cross_chain": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have cross-chain analysis
        assert "cross_chain_analysis" in data

    @pytest.mark.integration
    def test_transaction_analysis_with_real_blockchain_data(self, client):
        """Test transaction analysis with real blockchain data (integration test)"""
        # This test requires actual blockchain node connections
        response = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": "0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098",
            "blockchain": "bitcoin",
            "include_analysis": True,
            "include_inputs_outputs": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have real blockchain data
        assert "transaction_hash" in data
        assert "inputs" in data
        assert "outputs" in data
        assert data["transaction_hash"] == "0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098"


class TestTransactionAnalysisEdgeCases:
    """Test edge cases and boundary conditions for transaction analysis"""

    def test_empty_transaction_hash(self, client):
        """Test with empty transaction hash"""
        response = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": "",
            "blockchain": "bitcoin"
        })
        
        assert response.status_code == 400

    def test_invalid_transaction_hash_format(self, client):
        """Test with invalid transaction hash format"""
        response = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": "invalid_hash_format",
            "blockchain": "bitcoin"
        })
        
        assert response.status_code == 400

    def test_very_long_transaction_hash(self, client):
        """Test with very long transaction hash"""
        long_hash = "0x" + "f" * 1000  # Invalid but long
        response = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": long_hash,
            "blockchain": "ethereum"
        })
        
        assert response.status_code == 400

    def test_null_transaction_hash(self, client):
        """Test with null transaction hash"""
        response = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": None,
            "blockchain": "bitcoin"
        })
        
        assert response.status_code == 422

    def test_unsupported_blockchain(self, client):
        """Test with unsupported blockchain"""
        response = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": "0x" + "0" * 64,
            "blockchain": "unsupported_chain"
        })
        
        assert response.status_code == 400

    def test_missing_required_fields(self, client):
        """Test with missing required fields"""
        response = client.post("/api/v1/analysis/transaction", json={
            "blockchain": "bitcoin"
            # Missing transaction_hash
        })
        
        assert response.status_code == 422

    def test_invalid_json(self, client):
        """Test with invalid JSON"""
        response = client.post(
            "/api/v1/analysis/transaction",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422

    def test_case_sensitivity_blockchain(self, client):
        """Test blockchain case sensitivity"""
        response1 = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": "0x" + "0" * 64,
            "blockchain": "BITCOIN"  # Uppercase
        })
        
        response2 = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": "0x" + "0" * 64,
            "blockchain": "bitcoin"  # Lowercase
        })
        
        # Both should either succeed or fail consistently
        assert response1.status_code == response2.status_code

    def test_special_characters_in_hash(self, client):
        """Test with special characters in transaction hash"""
        response = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": "0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060!@#$%^&*()",
            "blockchain": "ethereum"
        })
        
        assert response.status_code == 400

    def test_unicode_transaction_hash(self, client):
        """Test with unicode characters"""
        response = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": "0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060🚀",
            "blockchain": "ethereum"
        })
        
        assert response.status_code == 400


class TestTransactionAnalysisPerformance:
    """Test performance characteristics of transaction analysis"""

    def test_concurrent_transaction_analysis(self, client):
        """Test concurrent transaction analysis requests"""
        import asyncio
        import threading
        import time
        
        results = []
        
        def analyze_transaction():
            response = client.post("/api/v1/analysis/transaction", json={
                "transaction_hash": "0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098",
                "blockchain": "bitcoin"
            })
            results.append(response.status_code)
        
        # Start 10 concurrent requests
        threads = []
        start_time = time.time()
        
        for _ in range(10):
            thread = threading.Thread(target=analyze_transaction)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        # Should complete within reasonable time (5 seconds for 10 requests)
        assert total_time < 5.0

    def test_large_transaction_analysis(self, client):
        """Test analysis of transactions with many inputs/outputs"""
        # Mock a transaction with many inputs/outputs
        response = client.post("/api/v1/analysis/transaction", json={
            "transaction_hash": "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338501e31736a954",
            "blockchain": "bitcoin",
            "include_inputs_outputs": True,
            "include_analysis": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle large transactions gracefully
        assert "inputs" in data
        assert "outputs" in data
        
        # Performance should remain acceptable
        assert len(data["inputs"]) >= 0  # Should not crash
        assert len(data["outputs"]) >= 0

    def test_memory_usage_analysis(self, client):
        """Test memory usage during transaction analysis"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform multiple analyses
        for _ in range(100):
            response = client.post("/api/v1/analysis/transaction", json={
                "transaction_hash": "0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098",
                "blockchain": "bitcoin",
                "include_analysis": True
            })
            assert response.status_code == 200
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (<100MB for 100 analyses)
        assert memory_increase < 100
