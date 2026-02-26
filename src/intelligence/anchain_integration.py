"""
Jackdaw Sentry - AnChain.ai Integration
REST API integration for AnChain.ai blockchain intelligence and AML screening.

Provides three capability groups:
  - Address/transaction risk scoring (anchain-data-mcp Intelligence API)
  - Sanctions and crypto screening (aml-mcp Sanctions API)
  - IP address risk screening (aml-mcp IP API)

AnChain.ai covers 14+ chains including niche ones (Stellar, Algorand, Zcash, Dash,
BSV) not covered by other integrated providers, and uniquely offers IP risk screening.
"""

import json
import logging
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Dict
from typing import Optional

import aiohttp

from src.api.config import settings
from src.api.database import get_redis_connection

logger = logging.getLogger(__name__)

# Cache TTL matches existing MCP pattern (5 minutes)
_CACHE_TTL = 300
# Free-tier rate limit
_RATE_LIMIT_PER_HOUR = 500

# AnChain.ai API base URLs
_INTELLIGENCE_BASE_URL = "https://api.anchainai.com/v1"
_AML_BASE_URL = "https://aml.anchainai.com/v1"


@dataclass
class AnChainScreeningResult:
    """Normalised result from any AnChain.ai screening call."""

    subject: str  # address, tx hash, entity name, or IP
    subject_type: str  # "address" | "transaction" | "entity" | "ip"
    risk_score: Optional[float]  # 0–100; None if not returned
    risk_level: str  # "low" | "medium" | "high" | "critical" | "unknown"
    labels: list = field(default_factory=list)
    categories: list = field(default_factory=list)
    sanctions_match: bool = False
    raw_data: Dict[str, Any] = field(default_factory=dict)
    source: str = "anchain_ai"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None


def _risk_level_from_score(score: Optional[float]) -> str:
    """Convert numeric 0–100 score to a risk label."""
    if score is None:
        return "unknown"
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


class AnChainIntegration:
    """AnChain.ai REST API integration for risk screening and AML compliance.

    Supports:
    - Address risk scoring and attribution (14+ chains)
    - Transaction risk scoring
    - Crypto address sanctions screening
    - Entity/individual sanctions screening
    - IP address risk screening
    - Multi-hop transaction tracing

    Authentication uses the ``X-API-Key`` header. Obtain a free development
    key at https://aml.anchainai.com.

    Results are cached in Redis for ``_CACHE_TTL`` seconds.
    """

    def __init__(self, api_key: str = None):
        """Initialise the integration.

        Args:
            api_key: AnChain.ai API key. Falls back to ``settings.ANCHAIN_API_KEY``.
        """
        self.api_key = api_key or getattr(settings, "ANCHAIN_API_KEY", None)
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
            self._session = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        """Build common request headers."""
        return {
            "X-API-Key": self.api_key or "",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _get_cached(self, cache_key: str) -> Optional[Any]:
        """Return cached value from Redis, or None on miss/error."""
        try:
            async with get_redis_connection() as redis:
                cached = await redis.get(cache_key)
                if cached:
                    return json.loads(cached)
        except Exception as exc:
            logger.debug("AnChain cache read error: %s", exc)
        return None

    async def _set_cached(self, cache_key: str, value: Any) -> None:
        """Store value in Redis with the standard TTL."""
        try:
            async with get_redis_connection() as redis:
                await redis.setex(cache_key, _CACHE_TTL, json.dumps(value, default=str))
        except Exception as exc:
            logger.debug("AnChain cache write error: %s", exc)

    async def _post(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST to AnChain API; raises on non-200 status."""
        if self._session is None:
            raise RuntimeError("AnChainIntegration must be used as an async context manager")
        async with self._session.post(url, headers=self._headers(), json=payload) as resp:
            if resp.status == 200:
                return await resp.json()
            error_body = await resp.text()
            raise Exception(f"AnChain API HTTP {resp.status}: {error_body}")

    # ------------------------------------------------------------------
    # Public screening methods
    # ------------------------------------------------------------------

    async def screen_address(
        self, address: str, blockchain: str
    ) -> AnChainScreeningResult:
        """Screen a crypto address for risk score and attribution labels.

        Args:
            address: On-chain address to screen.
            blockchain: Chain identifier (e.g. ``"ethereum"``, ``"bitcoin"``).

        Returns:
            AnChainScreeningResult with risk score and entity labels.
        """
        cache_key = f"anchain:address:{blockchain}:{address}"
        cached = await self._get_cached(cache_key)
        if cached:
            return AnChainScreeningResult(**cached)

        try:
            data = await self._post(
                f"{_INTELLIGENCE_BASE_URL}/address/risk",
                {"address": address, "blockchain": blockchain},
            )
            score = data.get("riskScore") or data.get("risk_score")
            result = AnChainScreeningResult(
                subject=address,
                subject_type="address",
                risk_score=score,
                risk_level=_risk_level_from_score(score),
                labels=data.get("labels", []),
                categories=data.get("categories", []),
                sanctions_match=bool(data.get("sanctionsMatch") or data.get("sanctions_match")),
                raw_data=data,
            )
        except Exception as exc:
            logger.error("AnChain address screening failed for %s: %s", address, exc)
            result = AnChainScreeningResult(
                subject=address,
                subject_type="address",
                risk_score=None,
                risk_level="unknown",
                error=str(exc),
            )

        await self._set_cached(cache_key, result.__dict__)
        return result

    async def screen_transaction(
        self, tx_hash: str, blockchain: str
    ) -> AnChainScreeningResult:
        """Screen a transaction hash for risk indicators.

        Args:
            tx_hash: Transaction hash to analyse.
            blockchain: Chain identifier.

        Returns:
            AnChainScreeningResult with risk score and suspicious activity flags.
        """
        cache_key = f"anchain:tx:{blockchain}:{tx_hash}"
        cached = await self._get_cached(cache_key)
        if cached:
            return AnChainScreeningResult(**cached)

        try:
            data = await self._post(
                f"{_INTELLIGENCE_BASE_URL}/transaction/risk",
                {"txHash": tx_hash, "blockchain": blockchain},
            )
            score = data.get("riskScore") or data.get("risk_score")
            result = AnChainScreeningResult(
                subject=tx_hash,
                subject_type="transaction",
                risk_score=score,
                risk_level=_risk_level_from_score(score),
                labels=data.get("labels", []),
                categories=data.get("categories", []),
                raw_data=data,
            )
        except Exception as exc:
            logger.error("AnChain transaction screening failed for %s: %s", tx_hash, exc)
            result = AnChainScreeningResult(
                subject=tx_hash,
                subject_type="transaction",
                risk_score=None,
                risk_level="unknown",
                error=str(exc),
            )

        await self._set_cached(cache_key, result.__dict__)
        return result

    async def screen_sanctions(
        self, address: str, blockchain: str
    ) -> AnChainScreeningResult:
        """Screen a crypto address against sanctions lists (OFAC, UN, EU, etc.).

        Args:
            address: Crypto address to check.
            blockchain: Chain identifier.

        Returns:
            AnChainScreeningResult indicating whether a sanctions match was found.
        """
        cache_key = f"anchain:sanctions:{blockchain}:{address}"
        cached = await self._get_cached(cache_key)
        if cached:
            return AnChainScreeningResult(**cached)

        try:
            data = await self._post(
                f"{_AML_BASE_URL}/crypto/screen",
                {"address": address, "blockchain": blockchain},
            )
            is_match = bool(data.get("match") or data.get("sanctionsMatch"))
            result = AnChainScreeningResult(
                subject=address,
                subject_type="address",
                risk_score=100.0 if is_match else 0.0,
                risk_level="critical" if is_match else "low",
                sanctions_match=is_match,
                labels=data.get("matchedLists", []),
                categories=["sanctions"] if is_match else [],
                raw_data=data,
            )
        except Exception as exc:
            logger.error("AnChain sanctions screening failed for %s: %s", address, exc)
            result = AnChainScreeningResult(
                subject=address,
                subject_type="address",
                risk_score=None,
                risk_level="unknown",
                error=str(exc),
            )

        await self._set_cached(cache_key, result.__dict__)
        return result

    async def screen_entity(
        self,
        name: str,
        id_number: Optional[str] = None,
        country: Optional[str] = None,
        entity_type: str = "individual",
    ) -> AnChainScreeningResult:
        """Screen an individual or company against global sanctions/PEP lists.

        Args:
            name: Full name of the individual or organisation.
            id_number: National ID, passport, or company registration number (optional).
            country: ISO 3166-1 alpha-2 country code (optional).
            entity_type: ``"individual"`` or ``"organization"``.

        Returns:
            AnChainScreeningResult with sanctions match status and matched lists.
        """
        cache_key = f"anchain:entity:{entity_type}:{name}:{id_number}:{country}"
        cached = await self._get_cached(cache_key)
        if cached:
            return AnChainScreeningResult(**cached)

        payload: Dict[str, Any] = {"name": name, "entityType": entity_type}
        if id_number:
            payload["idNumber"] = id_number
        if country:
            payload["country"] = country

        try:
            data = await self._post(f"{_AML_BASE_URL}/sanctions/screen", payload)
            is_match = bool(data.get("match") or data.get("sanctionsMatch"))
            result = AnChainScreeningResult(
                subject=name,
                subject_type="entity",
                risk_score=100.0 if is_match else 0.0,
                risk_level="critical" if is_match else "low",
                sanctions_match=is_match,
                labels=data.get("matchedLists", []),
                categories=["sanctions"] if is_match else [],
                raw_data=data,
            )
        except Exception as exc:
            logger.error("AnChain entity screening failed for %s: %s", name, exc)
            result = AnChainScreeningResult(
                subject=name,
                subject_type="entity",
                risk_score=None,
                risk_level="unknown",
                error=str(exc),
            )

        await self._set_cached(cache_key, result.__dict__)
        return result

    async def screen_ip(self, ip_address: str) -> AnChainScreeningResult:
        """Screen an IP address for geographic and threat-actor risk.

        This is a unique capability not offered by any other integrated provider.

        Args:
            ip_address: IPv4 or IPv6 address to screen.

        Returns:
            AnChainScreeningResult with risk score and geo/threat labels.
        """
        cache_key = f"anchain:ip:{ip_address}"
        cached = await self._get_cached(cache_key)
        if cached:
            return AnChainScreeningResult(**cached)

        try:
            data = await self._post(
                f"{_AML_BASE_URL}/ip/screen",
                {"ipAddress": ip_address},
            )
            score = data.get("riskScore") or data.get("risk_score")
            result = AnChainScreeningResult(
                subject=ip_address,
                subject_type="ip",
                risk_score=score,
                risk_level=_risk_level_from_score(score),
                labels=data.get("labels", []),
                categories=data.get("categories", []),
                raw_data=data,
            )
        except Exception as exc:
            logger.error("AnChain IP screening failed for %s: %s", ip_address, exc)
            result = AnChainScreeningResult(
                subject=ip_address,
                subject_type="ip",
                risk_score=None,
                risk_level="unknown",
                error=str(exc),
            )

        await self._set_cached(cache_key, result.__dict__)
        return result

    async def trace_transaction(
        self, tx_hash: str, blockchain: str, max_hops: int = 5
    ) -> Dict[str, Any]:
        """Trace a transaction through multiple hops to identify fund flows.

        Args:
            tx_hash: Starting transaction hash.
            blockchain: Chain identifier.
            max_hops: Maximum tracing depth (default 5).

        Returns:
            Raw AnChain tracing result dict with hop graph and risk annotations.
        """
        cache_key = f"anchain:trace:{blockchain}:{tx_hash}:{max_hops}"
        cached = await self._get_cached(cache_key)
        if cached:
            return cached

        try:
            data = await self._post(
                f"{_INTELLIGENCE_BASE_URL}/transaction/trace",
                {"txHash": tx_hash, "blockchain": blockchain, "maxHops": max_hops},
            )
        except Exception as exc:
            logger.error("AnChain transaction trace failed for %s: %s", tx_hash, exc)
            data = {
                "txHash": tx_hash,
                "error": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "anchain_ai",
            }

        await self._set_cached(cache_key, data)
        return data
