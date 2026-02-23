"""
Auto-generated Auth Rbac Tests
Generated on: 2026-02-23T18:37:57.658181+00:00
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



def test_role_based_access_control():
    """Test RBAC permissions for different roles"""
    # Test viewer permissions
    viewer_token = create_test_token("viewer")
    response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {viewer_token}"})
    assert response.status_code == 403  # Viewer shouldn't access user management
    
    # Test admin permissions
    admin_token = create_test_token("admin")
    response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200  # Admin should access user management
    
    # Test analyst permissions
    analyst_token = create_test_token("analyst")
    response = client.post("/api/v1/investigations", 
                          json={"title": "Test"}, 
                          headers={"Authorization": f"Bearer {analyst_token}"})
    assert response.status_code in [200, 201]  # Analyst should create investigations



def test_token_expiration():
    """Test token expiration handling"""
    # Create expired token
    expired_token = create_expired_token()
    
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
    assert "expired" in response.json().get("detail", "").lower()



def test_permission_inheritance():
    """Test that higher roles inherit lower role permissions"""
    admin_token = create_test_token("admin")
    
    # Admin should be able to access viewer-level endpoints
    response = client.get("/api/v1/analysis/address/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", 
                          headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200

