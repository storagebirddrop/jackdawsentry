"""
Intelligence Features Testing
Tests intelligence gathering, threat detection, and attribution capabilities
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import json
from datetime import datetime, timezone


class TestIntelligenceFeatures:
    """Test intelligence features across all capabilities"""

    def test_intelligence_query_address(self, client, auth_headers):
        """Test intelligence query for address analysis"""
        response = client.post("/api/v1/intelligence/query", json={
            "query_type": "address",
            "query_value": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "sources": ["all"],
            "time_range_days": 30
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "success" in data
        assert "intelligence_data" in data
        assert "metadata" in data
        assert data["success"] is True
        
        # Check nested data structure
        intelligence_data = data["intelligence_data"]
        assert "query_type" in intelligence_data
        assert "query_value" in intelligence_data
        assert "results" in intelligence_data or "intel_mentions" in intelligence_data

    def test_intelligence_query_entity(self, client, auth_headers):
        """Test intelligence query for entity analysis"""
        response = client.post("/api/v1/intelligence/query", json={
            "query_type": "entity",
            "query_value": "mixing_service",
            "sources": ["all"],  # Use valid source
            "time_range_days": 60
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "success" in data
        assert "intelligence_data" in data
        assert data["success"] is True
        
        # Check query details
        intelligence_data = data["intelligence_data"]
        assert intelligence_data["query_type"] == "entity"
        assert intelligence_data["query_value"] == "mixing_service"

    def test_intelligence_query_pattern(self, client, auth_headers):
        """Test intelligence query for pattern detection"""
        response = client.post("/api/v1/intelligence/query", json={
            "query_type": "pattern",
            "query_value": "peeling_chain",
            "sources": ["all"],
            "time_range_days": 30
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "success" in data
        assert "intelligence_data" in data
        assert data["success"] is True
        
        intelligence_data = data["intelligence_data"]
        assert intelligence_data["query_type"] == "pattern"

    def test_intelligence_query_threat(self, client, auth_headers):
        """Test intelligence query for threat intelligence"""
        response = client.post("/api/v1/intelligence/query", json={
            "query_type": "threat",
            "query_value": "ransomware",
            "sources": ["all"],  # Use valid source
            "time_range_days": 90
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "success" in data
        assert "intelligence_data" in data
        assert data["success"] is True
        
        intelligence_data = data["intelligence_data"]
        assert intelligence_data["query_type"] == "threat"

    def test_create_threat_alert(self, client, auth_headers):
        """Test creating a threat alert"""
        response = client.post("/api/v1/intelligence/alerts", json={
            "title": "Suspicious Activity Detected",
            "description": "Unusual transaction patterns detected",
            "severity": "high",
            "threat_type": "money_laundering",
            "indicators": [
                {
                    "type": "address",
                    "value": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                    "blockchain": "bitcoin"
                },
                {
                    "type": "entity",
                    "value": "mixing_service",
                    "confidence": 0.9
                }
            ],
            "confidence": 0.85
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "success" in data
        assert "intelligence_data" in data
        assert data["success"] is True
        
        # Check alert data
        alert_data = data["intelligence_data"]
        assert "alert_id" in alert_data
        assert alert_data["title"] == "Suspicious Activity Detected"
        assert alert_data["severity"] == "high"

    def test_list_threat_alerts(self, client, auth_headers):
        """Test listing threat alerts"""
        response = client.get("/api/v1/intelligence/alerts", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "success" in data
        assert "intelligence_data" in data
        assert data["success"] is True
        
        # Check alerts list
        alerts_data = data["intelligence_data"]
        assert "alerts" in alerts_data
        assert isinstance(alerts_data["alerts"], list)

    def test_list_threat_alerts_with_filters(self, client, auth_headers):
        """Test listing threat alerts with filters"""
        response = client.get(
            "/api/v1/intelligence/alerts?severity=high&status=active", 
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "success" in data
        assert "data" in data
        assert data["success"] is True

    def test_create_intelligence_subscription(self, client, auth_headers):
        """Test creating intelligence subscription"""
        response = client.post("/api/v1/intelligence/subscriptions", json={
            "subscription_type": "address_monitoring",
            "target": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "filters": {
                "min_risk_score": 0.7,
                "threat_types": ["money_laundering", "terrorism"],
                "sources": ["all"]
            },
            "notification_channels": ["email", "webhook"]
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "success" in data
        assert "intelligence_data" in data
        assert data["success"] is True
        
        # Check subscription data
        subscription_data = data["intelligence_data"]
        assert "subscription_id" in subscription_data
        assert subscription_data["subscription_type"] == "address_monitoring"

    def test_get_dark_web_monitoring_status(self, client, auth_headers):
        """Test getting dark web monitoring status"""
        response = client.get("/api/v1/intelligence/dark-web/monitoring", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "success" in data
        assert "monitoring_status" in data
        assert data["success"] is True
        
        # Check monitoring status
        monitoring_data = data["monitoring_status"]
        assert "monitoring_active" in monitoring_data
        assert "monitored_platforms" in monitoring_data
        assert "statistics" in monitoring_data

    def test_get_intelligence_sources(self, client, auth_headers):
        """Test getting intelligence sources"""
        response = client.get("/api/v1/intelligence/sources", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "success" in data
        assert "sources" in data
        assert data["success"] is True
        
        # Check sources data
        sources_data = data["sources"]
        assert isinstance(sources_data, list)

    def test_get_intelligence_statistics(self, client, auth_headers):
        """Test getting intelligence statistics"""
        response = client.get("/api/v1/intelligence/statistics", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "success" in data
        assert "statistics" in data
        assert data["success"] is True
        
        # Check statistics data
        stats_data = data["statistics"]
        assert "active_alerts" in stats_data
        assert "active_subscriptions" in stats_data
        assert "monitored_sources" in stats_data
