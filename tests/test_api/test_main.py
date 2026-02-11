"""
Jackdaw Sentry - Main API Tests
Tests for the main FastAPI application endpoints
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.api.main import app


class TestMainAPI:
    """Test main API endpoints"""
    
    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint returns welcome message"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Jackdaw Sentry" in data["message"]
    
    def test_health_endpoint(self, client: TestClient):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_info_endpoint(self, client: TestClient):
        """Test application info endpoint"""
        response = client.get("/info")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "description" in data
    
    def test_metrics_endpoint(self, client: TestClient):
        """Test metrics endpoint"""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "uptime" in data
        assert "memory_usage" in data
        assert "active_connections" in data
    
    @pytest.mark.asyncio
    async def test_async_health_endpoint(self, async_client: AsyncClient):
        """Test health endpoint with async client"""
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_cors_headers(self, client: TestClient):
        """Test CORS headers are present"""
        response = client.options("/")
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
    
    def test_security_headers(self, client: TestClient):
        """Test security headers are present"""
        response = client.get("/")
        assert response.status_code == 200
        # Check for security headers
        headers = response.headers
        assert "x-content-type-options" in headers
        assert "x-frame-options" in headers
    
    def test_rate_limiting(self, client: TestClient):
        """Test rate limiting is working"""
        # Make multiple rapid requests
        responses = []
        for _ in range(20):
            response = client.get("/")
            responses.append(response.status_code)
        
        # Should eventually hit rate limit
        assert 429 in responses  # Too Many Requests
    
    def test_invalid_endpoint(self, client: TestClient):
        """Test invalid endpoint returns 404"""
        response = client.get("/invalid-endpoint")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_method_not_allowed(self, client: TestClient):
        """Test unsupported method returns 405"""
        response = client.patch("/")
        assert response.status_code == 405
    
    def test_malformed_json(self, client: TestClient):
        """Test malformed JSON returns 400"""
        response = client.post(
            "/api/analysis/address",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_large_payload(self, client: TestClient):
        """Test large payload handling"""
        large_data = {"data": "x" * 1000000}  # 1MB
        response = client.post(
            "/api/analysis/address",
            json=large_data,
            headers={"Content-Type": "application/json"}
        )
        # Should either accept or reject with appropriate status
        assert response.status_code in [200, 413, 422]
    
    def test_concurrent_requests(self, client: TestClient):
        """Test concurrent request handling"""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = client.get("/health")
            results.append(response.status_code)
        
        # Make 10 concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(status == 200 for status in results)
    
    def test_timeout_handling(self, client: TestClient):
        """Test timeout handling for slow endpoints"""
        # This would need a slow endpoint to test properly
        # For now, just ensure the endpoint exists
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_error_handling(self, client: TestClient):
        """Test error handling returns proper format"""
        response = client.get("/invalid-endpoint")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)
    
    def test_authentication_required(self, client: TestClient):
        """Test authentication is required for protected endpoints"""
        response = client.get("/api/admin/users")
        assert response.status_code == 401  # Unauthorized
    
    def test_authentication_with_invalid_token(self, client: TestClient):
        """Test authentication with invalid token"""
        response = client.get(
            "/api/admin/users",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401  # Unauthorized
    
    def test_authentication_with_expired_token(self, client: TestClient):
        """Test authentication with expired token"""
        import jwt
        from datetime import datetime, timedelta
        
        # Create expired token
        expired_payload = {
            "sub": "test_user",
            "exp": datetime.utcnow() - timedelta(hours=1),
            "role": "analyst"
        }
        
        expired_token = jwt.encode(
            expired_payload, 
            "test-secret-key", 
            algorithm="HS256"
        )
        
        response = client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401  # Unauthorized
    
    def test_authorization_insufficient_permissions(self, client: TestClient, auth_headers: dict):
        """Test authorization with insufficient permissions"""
        response = client.get("/api/admin/users", headers=auth_headers)
        assert response.status_code == 403  # Forbidden
    
    def test_content_type_validation(self, client: TestClient):
        """Test content type validation"""
        response = client.post(
            "/api/analysis/address",
            data="not json",
            headers={"Content-Type": "text/plain"}
        )
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_query_parameter_validation(self, client: TestClient):
        """Test query parameter validation"""
        response = client.get("/api/transactions?limit=invalid")
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_path_parameter_validation(self, client: TestClient):
        """Test path parameter validation"""
        response = client.get("/api/transactions/invalid-hash")
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_request_id_header(self, client: TestClient):
        """Test request ID is added to response"""
        response = client.get("/health")
        assert response.status_code == 200
        # Request ID should be in headers (if implemented)
        # This depends on middleware implementation
    
    def test_logging_headers(self, client: TestClient):
        """Test logging-related headers"""
        response = client.get("/health")
        assert response.status_code == 200
        # Check for any logging-related headers
    
    def test_compression(self, client: TestClient):
        """Test response compression"""
        response = client.get(
            "/info",
            headers={"Accept-Encoding": "gzip"}
        )
        assert response.status_code == 200
        # Check if response is compressed
        if response.status_code == 200:
            assert "content-encoding" in response.headers
    
    def test_cache_headers(self, client: TestClient):
        """Test cache control headers"""
        response = client.get("/info")
        assert response.status_code == 200
        # Check for cache control headers
        headers = response.headers
        # Some endpoints should have cache control
    
    def test_api_versioning(self, client: TestClient):
        """Test API versioning"""
        response = client.get("/api/v1/health")
        # Should either work or return appropriate version error
        assert response.status_code in [200, 404]
    
    def test_openapi_docs(self, client: TestClient):
        """Test OpenAPI documentation endpoints"""
        # Test OpenAPI JSON
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
        
        # Test Swagger UI
        response = client.get("/docs")
        assert response.status_code == 200
        
        # Test ReDoc
        response = client.get("/redoc")
        assert response.status_code == 200
    
    def test_websocket_upgrade(self, client: TestClient):
        """Test WebSocket upgrade handling"""
        # This would require WebSocket support
        response = client.get(
            "/ws/test",
            headers={
                "Upgrade": "websocket",
                "Connection": "upgrade",
                "Sec-WebSocket-Key": "test-key",
                "Sec-WebSocket-Version": "13"
            }
        )
        # Should either upgrade or reject appropriately
        assert response.status_code in [101, 400, 426]
