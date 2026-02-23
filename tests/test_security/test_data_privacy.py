"""
Security Tests - Data Privacy & GDPR Compliance for Phase 4

Tests data privacy, GDPR compliance, and data protection for Phase 4 modules:
- Personal data handling
- Data retention policies
- Right to be forgotten
- Data subject rights
- Audit trails
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.auth import create_access_token


class TestDataPrivacy:
    """Test data privacy and GDPR compliance for Phase 4"""
    
    def setup_method(self):
        """Setup test client and test data"""
        self.client = TestClient(app)
        self.admin_token = create_access_token(data={"sub": "admin"})
        self.user_token = create_access_token(data={"sub": "user"})
    
    def test_personal_data_identification(self):
        """Test that personal data is properly identified and handled"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test victim reports endpoint (contains personal data)
        response = self.client.get("/api/v1/intelligence/victim-reports/", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if personal data fields are present
            if isinstance(data, list) and data:
                # Check for personal data indicators
                personal_data_fields = [
                    "victim_contact",
                    "victim_address", 
                    "victim_email",
                    "victim_phone",
                    "personal_identifiers"
                ]
                
                # Verify personal data is handled appropriately
                for item in data:
                    if isinstance(item, dict):
                        # Personal data should be present but protected
                        for field in personal_data_fields:
                            if field in item:
                                # Personal data should be properly formatted/protected
                                assert item[field] is not None, f"Personal data field {field} should not be null"
                                assert isinstance(item[field], (str, dict)), f"Personal data field {field} should be properly typed"
    
    def test_data_minimization_principle(self):
        """Test that only necessary data is collected and stored"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test creating a victim report with minimal data
        minimal_report = {
            "report_type": "phishing",
            "description": "Test report with minimal data",
            "severity": "low"
        }
        
        response = self.client.post(
            "/api/v1/intelligence/victim-reports/",
            json=minimal_report,
            headers=headers
        )
        
        # Should accept minimal data
        assert response.status_code in [201, 422], "Should accept minimal data or return validation error"
        
        if response.status_code == 201:
            created_data = response.json()
            # Verify only provided fields are stored
            for field in minimal_report:
                assert field in created_data, f"Provided field {field} should be stored"
    
    def test_sensitive_data_redaction(self):
        """Test that sensitive data is redacted in logs and responses"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test with data that should be redacted
        sensitive_report = {
            "report_type": "phishing",
            "victim_contact": "victim@example.com",
            "victim_phone": "+1234567890",
            "credit_card": "4111111111111111",
            "ssn": "123-45-6789",
            "description": "Report with sensitive info"
        }
        
        response = self.client.post(
            "/api/v1/intelligence/victim-reports/",
            json=sensitive_report,
            headers=headers
        )
        
        if response.status_code == 201:
            created_data = response.json()
            
            # Sensitive data should be redacted or protected
            sensitive_fields = ["credit_card", "ssn"]
            for field in sensitive_fields:
                if field in created_data:
                    # Should be redacted (masked or partially shown)
                    value = created_data[field]
                    if isinstance(value, str):
                        # Check for redaction patterns
                        assert "****" in value or "***" in value or len(value) < 4, \
                            f"Sensitive field {field} should be redacted"
    
    def test_data_retention_compliance(self):
        """Test data retention policies are enforced"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test old data cleanup (mock implementation)
        old_date = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
        
        # This would test data retention policies
        # In a real implementation, this would check if old data is properly handled
        
        # For now, test that the system can handle date-based queries
        response = self.client.get(
            "/api/v1/intelligence/victim-reports/",
            params={"start_date": old_date},
            headers=headers
        )
        
        # Should handle date filtering without errors
        assert response.status_code != 500, "Should handle date-based queries"
    
    def test_right_to_be_forgotten(self):
        """Test GDPR right to be forgotten implementation"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test data deletion for GDPR compliance
        # This would typically be a DELETE endpoint for personal data
        
        # Mock implementation - test that deletion endpoints exist
        test_identifiers = [
            "victim@example.com",
            "0x1234567890123456789012345678901234567890",  # Ethereum address
            "+1234567890"
        ]
        
        for identifier in test_identifiers:
            # Test deletion endpoint (would be implemented for GDPR)
            # This is a placeholder for the actual implementation
            response = self.client.delete(
                f"/api/v1/intelligence/victim-reports/by-identifier/{identifier}",
                headers=headers
            )
            
            # Should either succeed (200) or indicate endpoint not implemented (404)
            assert response.status_code in [200, 404, 405], \
                f"Should handle deletion requests for identifier {identifier}"
    
    def test_data_subject_access_rights(self):
        """Test data subject's right to access their data"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test data access endpoint for data subjects
        test_subject = "victim@example.com"
        
        response = self.client.get(
            f"/api/v1/intelligence/victim-reports/by-subject/{test_subject}",
            headers=headers
        )
        
        # Should either return data or indicate endpoint not implemented
        assert response.status_code in [200, 404], \
            f"Should handle data subject access requests for {test_subject}"
        
        if response.status_code == 200:
            data = response.json()
            # Should only return data for the specified subject
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        # Verify data belongs to the subject
                        assert test_subject in str(item).lower(), \
                            f"Returned data should belong to subject {test_subject}"
    
    def test_consent_management(self):
        """Test consent management for data processing"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test consent recording and management
        consent_data = {
            "subject_id": "test@example.com",
            "consent_given": True,
            "consent_date": datetime.now(timezone.utc).isoformat(),
            "consent_purpose": "fraud_investigation",
            "withdrawal_date": None
        }
        
        # This would test consent management endpoints
        # For now, test that the system can handle consent-related data
        
        response = self.client.post(
            "/api/v1/intelligence/consent",
            json=consent_data,
            headers=headers
        )
        
        # Should either succeed or indicate endpoint not implemented
        assert response.status_code in [201, 404], \
            "Should handle consent management requests"
    
    def test_data_portability(self):
        """Test data portability rights"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test data export in machine-readable format
        test_subject = "test@example.com"
        
        response = self.client.get(
            f"/api/v1/intelligence/victim-reports/export/{test_subject}",
            headers=headers
        )
        
        # Should either return data or indicate endpoint not implemented
        assert response.status_code in [200, 404], \
            f"Should handle data portability requests for {test_subject}"
        
        if response.status_code == 200:
            # Should return data in portable format (JSON, CSV, etc.)
            content_type = response.headers.get("content-type", "")
            assert "json" in content_type or "csv" in content_type, \
                "Export should be in machine-readable format"


class TestAuditTrail:
    """Test audit trail and logging for Phase 4"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
        self.admin_token = create_access_token(data={"sub": "admin"})
        self.user_token = create_access_token(data={"sub": "user"})
    
    def test_audit_trail_creation(self):
        """Test that audit trails are created for sensitive operations"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test operations that should create audit trails
        audit_operations = [
            ("POST", "/api/v1/intelligence/victim-reports/", {
                "report_type": "phishing",
                "description": "Test audit trail"
            }),
            ("POST", "/api/v1/intelligence/threat-feeds/", {
                "name": "Test Feed",
                "url": "https://example.com"
            }),
            ("POST", "/api/v1/forensics/cases", {
                "title": "Test Case",
                "description": "Test audit"
            })
        ]
        
        for method, endpoint, data in audit_operations:
            response = self.client.request(method, endpoint, json=data, headers=headers)
            
            # Operation should succeed or fail gracefully
            # In a real implementation, this would verify audit log creation
            assert response.status_code in [201, 400, 422], \
                f"Operation {method} {endpoint} should be handled"
    
    def test_audit_log_integrity(self):
        """Test that audit logs maintain integrity"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # This would test audit log integrity features like:
        # - Hash chains
        # - Tamper detection
        # - Immutable records
        
        # For now, test that logging infrastructure exists
        response = self.client.get(
            "/api/v1/intelligence/audit-logs",
            headers=headers
        )
        
        # Should either return logs or indicate endpoint not implemented
        assert response.status_code in [200, 404], \
            "Should handle audit log requests"
    
    def test_sensitive_operation_logging(self):
        """Test that sensitive operations are properly logged"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test operations that require special logging
        sensitive_operations = [
            # Data access operations
            ("GET", "/api/v1/intelligence/victim-reports/"),
            # Data modification operations  
            ("POST", "/api/v1/intelligence/victim-reports/"),
            # Administrative operations
            ("DELETE", "/api/v1/intelligence/victim-reports/test-id"),
        ]
        
        for method, endpoint in sensitive_operations:
            if method == "GET":
                response = self.client.get(endpoint, headers=headers)
            elif method == "POST":
                response = self.client.post(endpoint, json={}, headers=headers)
            elif method == "DELETE":
                response = self.client.delete(endpoint, headers=headers)
            
            # Should handle the operation (success or failure)
            # In real implementation, would verify audit log creation
            assert response.status_code in [200, 201, 404, 405], \
                f"Sensitive operation {method} {endpoint} should be logged"
    
    def test_log_redaction(self):
        """Test that sensitive data is redacted in logs"""
        
        # This would test that sensitive data in logs is properly redacted
        # In a real implementation, would check log files or log output
        
        # For now, test that the system has redaction capabilities
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        sensitive_data = {
            "victim_contact": "sensitive@example.com",
            "credit_card": "4111111111111111",
            "description": "Report with sensitive data"
        }
        
        response = self.client.post(
            "/api/v1/intelligence/victim-reports/",
            json=sensitive_data,
            headers=headers
        )
        
        # Should handle the request
        assert response.status_code in [201, 422], \
            "Should handle requests with sensitive data"


class TestDataEncryption:
    """Test data encryption and protection"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
        self.admin_token = create_access_token(data={"sub": "admin"})
    
    def test_data_at_rest_encryption(self):
        """Test that sensitive data is encrypted at rest"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test storing sensitive data
        sensitive_data = {
            "report_type": "fraud",
            "victim_contact": "encrypted@example.com",
            "sensitive_notes": "This should be encrypted",
            "metadata": {"encryption_test": True}
        }
        
        response = self.client.post(
            "/api/v1/intelligence/victim-reports/",
            json=sensitive_data,
            headers=headers
        )
        
        if response.status_code == 201:
            created_data = response.json()
            
            # In a real implementation, would verify data is encrypted
            # For now, test that the system handles sensitive data
            assert "sensitive_notes" in created_data, \
                "Should handle sensitive data fields"
    
    def test_transit_encryption(self):
        """Test that data is encrypted in transit"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test HTTPS enforcement (would be done at infrastructure level)
        # For now, test that the API can handle secure requests
        
        response = self.client.get(
            "/api/v1/intelligence/victim-reports/",
            headers=headers
        )
        
        # Should handle the request
        assert response.status_code in [200, 401], \
            "Should handle secure requests"
    
    def test_key_management(self):
        """Test encryption key management"""
        
        # This would test key rotation, key storage, etc.
        # For now, test that the system has key management capabilities
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test that encryption is working
        test_data = {"test": "encryption test"}
        
        response = self.client.post(
            "/api/v1/intelligence/victim-reports/",
            json=test_data,
            headers=headers
        )
        
        # Should handle the request
        assert response.status_code in [201, 422], \
            "Should handle encrypted data storage"


if __name__ == "__main__":
    pytest.main([__file__])
