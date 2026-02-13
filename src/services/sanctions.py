"""
Jackdaw Sentry - Sanctions Screening Service (M9.4)
Ingests OFAC SDN and EU Consolidated sanctions lists, stores sanctioned
crypto addresses in PostgreSQL, and provides screening functions.
"""

import asyncio
import logging
import re
import defusedxml.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import asyncpg

from src.api.config import settings
from src.api.database import get_postgres_pool, get_postgres_connection

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------

# OFAC pre-parsed crypto address list (GitHub mirror, updated daily)
OFAC_GITHUB_URL = (
    "https://raw.githubusercontent.com/0xB10C/"
    "ofac-sanctioned-digital-currency-addresses/lists/sanctioned_addresses_XBT.txt"
)
# OFAC SDN Advanced XML (full list, updated ~daily)
OFAC_SDN_XML_URL = (
    "https://www.treasury.gov/ofac/downloads/sanctions/1.0/sdn_advanced.xml"
)
# EU Consolidated Sanctions XML
EU_SANCTIONS_URL = (
    "https://webgate.ec.europa.eu/fsd/fsf/public/files/"
    "xmlFullSanctionsList_1_1/content"
)

# Chain detection heuristics
_CHAIN_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("bitcoin", re.compile(r"^(1|3|bc1)[a-zA-HJ-NP-Z0-9]{25,62}$")),
    ("ethereum", re.compile(r"^0x[0-9a-fA-F]{40}$")),
    ("tron", re.compile(r"^T[a-zA-HJ-NP-Z0-9]{33}$")),
    ("solana", re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")),
    ("xrpl", re.compile(r"^r[1-9A-HJ-NP-Za-km-z]{24,34}$")),
]


def _detect_chain(address: str) -> str:
    """Best-effort chain detection from address format."""
    for chain, pattern in _CHAIN_PATTERNS:
        if pattern.match(address):
            return chain
    return "unknown"


# ---------------------------------------------------------------------------
# Ingestion helpers
# ---------------------------------------------------------------------------


async def _fetch_text(url: str, timeout: int = 60) -> Optional[str]:
    """Download a URL and return its text content."""
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    logger.error(f"Sanctions fetch failed: HTTP {resp.status} from {url}")
                    return None
                return await resp.text()
    except Exception as exc:
        logger.error(f"Sanctions fetch error for {url}: {exc}")
        return None


async def ingest_ofac_github() -> int:
    """Ingest the pre-parsed OFAC BTC address list from GitHub.

    Returns the number of addresses upserted.
    """
    text = await _fetch_text(OFAC_GITHUB_URL)
    if not text:
        return 0

    addresses = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.startswith("#")
    ]

    pool = get_postgres_pool()
    count = 0
    async with pool.acquire() as conn:
        for addr in addresses:
            chain = _detect_chain(addr)
            try:
                await conn.execute(
                    """
                    INSERT INTO sanctioned_addresses
                        (address, blockchain, source, list_name, entity_name, last_seen_at)
                    VALUES ($1, $2, 'ofac_sdn', 'SDN List (GitHub mirror)', NULL, NOW())
                    ON CONFLICT (address, blockchain, source) DO UPDATE
                        SET last_seen_at = NOW(), removed_at = NULL
                    """,
                    addr,
                    chain,
                )
                count += 1
            except Exception as exc:
                logger.warning(f"OFAC upsert failed for {addr}: {exc}")

    logger.info(f"OFAC GitHub ingest complete: {count} addresses upserted")
    return count


async def ingest_ofac_sdn_xml() -> int:
    """Parse the OFAC SDN Advanced XML for digital currency addresses.

    Looks for <Feature FeatureTypeID="XXX"> entries where the feature type
    indicates a digital currency address.
    """
    text = await _fetch_text(OFAC_SDN_XML_URL, timeout=120)
    if not text:
        return 0

    count = 0
    pool = get_postgres_pool()

    try:
        root = ET.fromstring(text)
        ns = {"sdn": "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ADVANCED_XML"}
        # Try without namespace if the above fails
        if root.tag.startswith("{"):
            ns_uri = root.tag.split("}")[0].strip("{")
            ns = {"sdn": ns_uri}

        async with pool.acquire() as conn:
            # Find all DistinctParty entries
            for party in root.iter():
                if "DistinctParty" not in party.tag:
                    continue

                entity_name = ""
                entity_id = party.attrib.get("FixedRef", "")
                program = ""

                # Extract name
                for alias in party.iter():
                    if "Alias" in alias.tag:
                        for doc_val in alias.iter():
                            if "DocumentedName" in doc_val.tag:
                                for name_part in doc_val.iter():
                                    if name_part.text and name_part.text.strip():
                                        entity_name = name_part.text.strip()
                                        break
                        if entity_name:
                            break

                # Extract sanctions program
                for profile in party.iter():
                    if "SanctionsProgram" in profile.tag:
                        program = profile.text.strip() if profile.text else ""
                        break

                # Extract digital currency addresses from Features
                for feature in party.iter():
                    if "Feature" not in feature.tag:
                        continue
                    feature_type = feature.attrib.get("FeatureTypeID", "")
                    # FeatureTypeID for "Digital Currency Address" varies;
                    # look for the version value containing the address
                    for version_detail in feature.iter():
                        if version_detail.text and _looks_like_crypto_address(
                            version_detail.text.strip()
                        ):
                            addr = version_detail.text.strip()
                            chain = _detect_chain(addr)
                            try:
                                await conn.execute(
                                    """
                                    INSERT INTO sanctioned_addresses
                                        (address, blockchain, source, list_name,
                                         entity_name, entity_id, program, last_seen_at)
                                    VALUES ($1, $2, 'ofac_sdn', 'SDN Advanced XML',
                                            $3, $4, $5, NOW())
                                    ON CONFLICT (address, blockchain, source) DO UPDATE
                                        SET last_seen_at = NOW(),
                                            removed_at = NULL,
                                            entity_name = EXCLUDED.entity_name,
                                            entity_id = EXCLUDED.entity_id,
                                            program = EXCLUDED.program
                                    """,
                                    addr,
                                    chain,
                                    entity_name,
                                    entity_id,
                                    program,
                                )
                                count += 1
                            except Exception as exc:
                                logger.warning(f"OFAC XML upsert failed for {addr}: {exc}")

    except ET.ParseError as exc:
        logger.error(f"OFAC SDN XML parse error: {exc}")

    logger.info(f"OFAC SDN XML ingest complete: {count} addresses upserted")
    return count


async def ingest_eu_sanctions() -> int:
    """Parse the EU Consolidated Sanctions XML for crypto addresses.

    The EU list rarely contains explicit crypto addresses but may include
    them in remarks or identification fields. This is a best-effort parser.
    """
    text = await _fetch_text(EU_SANCTIONS_URL, timeout=120)
    if not text:
        return 0

    count = 0
    pool = get_postgres_pool()

    try:
        root = ET.fromstring(text)

        async with pool.acquire() as conn:
            for entity in root.iter():
                tag = entity.tag.split("}")[-1] if "}" in entity.tag else entity.tag
                if tag != "sanctionEntity":
                    continue

                entity_name = ""
                for name_el in entity.iter():
                    name_tag = name_el.tag.split("}")[-1] if "}" in name_el.tag else name_el.tag
                    if name_tag in ("wholeName", "lastName"):
                        if name_el.text and name_el.text.strip():
                            entity_name = name_el.text.strip()
                            break

                # Search remarks and identification for crypto addresses
                for el in entity.iter():
                    if el.text and _looks_like_crypto_address(el.text.strip()):
                        addr = el.text.strip()
                        chain = _detect_chain(addr)
                        try:
                            await conn.execute(
                                """
                                INSERT INTO sanctioned_addresses
                                    (address, blockchain, source, list_name,
                                     entity_name, last_seen_at)
                                VALUES ($1, $2, 'eu_consolidated', 'EU Consolidated Sanctions',
                                        $3, NOW())
                                ON CONFLICT (address, blockchain, source) DO UPDATE
                                    SET last_seen_at = NOW(),
                                        removed_at = NULL,
                                        entity_name = EXCLUDED.entity_name
                                """,
                                addr,
                                chain,
                                entity_name,
                            )
                            count += 1
                        except Exception as exc:
                            logger.warning(f"EU sanctions upsert failed for {addr}: {exc}")

    except ET.ParseError as exc:
        logger.error(f"EU sanctions XML parse error: {exc}")

    logger.info(f"EU sanctions ingest complete: {count} addresses upserted")
    return count


def _looks_like_crypto_address(text: str) -> bool:
    """Quick heuristic: does this text look like a crypto address?"""
    if len(text) < 26 or len(text) > 64:
        return False
    if " " in text:
        return False
    for _, pattern in _CHAIN_PATTERNS:
        if pattern.match(text):
            return True
    return False


# ---------------------------------------------------------------------------
# Screening functions
# ---------------------------------------------------------------------------


async def screen_address(
    address: str, blockchain: Optional[str] = None
) -> Dict[str, Any]:
    """Screen a single address against the sanctioned_addresses table.

    Returns a dict with 'matched', 'matches' (list of match details),
    and 'screened_at'.
    """
    pool = get_postgres_pool()
    async with pool.acquire() as conn:
        if blockchain:
            rows = await conn.fetch(
                """
                SELECT address, blockchain, source, list_name,
                       entity_name, entity_id, program, added_at
                FROM sanctioned_addresses
                WHERE address = $1 AND blockchain = $2 AND removed_at IS NULL
                """,
                address.strip(),
                blockchain.lower(),
            )
        else:
            rows = await conn.fetch(
                """
                SELECT address, blockchain, source, list_name,
                       entity_name, entity_id, program, added_at
                FROM sanctioned_addresses
                WHERE address = $1 AND removed_at IS NULL
                """,
                address.strip(),
            )

    matches = [dict(r) for r in rows]
    matched = len(matches) > 0

    return {
        "address": address,
        "blockchain": blockchain,
        "matched": matched,
        "match_count": len(matches),
        "matches": matches,
        "screened_at": datetime.now(timezone.utc).isoformat(),
    }


async def screen_addresses_bulk(
    addresses: List[str], blockchain: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Screen multiple addresses. Returns a list of screen results."""
    results = []
    for addr in addresses:
        result = await screen_address(addr, blockchain)
        results.append(result)
    return results


async def log_screening(
    address: str,
    blockchain: Optional[str],
    matched: bool,
    match_source: Optional[str],
    match_entity: Optional[str],
    user_id: Optional[int] = None,
) -> None:
    """Record a screening event in the audit log."""
    pool = get_postgres_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO sanctions_screening_log
                (address, blockchain, matched, match_source, match_entity, user_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            address,
            blockchain or "unknown",
            matched,
            match_source,
            match_entity,
            user_id,
        )


# ---------------------------------------------------------------------------
# Full sync orchestrator
# ---------------------------------------------------------------------------


async def sync_all(requested_by: str = "system") -> Dict[str, Any]:
    """Run a full sanctions sync: OFAC (GitHub + XML) + EU.

    Updates the sanctions_sync_status table with results.
    """
    pool = get_postgres_pool()
    results: Dict[str, Any] = {}

    sync_fns = [
        ("ofac_sdn", _sync_ofac),
        ("eu_consolidated", _sync_eu),
    ]
    for source, fn in sync_fns:
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE sanctions_sync_status SET status='running' WHERE source=$1",
                    source,
                )
            count = await fn()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE sanctions_sync_status
                    SET status='success', last_sync_at=NOW(),
                        records_synced=$2, error_message=NULL
                    WHERE source=$1
                    """,
                    source,
                    count,
                )
            results[source] = {"status": "success", "records": count}
        except Exception as exc:
            logger.error(f"Sanctions sync failed for {source}: {exc}")
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE sanctions_sync_status
                    SET status='error', error_message=$2
                    WHERE source=$1
                    """,
                    source,
                    str(exc)[:500],
                )
            results[source] = {"status": "error", "error": str(exc)[:200]}

    return results


async def _sync_ofac() -> int:
    """OFAC sync: GitHub list + SDN XML."""
    count_gh = await ingest_ofac_github()
    count_xml = await ingest_ofac_sdn_xml()
    return count_gh + count_xml


async def _sync_eu() -> int:
    """EU sanctions sync."""
    return await ingest_eu_sanctions()


async def get_sync_status() -> List[Dict[str, Any]]:
    """Get current sync status for all sources."""
    pool = get_postgres_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM sanctions_sync_status ORDER BY source"
        )
    return [dict(r) for r in rows]


async def get_sanctioned_count() -> Dict[str, int]:
    """Get count of active sanctioned addresses by source."""
    pool = get_postgres_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT source, count(*) AS cnt
            FROM sanctioned_addresses
            WHERE removed_at IS NULL
            GROUP BY source
            """
        )
    return {r["source"]: r["cnt"] for r in rows}
