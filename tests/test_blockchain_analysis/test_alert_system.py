"""
Alert System Testing
Tests real-time alert creation, delivery, and management functionality
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import json
import asyncio
from datetime import datetime, timezone, timedelta


class TestAlertSystem:
    """Test alert system functionality"""

    @pytest.mark.parametrize("alert_type,severity,test_data", [
        ("high_risk_address", "high", {"address": "bc1q...suspicious", "risk_score": 0.9}),
        ("pattern_detection", "medium", {"pattern": "peeling_chain", "confidence": 0.8}),
        ("transaction_threshold", "high", {"amount": 1000000, "currency": "BTC"}),
        ("bridge_activity", "critical", {"bridge": "wormhole", "volume": 500000}),
        ("mixing_detected", "high", {"mixer": "tornado_cash", "addresses": ["0x...mix"]}),
    ])
    def test_alert_creation_basic(self, client, alert_type, severity, test_data):
        """Test basic alert creation"""
        response = client.post("/api/v1/alerts/create", json={
            "alert_type": alert_type,
            "severity": severity,
            "data": test_data,
            "source": "automated_analysis"
        })
        
        assert response.status_code == 201
        data = response.json()
        
        # Basic response structure
        assert "alert_id" in data
        assert "alert_type" in data
        assert "severity" in data
        assert "status" in data
        assert "created_at" in data
        assert "data" in data
        
        # Verify alert details
        assert data["alert_type"] == alert_type
        assert data["severity"] == severity
        assert data["status"] == "active"
        assert data["source"] == "automated_analysis"
        assert data["alert_id"] is not None

    def test_alert_with_conditions(self, client):
        """Test alert creation with conditions"""
        response = client.post("/api/v1/alerts/create", json={
            "alert_type": "conditional_risk",
            "severity": "medium",
            "conditions": {
                "risk_score_threshold": 0.7,
                "transaction_count_min": 10,
                "time_window_hours": 24
            },
            "data": {
                "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                "current_risk_score": 0.8,
                "transaction_count": 15
            }
        })
        
        assert response.status_code == 201
        data = response.json()
        
        # Should have conditions
        assert "conditions" in data
        assert data["conditions"]["risk_score_threshold"] == 0.7
        assert data["conditions"]["transaction_count_min"] == 10

    def test_alert_with_metadata(self, client):
        """Test alert creation with metadata"""
        response = client.post("/api/v1/alerts/create", json={
            "alert_type": "entity_attribution",
            "severity": "low",
            "data": {"entity": "exchange", "confidence": 0.6},
            "metadata": {
                "investigation_id": "inv_123456",
                "analyst": "john_doe",
                "tags": ["exchange", "monitoring"],
                "priority": "medium"
            }
        })
        
        assert response.status_code == 201
        data = response.json()
        
        # Should have metadata
        assert "metadata" in data
        metadata = data["metadata"]
        assert metadata["investigation_id"] == "inv_123456"
        assert metadata["analyst"] == "john_doe"
        assert "exchange" in metadata["tags"]
        assert "monitoring" in metadata["tags"]

    def test_alert_list_retrieval(self, client):
        """Test alert list retrieval"""
        response = client.get("/api/v1/alerts/list", params={
            "limit": 10,
            "offset": 0,
            "severity": "all",
            "status": "active"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic response structure
        assert "alerts" in data
        assert "pagination" in data
        assert "total_count" in data
        
        # Validate pagination
        pagination = data["pagination"]
        assert "limit" in pagination
        assert "offset" in pagination
        assert "total_pages" in pagination
        
        # Validate alerts
        assert isinstance(data["alerts"], list)
        if data["alerts"]:
            alert = data["alerts"][0]
            assert "alert_id" in alert
            assert "alert_type" in alert
            assert "severity" in alert
            assert "status" in alert

    def test_alert_filtering(self, client):
        """Test alert filtering"""
        # Test filtering by severity
        response = client.get("/api/v1/alerts/list", params={
            "severity": "high",
            "status": "active",
            "limit": 5
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # All alerts should be high severity
        for alert in data["alerts"]:
            assert alert["severity"] == "high"
        
        # Test filtering by status
        response = client.get("/api/v1/alerts/list", params={
            "status": "resolved",
            "limit": 5
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # All alerts should be resolved
        for alert in data["alerts"]:
            assert alert["status"] == "resolved"

    def test_alert_details_retrieval(self, client):
        """Test alert details retrieval"""
        # First create an alert
        create_response = client.post("/api/v1/alerts/create", json={
            "alert_type": "test_alert",
            "severity": "medium",
            "data": {"test": "data"}
        })
        
        assert create_response.status_code == 201
        alert_id = create_response.json()["alert_id"]
        
        # Retrieve alert details
        response = client.get(f"/api/v1/alerts/{alert_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have full alert details
        assert "alert_id" in data
        assert "alert_type" in data
        assert "severity" in data
        assert "status" in data
        assert "data" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "history" in data

    def test_alert_update(self, client):
        """Test alert update"""
        # Create an alert
        create_response = client.post("/api/v1/alerts/create", json={
            "alert_type": "test_alert",
            "severity": "medium",
            "data": {"test": "data"}
        })
        
        alert_id = create_response.json()["alert_id"]
        
        # Update alert
        response = client.patch(f"/api/v1/alerts/{alert_id}", json={
            "status": "acknowledged",
            "assigned_to": "analyst_001",
            "notes": "Alert acknowledged, investigating further"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have updated fields
        assert data["status"] == "acknowledged"
        assert data["assigned_to"] == "analyst_001"
        assert "investigating further" in data["notes"]

    def test_alert_resolution(self, client):
        """Test alert resolution"""
        # Create an alert
        create_response = client.post("/api/v1/alerts/create", json={
            "alert_type": "test_alert",
            "severity": "low",
            "data": {"test": "data"}
        })
        
        alert_id = create_response.json()["alert_id"]
        
        # Resolve alert
        response = client.patch(f"/api/v1/alerts/{alert_id}/resolve", json={
            "resolution": "false_positive",
            "resolution_notes": "Investigation showed no suspicious activity",
            "resolved_by": "analyst_001"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be resolved
        assert data["status"] == "resolved"
        assert data["resolution"] == "false_positive"
        assert "no suspicious activity" in data["resolution_notes"]
        assert data["resolved_by"] == "analyst_001"

    def test_alert_escalation(self, client):
        """Test alert escalation"""
        # Create an alert
        create_response = client.post("/api/v1/alerts/create", json={
            "alert_type": "critical_pattern",
            "severity": "critical",
            "data": {"pattern": "mixing", "confidence": 0.95}
        })
        
        alert_id = create_response.json()["alert_id"]
        
        # Escalate alert
        response = client.post(f"/api/v1/alerts/{alert_id}/escalate", json={
            "escalation_level": "high",
            "escalation_reason": "Critical pattern detected with high confidence",
            "escalate_to": "security_team"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be escalated
        assert data["escalation_level"] == "high"
        assert data["escalate_to"] == "security_team"
        assert "Critical pattern detected" in data["escalation_reason"]

    @patch('src.monitoring.alert_rules.create_rule')
    def test_alert_rule_creation(self, mock_create_rule, client):
        """Test alert rule creation"""
        mock_create_rule.return_value = {"rule_id": "rule_123", "status": "active"}
        
        response = client.post("/api/v1/alerts/rules", json={
            "name": "High Risk Address Alert",
            "description": "Alert when address risk score exceeds threshold",
            "conditions": {
                "risk_score_threshold": 0.8,
                "blockchain": "bitcoin"
            },
            "actions": {
                "notification_channels": ["email", "slack"],
                "escalation_threshold": 0.9
            },
            "enabled": True
        })
        
        assert response.status_code == 201
        data = response.json()
        
        # Should have rule details
        assert "rule_id" in data
        assert "name" in data
        assert "conditions" in data
        assert "actions" in data
        assert data["name"] == "High Risk Address Alert"

    def test_alert_statistics(self, client):
        """Test alert statistics and metrics"""
        response = client.get("/api/v1/alerts/statistics", params={
            "timeframe": "7d",
            "group_by": "severity"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have statistics
        assert "total_alerts" in data
        assert "alert_counts" in data
        assert "resolution_rates" in data
        assert "response_times" in data
        
        # Validate alert counts
        counts = data["alert_counts"]
        assert "critical" in counts
        assert "high" in counts
        assert "medium" in counts
        assert "low" in counts

    @pytest.mark.asyncio
    async def test_websocket_alert_streaming(self, client):
        """Test WebSocket alert streaming"""
        # This would require WebSocket testing setup
        # For now, test the WebSocket endpoint creation
        response = client.get("/api/v1/alerts/ws")
        
        # Should accept WebSocket upgrade request
        assert response.status_code in [101, 400]  # 101 for WebSocket, 400 for non-WebSocket

    def test_alert_bulk_operations(self, client):
        """Test bulk alert operations"""
        # Create multiple alerts
        alert_ids = []
        for i in range(5):
            response = client.post("/api/v1/alerts/create", json={
                "alert_type": f"bulk_test_{i}",
                "severity": "medium",
                "data": {"index": i}
            })
            alert_ids.append(response.json()["alert_id"])
        
        # Bulk acknowledge
        response = client.post("/api/v1/alerts/bulk-acknowledge", json={
            "alert_ids": alert_ids,
            "acknowledged_by": "bulk_analyst",
            "notes": "Bulk acknowledgment for testing"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have bulk operation results
        assert "updated_count" in data
        assert "failed_count" in data
        assert "results" in data
        assert data["updated_count"] == len(alert_ids)

    def test_alert_search(self, client):
        """Test alert search functionality"""
        response = client.get("/api/v1/alerts/search", params={
            "query": "risk",
            "search_fields": ["alert_type", "data", "notes"],
            "time_range": "7d",
            "limit": 10
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have search results
        assert "alerts" in data
        assert "search_metadata" in data
        assert "total_matches" in data
        
        # Validate search metadata
        metadata = data["search_metadata"]
        assert metadata["query"] == "risk"
        assert "alert_type" in metadata["search_fields"]

    def test_alert_export(self, client):
        """Test alert export functionality"""
        response = client.post("/api/v1/alerts/export", json={
            "format": "csv",
            "filters": {
                "severity": ["high", "critical"],
                "status": "active",
                "time_range": "30d"
            },
            "fields": ["alert_id", "alert_type", "severity", "created_at", "data"]
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have export information
        assert "export_id" in data
        assert "format" in data
        assert "download_url" in data
        assert data["format"] == "csv"

    @pytest.mark.integration
    def test_alert_with_real_analysis_data(self, client):
        """Test alert creation with real analysis data (integration test)"""
        response = client.post("/api/v1/alerts/create", json={
            "alert_type": "pattern_detection",
            "severity": "high",
            "data": {
                "address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
                "pattern": "mixing",
                "confidence": 0.92,
                "evidence": [
                    {
                        "type": "mixing_service",
                        "service": "Tornado Cash",
                        "transaction_hash": "0x...mix_tx"
                    }
                ]
            },
            "source": "automated_analysis"
        })
        
        assert response.status_code == 201
        data = response.json()
        
        # Should have real analysis data
        assert "data" in data
        assert data["data"]["address"] == "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
        assert data["data"]["pattern"] == "mixing"
        assert data["data"]["confidence"] == 0.92


class TestAlertDelivery:
    """Test alert delivery mechanisms"""

    def test_email_notification(self, client):
        """Test email notification delivery"""
        response = client.post("/api/v1/alerts/notify/email", json={
            "alert_id": "alert_123456",
            "recipients": ["analyst@example.com", "security@example.com"],
            "subject": "High Risk Alert: Suspicious Pattern Detected",
            "template": "high_risk_alert",
            "data": {
                "alert_type": "pattern_detection",
                "severity": "high",
                "address": "bc1q...suspicious",
                "risk_score": 0.85
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have notification result
        assert "notification_id" in data
        assert "delivery_status" in data
        assert "recipients" in data
        assert data["delivery_status"] in ["sent", "queued", "failed"]

    def test_slack_notification(self, client):
        """Test Slack notification delivery"""
        response = client.post("/api/v1/alerts/notify/slack", json={
            "alert_id": "alert_123456",
            "channel": "#security-alerts",
            "message": "🚨 High Risk Alert Detected",
            "alert_data": {
                "alert_type": "pattern_detection",
                "severity": "high",
                "address": "bc1q...suspicious"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have Slack notification result
        assert "message_id" in data
        assert "channel" in data
        assert "timestamp" in data
        assert data["channel"] == "#security-alerts"

    def test_webhook_notification(self, client):
        """Test webhook notification delivery"""
        response = client.post("/api/v1/alerts/notify/webhook", json={
            "alert_id": "alert_123456",
            "webhook_url": "https://api.example.com/alerts/webhook",
            "method": "POST",
            "headers": {
                "Authorization": "Bearer token123",
                "Content-Type": "application/json"
            },
            "payload": {
                "alert_id": "alert_123456",
                "alert_type": "pattern_detection",
                "severity": "high",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have webhook result
        assert "webhook_id" in data
        assert "response_status" in data
        assert "delivery_attempts" in data

    def test_sms_notification(self, client):
        """Test SMS notification delivery"""
        response = client.post("/api/v1/alerts/notify/sms", json={
            "alert_id": "alert_123456",
            "phone_numbers": ["+1234567890", "+0987654321"],
            "message": "Critical alert: Suspicious activity detected",
            "alert_data": {
                "severity": "critical",
                "address": "bc1q...critical"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have SMS notification result
        assert "message_id" in data
        assert "recipients" in data
        assert "delivery_status" in data

    def test_notification_preferences(self, client):
        """Test notification preferences management"""
        response = client.post("/api/v1/alerts/notification-preferences", json={
            "user_id": "analyst_001",
            "preferences": {
                "email": {
                    "enabled": True,
                    "threshold": "medium",
                    "quiet_hours": {
                        "start": "22:00",
                        "end": "08:00"
                    }
                },
                "slack": {
                    "enabled": True,
                    "threshold": "high",
                    "channels": ["#alerts", "#security"]
                },
                "sms": {
                    "enabled": False,
                    "threshold": "critical"
                }
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have preferences
        assert "user_id" in data
        assert "preferences" in data
        assert data["preferences"]["email"]["enabled"] is True
        assert data["preferences"]["sms"]["enabled"] is False

    def test_notification_digest(self, client):
        """Test daily/weekly notification digest"""
        response = client.post("/api/v1/alerts/digest", json={
            "digest_type": "daily",
            "recipients": ["manager@example.com"],
            "time_range": "24h",
            "include_alerts": ["high", "critical"],
            "format": "html"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have digest result
        assert "digest_id" in data
        assert "digest_type" in data
        assert "alert_count" in data
        assert "delivery_status" in data
        assert data["digest_type"] == "daily"


class TestAlertRules:
    """Test alert rule management"""

    def test_create_alert_rule(self, client):
        """Test alert rule creation"""
        response = client.post("/api/v1/alerts/rules", json={
            "name": "Bitcoin Mixer Detection",
            "description": "Detect when Bitcoin addresses interact with known mixers",
            "conditions": {
                "blockchain": "bitcoin",
                "mixer_interaction": True,
                "confidence_threshold": 0.8
            },
            "actions": {
                "create_alert": True,
                "severity": "high",
                "notifications": ["email", "slack"]
            },
            "schedule": {
                "enabled": True,
                "frequency": "real_time"
            }
        })
        
        assert response.status_code == 201
        data = response.json()
        
        # Should have rule details
        assert "rule_id" in data
        assert "name" in data
        assert "conditions" in data
        assert "actions" in data
        assert data["name"] == "Bitcoin Mixer Detection"

    def test_list_alert_rules(self, client):
        """Test alert rule listing"""
        response = client.get("/api/v1/alerts/rules", params={
            "enabled_only": False,
            "limit": 10
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have rules list
        assert "rules" in data
        assert "total_count" in data
        assert isinstance(data["rules"], list)

    def test_update_alert_rule(self, client):
        """Test alert rule update"""
        # Create a rule first
        create_response = client.post("/api/v1/alerts/rules", json={
            "name": "Test Rule",
            "conditions": {"risk_threshold": 0.5},
            "actions": {"create_alert": True}
        })
        
        rule_id = create_response.json()["rule_id"]
        
        # Update the rule
        response = client.patch(f"/api/v1/alerts/rules/{rule_id}", json={
            "conditions": {"risk_threshold": 0.7},
            "actions": {"create_alert": True, "severity": "high"},
            "enabled": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have updated fields
        assert data["conditions"]["risk_threshold"] == 0.7
        assert data["actions"]["severity"] == "high"
        assert data["enabled"] is True

    def test_delete_alert_rule(self, client):
        """Test alert rule deletion"""
        # Create a rule first
        create_response = client.post("/api/v1/alerts/rules", json={
            "name": "Delete Test Rule",
            "conditions": {"risk_threshold": 0.5},
            "actions": {"create_alert": True}
        })
        
        rule_id = create_response.json()["rule_id"]
        
        # Delete the rule
        response = client.delete(f"/api/v1/alerts/rules/{rule_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should confirm deletion
        assert "deleted" in data
        assert data["deleted"] is True

    def test_alert_rule_execution(self, client):
        """Test alert rule execution"""
        response = client.post("/api/v1/alerts/rules/execute", json={
            "rule_id": "rule_123456",
            "test_data": {
                "address": "bc1q...test",
                "risk_score": 0.85,
                "blockchain": "bitcoin"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have execution result
        assert "execution_id" in data
        assert "rule_matched" in data
        assert "actions_taken" in data
        assert isinstance(data["actions_taken"], list)


class TestAlertSystemEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_invalid_alert_data(self, client):
        """Test alert creation with invalid data"""
        response = client.post("/api/v1/alerts/create", json={
            "alert_type": "",  # Empty alert type
            "severity": "invalid_severity",  # Invalid severity
            "data": None  # Null data
        })
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data

    def test_nonexistent_alert_retrieval(self, client):
        """Test retrieval of non-existent alert"""
        response = client.get("/api/v1/alerts/nonexistent_alert_id")
        
        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    def test_invalid_alert_update(self, client):
        """Test alert update with invalid data"""
        response = client.patch("/api/v1/alerts/invalid_id", json={
            "status": "invalid_status",
            "assigned_to": ""
        })
        
        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    def test_empty_filter_parameters(self, client):
        """Test alert filtering with empty parameters"""
        response = client.get("/api/v1/alerts/list", params={
            "severity": "",
            "status": "",
            "limit": 0
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_very_large_alert_data(self, client):
        """Test alert creation with very large data"""
        large_data = {"key" + str(i): "value" + str(i) for i in range(1000)}
        
        response = client.post("/api/v1/alerts/create", json={
            "alert_type": "large_data_test",
            "severity": "medium",
            "data": large_data
        })
        
        # Should either succeed or fail gracefully
        assert response.status_code in [201, 400, 413]

    def test_concurrent_alert_creation(self, client):
        """Test concurrent alert creation"""
        import threading
        import time
        
        results = []
        
        def create_alert():
            response = client.post("/api/v1/alerts/create", json={
                "alert_type": "concurrent_test",
                "severity": "medium",
                "data": {"thread": threading.current_thread().ident}
            })
            results.append(response.status_code)
        
        # Start 10 concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_alert)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(status == 201 for status in results)

    def test_alert_with_future_timestamp(self, client):
        """Test alert creation with future timestamp"""
        future_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        
        response = client.post("/api/v1/alerts/create", json={
            "alert_type": "future_test",
            "severity": "low",
            "data": {"test": "data"},
            "metadata": {"scheduled_time": future_time}
        })
        
        # Should handle future timestamps gracefully
        assert response.status_code in [201, 400]

    def test_null_notification_recipients(self, client):
        """Test notification with null recipients"""
        response = client.post("/api/v1/alerts/notify/email", json={
            "alert_id": "alert_123",
            "recipients": None,
            "subject": "Test"
        })
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data


class TestAlertSystemPerformance:
    """Test performance characteristics"""

    def test_alert_creation_performance(self, client):
        """Test alert creation performance"""
        import time
        
        start_time = time.time()
        response = client.post("/api/v1/alerts/create", json={
            "alert_type": "performance_test",
            "severity": "medium",
            "data": {"test": "data"}
        })
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 201
        # Should complete within 100ms
        assert response_time < 0.1

    def test_alert_list_performance(self, client):
        """Test alert list retrieval performance"""
        import time
        
        start_time = time.time()
        response = client.get("/api/v1/alerts/list", params={
            "limit": 100,
            "offset": 0
        })
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 200
        # Should complete within 500ms for 100 alerts
        assert response_time < 0.5

    def test_alert_search_performance(self, client):
        """Test alert search performance"""
        import time
        
        start_time = time.time()
        response = client.get("/api/v1/alerts/search", params={
            "query": "risk",
            "time_range": "30d",
            "limit": 50
        })
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 200
        # Should complete within 1 second for search
        assert response_time < 1.0

    def test_concurrent_alert_operations(self, client):
        """Test concurrent alert operations"""
        import threading
        import time
        
        results = []
        
        def alert_operation():
            # Create alert
            create_response = client.post("/api/v1/alerts/create", json={
                "alert_type": "concurrent_perf_test",
                "severity": "medium",
                "data": {"thread": threading.current_thread().ident}
            })
            
            if create_response.status_code == 201:
                alert_id = create_response.json()["alert_id"]
                # Update alert
                update_response = client.patch(f"/api/v1/alerts/{alert_id}", json={
                    "status": "acknowledged"
                })
                results.append((create_response.status_code, update_response.status_code))
            else:
                results.append((create_response.status_code, None))
        
        # Start 5 concurrent operations
        threads = []
        start_time = time.time()
        
        for _ in range(5):
            thread = threading.Thread(target=alert_operation)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All operations should succeed
        for create_status, update_status in results:
            assert create_status == 201
            assert update_status == 200
        
        # Should complete within reasonable time
        assert total_time < 5.0
