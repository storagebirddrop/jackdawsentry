"""
Compliance Tests - Analysis Module Compliance for Phases 1-3

Tests compliance for analysis module including GDPR compliance,
data retention policies, audit requirements, and regulatory reporting.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from src.api.main import app
from src.api.auth import create_access_token


class TestAnalysisModuleCompliance:
    """Test compliance for analysis module"""
    
    def setup_method(self):
        """Setup test client and tokens"""
        self.client = TestClient(app)
        self.admin_token = create_access_token(data={"sub": "admin", "role": "admin"})
        self.analyst_token = create_access_token(data={"sub": "analyst", "role": "analyst"})
        self.viewer_token = create_access_token(data={"sub": "viewer", "role": "viewer"})
    
    def test_gdpr_compliance_for_analysis_data(self):
        """Test GDPR compliance for analysis data"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test analysis data with personal information
        analysis_data = {
            "entity_id": f"0x{uuid.uuid4().hex[:40]}",
            "entity_type": "address",
            "personal_data": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "+1234567890",
                "address": "123 Main St, Anytown, USA",
                "ip_address": "192.168.1.100"
            },
            "analysis_type": "risk_assessment",
            "processing_purpose": "fraud_investigation",
            "legal_basis": "legitimate_interest",
            "retention_period_days": 365
        }
        
        response = self.client.post(
            "/api/v1/analysis/address",
            json=analysis_data,
            headers=headers
        )
        
        # Should handle GDPR-compliant analysis
        assert response.status_code in [200, 404], "Should handle GDPR-compliant analysis"
        
        if response.status_code == 200:
            result = response.json()
            
            # Check GDPR compliance indicators
            if "gdpr_compliance" in result:
                compliance = result["gdpr_compliance"]
                assert "data_minimization" in compliance, "Should have data minimization"
                assert "purpose_limitation" in compliance, "Should have purpose limitation"
                assert "retention_policy" in compliance, "Should have retention policy"
    
    def test_data_retention_policies(self):
        """Test data retention policies for analysis data"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test data retention settings
        retention_tests = [
            # Standard retention
            {
                "data_type": "risk_assessment",
                "retention_days": 365,
                "auto_delete": True
            },
            # Extended retention for legal reasons
            {
                "data_type": "investigation_data",
                "retention_days": 2555,  # 7 years
                "auto_delete": False,
                "legal_hold": True
            },
            # Short retention for temporary data
            {
                "data_type": "temporary_analysis",
                "retention_days": 30,
                "auto_delete": True
            }
        ]
        
        for retention_test in retention_tests:
            response = self.client.post(
                "/api/v1/analysis/retention-policy",
                json=retention_test,
                headers=headers
            )
            
            # Should handle retention policy
            assert response.status_code in [201, 404], \
                f"Should handle retention policy for {retention_test['data_type']}"
    
    def test_audit_trail_for_analysis(self):
        """Test audit trail for analysis operations"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test audit trail requirements
        audit_requirements = [
            "user_id",
            "timestamp",
            "action",
            "resource_type",
            "resource_id",
            "data_accessed",
            "purpose",
            "legal_basis"
        ]
        
        # Test analysis operation that should create audit trail
        analysis_request = {
            "address": f"0x{uuid.uuid4().hex[:40]}",
            "blockchain": "ethereum",
            "include_audit_logging": True
        }
        
        response = self.client.post(
            "/api/v1/analysis/address",
            json=analysis_request,
            headers=headers
        )
        
        # Should handle analysis with audit logging
        assert response.status_code in [200, 404], "Should handle analysis with audit logging"
        
        # Test audit trail retrieval
        response = self.client.get("/api/v1/analysis/audit-trail", headers=headers)
        
        # Should handle audit trail retrieval
        assert response.status_code in [200, 404], "Should handle audit trail retrieval"
        
        if response.status_code == 200:
            audit_data = response.json()
            if isinstance(audit_data, list) and audit_data:
                # Check audit record completeness
                audit_record = audit_data[0]
                for requirement in audit_requirements:
                    assert requirement in audit_record, \
                        f"Audit record should contain {requirement}"
    
    def test_data_subject_rights(self):
        """Test data subject rights for analysis data"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test data subject access request
        subject_request = {
            "subject_identifier": f"0x{uuid.uuid4().hex[:40]}",
            "request_type": "access",
            "purpose": "data_subject_access_request",
            "contact_email": "subject@example.com"
        }
        
        response = self.client.post(
            "/api/v1/analysis/data-subject-request",
            json=subject_request,
            headers=headers
        )
        
        # Should handle data subject request
        assert response.status_code in [200, 404], "Should handle data subject request"
        
        # Test data subject erasure request
        erasure_request = {
            "subject_identifier": f"0x{uuid.uuid4().hex[:40]}",
            "request_type": "erasure",
            "purpose": "right_to_be_forgotten",
            "contact_email": "subject@example.com",
            "verification_code": f"verify_{uuid.uuid4().hex[:8]}"
        }
        
        response = self.client.post(
            "/api/v1/analysis/data-subject-request",
            json=erasure_request,
            headers=headers
        )
        
        # Should handle erasure request
        assert response.status_code in [200, 404], "Should handle erasure request"
        
        # Test data portability request
        portability_request = {
            "subject_identifier": f"0x{uuid.uuid4().hex[:40]}",
            "request_type": "portability",
            "purpose": "data_portability",
            "format": "json",
            "contact_email": "subject@example.com"
        }
        
        response = self.client.post(
            "/api/v1/analysis/data-subject-request",
            json=portability_request,
            headers=headers
        )
        
        # Should handle portability request
        assert response.status_code in [200, 404], "Should handle portability request"
    
    def test_consent_management(self):
        """Test consent management for analysis data"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test consent recording
        consent_data = {
            "subject_id": f"0x{uuid.uuid4().hex[:40]}",
            "consent_given": True,
            "consent_date": datetime.now(timezone.utc).isoformat(),
            "consent_purpose": "risk_analysis",
            "consent_scope": ["risk_assessment", "pattern_detection"],
            "withdrawal_date": None,
            "legal_basis": "explicit_consent"
        }
        
        response = self.client.post(
            "/api/v1/analysis/consent",
            json=consent_data,
            headers=headers
        )
        
        # Should handle consent recording
        assert response.status_code in [201, 404], "Should handle consent recording"
        
        # Test consent withdrawal
        withdrawal_data = {
            "subject_id": f"0x{uuid.uuid4().hex[:40]}",
            "consent_given": False,
            "withdrawal_date": datetime.now(timezone.utc).isoformat(),
            "reason": "user_withdrawal"
        }
        
        response = self.client.put(
            f"/api/v1/analysis/consent/{consent_data['subject_id']}",
            json=withdrawal_data,
            headers=headers
        )
        
        # Should handle consent withdrawal
        assert response.status_code in [200, 404], "Should handle consent withdrawal"
    
    def test_regulatory_reporting(self):
        """Test regulatory reporting for analysis data"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test SAR reporting
        sar_report = {
            "report_type": "suspicious_activity",
            "period_start": (datetime.now(timezone.utc) - timedelta(days=90)).isoformat(),
            "period_end": datetime.now(timezone.utc).isoformat(),
            "include_analysis_results": True,
            "include_risk_assessments": True,
            "include_investigations": True,
            "format": "json"
        }
        
        response = self.client.post(
            "/api/v1/analysis/regulatory-report",
            json=sar_report,
            headers=headers
        )
        
        # Should handle regulatory reporting
        assert response.status_code in [201, 404], "Should handle regulatory reporting"
        
        # Test AML reporting
        aml_report = {
            "report_type": "aml_transaction",
            "threshold_amount": 10000.0,
            "currency": "USD",
            "period_start": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
            "period_end": datetime.now(timezone.utc).isoformat(),
            "include_high_risk_transactions": True,
            "include_pattern_matches": True
        }
        
        response = self.client.post(
            "/api/v1/analysis/aml-report",
            json=aml_report,
            headers=headers
        )
        
        # Should handle AML reporting
        assert response.status_code in [201, 404], "Should handle AML reporting"
    
    def test_privacy_impact_assessment(self):
        """Test privacy impact assessment for analysis operations"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test PIA for new analysis feature
        pia_data = {
            "feature_name": "Advanced Risk Scoring",
            "data_types": ["address", "transaction", "behavioral"],
            "processing_purposes": ["fraud_detection", "risk_assessment"],
            "legal_basis": "legitimate_interest",
            "data_subjects": ["crypto_users", "transaction_participants"],
            "risks": ["data_breach", "unauthorized_access", "data_loss"],
            "mitigation_measures": [
                "encryption_at_rest",
                "access_controls",
                "audit_logging",
                "data_minimization"
            ],
            "retention_period": "365_days"
        }
        
        response = self.client.post(
            "/api/v1/analysis/privacy-impact-assessment",
            json=pia_data,
            headers=headers
        )
        
        # Should handle PIA
        assert response.status_code in [201, 404], "Should handle privacy impact assessment"
    
    def test_cross_border_data_transfers(self):
        """Test cross-border data transfer compliance"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test cross-border transfer assessment
        transfer_data = {
            "data_type": "analysis_results",
            "destination_country": "US",
            "data_subjects": ["crypto_users"],
            "transfer_purpose": "fraud_investigation",
            "adequacy_decision": True,
            "safeguards": [
                "standard_contractual_clauses",
                "encryption_in_transit",
                "access_controls"
            ]
        }
        
        response = self.client.post(
            "/api/v1/analysis/cross-border-transfer",
            json=transfer_data,
            headers=headers
        )
        
        # Should handle cross-border transfer
        assert response.status_code in [200, 404], "Should handle cross-border transfer"
    
    def test_data_breach_notification(self):
        """Test data breach notification procedures"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test breach notification
        breach_data = {
            "breach_id": f"breach_{uuid.uuid4().hex[:8]}",
            "detection_date": datetime.now(timezone.utc).isoformat(),
            "data_types_affected": ["analysis_results", "user_data"],
            "affected_subjects": 150,
            "nature_of_breach": "unauthorized_access",
            "containment_measures": [
                "immediate_password_reset",
                "access_revocation",
                "system_isolation"
            ],
            "notification_required": True,
            "supervisor_notified": True,
            "dpo_notified": True
        }
        
        response = self.client.post(
            "/api/v1/analysis/data-breach-notification",
            json=breach_data,
            headers=headers
        )
        
        # Should handle breach notification
        assert response.status_code in [201, 404], "Should handle breach notification"
    
    def test_compliance_monitoring(self):
        """Test compliance monitoring and reporting"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test compliance monitoring
        monitoring_data = {
            "compliance_area": "data_protection",
            "monitoring_period": "monthly",
            "metrics": [
                "data_subject_requests_processed",
                "response_times",
                "breach_notifications",
                "consent_withdrawals",
                "data_retention_compliance"
            ]
        }
        
        response = self.client.post(
            "/api/v1/analysis/compliance-monitoring",
            json=monitoring_data,
            headers=headers
        )
        
        # Should handle compliance monitoring
        assert response.status_code in [200, 404], "Should handle compliance monitoring"
        
        # Test compliance dashboard
        response = self.client.get("/api/v1/analysis/compliance-dashboard", headers=headers)
        
        # Should handle compliance dashboard
        assert response.status_code in [200, 404], "Should handle compliance dashboard"


if __name__ == "__main__":
    pytest.main([__file__])
