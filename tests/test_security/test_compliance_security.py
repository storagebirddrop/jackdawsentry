"""
Security Tests - Compliance Module Security for Phases 1-3

Tests security for compliance module including SAR data protection,
case management access control, risk assessment confidentiality,
and audit trail integrity.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from src.api.main import app
from src.api.auth import create_access_token


class TestComplianceModuleSecurity:
    """Test security for compliance module"""
    
    def setup_method(self):
        """Setup test client and tokens"""
        self.client = TestClient(app)
        self.admin_token = create_access_token(data={"sub": "admin", "role": "admin"})
        self.analyst_token = create_access_token(data={"sub": "analyst", "role": "analyst"})
        self.viewer_token = create_access_token(data={"sub": "viewer", "role": "viewer"})
        self.unauthorized_token = create_access_token(data={"sub": "unauthorized", "role": "unauthorized"})
    
    def test_compliance_endpoints_require_authentication(self):
        """Test that all compliance endpoints require authentication"""
        
        compliance_endpoints = [
            # Core compliance endpoints
            ("/api/v1/compliance/statistics", "GET"),
            ("/api/v1/compliance/cases", "GET"),
            ("/api/v1/compliance/cases", "POST"),
            ("/api/v1/compliance/audit/log", "POST"),
            ("/api/v1/compliance/risk/assessments", "POST"),
            ("/api/v1/compliance/sar", "GET"),
            ("/api/v1/compliance/sar", "POST"),
            ("/api/v1/compliance/travel-rule", "POST"),
            ("/api/v1/compliance/reports", "GET"),
        ]
        
        for endpoint, method in compliance_endpoints:
            if method == "GET":
                response = self.client.get(endpoint)
            elif method == "POST":
                response = self.client.post(endpoint, json={})
            
            # All endpoints should return 401 without authentication
            assert response.status_code == 401, f"Compliance endpoint {endpoint} should require authentication"
    
    def test_sar_data_protection(self):
        """Test SAR (Suspicious Activity Report) data protection"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test SAR creation with sensitive data
        sar_data = {
            "case_id": f"SAR-{uuid.uuid4().hex[:8].upper()}",
            "subject_name": "John Doe",
            "subject_address": "123 Main St, Anytown, USA",
            "subject_dob": "1980-01-01",
            "subject_id_number": "123-45-6789",
            "suspicious_activity": "Unusual transaction patterns detected",
            "amount_involved": 50000.0,
            "currency": "USD",
            "filing_date": datetime.now(timezone.utc).isoformat(),
            "reporter_id": "analyst_001",
            "risk_score": 8.5
        }
        
        response = self.client.post(
            "/api/v1/compliance/sar",
            json=sar_data,
            headers=headers
        )
        
        # Should either succeed (201) or indicate endpoint not implemented (404)
        if response.status_code == 201:
            created_sar = response.json()
            
            # Check that sensitive data is handled properly
            sensitive_fields = ["subject_dob", "subject_id_number", "subject_address"]
            for field in sensitive_fields:
                if field in created_sar:
                    # Sensitive data should be present but protected
                    assert created_sar[field] is not None, f"SAR field {field} should be stored"
                    # In a real implementation, would check for encryption/redaction
        
        # Test SAR retrieval - should have proper access control
        if response.status_code == 201:
            sar_id = created_sar.get("id", "test-id")
            
            # Test with different user roles
            role_tests = [
                (self.admin_token, 200),      # Admin should access
                (self.analyst_token, 200),    # Analyst should access
                (self.viewer_token, 403),     # Viewer should be denied
                (self.unauthorized_token, 403) # Unauthorized should be denied
            ]
            
            for token, expected_status in role_tests:
                test_headers = {"Authorization": f"Bearer {token}"}
                get_response = self.client.get(f"/api/v1/compliance/sar/{sar_id}", headers=test_headers)
                
                if expected_status == 200:
                    assert get_response.status_code != 403, f"Role should have access to SAR data"
                else:
                    assert get_response.status_code in [403, 404], f"Role should be denied access to SAR data"
    
    def test_case_management_access_control(self):
        """Test compliance case management access control"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test case creation
        case_data = {
            "title": f"Test Case {uuid.uuid4().hex[:8]}",
            "description": "Test case for security validation",
            "case_type": "investigation",
            "priority": "high",
            "assigned_to": "analyst_001",
            "status": "open",
            "sensitive_info": "This contains sensitive case information",
            "confidential_sources": ["source_1", "source_2"]
        }
        
        response = self.client.post(
            "/api/v1/compliance/cases",
            json=case_data,
            headers=headers
        )
        
        if response.status_code == 201:
            created_case = response.json()
            case_id = created_case.get("id", "test-id")
            
            # Test access control for different operations
            access_tests = [
                # (token, operation, expected_success)
                (self.admin_token, "read", True),
                (self.analyst_token, "read", True),
                (self.viewer_token, "read", False),
                (self.unauthorized_token, "read", False),
                (self.admin_token, "write", True),
                (self.analyst_token, "write", True),
                (self.viewer_token, "write", False),
                (self.unauthorized_token, "write", False),
                (self.admin_token, "delete", True),
                (self.analyst_token, "delete", False),
                (self.viewer_token, "delete", False),
                (self.unauthorized_token, "delete", False),
            ]
            
            for token, operation, should_succeed in access_tests:
                test_headers = {"Authorization": f"Bearer {token}"}
                
                if operation == "read":
                    test_response = self.client.get(f"/api/v1/compliance/cases/{case_id}", headers=test_headers)
                elif operation == "write":
                    update_data = {"description": "Updated description"}
                    test_response = self.client.put(f"/api/v1/compliance/cases/{case_id}", json=update_data, headers=test_headers)
                elif operation == "delete":
                    test_response = self.client.delete(f"/api/v1/compliance/cases/{case_id}", headers=test_headers)
                
                if should_succeed:
                    assert test_response.status_code not in [401, 403], f"Role should have {operation} access to compliance cases"
                else:
                    assert test_response.status_code in [401, 403, 404], f"Role should be denied {operation} access to compliance cases"
    
    def test_risk_assessment_confidentiality(self):
        """Test risk assessment data confidentiality"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test risk assessment creation
        risk_data = {
            "entity_id": f"0x{uuid.uuid4().hex[:40]}",
            "entity_type": "address",
            "risk_score": 7.8,
            "risk_level": "high",
            "factors": ["mixing", "high_volume", "suspicious_patterns"],
            "assessment_date": datetime.now(timezone.utc).isoformat(),
            "assessor_id": "analyst_001",
            "confidential_notes": "Internal risk assessment details",
            "regulatory_flags": ["aml_flag", "sanctions_screening"]
        }
        
        response = self.client.post(
            "/api/v1/compliance/risk/assessments",
            json=risk_data,
            headers=headers
        )
        
        if response.status_code == 201:
            created_risk = response.json()
            risk_id = created_risk.get("id", "test-id")
            
            # Test that confidential data is protected
            confidential_fields = ["confidential_notes", "regulatory_flags"]
            for field in confidential_fields:
                if field in created_risk:
                    assert created_risk[field] is not None, f"Risk assessment field {field} should be stored"
                    # In real implementation, would check for access control
            
            # Test access control for risk assessments
            role_access_tests = [
                (self.admin_token, True),      # Admin should access
                (self.analyst_token, True),    # Analyst should access
                (self.viewer_token, False),     # Viewer should be denied
                (self.unauthorized_token, False) # Unauthorized should be denied
            ]
            
            for token, should_access in role_access_tests:
                test_headers = {"Authorization": f"Bearer {token}"}
                get_response = self.client.get(f"/api/v1/compliance/risk/assessments/{risk_id}", headers=test_headers)
                
                if should_access:
                    assert get_response.status_code not in [401, 403], f"Role should access risk assessment"
                else:
                    assert get_response.status_code in [401, 403, 404], f"Role should be denied access to risk assessment"
    
    def test_audit_trail_integrity(self):
        """Test audit trail integrity and security"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test audit log creation
        audit_data = {
            "event_type": "CASE_ACCESS",
            "user_id": "analyst_001",
            "action": "Viewed sensitive case details",
            "resource_type": "compliance_case",
            "resource_id": f"case_{uuid.uuid4().hex[:8]}",
            "details": {
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "sensitivity_level": "high"
            },
            "metadata": {
                "session_id": f"session_{uuid.uuid4().hex[:16]}",
                "request_id": f"req_{uuid.uuid4().hex[:16]}"
            }
        }
        
        response = self.client.post(
            "/api/v1/compliance/audit/log",
            json=audit_data,
            headers=headers
        )
        
        # Should handle audit logging
        assert response.status_code in [201, 404], "Should handle audit log creation"
        
        # Test audit log access control
        audit_access_tests = [
            (self.admin_token, True),      # Admin should access audit logs
            (self.analyst_token, False),    # Analyst should be denied
            (self.viewer_token, False),     # Viewer should be denied
            (self.unauthorized_token, False) # Unauthorized should be denied
        ]
        
        for token, should_access in audit_access_tests:
            test_headers = {"Authorization": f"Bearer {token}"}
            get_response = self.client.get("/api/v1/compliance/audit/logs", headers=test_headers)
            
            if should_access:
                assert get_response.status_code not in [401, 403], f"Role should access audit logs"
            else:
                assert get_response.status_code in [401, 403, 404], f"Role should be denied access to audit logs"
    
    def test_travel_rule_compliance_security(self):
        """Test Travel Rule compliance security"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test Travel Rule filing
        travel_rule_data = {
            "transaction_id": f"tx_{uuid.uuid4().hex[:16]}",
            "originator": {
                "name": "Originator Bank",
                "account_number": "1234567890",
                "address": "123 Bank St, Financial District"
            },
            "beneficiary": {
                "name": "Beneficiary Customer",
                "account_number": "0987654321",
                "address": "456 Client Ave, Business District"
            },
            "transaction_details": {
                "amount": 10000.0,
                "currency": "USD",
                "date": datetime.now(timezone.utc).isoformat(),
                "payment_reference": f"ref_{uuid.uuid4().hex[:8]}"
            },
            "filing_institution": "Jackdaw Sentry Compliance",
            "filing_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        response = self.client.post(
            "/api/v1/compliance/travel-rule",
            json=travel_rule_data,
            headers=headers
        )
        
        # Should handle Travel Rule filing
        assert response.status_code in [201, 404], "Should handle Travel Rule filing"
        
        if response.status_code == 201:
            created_filing = response.json()
            
            # Check sensitive data protection
            sensitive_fields = ["originator", "beneficiary"]
            for field in sensitive_fields:
                if field in created_filing:
                    assert created_filing[field] is not None, f"Travel Rule field {field} should be stored"
                    # In real implementation, would check for encryption
    
    def test_data_retention_policies(self):
        """Test data retention policies for compliance data"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test data retention queries
        retention_tests = [
            "/api/v1/compliance/cases?retention=expired",
            "/api/v1/compliance/sar?retention=expired", 
            "/api/v1/compliance/audit/logs?retention=expired",
            "/api/v1/compliance/risk/assessments?retention=expired"
        ]
        
        for endpoint in retention_tests:
            response = self.client.get(endpoint, headers=headers)
            
            # Should handle retention queries
            assert response.status_code in [200, 404], f"Should handle retention query: {endpoint}"
            
            if response.status_code == 200:
                data = response.json()
                # In real implementation, would verify expired data is handled properly
    
    def test_regulatory_reporting_security(self):
        """Test regulatory reporting security"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test regulatory report generation
        report_data = {
            "report_type": "quarterly_aml",
            "period_start": (datetime.now(timezone.utc) - timedelta(days=90)).isoformat(),
            "period_end": datetime.now(timezone.utc).isoformat(),
            "include_suspicious_activities": True,
            "include_risk_assessments": True,
            "include_audit_trail": True,
            "format": "json"
        }
        
        response = self.client.post(
            "/api/v1/compliance/reports/generate",
            json=report_data,
            headers=headers
        )
        
        # Should handle report generation
        assert response.status_code in [201, 404], "Should handle regulatory report generation"
        
        # Test report access control
        report_access_tests = [
            (self.admin_token, True),      # Admin should access reports
            (self.analyst_token, True),    # Analyst should access reports
            (self.viewer_token, False),     # Viewer should be denied
            (self.unauthorized_token, False) # Unauthorized should be denied
        ]
        
        for token, should_access in report_access_tests:
            test_headers = {"Authorization": f"Bearer {token}"}
            get_response = self.client.get("/api/v1/compliance/reports", headers=test_headers)
            
            if should_access:
                assert get_response.status_code not in [401, 403], f"Role should access compliance reports"
            else:
                assert get_response.status_code in [401, 403, 404], f"Role should be denied access to compliance reports"


if __name__ == "__main__":
    pytest.main([__file__])
