"""
Jackdaw Sentry - Entity Attribution Service (M11)
Ingests open-source address label datasets, stores entity-address mappings
in PostgreSQL, and provides lookup functions for graph enrichment,
risk scoring, and compliance reporting.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp

from src.api.database import get_postgres_pool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data source URLs
# ---------------------------------------------------------------------------

# brianleect/etherscan-labels — combined JSON of Etherscan-scraped labels
ETHERSCAN_LABELS_URL = (
    "https://raw.githubusercontent.com/brianleect/etherscan-labels/"
    "main/combined/combinedAllLabels.json"
)

# CryptoScamDB dataset
CRYPTOSCAMDB_URL = (
    "https://raw.githubusercontent.com/CryptoScamDB/blacklist/master/data/urls.json"
)

# Well-known exchange hot/cold wallets (community curated)
COMMUNITY_LABELS_URL = (
    "https://raw.githubusercontent.com/brianleect/etherscan-labels/"
    "main/combined/combinedExchangeLabels.json"
)

# Category mapping from Etherscan label nameTags to entity_type
# Ordered list — more specific keywords must come before generic ones
_CATEGORY_LIST = [
    ("exchange", "exchange"),
    ("cex", "exchange"),
    ("binance", "exchange"),
    ("coinbase", "exchange"),
    ("kraken", "exchange"),
    ("dex", "defi_protocol"),
    ("defi", "defi_protocol"),
    ("uniswap", "defi_protocol"),
    ("aave", "defi_protocol"),
    ("bridge", "bridge"),
    ("tornado", "mixer"),
    ("mixer", "mixer"),
    ("gambling", "gambling"),
    ("casino", "gambling"),
    ("phishing", "scam"),
    ("scam", "scam"),
    ("hack", "scam"),
    ("exploit", "scam"),
    ("ransomware", "ransomware"),
    ("darknet", "darknet_market"),
    ("mining", "mining_pool"),
    ("pool", "mining_pool"),
    ("nft", "nft_marketplace"),
    ("payment", "payment_processor"),
    ("government", "government"),
    ("wallet", "custodial_wallet"),
    ("fund", "custodial_wallet"),
    ("contract", "smart_contract"),
]


def _classify_entity_type(name: str, labels: List[str] = None) -> str:
    """Best-effort classification of entity type from name and labels."""
    search_text = (name or "").lower()
    if labels:
        search_text += " " + " ".join(l.lower() for l in labels)
    for keyword, etype in _CATEGORY_LIST:
        if keyword in search_text:
            return etype
    return "unknown"


def _risk_for_type(entity_type: str) -> str:
    """Default risk level based on entity type."""
    HIGH_RISK = {"mixer", "darknet_market", "ransomware", "scam", "gambling"}
    MEDIUM_RISK = {"unknown", "smart_contract", "bridge"}
    if entity_type in HIGH_RISK:
        return "high"
    if entity_type in MEDIUM_RISK:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

async def _fetch_text(url: str, timeout: int = 120) -> Optional[str]:
    """Download a URL and return its text content."""
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    logger.error(
                        f"Entity label fetch failed: HTTP {resp.status} from {url}"
                    )
                    return None
                return await resp.text()
    except Exception as exc:
        logger.error(f"Entity label fetch error for {url}: {exc}")
        return None


async def _fetch_json(url: str, timeout: int = 120) -> Any:
    """Download a URL and return parsed JSON."""
    text = await _fetch_text(url, timeout)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error(f"JSON parse error for {url}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Ingestion functions
# ---------------------------------------------------------------------------

async def _ensure_label_source(conn, source_key: str, name: str, url: str = None):
    """Insert label source row if it doesn't exist."""
    await conn.execute(
        """
        INSERT INTO label_sources (source_key, name, url)
        VALUES ($1, $2, $3)
        ON CONFLICT (source_key) DO NOTHING
        """,
        source_key,
        name,
        url,
    )


async def _upsert_entity(conn, name: str, entity_type: str, **kwargs) -> str:
    """Upsert an entity and return its id."""
    risk_level = kwargs.get("risk_level") or _risk_for_type(entity_type)
    row = await conn.fetchrow(
        """
        INSERT INTO entities (name, entity_type, category, risk_level, description, website, country)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (name, entity_type) DO UPDATE
            SET category = COALESCE(EXCLUDED.category, entities.category),
                risk_level = EXCLUDED.risk_level,
                updated_at = NOW()
        RETURNING id
        """,
        name,
        entity_type,
        kwargs.get("category"),
        risk_level,
        kwargs.get("description"),
        kwargs.get("website"),
        kwargs.get("country"),
    )
    return str(row["id"])


async def _upsert_entity_address(
    conn, entity_id: str, address: str, blockchain: str,
    source: str, label: str = None, confidence: float = 1.0,
):
    """Upsert an entity-address mapping."""
    await conn.execute(
        """
        INSERT INTO entity_addresses (entity_id, address, blockchain, label, confidence, source)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (address, blockchain, source) DO UPDATE
            SET entity_id = EXCLUDED.entity_id,
                label = COALESCE(EXCLUDED.label, entity_addresses.label),
                confidence = EXCLUDED.confidence,
                last_verified_at = NOW(),
                removed_at = NULL
        """,
        entity_id,
        address.lower().strip(),
        blockchain.lower(),
        label,
        confidence,
        source,
    )


async def ingest_etherscan_labels() -> int:
    """Ingest the brianleect/etherscan-labels combined dataset.

    Returns the number of address mappings upserted.
    """
    data = await _fetch_json(ETHERSCAN_LABELS_URL)
    if not data or not isinstance(data, dict):
        return 0

    pool = get_postgres_pool()
    count = 0
    source_key = "etherscan_labels"

    async with pool.acquire() as conn:
        await _ensure_label_source(
            conn, source_key, "Etherscan Labels (GitHub)", ETHERSCAN_LABELS_URL
        )

        for address, info in data.items():
            if not address or not address.startswith("0x"):
                continue
            try:
                name_tag = ""
                labels_list = []
                if isinstance(info, dict):
                    name_tag = info.get("nameTag") or info.get("name") or ""
                    labels_list = info.get("labels") or []
                elif isinstance(info, str):
                    name_tag = info

                if not name_tag:
                    continue

                entity_type = _classify_entity_type(name_tag, labels_list)
                entity_id = await _upsert_entity(
                    conn, name_tag, entity_type,
                    category=labels_list[0] if labels_list else None,
                )
                await _upsert_entity_address(
                    conn, entity_id, address, "ethereum",
                    source=source_key, label=name_tag, confidence=0.9,
                )
                count += 1
            except Exception as exc:
                logger.warning(f"Etherscan label upsert failed for {address}: {exc}")

        await conn.execute(
            """
            UPDATE label_sources
            SET status = 'success', last_sync_at = NOW(), records_synced = $2
            WHERE source_key = $1
            """,
            source_key,
            count,
        )

    logger.info(f"Etherscan labels ingest complete: {count} addresses upserted")
    return count


async def ingest_scam_databases() -> int:
    """Ingest CryptoScamDB blacklist data.

    Returns the number of address mappings upserted.
    """
    data = await _fetch_json(CRYPTOSCAMDB_URL)
    if not data:
        return 0

    pool = get_postgres_pool()
    count = 0
    source_key = "cryptoscamdb"

    async with pool.acquire() as conn:
        await _ensure_label_source(
            conn, source_key, "CryptoScamDB Blacklist", CRYPTOSCAMDB_URL
        )

        entries = data if isinstance(data, list) else data.values() if isinstance(data, dict) else []
        for entry in entries:
            try:
                if isinstance(entry, dict):
                    addresses = entry.get("addresses") or []
                    name = entry.get("name") or entry.get("url") or "Unknown Scam"
                    category = entry.get("category") or "scam"
                else:
                    continue

                if not addresses:
                    continue

                entity_id = await _upsert_entity(
                    conn, name, "scam",
                    category=category,
                    risk_level="high",
                )
                for addr in addresses:
                    if not addr or not isinstance(addr, str):
                        continue
                    blockchain = "ethereum" if addr.startswith("0x") else "bitcoin"
                    await _upsert_entity_address(
                        conn, entity_id, addr, blockchain,
                        source=source_key, label=f"Scam: {name}", confidence=0.8,
                    )
                    count += 1
            except Exception as exc:
                logger.warning(f"CryptoScamDB upsert failed: {exc}")

        await conn.execute(
            """
            UPDATE label_sources
            SET status = 'success', last_sync_at = NOW(), records_synced = $2
            WHERE source_key = $1
            """,
            source_key,
            count,
        )

    logger.info(f"CryptoScamDB ingest complete: {count} addresses upserted")
    return count


async def ingest_community_labels() -> int:
    """Ingest community-curated exchange labels.

    Returns the number of address mappings upserted.
    """
    data = await _fetch_json(COMMUNITY_LABELS_URL)
    if not data or not isinstance(data, dict):
        return 0

    pool = get_postgres_pool()
    count = 0
    source_key = "community_labels"

    async with pool.acquire() as conn:
        await _ensure_label_source(
            conn, source_key, "Community Exchange Labels", COMMUNITY_LABELS_URL
        )

        for address, info in data.items():
            if not address or not address.startswith("0x"):
                continue
            try:
                name_tag = ""
                if isinstance(info, dict):
                    name_tag = info.get("nameTag") or info.get("name") or ""
                elif isinstance(info, str):
                    name_tag = info

                if not name_tag:
                    continue

                entity_id = await _upsert_entity(
                    conn, name_tag, "exchange",
                    category="cex",
                    risk_level="low",
                )
                await _upsert_entity_address(
                    conn, entity_id, address, "ethereum",
                    source=source_key, label=name_tag, confidence=0.85,
                )
                count += 1
            except Exception as exc:
                logger.warning(f"Community label upsert failed for {address}: {exc}")

        await conn.execute(
            """
            UPDATE label_sources
            SET status = 'success', last_sync_at = NOW(), records_synced = $2
            WHERE source_key = $1
            """,
            source_key,
            count,
        )

    logger.info(f"Community labels ingest complete: {count} addresses upserted")
    return count


# ---------------------------------------------------------------------------
# Sync orchestrator
# ---------------------------------------------------------------------------

async def sync_all_labels(requested_by: str = "system") -> Dict[str, Any]:
    """Run a full entity label sync from all sources.

    Updates label_sources status table with results.
    """
    results: Dict[str, Any] = {}

    ingestors = [
        ("etherscan_labels", ingest_etherscan_labels),
        ("cryptoscamdb", ingest_scam_databases),
        ("community_labels", ingest_community_labels),
    ]

    for source_key, fn in ingestors:
        try:
            pool = get_postgres_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE label_sources SET status = 'running' WHERE source_key = $1",
                    source_key,
                )
            count = await fn()
            results[source_key] = {"status": "success", "records": count}
        except Exception as exc:
            logger.error(f"Entity label sync failed for {source_key}: {exc}")
            try:
                pool = get_postgres_pool()
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE label_sources
                        SET status = 'error', error_message = $2
                        WHERE source_key = $1
                        """,
                        source_key,
                        str(exc)[:500],
                    )
            except Exception:
                pass
            results[source_key] = {"status": "error", "error": str(exc)[:200]}

    return results


# ---------------------------------------------------------------------------
# Lookup functions
# ---------------------------------------------------------------------------

async def lookup_address(
    address: str, blockchain: str = None
) -> Optional[Dict[str, Any]]:
    """Look up entity attribution for a single address.

    Returns entity info dict or None if not found.
    """
    pool = get_postgres_pool()
    addr = address.lower().strip()

    bc_clause = "AND ea.blockchain = $2" if blockchain else ""
    params = [addr, blockchain.lower()] if blockchain else [addr]

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""
            SELECT e.name AS entity_name, e.entity_type, e.category,
                   e.risk_level, e.description, e.website,
                   ea.label, ea.confidence, ea.source, ea.blockchain
            FROM entity_addresses ea
            JOIN entities e ON e.id = ea.entity_id
            WHERE ea.address = $1 AND ea.removed_at IS NULL
            {bc_clause}
            ORDER BY ea.confidence DESC
            LIMIT 1
            """,
            *params,
        )

    if not row:
        return None

    return {
        "entity_name": row["entity_name"],
        "entity_type": row["entity_type"],
        "category": row["category"],
        "risk_level": row["risk_level"],
        "description": row["description"],
        "label": row["label"],
        "confidence": float(row["confidence"]) if row["confidence"] else 1.0,
        "source": row["source"],
        "blockchain": row["blockchain"],
    }


async def lookup_addresses_bulk(
    addresses: List[str], blockchain: str = None
) -> Dict[str, Dict[str, Any]]:
    """Bulk lookup entity attribution for multiple addresses.

    Returns a dict of address → entity info (only for matched addresses).
    """
    if not addresses:
        return {}

    pool = get_postgres_pool()
    cleaned = [a.lower().strip() for a in addresses]

    bc_clause = "AND ea.blockchain = $2" if blockchain else ""
    params = [cleaned, blockchain.lower()] if blockchain else [cleaned]

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT DISTINCT ON (ea.address)
                   ea.address, e.name AS entity_name, e.entity_type,
                   e.category, e.risk_level, ea.label, ea.confidence, ea.source
            FROM entity_addresses ea
            JOIN entities e ON e.id = ea.entity_id
            WHERE ea.address = ANY($1) AND ea.removed_at IS NULL
            {bc_clause}
            ORDER BY ea.address, ea.confidence DESC
            """,
            *params,
        )

    result = {}
    for row in rows:
        result[row["address"]] = {
            "entity_name": row["entity_name"],
            "entity_type": row["entity_type"],
            "category": row["category"],
            "risk_level": row["risk_level"],
            "label": row["label"],
            "confidence": float(row["confidence"]) if row["confidence"] else 1.0,
            "source": row["source"],
        }
    return result


async def get_entity_details(entity_id: str) -> Optional[Dict[str, Any]]:
    """Get full entity info with all associated addresses."""
    pool = get_postgres_pool()

    async with pool.acquire() as conn:
        entity = await conn.fetchrow(
            "SELECT * FROM entities WHERE id = $1", entity_id
        )
        if not entity:
            return None

        addresses = await conn.fetch(
            """
            SELECT address, blockchain, label, confidence, source,
                   first_seen_at, last_verified_at
            FROM entity_addresses
            WHERE entity_id = $1 AND removed_at IS NULL
            ORDER BY last_verified_at DESC
            """,
            entity_id,
        )

    return {
        "id": str(entity["id"]),
        "name": entity["name"],
        "entity_type": entity["entity_type"],
        "category": entity["category"],
        "risk_level": entity["risk_level"],
        "description": entity["description"],
        "website": entity["website"],
        "country": entity["country"],
        "metadata": entity["metadata"],
        "created_at": entity["created_at"].isoformat() if entity["created_at"] else None,
        "updated_at": entity["updated_at"].isoformat() if entity["updated_at"] else None,
        "addresses": [
            {
                "address": a["address"],
                "blockchain": a["blockchain"],
                "label": a["label"],
                "confidence": float(a["confidence"]) if a["confidence"] else 1.0,
                "source": a["source"],
                "first_seen_at": a["first_seen_at"].isoformat() if a["first_seen_at"] else None,
                "last_verified_at": a["last_verified_at"].isoformat() if a["last_verified_at"] else None,
            }
            for a in addresses
        ],
    }


async def search_entities(
    query: str, entity_type: str = None, limit: int = 50
) -> List[Dict[str, Any]]:
    """Search entities by name or address."""
    pool = get_postgres_pool()
    search = f"%{query.strip()}%"

    type_clause = "AND e.entity_type = $3" if entity_type else ""
    params = [search, limit, entity_type] if entity_type else [search, limit]

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT DISTINCT e.id, e.name, e.entity_type, e.category,
                   e.risk_level, e.description
            FROM entities e
            LEFT JOIN entity_addresses ea ON ea.entity_id = e.id
            WHERE (e.name ILIKE $1 OR ea.address ILIKE $1)
            {type_clause}
            ORDER BY e.name
            LIMIT $2
            """,
            *params,
        )

    return [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "entity_type": r["entity_type"],
            "category": r["category"],
            "risk_level": r["risk_level"],
            "description": r["description"],
        }
        for r in rows
    ]


async def get_sync_status() -> List[Dict[str, Any]]:
    """Get current sync status for all label sources."""
    pool = get_postgres_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM label_sources ORDER BY source_key"
        )
    return [dict(r) for r in rows]


async def get_entity_counts() -> Dict[str, int]:
    """Get count of active entity-address mappings by source."""
    pool = get_postgres_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT source, count(*) AS cnt
            FROM entity_addresses
            WHERE removed_at IS NULL
            GROUP BY source
            """
        )
    return {r["source"]: r["cnt"] for r in rows}
