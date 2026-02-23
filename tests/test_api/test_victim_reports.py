"""
Jackdaw Sentry - Victim Reports API Unit Tests
Tests for victim reports API endpoints
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
import json

from fastapi.testclient import TestClient
from src.api.main import app


class TestVictimReportsAPI:
    """Test suite for Victim Reports API endpoints"""

    @pytest.fixture
    def client(self):
        """Create FastAPI TestClient"""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, make_token):
        """Create authentication headers"""
        token = make_token(
            sub="analyst",
            permissions=["intelligence:read", "intelligence:write", "intelligence:create", "intelligence:update", "intelligence:delete", "intelligence:verify"]
        )
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def admin_headers(self, make_token):
        """Create admin authentication headers"""
        from src.api.auth import ROLES
        token = make_token(sub="admin", permissions=ROLES["admin"])
        return {"Authorization": f"Bearer {token}"}

    # ---- POST /api/v1/intelligence/victim-reports/ ----

    @pytest.mark.api
    @pytest.mark.asyncio
    def test_create_victim_report_success(self, client, auth_headers):
        """Test successful victim report creation"""
        with patch("src.intelligence.victim_reports.get_victim_reports_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Mock report creation
            mock_report = MagicMock()
            mock_report.id = str(uuid4())
            mock_report.report_type = "scam"
            mock_report.victim_contact = "victim@example.com"
            mock_report.incident_date = datetime.now(timezone.utc)
            mock_report.amount_lost = 1000.0
            mock_report.currency = "BTC"
            mock_report.description = "Bitcoin investment scam"
            mock_report.related_addresses = ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"]
            mock_report.severity = "high"
            mock_report.status = "pending"
            mock_report.created_date = datetime.now(timezone.utc)
            mock_report.last_updated = datetime.now(timezone.utc)
            
            mock_db.create_report.return_value = mock_report
            
            report_data = {
                "report_type": "scam",
                "victim_contact": "victim@example.com",
                "incident_date": datetime.now(timezone.utc).isoformat(),
                "amount_lost": 1000.0,
                "currency": "BTC",
                "description": "Bitcoin investment scam",
                "related_addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
                "severity": "high"
            }
            
            response = client.post(
                "/api/v1/intelligence/victim-reports/",
                json=report_data,
                headers=auth_headers
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["report_type"] == "scam"
            assert data["victim_contact"] == "victim@example.com"
            assert data["amount_lost"] == 1000.0
            assert data["severity"] == "high"
            assert data["status"] == "pending"

    @pytest.mark.api
    def test_create_victim_report_unauthorized(self, client):
        """Test victim report creation without authentication"""
        report_data = {
            "report_type": "scam",
            "victim_contact": "victim@example.com",
            "description": "Test report"
        }
        
        response = client.post(
            "/api/v1/intelligence/victim-reports/",
            json=report_data
        )
        
        assert response.status_code == 401

    @pytest.mark.api
    def test_create_victim_report_invalid_data(self, client, auth_headers):
        """Test victim report creation with invalid data"""
        invalid_data = {
            "report_type": "invalid_type",  # Invalid enum value
            "victim_contact": "",  # Empty required field
            "description": "Test report"
        }
        
        response = client.post(
            "/api/v1/intelligence/victim-reports/",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422

    # ---- GET /api/v1/intelligence/victim-reports/ ----

    @pytest.mark.api
    @pytest.mark.asyncio
    def test_list_victim_reports_success(self, client, auth_headers):
        """Test successful victim reports listing"""
        with patch("src.intelligence.victim_reports.get_victim_reports_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Mock reports list
            mock_reports = [
                MagicMock(
                    id=str(uuid4()),
                    report_type="scam",
                    victim_contact="victim1@example.com",
                    status="pending",
                    severity="high",
                    created_date=datetime.now(timezone.utc),
                    last_updated=datetime.now(timezone.utc)
                ),
                MagicMock(
                    id=str(uuid4()),
                    report_type="fraud",
                    victim_contact="victim2@example.com",
                    status="verified",
                    severity="medium",
                    created_date=datetime.now(timezone.utc),
                    last_updated=datetime.now(timezone.utc)
                )
            ]
            
            mock_db.get_reports.return_value = mock_reports
            
            response = client.get(
                "/api/v1/intelligence/victim-reports/",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["report_type"] == "scam"
            assert data[1]["report_type"] == "fraud"

    @pytest.mark.api
    @pytest.mark.asyncio
    def test_list_victim_reports_with_filters(self, client, auth_headers):
        """Test victim reports listing with filters"""
        with patch("src.intelligence.victim_reports.get_victim_reports_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Mock filtered reports
            mock_reports = [
                MagicMock(
                    id=str(uuid4()),
                    report_type="scam",
                    victim_contact="victim@example.com",
                    status="verified",
                    severity="high",
                    created_date=datetime.now(timezone.utc),
                    last_updated=datetime.now(timezone.utc)
                )
            ]
            
            mock_db.get_reports.return_value = mock_reports
            
            response = client.get(
                "/api/v1/intelligence/victim-reports/?status=verified&report_type=scam&severity=high",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["status"] == "verified"
            assert data[0]["report_type"] == "scam"
            assert data[0]["severity"] == "high"

    @pytest.mark.api
    def test_list_victim_reports_invalid_filter(self, client, auth_headers):
        """Test victim reports listing with invalid filter"""
        response = client.get(
            "/api/v1/intelligence/victim-reports/?status=invalid_status",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]

    # ---- GET /api/v1/intelligence/victim-reports/{report_id} ----

    @pytest.mark.api
    @pytest.mark.asyncio
    def test_get_victim_report_success(self, client, auth_headers):
        """Test successful victim report retrieval"""
        with patch("src.intelligence.victim_reports.get_victim_reports_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            report_id = str(uuid4())
            
            # Mock report
            mock_report = MagicMock(
                id=report_id,
                report_type="fraud",
                victim_contact="victim@example.com",
                incident_date=datetime.now(timezone.utc),
                amount_lost=5000.0,
                currency="ETH",
                description="Ethereum fraud case",
                related_addresses=["0x742d35Cc6634C0532925a3b844Bc454e4438f44e"],
                severity="medium",
                status="investigating",
                verified_by=None,
                verification_date=None,
                notes="Under investigation",
                created_date=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc)
            )
            
            mock_db.get_report.return_value = mock_report
            
            response = client.get(
                f"/api/v1/intelligence/victim-reports/{report_id}",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == report_id
            assert data["report_type"] == "fraud"
            assert data["victim_contact"] == "victim@example.com"
            assert data["amount_lost"] == 5000.0
            assert data["status"] == "investigating"

    @pytest.mark.api
    @pytest.mark.asyncio
    def test_get_victim_report_not_found(self, client, auth_headers):
        """Test victim report retrieval when report doesn't exist"""
        with patch("src.intelligence.victim_reports.get_victim_reports_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            mock_db.get_report.return_value = None
            
            response = client.get(
                "/api/v1/intelligence/victim-reports/nonexistent_id",
                headers=auth_headers
            )
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]

    # ---- PUT /api/v1/intelligence/victim-reports/{report_id} ----

    @pytest.mark.api
    @pytest.mark.asyncio
    def test_update_victim_report_success(self, client, auth_headers):
        """Test successful victim report update"""
        with patch("src.intelligence.victim_reports.get_victim_reports_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            report_id = str(uuid4())
            
            # Mock existing report
            mock_db.get_report.return_value = MagicMock(id=report_id)
            
            # Mock updated report
            mock_updated_report = MagicMock(
                id=report_id,
                report_type="scam",
                victim_contact="victim@example.com",
                status="verified",
                severity="high",
                notes="Investigation completed",
                last_updated=datetime.now(timezone.utc)
            )
            
            mock_db.update_report.return_value = mock_updated_report
            
            update_data = {
                "status": "verified",
                "severity": "high",
                "notes": "Investigation completed"
            }
            
            response = client.put(
                f"/api/v1/intelligence/victim-reports/{report_id}",
                json=update_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == report_id
            assert data["status"] == "verified"
            assert data["severity"] == "high"
            assert data["notes"] == "Investigation completed"

    @pytest.mark.api
    @pytest.mark.asyncio
    def test_update_victim_report_not_found(self, client, auth_headers):
        """Test victim report update when report doesn't exist"""
        with patch("src.intelligence.victim_reports.get_victim_reports_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            mock_db.get_report.return_value = None
            
            update_data = {"status": "verified"}
            
            response = client.put(
                "/api/v1/intelligence/victim-reports/nonexistent_id",
                json=update_data,
                headers=auth_headers
            )
            
            assert response.status_code == 404

    # ---- DELETE /api/v1/intelligence/victim-reports/{report_id} ----

    @pytest.mark.api
    @pytest.mark.asyncio
    def test_delete_victim_report_success(self, client, auth_headers):
        """Test successful victim report deletion"""
        with patch("src.intelligence.victim_reports.get_victim_reports_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            report_id = str(uuid4())
            
            # Mock existing report
            mock_db.get_report.return_value = MagicMock(id=report_id)
            
            response = client.delete(
                f"/api/v1/intelligence/victim-reports/{report_id}",
                headers=auth_headers
            )
            
            assert response.status_code == 204

    @pytest.mark.api
    @pytest.mark.asyncio
    def test_delete_victim_report_not_found(self, client, auth_headers):
        """Test victim report deletion when report doesn't exist"""
        with patch("src.intelligence.victim_reports.get_victim_reports_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            mock_db.get_report.return_value = None
            
            response = client.delete(
                "/api/v1/intelligence/victim-reports/nonexistent_id",
                headers=auth_headers
            )
            
            assert response.status_code == 404

    # ---- POST /api/v1/intelligence/victim-reports/{report_id}/verify ----

    @pytest.mark.api
    @pytest.mark.asyncio
    def test_verify_victim_report_success(self, client, auth_headers):
        """Test successful victim report verification"""
        with patch("src.intelligence.victim_reports.get_victim_reports_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            report_id = str(uuid4())
            
            # Mock existing report
            mock_db.get_report.return_value = MagicMock(id=report_id)
            
            # Mock verified report
            mock_verified_report = MagicMock(
                id=report_id,
                status="verified",
                verified_by="analyst_123",
                verification_date=datetime.now(timezone.utc),
                notes="Evidence verified",
                last_updated=datetime.now(timezone.utc)
            )
            
            mock_db.update_report.return_value = mock_verified_report
            
            verification_data = {
                "status": "verified",
                "notes": "Evidence verified"
            }
            
            response = client.post(
                f"/api/v1/intelligence/victim-reports/{report_id}/verify",
                json=verification_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == report_id
            assert data["status"] == "verified"
            assert data["verified_by"] == "analyst_123"
            assert data["notes"] == "Evidence verified"

    @pytest.mark.api
    @pytest.mark.asyncio
    def test_verify_victim_report_invalid_status(self, client, auth_headers):
        """Test victim report verification with invalid status"""
        verification_data = {
            "status": "invalid_status",  # Invalid enum value
            "notes": "Test verification"
        }
        
        response = client.post(
            "/api/v1/intelligence/victim-reports/report_id/verify",
            json=verification_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422

    # ---- GET /api/v1/intelligence/victim-reports/statistics/overview ----

    @pytest.mark.api
    @pytest.mark.asyncio
    def test_get_report_statistics_success(self, client, auth_headers):
        """Test successful report statistics retrieval"""
        with patch("src.intelligence.victim_reports.get_victim_reports_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Mock statistics
            mock_stats = MagicMock(
                total_reports=100,
                reports_by_status={"pending": 30, "verified": 50, "false_positive": 20},
                reports_by_type={"scam": 40, "fraud": 30, "theft": 20, "phishing": 10},
                reports_by_severity={"low": 20, "medium": 40, "high": 30, "critical": 10},
                reports_by_timeframe={"last_24h": 5, "last_7d": 25, "last_30d": 70},
                total_amount_lost=50000.0,
                average_amount_lost=500.0,
                verification_rate=0.8
            )
            
            mock_db.get_statistics.return_value = mock_stats
            
            response = client.get(
                "/api/v1/intelligence/victim-reports/statistics/overview",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_reports"] == 100
            assert data["total_amount_lost"] == 50000.0
            assert data["average_amount_lost"] == 500.0
            assert data["verification_rate"] == 0.8

    # ---- GET /api/v1/intelligence/victim-reports/search/addresses ----

    @pytest.mark.api
    @pytest.mark.asyncio
    def test_search_reports_by_address_success(self, client, auth_headers):
        """Test successful search by address"""
        with patch("src.intelligence.victim_reports.get_victim_reports_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
            
            # Mock search results
            mock_reports = [
                MagicMock(
                    id=str(uuid4()),
                    report_type="scam",
                    victim_contact="victim1@example.com",
                    related_addresses=[address],
                    status="verified",
                    created_date=datetime.now(timezone.utc),
                    last_updated=datetime.now(timezone.utc)
                ),
                MagicMock(
                    id=str(uuid4()),
                    report_type="fraud",
                    victim_contact="victim2@example.com",
                    related_addresses=[address],
                    status="investigating",
                    created_date=datetime.now(timezone.utc),
                    last_updated=datetime.now(timezone.utc)
                )
            ]
            
            mock_db.search_by_address.return_value = mock_reports
            
            response = client.get(
                f"/api/v1/intelligence/victim-reports/search/addresses?address={address}",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            for report in data:
                assert address in report["related_addresses"]

    # ---- GET /api/v1/intelligence/victim-reports/search/transactions ----

    @pytest.mark.api
    @pytest.mark.asyncio
    def test_search_reports_by_transaction_success(self, client, auth_headers):
        """Test successful search by transaction hash"""
        with patch("src.intelligence.victim_reports.get_victim_reports_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            tx_hash = "a1b2c3d4e5f6789012345678901234567890abcdef"
            
            # Mock search results
            mock_reports = [
                MagicMock(
                    id=str(uuid4()),
                    report_type="theft",
                    victim_contact="victim@example.com",
                    related_transactions=[tx_hash],
                    status="verified",
                    created_date=datetime.now(timezone.utc),
                    last_updated=datetime.now(timezone.utc)
                )
            ]
            
            mock_db.search_by_transaction.return_value = mock_reports
            
            response = client.get(
                f"/api/v1/intelligence/victim-reports/search/transactions?transaction_hash={tx_hash}",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert tx_hash in data[0]["related_transactions"]

    # ---- Permission Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    def test_read_permission_required(self, client):
        """Test that read permission is required for GET endpoints"""
        # Create token without intelligence:read permission
        token = make_token(
            sub="user",
            permissions=["other:permission"]
        )
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get(
            "/api/v1/intelligence/victim-reports/",
            headers=headers
        )
        
        assert response.status_code == 403

    @pytest.mark.api
    @pytest.mark.asyncio
    def test_write_permission_required(self, client):
        """Test that write permission is required for POST endpoints"""
        # Create token without intelligence:create permission
        token = make_token(
            sub="user",
            permissions=["intelligence:read"]
        )
        headers = {"Authorization": f"Bearer {token}"}
        
        report_data = {
            "report_type": "scam",
            "victim_contact": "victim@example.com",
            "description": "Test report"
        }
        
        response = client.post(
            "/api/v1/intelligence/victim-reports/",
            json=report_data,
            headers=headers
        )
        
        assert response.status_code == 403

    @pytest.mark.api
    @pytest.mark.asyncio
    def test_verify_permission_required(self, client):
        """Test that verify permission is required for verification endpoint"""
        # Create token without intelligence:verify permission
        token = make_token(
            sub="user",
            permissions=["intelligence:read", "intelligence:write"]
        )
        headers = {"Authorization": f"Bearer {token}"}
        
        verification_data = {
            "status": "verified",
            "notes": "Test verification"
        }
        
        response = client.post(
            "/api/v1/intelligence/victim-reports/report_id/verify",
            json=verification_data,
            headers=headers
        )
        
        assert response.status_code == 403

    # ---- Error Handling Tests ----

    @pytest.mark.api
    @pytest.mark.asyncio
    def test_database_error_handling(self, client, auth_headers):
        """Test handling of database errors"""
        with patch("src.intelligence.victim_reports.get_victim_reports_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            mock_db.create_report.side_effect = Exception("Database connection failed")
            
            report_data = {
                "report_type": "scam",
                "victim_contact": "victim@example.com",
                "description": "Test report"
            }
            
            response = client.post(
                "/api/v1/intelligence/victim-reports/",
                json=report_data,
                headers=auth_headers
            )
            
            assert response.status_code == 500
            assert "Failed to create victim report" in response.json()["message"]

    @pytest.mark.api
    @pytest.mark.asyncio
    def test_service_initialization_error(self, client, auth_headers):
        """Test handling of service initialization errors"""
        with patch("src.intelligence.victim_reports.get_victim_reports_db", side_effect=Exception("Service unavailable")):
            
            response = client.get(
                "/api/v1/intelligence/victim-reports/",
                headers=auth_headers
            )
            
            assert response.status_code == 500

    # ---- Input Validation Tests ----

    @pytest.mark.api
    def test_invalid_date_format(self, client, auth_headers):
        """Test handling of invalid date format"""
        report_data = {
            "report_type": "scam",
            "victim_contact": "victim@example.com",
            "incident_date": "invalid_date_format",  # Invalid date
            "description": "Test report"
        }
        
        response = client.post(
            "/api/v1/intelligence/victim-reports/",
            json=report_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422

    @pytest.mark.api
    def test_invalid_amount_type(self, client, auth_headers):
        """Test handling of invalid amount type"""
        report_data = {
            "report_type": "scam",
            "victim_contact": "victim@example.com",
            "amount_lost": "invalid_amount",  # Should be number
            "description": "Test report"
        }
        
        response = client.post(
            "/api/v1/intelligence/victim-reports/",
            json=report_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422

    @pytest.mark.api
    def test_invalid_severity_value(self, client, auth_headers):
        """Test handling of invalid severity value"""
        report_data = {
            "report_type": "scam",
            "victim_contact": "victim@example.com",
            "severity": "invalid_severity",  # Invalid enum value
            "description": "Test report"
        }
        
        response = client.post(
            "/api/v1/intelligence/victim-reports/",
            json=report_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422


# Helper function for creating test tokens
def make_token(sub, permissions):
    """Create a JWT token for testing"""
    import jwt as pyjwt
    from datetime import datetime, timedelta, timezone
    
    payload = {
        "sub": sub,
        "permissions": permissions,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    
    return pyjwt.encode(payload, "test-secret-key", algorithm="HS256")
