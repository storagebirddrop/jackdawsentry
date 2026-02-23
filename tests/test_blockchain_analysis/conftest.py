"""
Jackdaw Sentry - Test Configuration for Blockchain Analysis
Pytest fixtures for unit, smoke, and integration tests.
"""

import os
import pytest
from typing import Generator
from unittest.mock import AsyncMock, patch

# ---------------------------------------------------------------------------
# Environment overrides — must happen before any app imports
# ---------------------------------------------------------------------------
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("API_SECRET_KEY", "test-secret-key-for-testing-only-1234")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-32-chars-long!!")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-for-testing-ok")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "30")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("API_HOST", "0.0.0.0")
os.environ.setdefault("API_PORT", "8000")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("AUDIT_LOG_DIR", "/tmp/jds_test_audit")


# ---------------------------------------------------------------------------
# Fixtures — API client (uses TestClient, no lifespan/DB required)
# ---------------------------------------------------------------------------
@pytest.fixture
def client():
    """Provide a FastAPI TestClient with DB init/shutdown mocked out."""
    from fastapi.testclient import TestClient
    from src.api.main import app
    from src.api.auth import User
    from unittest.mock import MagicMock, AsyncMock
    
    # Create mock Neo4j driver and session
    mock_driver = MagicMock()
    mock_session = AsyncMock()
    
    # Mock the session.run method to return mock result
    mock_result = MagicMock()
    mock_result.single = MagicMock(return_value=None)
    mock_result.data = MagicMock(return_value=[])
    mock_result.__aiter__ = MagicMock(return_value=iter([]))
    mock_session.run = AsyncMock(return_value=mock_result)
    
    # Mock session context manager
    mock_driver.session = MagicMock(return_value=mock_session)
    
    with (
        patch("src.api.main.init_databases", new_callable=AsyncMock),
        patch("src.api.main.close_databases", new_callable=AsyncMock),
        patch("src.api.main.start_background_tasks", new_callable=AsyncMock),
        patch("src.api.main.stop_background_tasks", new_callable=AsyncMock),
        patch("src.monitoring.alert_rules.ensure_tables", new_callable=AsyncMock),
        patch("src.api.auth.check_permissions", return_value=lambda: User(
            id="550e8400-e29b-41d4-a716-446655440000",
            username="test_user",
            email="test@example.com",
            role="analyst",
            is_active=True
        )),
        # Mock Neo4j driver and session
        patch("src.api.database.get_neo4j_driver", return_value=mock_driver),
        patch("src.api.database.get_neo4j_session", return_value=mock_session),
    ):
        with TestClient(app, raise_server_exceptions=False, base_url="http://localhost") as c:
            yield c


# ---------------------------------------------------------------------------
# Auth helper fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def jwt_secret():
    return os.environ["JWT_SECRET_KEY"]


@pytest.fixture
def auth_headers(jwt_secret):
    """Provide authentication headers for testing."""
    import jwt
    from datetime import datetime, timezone, timedelta
    
    token = jwt.encode(
        {
            "sub": "test_user",  # Required field for username
            "user_id": "550e8400-e29b-41d4-a716-446655440000",  # Valid UUID format
            "username": "test_user",  # Explicit username field
            "permissions": ["analysis:read", "analysis:write", "intelligence:read", "intelligence:write", "blockchain:read", "blockchain:write"],  # Add blockchain permissions
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        },
        jwt_secret,
        algorithm="HS256"
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Mock fixtures for blockchain data
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_bitcoin_address():
    """Mock Bitcoin address for testing."""
    return "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"


@pytest.fixture
def mock_ethereum_address():
    """Mock Ethereum address for testing."""
    return "0x742d35Cc6634C0532925a3b8D4E7E0E0e9e0dF3"


@pytest.fixture
def mock_solana_address():
    """Mock Solana address for testing."""
    return "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"


@pytest.fixture
def mock_transaction_data():
    """Mock transaction data for testing."""
    return {
        "hash": "0x1234567890abcdef",
        "from_address": "0x742d35Cc6634C0532925a3b8D4E7E0E0e9e0dF3",
        "to_address": "0x8894E0a0c962CB7185c1888beBB3a4618a7730D6",
        "value": 1000000000000000000,  # 1 ETH in wei
        "gas_used": 21000,
        "gas_price": 20000000000,  # 20 gwei
        "block_number": 12345,
        "timestamp": 1640995200
    }


# ---------------------------------------------------------------------------
# Mock analysis results
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_address_analysis():
    """Mock address analysis result."""
    return {
        "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        "blockchain": "bitcoin",
        "risk_score": 0.3,
        "entity_type": "individual",
        "confidence": 0.8,
        "transaction_count": 150,
        "total_received": 1.5,
        "total_sent": 1.2,
        "first_seen": "2021-01-01T00:00:00Z",
        "last_seen": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def mock_pattern_detection():
    """Mock pattern detection result."""
    return {
        "patterns": [
            {
                "pattern_type": "peeling_chain",
                "confidence": 0.85,
                "transactions": ["tx1", "tx2", "tx3"],
                "evidence": "Multiple small transactions to different addresses"
            }
        ],
        "total_patterns": 1,
        "risk_level": "medium"
    }


# ---------------------------------------------------------------------------
# Performance testing fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def performance_thresholds():
    """Performance thresholds for testing."""
    return {
        "address_analysis": 0.2,  # 200ms
        "transaction_analysis": 0.3,  # 300ms
        "pattern_detection": 0.5,  # 500ms
        "graph_generation": 2.0,  # 2s
        "alert_creation": 0.1  # 100ms
    }
