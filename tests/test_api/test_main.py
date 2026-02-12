"""
Jackdaw Sentry - Smoke & API Tests
Verifies the app imports, starts, and core endpoints respond correctly.
No external services required.
"""

import pytest


# ---------------------------------------------------------------------------
# M5.1  Smoke tests
# ---------------------------------------------------------------------------
class TestSmoke:
    """Bare-minimum checks: app imports and core endpoints respond."""

    @pytest.mark.smoke
    def test_app_imports(self):
        """The FastAPI app object can be imported without error."""
        from src.api.main import app  # noqa: F401

    @pytest.mark.smoke
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    @pytest.mark.smoke
    def test_root_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "Jackdaw Sentry" in data["name"]

    @pytest.mark.smoke
    def test_openapi_json(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema

    @pytest.mark.smoke
    def test_docs_page(self, client):
        response = client.get("/docs")
        assert response.status_code == 200

    @pytest.mark.smoke
    def test_unknown_route_404(self, client):
        response = client.get("/this-does-not-exist")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# M5.2  Contract tests — mounted routes match expectations
# ---------------------------------------------------------------------------
class TestRouteContract:
    """Verify that documented router prefixes are actually mounted."""

    EXPECTED_PREFIXES = [
        "/api/v1/auth",
        "/api/v1/analysis",
        "/api/v1/compliance",
        "/api/v1/compliance/analytics",
        "/api/v1/compliance/export",
        "/api/v1/compliance/workflows",
        "/api/v1/compliance/monitoring",
        "/api/v1/compliance/rate-limit",
        "/api/v1/compliance/visualization",
        "/api/v1/compliance/scheduler",
        "/api/v1/compliance/mobile",
        "/api/v1/investigations",
        "/api/v1/blockchain",
        "/api/v1/intelligence",
        "/api/v1/reports",
        "/api/v1/admin",
    ]

    PROTECTED_PATHS = [
        "/api/v1/analysis/statistics",
        "/api/v1/compliance/statistics",
        "/api/v1/compliance/analytics/dashboard",
        "/api/v1/compliance/export/list",
        "/api/v1/compliance/workflows/list",
        "/api/v1/compliance/monitoring/metrics",
        "/api/v1/compliance/rate-limit/statistics",
        "/api/v1/compliance/visualization/list",
        "/api/v1/compliance/scheduler/tasks",
        "/api/v1/compliance/mobile/dashboard",
        "/api/v1/investigations/list",
        "/api/v1/blockchain/supported",
        "/api/v1/intelligence/sources",
        "/api/v1/reports/list",
        "/api/v1/admin/users",
    ]

    @pytest.fixture(scope="class")
    def openapi_schema(self, client):
        """Fetch the OpenAPI schema once per test class."""
        return client.get("/openapi.json").json()

    @pytest.mark.api
    def test_all_router_prefixes_present_in_openapi(self, openapi_schema):
        """Every expected prefix appears at least once in the OpenAPI paths."""
        paths = list(openapi_schema["paths"].keys())

        for prefix in self.EXPECTED_PREFIXES:
            matching = [p for p in paths if p.startswith(prefix)]
            assert matching, f"No paths found with prefix {prefix}"

    @pytest.mark.api
    def test_auth_login_endpoint_exists(self, openapi_schema):
        """POST /api/v1/auth/login is documented in OpenAPI."""
        assert "/api/v1/auth/login" in openapi_schema["paths"]
        assert "post" in openapi_schema["paths"]["/api/v1/auth/login"]

    @pytest.mark.api
    @pytest.mark.parametrize("path", PROTECTED_PATHS)
    @pytest.mark.parametrize("method", ["get", "post", "put", "delete"])
    def test_protected_endpoints_require_auth(self, client, path, method):
        """Protected endpoints return 401/403 without a token for any method."""
        resp = getattr(client, method)(path)
        assert resp.status_code in (401, 403, 405), (
            f"{method.upper()} {path} returned {resp.status_code}, "
            f"expected 401, 403, or 405"
        )
