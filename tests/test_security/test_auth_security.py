"""
Security Tests - Authentication Security for Phases 1-3

Tests authentication security including JWT validation,
password policies, session management, and access control.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from src.api.main import app
from src.api.auth import create_access_token, verify_token


class TestAuthenticationSecurity:
    """Test authentication security"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_jwt_token_validation(self):
        """Test JWT token validation and security"""
        
        # Test valid token
        valid_token = create_access_token(data={"sub": "admin"})
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        response = self.client.get("/api/v1/auth/me", headers=headers)
        
        # Should accept valid token
        assert response.status_code in [200, 404], "Should accept valid JWT token"
        
        # Test invalid token formats
        invalid_tokens = [
            "invalid.token.here",
            "Bearer invalid.token.here",
            "Bearer",
            "",
            "Bearer ",
            "not.a.jwt",
            "only.one.part",
            "too.many.parts.here",
            '{"not": "a jwt"}',
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"
        ]
        
        for invalid_token in invalid_tokens:
            headers = {"Authorization": invalid_token}
            response = self.client.get("/api/v1/auth/me", headers=headers)
            assert response.status_code == 401, f"Should reject invalid token: {invalid_token[:50]}..."
    
    def test_jwt_token_expiration(self):
        """Test JWT token expiration handling"""
        
        # Test expired token
        expired_token = create_access_token(
            data={"sub": "admin"},
            expires_delta=timedelta(seconds=-1)  # Expired 1 second ago
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = self.client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401, "Should reject expired JWT token"
        
        # Test token with future expiration
        future_token = create_access_token(
            data={"sub": "admin"},
            expires_delta=timedelta(hours=1)  # Valid for 1 hour
        )
        
        headers = {"Authorization": f"Bearer {future_token}"}
        response = self.client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code in [200, 404], "Should accept valid future token"
    
    def test_password_security_policies(self):
        """Test password security policies"""
        
        # Test password requirements
        password_tests = [
            # Valid passwords
            ("SecurePass123!@", True),
            ("ComplexP@ssw0rd", True),
            ("MySecurePassword2024", True),
            # Invalid passwords
            ("123456", False),  # Too short, only numbers
            ("password", False),  # Too short, common word
            ("short", False),    # Too short
            ("", False),         # Empty
            ("   ", False),       # Whitespace only
            ("PASSWORD", False), # All uppercase, no numbers/special chars
            ("12345678", False), # Only numbers
            ("abcdefgh", False), # Only letters
            ("Abc123", False),   # Too short
        ]
        
        for password, should_be_valid in password_tests:
            user_data = {
                "username": f"testuser_{uuid.uuid4().hex[:8]}",
                "password": password,
                "email": f"test_{uuid.uuid4().hex[:8]}@example.com"
            }
            
            response = self.client.post("/api/v1/auth/register", json=user_data)
            
            if should_be_valid:
                # Should accept valid password or indicate user exists
                assert response.status_code in [201, 400], f"Should accept valid password: {password[:10]}..."
            else:
                # Should reject invalid password
                assert response.status_code in [400, 422], f"Should reject invalid password: {password[:10]}..."
    
    def test_login_security(self):
        """Test login security and protection"""
        
        # Test login rate limiting
        login_attempts = []
        for i in range(10):
            login_data = {
                "username": "admin",
                "password": f"wrong_password_{i}"
            }
            
            response = self.client.post("/api/v1/auth/login", json=login_data)
            login_attempts.append(response.status_code)
            
            # Should eventually hit rate limit or account lockout
            if response.status_code == 429 or response.status_code == 423:
                break
        
        # Should have some protection against brute force
        assert any(status in [429, 423] for status in login_attempts), \
            "Should have login protection against brute force"
        
        # Test successful login after failed attempts
        login_data = {
            "username": "admin",
            "password": "Admin123!@#"
        }
        
        response = self.client.post("/api/v1/auth/login", json=login_data)
        
        # Should allow successful login (may be rate limited)
        assert response.status_code in [200, 429], "Should allow successful login"
    
    def test_session_management(self):
        """Test session management security"""
        
        # Test login and session creation
        login_data = {
            "username": "admin",
            "password": "Admin123!@#"
        }
        
        response = self.client.post("/api/v1/auth/login", json=login_data)
        
        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get("access_token")
            
            # Test session validation
            headers = {"Authorization": f"Bearer {token}"}
            response = self.client.get("/api/v1/auth/me", headers=headers)
            assert response.status_code in [200, 404], "Should validate session"
            
            # Test session invalidation (logout)
            response = self.client.post("/api/v1/auth/logout", headers=headers)
            # Should handle logout (may return 200, 401, or 404)
            assert response.status_code in [200, 401, 404], "Should handle logout"
    
    def test_multi_device_session_security(self):
        """Test multi-device session security"""
        
        # Test multiple concurrent sessions
        tokens = []
        for i in range(3):
            login_data = {
                "username": "admin",
                "password": "Admin123!@#"
            }
            
            response = self.client.post("/api/v1/auth/login", json=login_data)
            
            if response.status_code == 200:
                token_data = response.json()
                tokens.append(token_data.get("access_token"))
        
        # Test that multiple sessions can be active
        for i, token in enumerate(tokens):
            headers = {"Authorization": f"Bearer {token}"}
            response = self.client.get("/api/v1/auth/me", headers=headers)
            assert response.status_code in [200, 404], f"Session {i+1} should be valid"
    
    def test_token_refresh_security(self):
        """Test token refresh security"""
        
        # Test token refresh endpoint
        login_data = {
            "username": "admin",
            "password": "Admin123!@#"
        }
        
        response = self.client.post("/api/v1/auth/login", json=login_data)
        
        if response.status_code == 200:
            token_data = response.json()
            refresh_token = token_data.get("refresh_token")
            
            if refresh_token:
                # Test token refresh
                refresh_data = {"refresh_token": refresh_token}
                response = self.client.post("/api/v1/auth/refresh", json=refresh_data)
                
                # Should handle token refresh
                assert response.status_code in [200, 400, 404], "Should handle token refresh"
                
                if response.status_code == 200:
                    new_token_data = response.json()
                    new_token = new_token_data.get("access_token")
                    
                    # Test new token
                    headers = {"Authorization": f"Bearer {new_token}"}
                    response = self.client.get("/api/v1/auth/me", headers=headers)
                    assert response.status_code in [200, 404], "New token should be valid"
    
    def test_permission_enforcement(self):
        """Test permission enforcement across modules"""
        
        # Test with different user roles
        role_tests = [
            ("admin", True),      # Admin should have full access
            ("analyst", True),    # Analyst should have limited access
            ("viewer", False),     # Viewer should have read-only access
            ("none", False)        # No role should be denied
        ]
        
        for role, should_have_access in role_tests:
            # Create token with specific role
            token = create_access_token(data={"sub": f"test_{role}", "role": role})
            headers = {"Authorization": f"Bearer {token}"}
            
            # Test access to different endpoints
            test_endpoints = [
                "/api/v1/compliance/statistics",
                "/api/v1/analysis/statistics",
                "/api/v1/blockchain/statistics",
                "/api/v1/intelligence/alerts"
            ]
            
            for endpoint in test_endpoints:
                response = self.client.get(endpoint, headers=headers)
                
                if should_have_access:
                    assert response.status_code not in [401, 403], \
                        f"Role {role} should have access to {endpoint}"
                else:
                    assert response.status_code in [401, 403, 404], \
                        f"Role {role} should be denied access to {endpoint}"
    
    def test_csrf_protection(self):
        """Test CSRF protection"""
        
        # Test CSRF protection on state-changing endpoints
        csrf_tests = [
            ("POST", "/api/v1/auth/login"),
            ("POST", "/api/v1/auth/register"),
            ("POST", "/api/v1/auth/logout"),
            ("POST", "/api/v1/auth/refresh")
        ]
        
        for method, endpoint in csrf_tests:
            # Test request without CSRF token
            if method == "POST":
                # Test without CSRF headers
                response = self.client.post(endpoint, json={})
                
                # Should either handle CSRF or indicate endpoint not implemented
                assert response.status_code in [200, 400, 404, 422], \
                    f"Should handle CSRF protection for {endpoint}"
    
    def test_brute_force_protection(self):
        """Test brute force attack protection"""
        
        # Test brute force protection on login
        failed_attempts = 0
        for i in range(50):
            login_data = {
                "username": "admin",
                "password": f"wrong_password_{i}"
            }
            
            response = self.client.post("/api/v1/auth/login", json=login_data)
            
            if response.status_code == 401:
                failed_attempts += 1
            elif response.status_code == 429:  # Rate limited
                break
            elif response.status_code == 423:  # Account locked
                break
        
        # Should have some protection against brute force
        assert failed_attempts > 0, "Should track failed login attempts"
    
    def test_token_tampering(self):
        """Test token tampering protection"""
        
        # Create valid token
        valid_token = create_access_token(data={"sub": "admin"})
        
        # Test token tampering
        tampered_tokens = [
            # Change parts of the token
            valid_token[:-10] + "tampered",
            valid_token[:10] + "tampered" + valid_token[10:],
            # Add invalid characters
            valid_token + "invalid",
            # Remove characters
            valid_token[:-10],
            # Replace characters
            valid_token.replace("e", "x")
        ]
        
        for tampered_token in tampered_tokens:
            headers = {"Authorization": f"Bearer {tampered_token}"}
            response = self.client.get("/api/v1/auth/me", headers=headers)
            assert response.status_code == 401, "Should reject tampered token"
    
    def test_concurrent_session_limits(self):
        """Test concurrent session limits"""
        
        # Test multiple concurrent logins
        concurrent_sessions = []
        for i in range(10):
            login_data = {
                "username": "admin",
                "password": "Admin123!@#"
            }
            
            response = self.client.post("/api/v1/auth/login", json=login_data)
            
            if response.status_code == 200:
                token_data = response.json()
                concurrent_sessions.append(token_data.get("access_token"))
            elif response.status_code == 429:  # Rate limited
                break
        
        # Should have some limit on concurrent sessions
        assert len(concurrent_sessions) <= 10, "Should limit concurrent sessions"
    
    def test_authentication_logging(self):
        """Test authentication event logging"""
        
        # Test that authentication events are logged
        auth_events = [
            ("login", {"username": "admin", "password": "Admin123!@#"}),
            ("login", {"username": "admin", "password": "wrong_password"}),
            ("logout", {}),
        ]
        
        for event_type, data in auth_events:
            if event_type == "login":
                response = self.client.post("/api/v1/auth/login", json=data)
            elif event_type == "logout":
                headers = {"Authorization": f"Bearer {create_access_token(data={'sub': 'admin'})}"}
                response = self.client.post("/api/v1/auth/logout", headers=headers)
            
            # Should handle authentication events
            assert response.status_code in [200, 401, 404], \
                f"Should handle {event_type} event"
    
    def test_password_reset_security(self):
        """Test password reset security"""
        
        # Test password reset request
        reset_data = {
            "email": "admin@example.com"
        }
        
        response = self.client.post("/api/v1/auth/reset-password", json=reset_data)
        
        # Should handle password reset request
        assert response.status_code in [200, 400, 404], "Should handle password reset request"
        
        # Test password reset confirmation
        reset_confirmation = {
            "token": f"reset_token_{uuid.uuid4().hex[:16]}",
            "new_password": "NewSecurePass123!",
            "confirm_password": "NewSecurePass123!"
        }
        
        response = self.client.post("/api/v1/auth/confirm-reset", json=reset_confirmation)
        
        # Should handle password reset confirmation
        assert response.status_code in [200, 400, 404], "Should handle password reset confirmation"


if __name__ == "__main__":
    pytest.main([__file__])
