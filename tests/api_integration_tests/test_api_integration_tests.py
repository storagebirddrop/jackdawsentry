"""
Auto-generated Api Integration Tests
Generated on: 2026-02-23T18:37:57.655247+00:00
"""

import pytest
import asyncio
import time
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

# Helper functions for token creation
def create_test_token(role: str = "viewer") -> str:
    """Create test JWT token for given role"""
    import jwt
    from datetime import datetime, timezone, timedelta
    import os
    
    payload = {
        "sub": "test_viewer",
        "user_id": "test_user_viewer",
        "role": "viewer",
        "permissions": ["test_permission"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    
    return jwt.encode(payload, os.getenv("TEST_JWT_SECRET", "test_secret"), algorithm="HS256")

def create_expired_token() -> str:
    """Create expired JWT token"""
    import jwt
    from datetime import datetime, timezone, timedelta
    import os
    
    payload = {
        "sub": "test_user",
        "user_id": "test_user",
        "role": "viewer",
        "permissions": ["test_permission"],
        "exp": datetime.now(timezone.utc) - timedelta(hours=1)  # Expired
    }
    
    return jwt.encode(payload, os.getenv("TEST_JWT_SECRET", "test_secret"), algorithm="HS256")



def test_complete_investigation_workflow():
    """Test complete investigation workflow from start to finish"""
    # Start investigation
    response = client.post("/api/v1/investigations", json={
        "title": "Test Investigation",
        "description": "Integration test investigation",
        "priority": "medium",
        "addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"]
    })
    assert response.status_code == 201
    investigation_id = response.json()["id"]
    
    # Add analysis
    response = client.post(f"/api/v1/investigations/{investigation_id}/analysis", json={
        "type": "address_analysis",
        "target": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    })
    assert response.status_code == 200
    
    # Get investigation details
    response = client.get(f"/api/v1/investigations/{investigation_id}")
    assert response.status_code == 200
    assert response.json()["id"] == investigation_id
    
    # Generate report
    response = client.post("/api/v1/reports/generate", json={
        "type": "investigation",
        "id": investigation_id,
        "format": "pdf"
    })
    assert response.status_code == 200



def test_cross_chain_analysis():
    """Test cross-chain analysis functionality"""
    addresses = [
        "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",  # Bitcoin
        "0x742d35Cc6634C0532925a3b8D4E7E0E0e9e0dF3",  # Ethereum
        "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"  # Solana
    ]
    
    response = client.post("/api/v1/analysis/cross-chain", json={
        "addresses": addresses,
        "blockchains": ["bitcoin", "ethereum", "solana"]
    })
    assert response.status_code == 200
    
    data = response.json()
    assert "cross_chain_links" in data
    assert len(data["cross_chain_links"]) >= 0



def test_bulk_operations():
    """Test bulk operation endpoints"""
    # Bulk address analysis
    addresses = [f"1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfN{i}" for i in range(10)]
    
    response = client.post("/api/v1/analysis/bulk", json={
        "addresses": addresses,
        "include_transactions": True
    })
    assert response.status_code == 200
    
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == len(addresses)
    
    # Bulk compliance screening
    response = client.post("/api/v1/compliance/bulk-screen", json={
        "addresses": addresses[:5],  # Smaller batch for compliance
        "include_risk_scoring": True
    })
    assert response.status_code == 200



def test_real_time_alerts():
    """Test real-time alert functionality"""
    # Create alert rule
    response = client.post("/api/v1/alerts/rules", json={
        "name": "Test Rule",
        "condition": "address_volume > 1000",
        "severity": "medium",
        "blockchain": "bitcoin"
    })
    assert response.status_code == 201
    rule_id = response.json()["id"]
    
    # Trigger alert (simulate)
    response = client.post("/api/v1/alerts/trigger", json={
        "rule_id": rule_id,
        "test_data": {"address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "volume": 1500}
    })
    assert response.status_code == 200
    
    # Check alert was created
    response = client.get("/api/v1/alerts/active")
    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) > 0
    
    # Clean up
    client.delete(f"/api/v1/alerts/rules/{rule_id}")



def test_api_error_handling():
    """Test comprehensive API error handling"""
    test_cases = [
        # Invalid endpoints
        ("/api/v1/nonexistent", 404),
        # Invalid methods
        ("/api/v1/auth/login", 405),  # GET on POST endpoint
        # Invalid content types
        ("/api/v1/analysis/address", 415),  # No content-type header
        # Malformed JSON
        ("/api/v1/compliance/screen", 400),  # Invalid JSON
    ]
    
    for endpoint, expected_status in test_cases:
        if expected_status == 405:
            response = client.get(endpoint)
        elif expected_status == 415:
            response = client.post(endpoint, data="not json")
        elif expected_status == 400:
            response = client.post(endpoint, data="invalid json")
        else:
            response = client.get(endpoint)
        
        assert response.status_code == expected_status

