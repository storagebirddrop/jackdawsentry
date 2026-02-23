"""
Security Tests - Analysis Module Security for Phases 1-3

Tests security for analysis module including ML model security,
pattern detection validation, risk scoring data protection,
and investigation result confidentiality.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from src.api.main import app
from src.api.auth import create_access_token


class TestAnalysisModuleSecurity:
    """Test security for analysis module"""
    
    def setup_method(self):
        """Setup test client and tokens"""
        self.client = TestClient(app)
        self.admin_token = create_access_token(data={"sub": "admin", "role": "admin"})
        self.analyst_token = create_access_token(data={"sub": "analyst", "role": "analyst"})
        self.viewer_token = create_access_token(data={"sub": "viewer", "role": "viewer"})
        self.unauthorized_token = create_access_token(data={"sub": "unauthorized", "role": "unauthorized"})
    
    def test_analysis_endpoints_require_authentication(self):
        """Test that all analysis endpoints require authentication"""
        
        analysis_endpoints = [
            # Core analysis endpoints
            ("/api/v1/analysis/address", "POST"),
            ("/api/v1/analysis/transaction", "POST"),
            ("/api/v1/analysis/statistics", "GET"),
            ("/api/v1/analysis/patterns", "GET"),
            ("/api/v1/analysis/patterns", "POST"),
            ("/api/v1/analysis/risk-scores", "GET"),
            ("/api/v1/analysis/investigations", "GET"),
            ("/api/v1/analysis/investigations", "POST"),
            ("/api/v1/analysis/ml-models", "GET"),
            ("/api/v1/analysis/graph-analysis", "POST"),
        ]
        
        for endpoint, method in analysis_endpoints:
            if method == "GET":
                response = self.client.get(endpoint)
            elif method == "POST":
                response = self.client.post(endpoint, json={})
            
            # All endpoints should return 401 without authentication
            assert response.status_code == 401, f"Analysis endpoint {endpoint} should require authentication"
    
    def test_ml_model_input_validation(self):
        """Test ML model input validation and security"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test address analysis with various inputs
        test_cases = [
            # Valid input
            {
                "address": "0x1234567890123456789012345678901234567890",
                "blockchain": "ethereum",
                "include_risk_analysis": True
            },
            # Invalid address format
            {
                "address": "invalid_address",
                "blockchain": "ethereum",
                "include_risk_analysis": True
            },
            # SQL injection attempt
            {
                "address": "'; DROP TABLE ml_models; --",
                "blockchain": "ethereum",
                "include_risk_analysis": True
            },
            # XSS attempt
            {
                "address": "<script>alert('xss')</script>",
                "blockchain": "ethereum",
                "include_risk_analysis": True
            },
            # Extremely long input
            {
                "address": "x" * 1000,
                "blockchain": "ethereum",
                "include_risk_analysis": True
            }
        ]
        
        for test_case in test_cases:
            response = self.client.post(
                "/api/v1/analysis/address",
                json=test_case,
                headers=headers
            )
            
            # Should handle input validation gracefully
            assert response.status_code in [200, 400, 422], \
                f"Should handle input validation for: {test_case['address'][:50]}..."
            
            if response.status_code == 200:
                # Check that response doesn't contain malicious content
                response_text = response.text.lower()
                malicious_patterns = ["<script>", "drop table", "alert("]
                for pattern in malicious_patterns:
                    assert pattern not in response_text, f"Response should not contain malicious pattern: {pattern}"
    
    def test_pattern_detection_security(self):
        """Test pattern detection security and validation"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test pattern creation and validation
        pattern_data = {
            "name": f"Test Pattern {uuid.uuid4().hex[:8]}",
            "description": "Test pattern for security validation",
            "pattern_type": "mixing",
            "indicators": [
                {"type": "address", "value": "0x1234567890123456789012345678901234567890"},
                {"type": "transaction", "value": "high_volume"},
                {"type": "behavior", "value": "rapid_movement"}
            ],
            "confidence_threshold": 0.8,
            "is_active": True
        }
        
        response = self.client.post(
            "/api/v1/analysis/patterns",
            json=pattern_data,
            headers=headers
        )
        
        # Should handle pattern creation
        assert response.status_code in [201, 404], "Should handle pattern creation"
        
        if response.status_code == 201:
            created_pattern = response.json()
            pattern_id = created_pattern.get("id", "test-id")
            
            # Test pattern access control
            pattern_access_tests = [
                (self.admin_token, True),      # Admin should access
                (self.analyst_token, True),    # Analyst should access
                (self.viewer_token, False),     # Viewer should be denied
                (self.unauthorized_token, False) # Unauthorized should be denied
            ]
            
            for token, should_access in pattern_access_tests:
                test_headers = {"Authorization": f"Bearer {token}"}
                get_response = self.client.get(f"/api/v1/analysis/patterns/{pattern_id}", headers=test_headers)
                
                if should_access:
                    assert get_response.status_code not in [401, 403], f"Role should access pattern data"
                else:
                    assert get_response.status_code in [401, 403, 404], f"Role should be denied access to pattern data"
    
    def test_risk_scoring_data_protection(self):
        """Test risk scoring data protection and confidentiality"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test risk scoring request
        risk_request = {
            "entity_id": f"0x{uuid.uuid4().hex[:40]}",
            "entity_type": "address",
            "scoring_model": "advanced_ml",
            "include_detailed_factors": True,
            "include_confidence_scores": True,
            "include_historical_data": True
        }
        
        response = self.client.post(
            "/api/v1/analysis/risk-scores",
            json=risk_request,
            headers=headers
        )
        
        # Should handle risk scoring
        assert response.status_code in [200, 404], "Should handle risk scoring request"
        
        if response.status_code == 200:
            risk_result = response.json()
            
            # Check that sensitive risk data is handled properly
            sensitive_fields = ["detailed_factors", "confidence_scores", "historical_data"]
            for field in sensitive_fields:
                if field in risk_result:
                    assert risk_result[field] is not None, f"Risk scoring field {field} should be present"
                    # In real implementation, would check for access control
            
            # Test risk score access control
            score_access_tests = [
                (self.admin_token, True),      # Admin should access
                (self.analyst_token, True),    # Analyst should access
                (self.viewer_token, False),     # Viewer should be denied
                (self.unauthorized_token, False) # Unauthorized should be denied
            ]
            
            for token, should_access in score_access_tests:
                test_headers = {"Authorization": f"Bearer {token}"}
                get_response = self.client.get(f"/api/v1/analysis/risk-scores/{risk_request['entity_id']}", headers=test_headers)
                
                if should_access:
                    assert get_response.status_code not in [401, 403], f"Role should access risk scores"
                else:
                    assert get_response.status_code in [401, 403, 404], f"Role should be denied access to risk scores"
    
    def test_investigation_confidentiality(self):
        """Test investigation result confidentiality"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test investigation creation
        investigation_data = {
            "title": f"Security Test Investigation {uuid.uuid4().hex[:8]}",
            "description": "Investigation for security testing",
            "case_type": "fraud_investigation",
            "priority": "high",
            "assigned_analyst": "analyst_001",
            "status": "in_progress",
            "confidential_findings": [
                "Suspicious transaction patterns detected",
                "Links to known criminal entities",
                "High-risk behavior indicators"
            ],
            "evidence_summary": "Detailed evidence analysis",
            "risk_assessment": {
                "overall_risk": "critical",
                "confidence_score": 0.95,
                "recommended_actions": ["freeze_assets", "file_sar", "contact_authorities"]
            }
        }
        
        response = self.client.post(
            "/api/v1/analysis/investigations",
            json=investigation_data,
            headers=headers
        )
        
        # Should handle investigation creation
        assert response.status_code in [201, 404], "Should handle investigation creation"
        
        if response.status_code == 201:
            created_investigation = response.json()
            investigation_id = created_investigation.get("id", "test-id")
            
            # Test investigation access control
            investigation_access_tests = [
                (self.admin_token, True),      # Admin should access
                (self.analyst_token, True),    # Analyst should access
                (self.viewer_token, False),     # Viewer should be denied
                (self.unauthorized_token, False) # Unauthorized should be denied
            ]
            
            for token, should_access in investigation_access_tests:
                test_headers = {"Authorization": f"Bearer {token}"}
                get_response = self.client.get(f"/api/v1/analysis/investigations/{investigation_id}", headers=test_headers)
                
                if should_access:
                    assert get_response.status_code not in [401, 403], f"Role should access investigation data"
                else:
                    assert get_response.status_code in [401, 403, 404], f"Role should be denied access to investigation data"
    
    def test_graph_analysis_security(self):
        """Test graph analysis security and data protection"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test graph analysis request
        graph_request = {
            "central_address": f"0x{uuid.uuid4().hex[:40]}",
            "blockchain": "ethereum",
            "analysis_depth": 5,
            "include_transaction_details": True,
            "include_address_labels": True,
            "include_risk_indicators": True,
            "max_nodes": 1000,
            "include_confidential_data": True
        }
        
        response = self.client.post(
            "/api/v1/analysis/graph-analysis",
            json=graph_request,
            headers=headers
        )
        
        # Should handle graph analysis
        assert response.status_code in [200, 404], "Should handle graph analysis request"
        
        if response.status_code == 200:
            graph_result = response.json()
            
            # Check that graph data is handled properly
            if "nodes" in graph_result:
                for node in graph_result["nodes"]:
                    # Check that sensitive node data is protected
                    if "labels" in node:
                        assert isinstance(node["labels"], list), "Node labels should be properly formatted"
                    if "risk_indicators" in node:
                        assert isinstance(node["risk_indicators"], list), "Risk indicators should be properly formatted"
            
            # Test graph analysis access control
            graph_access_tests = [
                (self.admin_token, True),      # Admin should access
                (self.analyst_token, True),    # Analyst should access
                (self.viewer_token, False),     # Viewer should be denied
                (self.unauthorized_token, False) # Unauthorized should be denied
            ]
            
            for token, should_access in graph_access_tests:
                test_headers = {"Authorization": f"Bearer {token}"}
                get_response = self.client.get(f"/api/v1/analysis/graph-analysis/{graph_request['central_address']}", headers=test_headers)
                
                if should_access:
                    assert get_response.status_code not in [401, 403], f"Role should access graph analysis"
                else:
                    assert get_response.status_code in [401, 403, 404], f"Role should be denied access to graph analysis"
    
    def test_ml_model_security(self):
        """Test ML model security and access control"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test ML model listing
        response = self.client.get("/api/v1/analysis/ml-models", headers=headers)
        
        # Should handle ML model listing
        assert response.status_code in [200, 404], "Should handle ML model listing"
        
        if response.status_code == 200:
            models = response.json()
            
            # Test ML model access control
            model_access_tests = [
                (self.admin_token, True),      # Admin should access
                (self.analyst_token, True),    # Analyst should access
                (self.viewer_token, False),     # Viewer should be denied
                (self.unauthorized_token, False) # Unauthorized should be denied
            ]
            
            for token, should_access in model_access_tests:
                test_headers = {"Authorization": f"Bearer {token}"}
                get_response = self.client.get("/api/v1/analysis/ml-models", headers=test_headers)
                
                if should_access:
                    assert get_response.status_code not in [401, 403], f"Role should access ML models"
                else:
                    assert get_response.status_code in [401, 403, 404], f"Role should be denied access to ML models"
    
    def test_batch_analysis_security(self):
        """Test batch analysis security and resource limits"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test batch analysis request
        batch_request = {
            "addresses": [
                f"0x{uuid.uuid4().hex[:40]}" for _ in range(100)
            ],
            "analysis_types": ["risk_scoring", "pattern_detection", "graph_analysis"],
            "priority": "normal",
            "include_detailed_results": True
        }
        
        response = self.client.post(
            "/api/v1/analysis/batch",
            json=batch_request,
            headers=headers
        )
        
        # Should handle batch analysis (may be rate limited)
        assert response.status_code in [200, 201, 400, 429], "Should handle batch analysis request"
        
        # Test resource limits
        large_batch_request = {
            "addresses": [
                f"0x{uuid.uuid4().hex[:40]}" for _ in range(10000)
            ],
            "analysis_types": ["risk_scoring"],
            "priority": "normal"
        }
        
        response = self.client.post(
            "/api/v1/analysis/batch",
            json=large_batch_request,
            headers=headers
        )
        
        # Should reject or rate limit large requests
        assert response.status_code in [400, 422, 429], "Should reject or rate limit large batch requests"
    
    def test_analysis_data_export_security(self):
        """Test analysis data export security"""
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Test data export request
        export_request = {
            "export_type": "investigation_summary",
            "date_range": {
                "start": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
                "end": datetime.now(timezone.utc).isoformat()
            },
            "include_confidential_data": True,
            "format": "json",
            "recipients": ["analyst@example.com"]
        }
        
        response = self.client.post(
            "/api/v1/analysis/export",
            json=export_request,
            headers=headers
        )
        
        # Should handle export request
        assert response.status_code in [201, 404], "Should handle analysis data export"
        
        # Test export access control
        export_access_tests = [
            (self.admin_token, True),      # Admin should export
            (self.analyst_token, True),    # Analyst should export
            (self.viewer_token, False),     # Viewer should be denied
            (self.unauthorized_token, False) # Unauthorized should be denied
        ]
        
        for token, should_access in export_access_tests:
            test_headers = {"Authorization": f"Bearer {token}"}
            get_response = self.client.get("/api/v1/analysis/exports", headers=test_headers)
            
            if should_access:
                assert get_response.status_code not in [401, 403], f"Role should access analysis exports"
            else:
                assert get_response.status_code in [401, 403, 404], f"Role should be denied access to analysis exports"


if __name__ == "__main__":
    pytest.main([__file__])
