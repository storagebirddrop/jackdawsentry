"""
Tests for the Entity Attribution API Router (M11).
"""

import pytest
from unittest.mock import AsyncMock, patch


class TestEntityLookupEndpoint:
    def test_entity_lookup_requires_auth(self, client):
        resp = client.get("/api/v1/entities/lookup?address=0xtest")
        assert resp.status_code == 401 or resp.status_code == 403

    def test_entity_lookup_success(self, client, auth_headers):
        with patch(
            "src.api.routers.entities.lookup_address",
            new_callable=AsyncMock,
            return_value={
                "entity_name": "Binance",
                "entity_type": "exchange",
                "category": "cex",
                "risk_level": "low",
                "label": "Binance Hot Wallet",
                "confidence": 0.9,
                "source": "etherscan_labels",
                "blockchain": "ethereum",
            },
        ):
            resp = client.get(
                "/api/v1/entities/lookup?address=0xtest&blockchain=ethereum",
                headers=auth_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["found"] is True
        assert data["entity"]["entity_name"] == "Binance"

    def test_entity_lookup_not_found(self, client, auth_headers):
        with patch(
            "src.api.routers.entities.lookup_address",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = client.get(
                "/api/v1/entities/lookup?address=0xunknown",
                headers=auth_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is False
        assert data["entity"] is None


class TestEntityBulkLookup:
    def test_bulk_lookup(self, client, auth_headers):
        with patch(
            "src.api.routers.entities.lookup_addresses_bulk",
            new_callable=AsyncMock,
            return_value={
                "0xaaa": {
                    "entity_name": "Exchange A",
                    "entity_type": "exchange",
                },
            },
        ):
            resp = client.post(
                "/api/v1/entities/lookup",
                headers=auth_headers,
                json={"addresses": ["0xaaa", "0xbbb"]},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["found_count"] == 1
        assert data["total_queried"] == 2


class TestEntitySearch:
    def test_search(self, client, auth_headers):
        with patch(
            "src.api.routers.entities.search_entities",
            new_callable=AsyncMock,
            return_value=[
                {
                    "id": "uuid-1",
                    "name": "Binance",
                    "entity_type": "exchange",
                    "category": "cex",
                    "risk_level": "low",
                    "description": None,
                }
            ],
        ):
            resp = client.get(
                "/api/v1/entities/search?q=Binance",
                headers=auth_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["name"] == "Binance"


class TestEntitySync:
    def test_sync_requires_admin(self, client, auth_headers):
        """Non-admin should be forbidden from triggering sync."""
        resp = client.post("/api/v1/entities/sync", headers=auth_headers)
        assert resp.status_code == 403

    def test_sync_as_admin(self, client, admin_headers):
        with patch(
            "src.api.routers.entities.sync_all_labels",
            new_callable=AsyncMock,
            return_value={"etherscan_labels": {"status": "success", "records": 100}},
        ):
            resp = client.post("/api/v1/entities/sync", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True


class TestSyncStatus:
    def test_sync_status(self, client, auth_headers):
        with (
            patch(
                "src.api.routers.entities.get_sync_status",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "src.api.routers.entities.get_entity_counts",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            resp = client.get(
                "/api/v1/entities/sync/status",
                headers=auth_headers,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
