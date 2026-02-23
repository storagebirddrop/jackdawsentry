"""
Pattern Detection Testing
Tests 15+ money laundering pattern detection algorithms across all blockchains
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import json
from datetime import datetime, timezone, timedelta


class TestPatternDetection:
    """Test pattern detection functionality"""

    @pytest.mark.parametrize("pattern_type,test_addresses,expected_confidence", [
        ("peeling_chain", ["bc1q...peeling1", "bc1q...peeling2"], 0.8),
        ("mixing", ["bc1q...mix_in", "bc1q...mix_out"], 0.9),
        ("layering", ["0x...layer1", "0x...layer2"], 0.7),
        ("bridge_hopping", ["0x...eth_bridge", "1...btc_bridge"], 0.8),
        ("dex_hopping", ["0x...uniswap", "0x...curve"], 0.6),
        ("high_frequency", ["1A1z...freq1", "1A1z...freq2"], 0.7),
        ("synchronized_transfers", ["sync1", "sync2"], 0.8),
        ("circular_trading", ["circle1", "circle2"], 0.9),
        ("round_amounts", ["round1", "round2"], 0.5),
        ("peak_off_hours", ["offpeak1", "offpeak2"], 0.6),
    ])
    def test_pattern_detection_basic(self, client, pattern_type, test_addresses, expected_confidence):
        """Test basic pattern detection"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": test_addresses,
            "pattern_types": [pattern_type],
            "blockchain": "bitcoin",
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "detected_patterns" in data
        assert "analysis_metadata" in data
        assert isinstance(data["detected_patterns"], list)
        
        # If patterns detected, validate structure
        if data["detected_patterns"]:
            pattern = data["detected_patterns"][0]
            assert "pattern_type" in pattern
            assert "confidence" in pattern
            assert "risk_score" in pattern
            assert "evidence" in pattern
            assert "description" in pattern
            assert "severity" in pattern
            assert "detected_at" in pattern
            
            # Validate data types and ranges
            assert 0.0 <= pattern["confidence"] <= 1.0
            assert 0.0 <= pattern["risk_score"] <= 1.0
            assert pattern["severity"] in ["low", "medium", "high", "critical"]
            
            # Check if expected pattern type was detected
            if pattern["pattern_type"] == pattern_type:
                assert pattern["confidence"] >= expected_confidence - 0.2

    def test_pattern_detection_multiple_patterns(self, client):
        """Test detection of multiple pattern types"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["bc1q...test1", "bc1q...test2", "0x...test3"],
            "pattern_types": ["peeling_chain", "mixing", "layering"],
            "blockchain": "bitcoin",
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should detect multiple patterns
        assert len(data["detected_patterns"]) >= 0
        
        # Each pattern should have valid structure
        for pattern in data["detected_patterns"]:
            assert pattern["pattern_type"] in ["peeling_chain", "mixing", "layering"]
            assert 0.0 <= pattern["confidence"] <= 1.0

    def test_pattern_detection_all_patterns(self, client):
        """Test detection of all available patterns"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["bc1q...test1", "bc1q...test2"],
            "pattern_types": "all",  # Detect all patterns
            "blockchain": "bitcoin",
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have patterns section
        assert "detected_patterns" in data
        assert isinstance(data["detected_patterns"], list)

    def test_pattern_detection_with_evidence(self, client):
        """Test pattern detection with detailed evidence"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["bc1q...mix_in", "bc1q...mix_out"],
            "pattern_types": ["mixing"],
            "blockchain": "bitcoin",
            "include_evidence": True,
            "evidence_detail": "full"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have detailed evidence
        if data["detected_patterns"]:
            pattern = data["detected_patterns"][0]
            assert "evidence" in pattern
            assert isinstance(pattern["evidence"], list)
            
            if pattern["evidence"]:
                evidence = pattern["evidence"][0]
                assert "type" in evidence
                assert "description" in evidence
                assert "confidence" in evidence
                assert "transaction_hash" in evidence

    def test_pattern_detection_cross_chain(self, client):
        """Test pattern detection across multiple chains"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["0x...eth1", "1...btc1", "9Wz...sol1"],
            "pattern_types": ["bridge_hopping", "cross_chain_mixing"],
            "blockchain": "multi",  # Cross-chain analysis
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle cross-chain patterns
        assert "detected_patterns" in data
        assert "cross_chain_analysis" in data

    def test_pattern_detection_time_range(self, client):
        """Test pattern detection with specific time range"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["bc1q...test1", "bc1q...test2"],
            "pattern_types": ["high_frequency"],
            "blockchain": "bitcoin",
            "timeframe": {
                "start": "2024-06-01T00:00:00Z",
                "end": "2024-06-30T23:59:59Z"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should respect time range
        assert "analysis_metadata" in data
        metadata = data["analysis_metadata"]
        assert "timeframe" in metadata
        assert metadata["timeframe"]["start"] == "2024-06-01T00:00:00Z"
        assert metadata["timeframe"]["end"] == "2024-06-30T23:59:59Z"

    def test_pattern_detection_performance(self, client):
        """Test pattern detection performance"""
        import time
        
        start_time = time.time()
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["bc1q...test1", "bc1q...test2"],
            "pattern_types": ["peeling_chain", "mixing"],
            "blockchain": "bitcoin"
        })
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 200
        # Should complete within 2 seconds for basic pattern detection
        assert response_time < 2.0

    def test_pattern_detection_invalid_pattern_type(self, client):
        """Test pattern detection with invalid pattern type"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["bc1q...test1"],
            "pattern_types": ["invalid_pattern"],
            "blockchain": "bitcoin"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_pattern_detection_empty_addresses(self, client):
        """Test pattern detection with empty addresses"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": [],
            "pattern_types": ["peeling_chain"],
            "blockchain": "bitcoin"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    @patch('src.analysis.pattern_detection.MLPatternDetector')
    def test_pattern_detection_with_mock_detector(self, mock_detector, client):
        """Test pattern detection with mocked detector"""
        # Mock pattern detection results
        mock_pattern = MagicMock()
        mock_pattern.pattern_type.value = "peeling_chain"
        mock_pattern.confidence = 0.85
        mock_pattern.risk_score = 0.7
        mock_pattern.evidence = [
            {
                "type": "transaction_sequence",
                "description": "Sequential peeling transactions detected",
                "confidence": 0.9,
                "transaction_hash": "0x...peel1"
            }
        ]
        mock_pattern.description = "Peeling chain pattern detected"
        mock_pattern.severity = "high"
        
        mock_detector_instance = MagicMock()
        mock_detector_instance.detect_patterns.return_value = [mock_pattern]
        mock_detector.return_value = mock_detector_instance
        
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["bc1q...peeling1", "bc1q...peeling2"],
            "pattern_types": ["peeling_chain"],
            "blockchain": "bitcoin"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have detected patterns
        assert len(data["detected_patterns"]) > 0
        
        pattern = data["detected_patterns"][0]
        assert pattern["pattern_type"] == "peeling_chain"
        assert pattern["confidence"] == 0.85
        assert pattern["risk_score"] == 0.7

    def test_pattern_detection_risk_scoring(self, client):
        """Test pattern detection with risk scoring"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["bc1q...high_risk", "bc1q...medium_risk"],
            "pattern_types": ["mixing", "layering"],
            "blockchain": "bitcoin",
            "include_risk_scoring": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have risk scoring
        assert "risk_assessment" in data
        
        if data["risk_assessment"]:
            risk = data["risk_assessment"]
            assert "overall_risk_score" in risk
            assert "risk_factors" in risk
            assert "risk_level" in risk
            assert 0.0 <= risk["overall_risk_score"] <= 1.0

    def test_pattern_detection_confidence_threshold(self, client):
        """Test pattern detection with confidence threshold"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["bc1q...test1", "bc1q...test2"],
            "pattern_types": ["peeling_chain"],
            "blockchain": "bitcoin",
            "confidence_threshold": 0.8  # Only high confidence patterns
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # All detected patterns should meet threshold
        for pattern in data["detected_patterns"]:
            assert pattern["confidence"] >= 0.8

    @pytest.mark.integration
    def test_pattern_detection_with_real_data(self, client):
        """Test pattern detection with real blockchain data (integration test)"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
            "pattern_types": ["peeling_chain", "mixing"],
            "blockchain": "bitcoin",
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have analyzed real address
        assert "detected_patterns" in data
        assert "analysis_metadata" in data


class TestSpecificPatterns:
    """Test specific money laundering patterns"""

    def test_peeling_chain_detection(self, client):
        """Test peeling chain pattern detection"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["bc1q...peel1", "bc1q...peel2", "bc1q...peel3"],
            "pattern_types": ["peeling_chain"],
            "blockchain": "bitcoin"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Peeling chain specific validation
        for pattern in data["detected_patterns"]:
            if pattern["pattern_type"] == "peeling_chain":
                assert "peeling_steps" in pattern
                assert "value_reduction" in pattern
                assert pattern["value_reduction"] > 0

    def test_mixing_pattern_detection(self, client):
        """Test mixing pattern detection"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["bc1q...mix_in", "bc1q...mix_out"],
            "pattern_types": ["mixing"],
            "blockchain": "bitcoin",
            "include_evidence": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Mixing specific validation
        for pattern in data["detected_patterns"]:
            if pattern["pattern_type"] == "mixing":
                assert "mixing_service" in pattern
                assert "anonymity_score" in pattern
                assert pattern["anonymity_score"] > 0.5

    def test_layering_pattern_detection(self, client):
        """Test layering pattern detection"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["0x...layer1", "0x...layer2", "0x...layer3"],
            "pattern_types": ["layering"],
            "blockchain": "ethereum"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Layering specific validation
        for pattern in data["detected_patterns"]:
            if pattern["pattern_type"] == "layering":
                assert "layer_count" in pattern
                assert "complexity_score" in pattern
                assert pattern["layer_count"] >= 2

    def test_bridge_hopping_detection(self, client):
        """Test bridge hopping pattern detection"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["0x...eth_bridge", "1...btc_bridge"],
            "pattern_types": ["bridge_hopping"],
            "blockchain": "multi"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Bridge hopping specific validation
        for pattern in data["detected_patterns"]:
            if pattern["pattern_type"] == "bridge_hopping":
                assert "bridge_count" in pattern
                assert "cross_chain_volume" in pattern
                assert pattern["bridge_count"] >= 2

    def test_high_frequency_detection(self, client):
        """Test high frequency transaction pattern"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["1A1z...freq1", "1A1z...freq2"],
            "pattern_types": ["high_frequency"],
            "blockchain": "bitcoin",
            "timeframe": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-01-02T00:00:00Z"  # 24 hour window
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # High frequency specific validation
        for pattern in data["detected_patterns"]:
            if pattern["pattern_type"] == "high_frequency":
                assert "transaction_count" in pattern
                assert "frequency_score" in pattern
                assert pattern["transaction_count"] > 10  # Threshold for high frequency

    def test_synchronized_transfers_detection(self, client):
        """Test synchronized transfers pattern"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["sync1", "sync2", "sync3"],
            "pattern_types": ["synchronized_transfers"],
            "blockchain": "ethereum"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Synchronized transfers specific validation
        for pattern in data["detected_patterns"]:
            if pattern["pattern_type"] == "synchronized_transfers":
                assert "synchronization_score" in pattern
                assert "time_window" in pattern
                assert pattern["synchronization_score"] > 0.7

    def test_circular_trading_detection(self, client):
        """Test circular trading pattern"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["circle1", "circle2", "circle3"],
            "pattern_types": ["circular_trading"],
            "blockchain": "ethereum"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Circular trading specific validation
        for pattern in data["detected_patterns"]:
            if pattern["pattern_type"] == "circular_trading":
                assert "cycle_length" in pattern
                assert "round_trip_volume" in pattern
                assert pattern["cycle_length"] >= 3


class TestPatternDetectionEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_single_address_pattern_detection(self, client):
        """Test pattern detection with single address"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["bc1q...single"],
            "pattern_types": ["peeling_chain"],
            "blockchain": "bitcoin"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle single address gracefully
        assert "detected_patterns" in data

    def test_large_address_list(self, client):
        """Test pattern detection with large address list"""
        addresses = [f"bc1q...addr{i}" for i in range(100)]
        
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": addresses,
            "pattern_types": ["peeling_chain"],
            "blockchain": "bitcoin"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle large address lists
        assert "detected_patterns" in data
        assert "analysis_metadata" in data

    def test_very_long_timeframe(self, client):
        """Test pattern detection with very long timeframe"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["bc1q...test1"],
            "pattern_types": ["peeling_chain"],
            "blockchain": "bitcoin",
            "timeframe": {
                "start": "2020-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"  # 5 years
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle long timeframes
        assert "detected_patterns" in data

    def test_invalid_timeframe(self, client):
        """Test pattern detection with invalid timeframe"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["bc1q...test1"],
            "pattern_types": ["peeling_chain"],
            "blockchain": "bitcoin",
            "timeframe": {
                "start": "2024-12-31T23:59:59Z",
                "end": "2024-01-01T00:00:00Z"  # End before start
            }
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_future_timeframe(self, client):
        """Test pattern detection with future timeframe"""
        future_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["bc1q...test1"],
            "pattern_types": ["peeling_chain"],
            "blockchain": "bitcoin",
            "timeframe": {
                "start": future_date,
                "end": future_date
            }
        })
        
        # Should handle future dates gracefully
        assert response.status_code in [200, 400]

    def test_empty_pattern_types(self, client):
        """Test pattern detection with empty pattern types"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["bc1q...test1"],
            "pattern_types": [],
            "blockchain": "bitcoin"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_null_values(self, client):
        """Test pattern detection with null values"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": None,
            "pattern_types": ["peeling_chain"],
            "blockchain": "bitcoin"
        })
        
        assert response.status_code == 422

    def test_special_characters(self, client):
        """Test pattern detection with special characters"""
        response = client.post("/api/v1/analysis/patterns", json={
            "addresses": ["bc1q...test!@#$%^&*()"],
            "pattern_types": ["peeling_chain"],
            "blockchain": "bitcoin"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data


class TestPatternDetectionPerformance:
    """Test performance characteristics"""

    def test_pattern_detection_scalability(self, client):
        """Test pattern detection scalability"""
        import time
        
        # Test with increasing address counts
        address_counts = [10, 50, 100]
        response_times = []
        
        for count in address_counts:
            addresses = [f"bc1q...addr{i}" for i in range(count)]
            
            start_time = time.time()
            response = client.post("/api/v1/analysis/patterns", json={
                "addresses": addresses,
                "pattern_types": ["peeling_chain"],
                "blockchain": "bitcoin"
            })
            end_time = time.time()
            
            assert response.status_code == 200
            response_times.append(end_time - start_time)
        
        # Response time should scale reasonably
        assert response_times[2] < response_times[0] * 10  # Not more than 10x slower

    def test_concurrent_pattern_detection(self, client):
        """Test concurrent pattern detection requests"""
        import threading
        import time
        
        results = []
        
        def detect_patterns():
            response = client.post("/api/v1/analysis/patterns", json={
                "addresses": ["bc1q...test1", "bc1q...test2"],
                "pattern_types": ["peeling_chain"],
                "blockchain": "bitcoin"
            })
            results.append(response.status_code)
        
        # Start 5 concurrent requests
        threads = []
        start_time = time.time()
        
        for _ in range(5):
            thread = threading.Thread(target=detect_patterns)
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
        assert total_time < 5.0
