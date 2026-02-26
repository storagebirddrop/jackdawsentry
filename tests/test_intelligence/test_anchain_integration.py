"""
Unit tests for AnChain.ai integration module.

All HTTP calls are mocked — no live API key required.
"""

import json
from datetime import datetime
from datetime import timezone
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from src.intelligence.anchain_integration import AnChainIntegration
from src.intelligence.anchain_integration import AnChainScreeningResult
from src.intelligence.anchain_integration import _risk_level_from_score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_session(response_data: dict, status: int = 200):
    """Return a context-manager mock that yields an aiohttp-like response."""
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=response_data)
    resp.text = AsyncMock(return_value=json.dumps(response_data))

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _patched_session(response_data: dict, status: int = 200):
    """Patch aiohttp.ClientSession.post to return mock response."""
    session_mock = MagicMock()
    session_mock.post = MagicMock(return_value=_mock_session(response_data, status))
    session_mock.close = AsyncMock()
    return session_mock


# ---------------------------------------------------------------------------
# _risk_level_from_score
# ---------------------------------------------------------------------------

def test_risk_level_from_score_none():
    assert _risk_level_from_score(None) == "unknown"


@pytest.mark.parametrize(
    "score, expected",
    [
        (0.0, "low"),
        (39.9, "low"),
        (40.0, "medium"),
        (59.9, "medium"),
        (60.0, "high"),
        (79.9, "high"),
        (80.0, "critical"),
        (100.0, "critical"),
    ],
)
def test_risk_level_from_score_ranges(score, expected):
    assert _risk_level_from_score(score) == expected


# ---------------------------------------------------------------------------
# screen_address
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_screen_address_success():
    payload = {
        "riskScore": 25.0,
        "labels": ["exchange"],
        "categories": ["defi"],
        "sanctionsMatch": False,
    }

    with patch("src.intelligence.anchain_integration.get_redis_connection") as mock_redis, \
         patch("aiohttp.ClientSession") as mock_cls:

        # Redis returns no cache hit
        mock_redis_ctx = AsyncMock()
        mock_redis_ctx.__aenter__ = AsyncMock(return_value=AsyncMock(get=AsyncMock(return_value=None), setex=AsyncMock()))
        mock_redis_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_redis.return_value = mock_redis_ctx

        mock_cls.return_value = _patched_session(payload)

        async with AnChainIntegration(api_key="test-key") as client:
            result = await client.screen_address("0xABC", "ethereum")

    assert isinstance(result, AnChainScreeningResult)
    assert result.risk_score == 25.0
    assert result.risk_level == "low"
    assert result.labels == ["exchange"]
    assert result.sanctions_match is False
    assert result.error is None


@pytest.mark.asyncio
async def test_screen_address_api_error():
    with patch("src.intelligence.anchain_integration.get_redis_connection") as mock_redis, \
         patch("aiohttp.ClientSession") as mock_cls:

        mock_redis_ctx = AsyncMock()
        mock_redis_ctx.__aenter__ = AsyncMock(return_value=AsyncMock(get=AsyncMock(return_value=None), setex=AsyncMock()))
        mock_redis_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_redis.return_value = mock_redis_ctx

        mock_cls.return_value = _patched_session({"error": "unauthorized"}, status=401)

        async with AnChainIntegration(api_key="bad-key") as client:
            result = await client.screen_address("0xABC", "ethereum")

    assert result.risk_level == "unknown"
    assert result.error is not None


# ---------------------------------------------------------------------------
# screen_sanctions — match found
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_screen_sanctions_match():
    payload = {
        "match": True,
        "matchedLists": ["OFAC-SDN", "EU-CONSOLIDATED"],
    }

    with patch("src.intelligence.anchain_integration.get_redis_connection") as mock_redis, \
         patch("aiohttp.ClientSession") as mock_cls:

        mock_redis_ctx = AsyncMock()
        mock_redis_ctx.__aenter__ = AsyncMock(return_value=AsyncMock(get=AsyncMock(return_value=None), setex=AsyncMock()))
        mock_redis_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_redis.return_value = mock_redis_ctx

        mock_cls.return_value = _patched_session(payload)

        async with AnChainIntegration(api_key="test-key") as client:
            result = await client.screen_sanctions("0xSANCTIONED", "ethereum")

    assert result.sanctions_match is True
    assert result.risk_level == "critical"
    assert "OFAC-SDN" in result.labels


# ---------------------------------------------------------------------------
# screen_sanctions — no match
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_screen_sanctions_no_match():
    payload = {"match": False, "matchedLists": []}

    with patch("src.intelligence.anchain_integration.get_redis_connection") as mock_redis, \
         patch("aiohttp.ClientSession") as mock_cls:

        mock_redis_ctx = AsyncMock()
        mock_redis_ctx.__aenter__ = AsyncMock(return_value=AsyncMock(get=AsyncMock(return_value=None), setex=AsyncMock()))
        mock_redis_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_redis.return_value = mock_redis_ctx

        mock_cls.return_value = _patched_session(payload)

        async with AnChainIntegration(api_key="test-key") as client:
            result = await client.screen_sanctions("0xCLEAN", "ethereum")

    assert result.sanctions_match is False
    assert result.risk_level == "low"


# ---------------------------------------------------------------------------
# screen_ip
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_screen_ip_high_risk():
    payload = {
        "riskScore": 72.0,
        "labels": ["tor-exit-node"],
        "categories": ["anonymizer"],
    }

    with patch("src.intelligence.anchain_integration.get_redis_connection") as mock_redis, \
         patch("aiohttp.ClientSession") as mock_cls:

        mock_redis_ctx = AsyncMock()
        mock_redis_ctx.__aenter__ = AsyncMock(return_value=AsyncMock(get=AsyncMock(return_value=None), setex=AsyncMock()))
        mock_redis_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_redis.return_value = mock_redis_ctx

        mock_cls.return_value = _patched_session(payload)

        async with AnChainIntegration(api_key="test-key") as client:
            result = await client.screen_ip("1.2.3.4")

    assert result.risk_score == 72.0
    assert result.risk_level == "high"
    assert result.subject_type == "ip"
    assert "tor-exit-node" in result.labels


# ---------------------------------------------------------------------------
# Cache hit path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_screen_address_cache_hit():
    cached_payload = {
        "subject": "0xCACHED",
        "subject_type": "address",
        "risk_score": 10.0,
        "risk_level": "low",
        "labels": [],
        "categories": [],
        "sanctions_match": False,
        "raw_data": {},
        "source": "anchain_ai",
        "timestamp": datetime.now(timezone.utc),
        "error": None,
    }

    with patch("src.intelligence.anchain_integration.get_redis_connection") as mock_redis, \
         patch("aiohttp.ClientSession") as mock_cls:

        mock_redis_ctx = AsyncMock()
        mock_redis_ctx.__aenter__ = AsyncMock(
            return_value=AsyncMock(
                get=AsyncMock(return_value=json.dumps(cached_payload, default=str)),
                setex=AsyncMock(),
            )
        )
        mock_redis_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_redis.return_value = mock_redis_ctx

        # Ensure session.close() is awaitable
        mock_session = MagicMock()
        mock_session.post = MagicMock()
        mock_session.close = AsyncMock()
        mock_cls.return_value = mock_session

        async with AnChainIntegration(api_key="test-key") as client:
            result = await client.screen_address("0xCACHED", "ethereum")

        # HTTP session must never have been used
        mock_session.post.assert_not_called()

    assert result.risk_score == 10.0
