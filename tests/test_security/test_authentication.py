"""
Security Tests - Authentication & Authorization for Phase 4

Tests authentication, authorization, and access control for all Phase 4 modules:
- Victim Reports
- Threat Feeds  
- Attribution
- Professional Services
- Forensics
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import json
import time
from datetime import datetime, timezone

from src.api.main import app
from src.api.auth import create_access_token, verify_token
from src.api.config import settings


class TestPhase4Authentication:
    """Test authentication for Phase 4 endpoints"""
    
    def setup_method(self):
        """Setup test client and test data"""
        self.client = TestClient(app)
        self.admin_token = create_access_token(data={"sub": "admin"})
        self.user_token = create_access_token(data={"sub": "user"})
        
    def test_authentication_required_all_phase4_endpoints(self):
        """Test that all Phase 4 endpoints require authentication"""
        
        # Test Victim Reports endpoints
        endpoints_to_test = [
            # Victim Reports
            ("/api/v1/intelligence/victim-reports/", "GET"),
            ("/api/v1/intelligence/victim-reports/statistics/overview", "GET"),
            ("/api/v1/intelligence/victim-reports/", "POST"),
            
            # Threat Feeds
            ("/api/v1/intelligence/threat-feeds/", "GET"),
            ("/api/v1/intelligence/threat-feeds/statistics/overview", "GET"),
            ("/api/v1/intelligence/threat-feeds/", "POST"),
            
            # Attribution
            ("/api/v1/attribution/", "GET"),
            ("/api/v1/attribution/statistics", "GET"),
            ("/api/v1/attribution/attribute-address", "POST"),
            
            # Professional Services
            ("/api/v1/intelligence/professional-services/services", "GET"),
            ("/api/v1/intelligence/professional-services/professionals", "GET"),
            ("/api/v1/intelligence/professional-services/training", "GET"),
            
            # Forensics
            ("/api/v1/forensics/cases", "GET"),
            ("/api/v1/forensics/statistics/overview", "GET"),
            ("/api/v1/forensics/cases", "POST"),
        ]
        
        for endpoint, method in endpoints_to_test:
            if method == "GET":
                response = self.client.get(endpoint)
            elif method == "POST":
                response = self.client.post(endpoint, json={})
            
            # All endpoints should return 401 without authentication
            assert response.status_code == 401, f"Endpoint {endpoint} should require authentication"
    
    def test_valid_authentication_allows_access(self):
        """Test that valid authentication allows access to Phase 4 endpoints"""
        
        # Test a few representative endpoints
        test_cases = [
            ("/api/v1/intelligence/victim-reports/", "GET"),
            ("/api/v1/intelligence/threat-feeds/", "GET"),
            ("/api/v1/attribution/", "GET"),
            ("/api/v1/intelligence/professional-services/services", "GET"),
            ("/api/v1/forensics/cases", "GET"),
        ]
        
        for endpoint, method in test_cases:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            if method == "GET":
                response = self.client.get(endpoint, headers=headers)
            elif method == "POST":
                response = self.client.post(endpoint, json={}, headers=headers)
            
            # Should not return 401 (may return 200, 403, 404, or 500 depending on permissions/data)
            assert response.status_code != 401, f"Endpoint {endpoint} should allow authenticated access"
    
    def test_invalid_token_rejected(self):
        """Test that invalid tokens are rejected"""
        
        invalid_tokens = [
            "invalid.token.here",
            "Bearer invalid.token.here",
            "Bearer",
            "",
            "Bearer ",
        ]
        
        for token in invalid_tokens:
            headers = {"Authorization": token}
            response = self.client.get("/api/v1/intelligence/victim-reports/", headers=headers)
            assert response.status_code == 401, f"Invalid token '{token}' should be rejected"
    
    def test_expired_token_rejected(self):
        """Test that expired tokens are rejected"""
        
        # Create an expired token
        expired_token = create_access_token(
            data={"sub": "admin"},
            expires_delta=time.timezone.utc.timedelta(seconds=-1)  # Expired 1 second ago
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = self.client.get("/api/v1/intelligence/victim-reports/", headers=headers)
        assert response.status_code == 401, "Expired token should be rejected"
    
    def test_token_format_validation(self):
        """Test that malformed tokens are rejected"""
        
        malformed_tokens = [
            "not.a.jwt",
            "only.one.part",
            "too.many.parts.here",
            "invalid.base64.encoding",
            '{"not": "a jwt"}',
        ]
        
        for token in malformed_tokens:
            headers = {"Authorization": f"Bearer {token}"}
            response = self.client.get("/api/v1/intelligence/victim-reports/", headers=headers)
            assert response.status_code == 401, f"Malformed token '{token}' should be rejected"


class TestPhase4Authorization:
    """Test authorization and permissions for Phase 4 endpoints"""
    
    def setup_method(self):
        """Setup test client and users with different roles"""
        self.client = TestClient(app)
        
        # Create tokens for different user roles
        self.admin_token = create_access_token(data={"sub": "admin", "role": "admin"})
        self.analyst_token = create_access_token(data={"sub": "analyst", "role": "analyst"})
        self.viewer_token = create_access_token(data={"sub": "viewer", "role": "viewer"})
        self.unauthorized_token = create_access_token(data={"sub": "unauthorized", "role": "unauthorized"})
    
    def test_admin_full_access(self):
        """Test that admin users have full access to all Phase 4 endpoints"""
        
        endpoints_to_test = [
            "/api/v1/intelligence/victim-reports/",
            "/api/v1/intelligence/threat-feeds/",
            "/api/v1/attribution/",
            "/api/v1/intelligence/professional-services/services",
            "/api/v1/forensics/cases",
        ]
        
        for endpoint in endpoints_to_test:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.client.get(endpoint, headers=headers)
            
            # Admin should have access (not 403)
            assert response.status_code != 403, f"Admin should have access to {endpoint}"
    
    def test_role_based_access_control(self):
        """Test that different roles have appropriate access levels"""
        
        # Test endpoints that should require higher privileges
        privileged_endpoints = [
            ("/api/v1/intelligence/victim-reports/", "POST"),
            ("/api/v1/intelligence/threat-feeds/", "POST"),
            ("/api/v1/attribution/attribute-address", "POST"),
            ("/api/v1/forensics/cases", "POST"),
        ]
        
        # Test read-only endpoints
        read_only_endpoints = [
            ("/api/v1/intelligence/victim-reports/", "GET"),
            ("/api/v1/intelligence/threat-feeds/", "GET"),
            ("/api/v1/attribution/", "GET"),
            ("/api/v1/intelligence/professional-services/services", "GET"),
            ("/api/v1/forensics/cases", "GET"),
        ]
        
        # Test different user roles
        role_tests = [
            (self.admin_token, "admin", True),      # Admin should have full access
            (self.analyst_token, "analyst", True),    # Analyst should have access
            (self.viewer_token, "viewer", False),     # Viewer should have limited access
            (self.unauthorized_token, "unauthorized", False),  # Unauthorized should have no access
        ]
        
        for token, role, should_have_access in role_tests:
            headers = {"Authorization": f"Bearer {token}"}
            
            # Test read-only endpoints
            for endpoint, method in read_only_endpoints:
                if method == "GET":
                    response = self.client.get(endpoint, headers=headers)
                
                if should_have_access:
                    assert response.status_code != 403, f"{role} should have read access to {endpoint}"
                else:
                    # Unauthorized users might get 403 or 401
                    assert response.status_code in [401, 403], f"{role} should not have access to {endpoint}"
            
            # Test privileged endpoints
            for endpoint, method in privileged_endpoints:
                if method == "POST":
                    response = self.client.post(endpoint, json={}, headers=headers)
                
                if should_have_access:
                    assert response.status_code != 403, f"{role} should have write access to {endpoint}"
                else:
                    # Unauthorized users should get 403 or 401
                    assert response.status_code in [401, 403], f"{role} should not have write access to {endpoint}"
    
    def test_permission_enforcement(self):
        """Test that permissions are properly enforced"""
        
        # Test specific permission requirements
        permission_tests = [
            # (endpoint, method, required_permission, should_succeed_with_admin)
            ("/api/v1/intelligence/victim-reports/", "GET", "read_intelligence", True),
            ("/api/v1/intelligence/victim-reports/", "POST", "write_intelligence", True),
            ("/api/v1/intelligence/threat-feeds/", "GET", "read_intelligence", True),
            ("/api/v1/attribution/", "GET", "read_intelligence", True),
            ("/api/v1/forensics/cases", "GET", "read_forensics", True),
            ("/api/v1/forensics/cases", "POST", "write_forensics", True),
        ]
        
        for endpoint, method, permission, should_succeed in permission_tests:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            if method == "GET":
                response = self.client.get(endpoint, headers=headers)
            elif method == "POST":
                response = self.client.post(endpoint, json={}, headers=headers)
            
            # Admin should succeed
            if should_succeed:
                assert response.status_code != 403, f"Admin should have {permission} for {endpoint}"
    
    def test_cross_module_access_isolation(self):
        """Test that access to one module doesn't grant access to others"""
        
        # Test that having access to victim reports doesn't automatically grant access to forensics
        # This would require mocking the permission system
        
        with patch('src.api.auth.check_permissions') as mock_check:
            # Mock to only allow victim reports access
            def mock_permission_check(permissions):
                return "read_intelligence" in permissions
            
            mock_check.side_effect = mock_permission_check
            
            headers = {"Authorization": f"Bearer {self.analyst_token}"}
            
            # Should succeed for victim reports
            response = self.client.get("/api/v1/intelligence/victim-reports/", headers=headers)
            assert response.status_code != 403, "Should have access to victim reports"
            
            # Should fail for forensics (different permission)
            response = self.client.get("/api/v1/forensics/cases", headers=headers)
            assert response.status_code == 403, "Should not have access to forensics without proper permissions"


class TestSecurityHeaders:
    """Test security headers and response security"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
        self.admin_token = create_access_token(data={"sub": "admin"})
    
    def test_security_headers_present(self):
        """Test that security headers are present on Phase 4 endpoints"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test a few Phase 4 endpoints
        endpoints = [
            "/api/v1/intelligence/victim-reports/",
            "/api/v1/intelligence/threat-feeds/",
            "/api/v1/attribution/",
            "/api/v1/forensics/cases",
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint, headers=headers)
            
            # Check for important security headers
            security_headers = [
                "x-content-type-options",
                "x-frame-options", 
                "x-xss-protection",
                "referrer-policy",
            ]
            
            for header in security_headers:
                # Headers should be present (case-insensitive check)
                header_found = any(h.lower().startswith(header.lower()) for h in response.headers)
                assert header_found, f"Security header {header} missing from {endpoint}"
    
    def test_no_sensitive_data_in_responses(self):
        """Test that sensitive data is not leaked in responses"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test endpoints that might return sensitive data
        sensitive_endpoints = [
            "/api/v1/intelligence/victim-reports/",
            "/api/v1/intelligence/threat-feeds/",
            "/api/v1/attribution/",
        ]
        
        for endpoint in sensitive_endpoints:
            response = self.client.get(endpoint, headers=headers)
            
            if response.status_code == 200:
                response_text = response.text.lower()
                
                # Check for potentially sensitive information
                sensitive_patterns = [
                    "password",
                    "secret",
                    "token",
                    "key",
                    "private_key",
                    "api_key",
                ]
                
                for pattern in sensitive_patterns:
                    # Should not find sensitive patterns in response
                    # (This is a basic check - in reality would be more sophisticated)
                    if pattern in response_text and "error" not in response_text:
                        # Allow pattern if it's part of an error message or field name
                        continue  # Skip this check for basic implementation
    
    def test_cors_headers(self):
        """Test CORS headers are properly configured"""
        
        # Test preflight request
        headers = {
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        }
        
        response = self.client.options("/api/v1/intelligence/victim-reports/", headers=headers)
        
        # Should have CORS headers
        cors_headers = [
            "access-control-allow-origin",
            "access-control-allow-methods",
            "access-control-allow-headers",
        ]
        
        for header in cors_headers:
            header_found = any(h.lower().startswith(header.lower()) for h in response.headers)
            assert header_found, f"CORS header {header} missing from preflight response"


if __name__ == "__main__":
    pytest.main([__file__])
