"""
Graph Summary Testing
Tests address summary and graph metadata endpoints
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import json
from datetime import datetime, timezone, timedelta


class TestGraphSummary:
    """Test graph summary functionality"""

    def test_address_summary(self, client, auth_headers):
        """Test address summary endpoint"""
        response = client.get("/api/v1/graph/address/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa/summary?blockchain=bitcoin", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "address" in data
        assert "blockchain" in data
        assert "balance" in data
        assert "transaction_count" in data
        assert "first_seen" in data
        assert "last_seen" in data
        assert "risk_score" in data
        assert "labels" in data
        assert "sanctions_status" in data
        
        # Verify address matches
        assert data["address"] == "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        assert data["blockchain"] == "bitcoin"

    def test_address_summary_ethereum(self, client, auth_headers):
        """Test address summary for Ethereum"""
        response = client.get("/api/v1/graph/address/0x742d35Cc6634C0532925a3b8D4E7E0E0e9e0dF3/summary", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "address" in data
        assert "blockchain" in data
        assert data["address"] == "0x742d35Cc6634C0532925a3b8D4E7E0E0e9e0dF3"
        assert data["blockchain"] == "ethereum"  # Default blockchain

    def test_graph_search_endpoint(self, client, auth_headers):
        """Test graph search endpoint"""
        response = client.post("/api/v1/graph/search", json={
            "query": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "query_type": "address",
            "blockchain": "bitcoin"
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "nodes" in data
        assert "edges" in data
        assert "metadata" in data
        assert "success" in data
        assert data["success"] is True
        
        # Should have at least one node (the searched address)
        assert len(data["nodes"]) >= 1

    def test_graph_search_transaction(self, client, auth_headers):
        """Test graph search for transaction"""
        response = client.post("/api/v1/graph/search", json={
            "query": "ff061bed4ba93779bf6b27322b79ff12663ed479e5d52ddc695a17380b9351ce",
            "query_type": "transaction",
            "blockchain": "bitcoin"
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "nodes" in data
        assert "edges" in data
        assert "metadata" in data
        assert "success" in data

    def test_graph_cluster_endpoint(self, client, auth_headers):
        """Test graph clustering endpoint"""
        response = client.post("/api/v1/graph/cluster", json={
            "addresses": [
                "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"
            ],
            "blockchain": "bitcoin",
            "cluster_type": "common_counterparties"
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "nodes" in data
        assert "edges" in data
        assert "metadata" in data
        assert "success" in data
        assert data["success"] is True
