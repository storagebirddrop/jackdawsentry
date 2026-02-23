"""
Graph Visualization Testing
Tests transaction graph generation, visualization performance, and graph analysis features
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import json
from datetime import datetime, timezone, timedelta


class TestGraphVisualization:
    """Test graph visualization functionality"""

    @pytest.mark.parametrize("address,blockchain,graph_type", [
        ("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "bitcoin", "transaction"),
        ("0x742d35Cc6634C0532925a3b8D4E7E0E0e9e0dF3", "ethereum", "address"),
        ("9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM", "solana", "entity"),
    ])
    def test_graph_generation_basic(self, client, auth_headers, address, blockchain, graph_type):
        """Test basic graph generation"""
        response = client.post("/api/v1/graph/expand", json={
            "address": address,
            "blockchain": blockchain,
            "depth": 1,
            "direction": "both"
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "nodes" in data
        assert "edges" in data
        assert "metadata" in data
        assert "success" in data
        
        # Validate nodes
        assert isinstance(data["nodes"], list)
        if data["nodes"]:
            node = data["nodes"][0]
            assert "balance" in node
            assert "chain" in node
            assert "entity_category" in node
            assert "entity_name" in node
        
        # Validate edges
        assert isinstance(data["edges"], list)
        if data["edges"]:
            edge = data["edges"][0]
            assert "id" in edge
            assert "source" in edge
            assert "target" in edge
            assert "edge_type" in edge
            assert "chain" in edge

    def test_graph_expand_functionality(self, client, auth_headers):
        """Test graph expansion from initial node"""
        response = client.post("/api/v1/graph/expand", json={
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "blockchain": "bitcoin",
            "depth": 1,
            "direction": "both"
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have expanded graph
        assert "nodes" in data
        assert "edges" in data
        assert "metadata" in data
        
        # Should respect limits
        assert data["metadata"]["depth"] == 1
        assert data["metadata"]["direction"] == "both"

    def test_graph_with_time_filter(self, client):
        """Test graph generation with time filtering"""
        response = client.post("/api/v1/graph/generate", json={
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "blockchain": "bitcoin",
            "time_range": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            },
            "include_temporal": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have temporal data
        assert "nodes" in data
        assert "edges" in data
        assert "temporal_metadata" in data
        
        # Validate temporal metadata
        temporal = data["temporal_metadata"]
        assert "time_range" in temporal
        assert temporal["time_range"]["start"] == "2024-01-01T00:00:00Z"
        assert temporal["time_range"]["end"] == "2024-12-31T23:59:59Z"

    def test_graph_with_risk_scoring(self, client):
        """Test graph with risk-based node coloring"""
        response = client.post("/api/v1/graph/generate", json={
            "address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            "blockchain": "bitcoin",
            "include_risk_scoring": True,
            "risk_coloring": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have risk scoring
        assert "nodes" in data
        assert "risk_metadata" in data
        
        # Validate risk coloring
        if data["nodes"]:
            node = data["nodes"][0]
            if "risk_score" in node.get("data", {}):
                assert "color" in node
                assert node["color"] in ["red", "orange", "yellow", "green", "blue"]

    def test_graph_with_entity_attribution(self, client):
        """Test graph with entity attribution"""
        response = client.post("/api/v1/graph/generate", json={
            "address": "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2",
            "blockchain": "bitcoin",
            "include_attribution": True,
            "entity_clustering": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have attribution data
        assert "nodes" in data
        assert "attribution_metadata" in data
        
        # Validate entity clustering
        if data["nodes"]:
            node = data["nodes"][0]
            if "entity" in node.get("data", {}):
                entity = node["data"]["entity"]
                assert "name" in entity
                assert "category" in entity
                assert "confidence" in entity

    def test_graph_performance_large_graph(self, client):
        """Test graph generation performance with large graphs"""
        import time
        
        start_time = time.time()
        response = client.post("/api/v1/graph/generate", json={
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "blockchain": "bitcoin",
            "depth": 3,
            "max_nodes": 500,
            "direction": "both"
        })
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 200
        data = response.json()
        
        # Should complete within 5 seconds for large graphs
        assert response_time < 5.0
        
        # Should respect node limit
        assert len(data["nodes"]) <= 500

    def test_graph_layout_algorithms(self, client):
        """Test different graph layout algorithms"""
        layouts = ["force_directed", "hierarchical", "circular", "geographic"]
        
        for layout in layouts:
            response = client.post("/api/v1/graph/generate", json={
                "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                "blockchain": "bitcoin",
                "layout_algorithm": layout,
                "depth": 1
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Should have layout-specific data
            assert "visualization_config" in data
            assert data["visualization_config"]["layout"] == layout

    def test_graph_interaction_features(self, client):
        """Test graph interaction features"""
        response = client.post("/api/v1/graph/generate", json={
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "blockchain": "bitcoin",
            "include_interactions": True,
            "interactive_features": ["zoom", "pan", "click", "hover"]
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have interaction configuration
        assert "interaction_config" in data
        assert "visualization_config" in data
        
        # Validate interaction features
        interaction = data["interaction_config"]
        assert "zoom" in interaction
        assert "pan" in interaction
        assert "click" in interaction
        assert "hover" in interaction

    def test_graph_export_formats(self, client):
        """Test graph export in different formats"""
        formats = ["json", "graphml", "gexf", "cytoscape"]
        
        for format_type in formats:
            response = client.post("/api/v1/graph/export", json={
                "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                "blockchain": "bitcoin",
                "export_format": format_type,
                "depth": 1
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Should have export data
            assert "export_data" in data
            assert "export_metadata" in data
            assert data["export_metadata"]["format"] == format_type

    @patch('src.analysis.graph_enhancement.GraphEnhancer')
    def test_graph_with_mock_enhancement(self, mock_enhancer, client):
        """Test graph generation with mocked enhancement"""
        # Mock graph enhancement results
        mock_enhanced_graph = MagicMock()
        mock_enhanced_graph.nodes = [
            {"id": "node1", "label": "Address 1", "type": "address"},
            {"id": "node2", "label": "Address 2", "type": "address"}
        ]
        mock_enhanced_graph.edges = [
            {"id": "edge1", "source": "node1", "target": "node2", "type": "transaction"}
        ]
        
        mock_enhancer_instance = MagicMock()
        mock_enhancer_instance.enhance_graph.return_value = mock_enhanced_graph
        mock_enhancer.return_value = mock_enhancer_instance
        
        response = client.post("/api/v1/graph/generate", json={
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "blockchain": "bitcoin",
            "include_enhancements": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have enhanced graph
        assert "nodes" in data
        assert "edges" in data
        assert "enhancement_metadata" in data

    def test_graph_analysis_features(self, client):
        """Test graph analysis algorithms"""
        response = client.post("/api/v1/graph/analyze", json={
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "blockchain": "bitcoin",
            "analysis_types": ["centrality", "community_detection", "path_finding"],
            "depth": 2
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have analysis results
        assert "graph_analysis" in data
        assert "centrality_analysis" in data["graph_analysis"]
        assert "community_analysis" in data["graph_analysis"]
        assert "path_analysis" in data["graph_analysis"]
        
        # Validate centrality analysis
        centrality = data["graph_analysis"]["centrality_analysis"]
        assert "betweenness" in centrality
        assert "closeness" in centrality
        assert "eigenvector" in centrality

    def test_graph_real_time_updates(self, client):
        """Test real-time graph updates"""
        response = client.post("/api/v1/graph/real-time", json={
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "blockchain": "bitcoin",
            "enable_updates": True,
            "update_interval": 30
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have real-time configuration
        assert "real_time_config" in data
        assert "websocket_url" in data
        assert "update_interval" in data
        assert data["real_time_config"]["enable_updates"] is True

    @pytest.mark.integration
    def test_graph_with_real_blockchain_data(self, client):
        """Test graph generation with real blockchain data (integration test)"""
        response = client.post("/api/v1/graph/generate", json={
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "blockchain": "bitcoin",
            "depth": 1,
            "direction": "both",
            "include_transactions": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have real blockchain graph data
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) > 0  # Should have at least the starting node


class TestGraphAnalysis:
    """Test advanced graph analysis features"""

    def test_path_finding_analysis(self, client):
        """Test path finding between nodes"""
        response = client.post("/api/v1/graph/paths", json={
            "source_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "target_address": "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2",
            "blockchain": "bitcoin",
            "path_types": ["shortest", "all_paths"],
            "max_paths": 10
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have path results
        assert "paths" in data
        assert "path_metadata" in data
        
        # Validate path structure
        if data["paths"]:
            path = data["paths"][0]
            assert "path_id" in path
            assert "nodes" in path
            assert "edges" in path
            assert "length" in path
            assert "weight" in path

    def test_centrality_analysis(self, client):
        """Test centrality analysis for graph nodes"""
        response = client.post("/api/v1/graph/centrality", json={
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "blockchain": "bitcoin",
            "depth": 2,
            "centrality_types": ["betweenness", "closeness", "eigenvector", "pagerank"]
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have centrality results
        assert "centrality_scores" in data
        assert "analysis_metadata" in data
        
        # Validate centrality scores
        centrality = data["centrality_scores"]
        for node_id, scores in centrality.items():
            assert "betweenness" in scores
            assert "closeness" in scores
            assert "eigenvector" in scores
            assert "pagerank" in scores

    def test_community_detection(self, client):
        """Test community detection in graphs"""
        response = client.post("/api/v1/graph/communities", json={
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "blockchain": "bitcoin",
            "depth": 2,
            "algorithm": "louvain",
            "resolution": 1.0
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have community results
        assert "communities" in data
        assert "community_metadata" in data
        
        # Validate community structure
        if data["communities"]:
            community = data["communities"][0]
            assert "community_id" in community
            assert "nodes" in community
            assert "modularity" in community
            assert len(community["nodes"]) > 0

    def test_anomaly_detection(self, client):
        """Test anomaly detection in graph patterns"""
        response = client.post("/api/v1/graph/anomalies", json={
            "address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            "blockchain": "bitcoin",
            "depth": 2,
            "anomaly_types": ["structural", "temporal", "behavioral"],
            "threshold": 0.8
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have anomaly results
        assert "anomalies" in data
        assert "anomaly_metadata" in data
        
        # Validate anomaly structure
        if data["anomalies"]:
            anomaly = data["anomalies"][0]
            assert "anomaly_id" in anomaly
            assert "anomaly_type" in anomaly
            assert "confidence" in anomaly
            assert "description" in anomaly
            assert 0.0 <= anomaly["confidence"] <= 1.0

    def test_flow_analysis(self, client):
        """Test transaction flow analysis"""
        response = client.post("/api/v1/graph/flow", json={
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "blockchain": "bitcoin",
            "depth": 2,
            "flow_type": "value",
            "time_window": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have flow results
        assert "flow_analysis" in data
        assert "flow_metrics" in data
        
        # Validate flow analysis
        flow = data["flow_analysis"]
        assert "inflow" in flow
        assert "outflow" in flow
        assert "net_flow" in flow
        assert "flow_patterns" in flow

    def test_temporal_analysis(self, client):
        """Test temporal graph analysis"""
        response = client.post("/api/v1/graph/temporal", json={
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "blockchain": "bitcoin",
            "time_granularity": "daily",
            "time_range": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-01-31T23:59:59Z"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have temporal results
        assert "temporal_analysis" in data
        assert "time_series" in data
        
        # Validate temporal analysis
        temporal = data["temporal_analysis"]
        assert "activity_patterns" in temporal
        assert "peak_times" in temporal
        assert "trend_analysis" in temporal


class TestGraphVisualizationEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_graph_generation(self, client):
        """Test graph generation with no results"""
        response = client.post("/api/v1/graph/generate", json={
            "address": "1nonexistent123456789abcdef",
            "blockchain": "bitcoin",
            "depth": 1
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return empty graph gracefully
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) >= 0  # Should have at least the starting node or be empty

    def test_very_deep_graph(self, client):
        """Test graph generation with very deep depth"""
        response = client.post("/api/v1/graph/generate", json={
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "blockchain": "bitcoin",
            "depth": 10,  # Very deep
            "max_nodes": 1000
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle deep graphs gracefully
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) <= 1000  # Should respect node limit

    def test_invalid_layout_algorithm(self, client):
        """Test graph generation with invalid layout"""
        response = client.post("/api/v1/graph/generate", json={
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "blockchain": "bitcoin",
            "layout_algorithm": "invalid_layout"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_negative_depth(self, client):
        """Test graph generation with negative depth"""
        response = client.post("/api/v1/graph/generate", json={
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "blockchain": "bitcoin",
            "depth": -1
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_zero_max_nodes(self, client):
        """Test graph generation with zero max nodes"""
        response = client.post("/api/v1/graph/generate", json={
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "blockchain": "bitcoin",
            "max_nodes": 0
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_very_large_max_nodes(self, client):
        """Test graph generation with very large max nodes"""
        response = client.post("/api/v1/graph/generate", json={
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "blockchain": "bitcoin",
            "max_nodes": 100000  # Very large
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle large limits gracefully
        assert "nodes" in data
        assert len(data["nodes"]) <= 100000

    def test_invalid_time_range(self, client):
        """Test graph generation with invalid time range"""
        response = client.post("/api/v1/graph/generate", json={
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "blockchain": "bitcoin",
            "time_range": {
                "start": "2024-12-31T23:59:59Z",
                "end": "2024-01-01T00:00:00Z"  # End before start
            }
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_null_values_graph(self, client):
        """Test graph generation with null values"""
        response = client.post("/api/v1/graph/generate", json={
            "address": None,
            "blockchain": "bitcoin"
        })
        
        assert response.status_code == 422

    def test_special_characters_address(self, client):
        """Test graph generation with special characters"""
        response = client.post("/api/v1/graph/generate", json={
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa!@#$%^&*()",
            "blockchain": "bitcoin"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data


class TestGraphPerformance:
    """Test performance characteristics"""

    def test_graph_generation_performance(self, client):
        """Test graph generation performance metrics"""
        import time
        
        # Test different depths
        depths = [1, 2, 3]
        response_times = []
        
        for depth in depths:
            start_time = time.time()
            response = client.post("/api/v1/graph/generate", json={
                "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                "blockchain": "bitcoin",
                "depth": depth
            })
            end_time = time.time()
            
            assert response.status_code == 200
            response_times.append(end_time - start_time)
        
        # Performance should be reasonable
        assert response_times[0] < 1.0  # Depth 1: < 1 second
        assert response_times[1] < 2.0  # Depth 2: < 2 seconds
        assert response_times[2] < 5.0  # Depth 3: < 5 seconds

    def test_concurrent_graph_generation(self, client):
        """Test concurrent graph generation requests"""
        import threading
        import time
        
        results = []
        
        def generate_graph():
            response = client.post("/api/v1/graph/generate", json={
                "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                "blockchain": "bitcoin",
                "depth": 1
            })
            results.append(response.status_code)
        
        # Start 5 concurrent requests
        threads = []
        start_time = time.time()
        
        for _ in range(5):
            thread = threading.Thread(target=generate_graph)
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

    def test_memory_usage_graph_generation(self, client):
        """Test memory usage during graph generation"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate multiple graphs
        for i in range(10):
            response = client.post("/api/v1/graph/generate", json={
                "address": f"1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa{i}",
                "blockchain": "bitcoin",
                "depth": 2
            })
            assert response.status_code == 200
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (<200MB for 10 graphs)
        assert memory_increase < 200

    def test_graph_rendering_performance(self, client):
        """Test graph rendering performance"""
        response = client.post("/api/v1/graph/generate", json={
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "blockchain": "bitcoin",
            "depth": 2,
            "max_nodes": 100,
            "layout_algorithm": "force_directed"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have rendering metadata
        assert "rendering_metadata" in data
        
        if data["rendering_metadata"]:
            rendering = data["rendering_metadata"]
            assert "generation_time" in rendering
            assert "layout_time" in rendering
            assert "total_time" in rendering
            
            # Rendering should be fast
            assert rendering["total_time"] < 2.0
