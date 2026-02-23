"""
Auto-generated Compliance Tests
Generated on: 2026-02-23T18:37:57.656796+00:00
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



def test_gdpr_compliance():
    """Test GDPR compliance features"""
    # Test data deletion request
    response = client.post("/api/v1/compliance/gdpr/delete-request", json={
        "user_id": "test_user",
        "reason": "data_deletion_request"
    })
    assert response.status_code == 200
    
    # Test data export
    response = client.post("/api/v1/compliance/gdpr/data-export", json={
        "user_id": "test_user",
        "format": "json"
    })
    assert response.status_code == 200
    assert "export_data" in response.json()
    
    # Test consent management
    response = client.post("/api/v1/compliance/gdpr/consent", json={
        "user_id": "test_user",
        "consent_given": True,
        "purpose": "investigation_analysis"
    })
    assert response.status_code == 200



def test_aml_compliance():
    """Test AML compliance screening"""
    # Test sanctions screening
    response = client.post("/api/v1/compliance/sanctions-screen", json={
        "addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
        "include_risk_scoring": True
    })
    assert response.status_code == 200
    assert "screening_results" in response.json()
    
    # Test risk assessment
    response = client.post("/api/v1/compliance/risk-assessment", json={
        "entity": {
            "addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
            "entity_type": "individual"
        },
        "assessment_type": "standard"
    })
    assert response.status_code == 200
    assert "risk_score" in response.json()
    assert "risk_factors" in response.json()



def test_travel_rule_compliance():
    """Test Travel Rule compliance"""
    # Test travel rule reporting
    response = client.post("/api/v1/compliance/travel-rule/report", json={
        "transaction": {
            "originator": {"name": "Test Sender", "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"},
            "beneficiary": {"name": "Test Recipient", "address": "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"},
            "amount": 1000.0,
            "currency": "BTC",
            "blockchain": "bitcoin"
        }
    })
    assert response.status_code == 200
    assert "report_id" in response.json()
    
    # Test travel rule retrieval
    response = client.get("/api/v1/compliance/travel-rule/reports")
    assert response.status_code == 200
    assert isinstance(response.json(), list)



def test_audit_trail():
    """Test comprehensive audit trail"""
    # Create audit entry
    response = client.post("/api/v1/compliance/audit/log", json={
        "action": "data_access",
        "user_id": "test_user",
        "resource": "investigation_123",
        "details": {"purpose": "investigation_review"}
    })
    assert response.status_code == 201
    
    # Retrieve audit trail
    response = client.get("/api/v1/compliance/audit/trail", params={
        "user_id": "test_user",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
    })
    assert response.status_code == 200
    assert "audit_entries" in response.json()
    assert len(response.json()["audit_entries"]) > 0



def test_regulatory_reporting():
    """Test regulatory reporting features"""
    # Generate SAR (Suspicious Activity Report)
    response = client.post("/api/v1/compliance/reports/sar", json={
        "suspicious_addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
        "suspicion_reason": "Unusual transaction pattern",
        "reporting_period": {
            "start": "2024-01-01",
            "end": "2024-01-31"
        }
    })
    assert response.status_code == 200
    assert "sar_id" in response.json()
    
    # Generate CTR (Currency Transaction Report)
    response = client.post("/api/v1/compliance/reports/ctr", json={
        "transactions": [
            {"address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "amount": 15000.0, "currency": "USD"}
        ],
        "reporting_date": "2024-01-15"
    })
    assert response.status_code == 200
    assert "ctr_id" in response.json()

