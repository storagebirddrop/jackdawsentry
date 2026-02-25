"""
Jackdaw Sentry - Threat Intelligence Feeds
Real-time intelligence from multiple sources
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Set

import aiohttp
from cryptography.fernet import Fernet

from src.api.config import settings
from src.api.database import get_postgres_connection

logger = logging.getLogger(__name__)


class ThreatLevel(str, Enum):
    """Threat intelligence levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    SEVERE = "severe"


class ThreatType(str, Enum):
    """Types of threat intelligence"""

    SANCTIONS = "sanctions"
    SCAM = "scam"
    HACK = "hack"
    PHISHING = "phishing"
    MALWARE = "malware"
    RANSOMWARE = "ransomware"
    TERRORISM = "terrorism"
    MONEY_LAUNDERING = "money_laundering"
    DARK_WEB = "dark_web"
    MIXER = "mixer"
    EXCHANGE_HACK = "exchange_hack"
    DEFI_EXPLOIT = "defi_exploit"
    NFT_FRAUD = "nft_fraud"
    SOCIAL_ENGINEERING = "social_engineering"


class FeedStatus(str, Enum):
    """Status of threat intelligence feeds"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    SYNCING = "syncing"


@dataclass
class ThreatIntelligence:
    """Threat intelligence data structure"""

    id: str
    feed_source: str
    threat_type: ThreatType
    threat_level: ThreatLevel
    address: str
    entity: Optional[str] = None
    description: Optional[str] = None
    confidence_score: float = 1.0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    is_active: bool = True
    tags: List[str] = None
    evidence: List[Dict[str, Any]] = None
    raw_data: Dict[str, Any] = None
    created_at: datetime = None
    updated_at: datetime = None


@dataclass
class ThreatFeed:
    """Threat intelligence feed configuration"""

    id: str
    name: str
    feed_type: str
    api_endpoint: str
    api_key: str
    headers: Dict[str, str]
    sync_frequency_minutes: int
    is_active: bool
    last_sync: Optional[datetime] = None
    error_count: int = 0
    metadata: Dict[str, Any] = None


class ThreatIntelligenceManager:
    """Manager for threat intelligence feeds and data"""

    def __init__(self):
        self.feeds: Dict[str, ThreatFeed] = {}
        self.intelligence_cache: Dict[str, ThreatIntelligence] = {}
        self.cache_ttl = 1800  # 30 minutes
        self._initialized = False
        self.settings = settings
        self.fernet = Fernet(self.settings.encryption_key.encode())
        self.http_session = None

    async def initialize(self):
        """Initialize the threat intelligence manager"""
        if self._initialized:
            return

        logger.info("Initializing Threat Intelligence Manager...")

        # Initialize HTTP session
        self.http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30, connect=10),
            headers={"User-Agent": "Jackdaw-Sentry/1.0"},
        )

        await self._create_threat_intelligence_tables()
        await self._load_default_feeds()
        self._initialized = True
        logger.info("Threat Intelligence Manager initialized successfully")

    async def _create_threat_intelligence_tables(self):
        """Create threat intelligence tables"""

        create_intelligence_table = """
        CREATE TABLE IF NOT EXISTS threat_intelligence (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            feed_source VARCHAR(100) NOT NULL,
            threat_type VARCHAR(50) NOT NULL,
            threat_level VARCHAR(20) NOT NULL,
            address VARCHAR(255) NOT NULL,
            entity VARCHAR(255),
            description TEXT,
            confidence_score DECIMAL(5,4) NOT NULL DEFAULT 1.0,
            first_seen TIMESTAMP WITH TIME ZONE,
            last_seen TIMESTAMP WITH TIME ZONE,
            is_active BOOLEAN DEFAULT TRUE,
            tags TEXT[] DEFAULT '{}',
            evidence JSONB DEFAULT '[]',
            raw_data JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_threat_intelligence_address ON threat_intelligence(address);
        CREATE INDEX IF NOT EXISTS idx_threat_intelligence_source ON threat_intelligence(feed_source);
        CREATE INDEX IF NOT EXISTS idx_threat_intelligence_type ON threat_intelligence(threat_type);
        CREATE INDEX IF NOT EXISTS idx_threat_intelligence_level ON threat_intelligence(threat_level);
        CREATE INDEX IF NOT EXISTS idx_threat_intelligence_active ON threat_intelligence(is_active);
        CREATE INDEX IF NOT EXISTS idx_threat_intelligence_seen ON threat_intelligence(last_seen);
        """

        create_feeds_table = """
        CREATE TABLE IF NOT EXISTS threat_feeds (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            feed_id VARCHAR(100) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            feed_type VARCHAR(50) NOT NULL,
            api_endpoint VARCHAR(500) NOT NULL,
            api_key_encrypted TEXT NOT NULL,
            headers JSONB DEFAULT '{}',
            sync_frequency_minutes INTEGER NOT NULL DEFAULT 60,
            is_active BOOLEAN DEFAULT TRUE,
            last_sync TIMESTAMP WITH TIME ZONE,
            error_count INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_threat_feeds_active ON threat_feeds(is_active);
        CREATE INDEX IF NOT EXISTS idx_threat_feeds_sync ON threat_feeds(last_sync);
        """

        create_sync_log_table = """
        CREATE TABLE IF NOT EXISTS threat_feed_sync_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            feed_id VARCHAR(100) NOT NULL,
            sync_status VARCHAR(50) NOT NULL,
            records_processed INTEGER NOT NULL DEFAULT 0,
            records_added INTEGER NOT NULL DEFAULT 0,
            records_updated INTEGER NOT NULL DEFAULT 0,
            records_removed INTEGER NOT NULL DEFAULT 0,
            sync_duration_ms INTEGER,
            error_message TEXT,
            sync_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_threat_sync_log_feed ON threat_feed_sync_log(feed_id);
        CREATE INDEX IF NOT EXISTS idx_threat_sync_log_timestamp ON threat_feed_sync_log(sync_timestamp);
        """

        conn = await get_postgres_connection()
        try:
            await conn.execute(create_intelligence_table)
            await conn.execute(create_feeds_table)
            await conn.execute(create_sync_log_table)
            await conn.commit()
            logger.info("Threat intelligence tables created/verified")
        except Exception as e:
            logger.error(f"Error creating threat intelligence tables: {e}")
            await conn.rollback()
            raise
        finally:
            await conn.close()

    async def _load_default_feeds(self):
        """Load default threat intelligence feeds"""

        default_feeds = [
            ThreatFeed(
                id="cryptoscdb",
                name="CryptoScamDB",
                feed_type="cryptoscdb",
                api_endpoint="https://api.cryptoscamdb.org/api/v1/addresses",
                api_key="",
                headers={"Accept": "application/json"},
                sync_frequency_minutes=60,
                is_active=True,
            ),
            ThreatFeed(
                id="chainalysis",
                name="Chainalysis",
                feed_type="chainalysis",
                api_endpoint="https://api.chainalysis.com/kyt/v2/address",
                api_key="",
                headers={"Accept": "application/json"},
                sync_frequency_minutes=30,
                is_active=True,
            ),
            ThreatFeed(
                id="trmlabs",
                name="TRM Labs",
                feed_type="trmlabs",
                api_endpoint="https://api.trmlabs.com/v1/address",
                api_key="",
                headers={"Accept": "application/json"},
                sync_frequency_minutes=15,
                is_active=True,
            ),
            ThreatFeed(
                id="elliptic",
                name="Elliptic",
                feed_type="elliptic",
                api_endpoint="https://api.elliptic.co/v2/address",
                api_key="",
                headers={"Accept": "application/json"},
                sync_frequency_minutes=30,
                is_active=True,
            ),
            ThreatFeed(
                id="cipherblade",
                name="CipherBlade",
                feed_type="cipherblade",
                api_endpoint="https://api.cipherblade.com/v1/address",
                api_key="",
                headers={"Accept": "application/json"},
                sync_frequency_minutes=60,
                is_active=True,
            ),
        ]

        for feed in default_feeds:
            await self.add_feed(feed)

    async def add_feed(self, feed: ThreatFeed) -> bool:
        """Add a threat intelligence feed"""

        # Encrypt API key
        encrypted_key = self.fernet.encrypt(feed.api_key.encode()).decode()

        insert_query = """
        INSERT INTO threat_feeds (
            feed_id, name, feed_type, api_endpoint, api_key_encrypted,
            headers, sync_frequency_minutes, is_active, metadata
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (feed_id) DO UPDATE SET
            name = EXCLUDED.name,
            api_endpoint = EXCLUDED.api_endpoint,
            api_key_encrypted = EXCLUDED.api_key_encrypted,
            headers = EXCLUDED.headers,
            sync_frequency_minutes = EXCLUDED.sync_frequency_minutes,
            is_active = EXCLUDED.is_active,
            metadata = EXCLUDED.metadata,
            updated_at = NOW()
        RETURNING id
        """

        conn = await get_postgres_connection()
        try:
            await conn.execute(
                insert_query,
                feed.id,
                feed.name,
                feed.feed_type,
                feed.api_endpoint,
                encrypted_key,
                json.dumps(feed.headers),
                feed.sync_frequency_minutes,
                feed.is_active,
                json.dumps(feed.metadata or {}),
            )
            await conn.commit()

            self.feeds[feed.id] = feed
            logger.info(f"Added threat feed: {feed.name}")
            return True

        except Exception as e:
            logger.error(f"Error adding threat feed {feed.id}: {e}")
            await conn.rollback()
            return False
        finally:
            await conn.close()

    async def sync_all_feeds(self) -> Dict[str, Any]:
        """Sync all active threat intelligence feeds"""

        results = {}

        for feed_id, feed in self.feeds.items():
            if feed.is_active:
                try:
                    result = await self.sync_feed(feed_id)
                    results[feed_id] = result
                except Exception as e:
                    logger.error(f"Error syncing feed {feed_id}: {e}")
                    results[feed_id] = {"status": "error", "error": str(e)}

        return results

    async def sync_feed(self, feed_id: str) -> Dict[str, Any]:
        """Sync a specific threat intelligence feed"""

        feed = self.feeds.get(feed_id)
        if not feed:
            return {"status": "error", "error": f"Feed {feed_id} not found"}

        if not feed.is_active:
            return {"status": "inactive", "message": f"Feed {feed_id} is inactive"}

        start_time = datetime.now(timezone.utc)

        try:
            # Decrypt API key
            api_key = self.fernet.decrypt(feed.api_key_encrypted.encode()).decode()

            # Sync based on feed type
            if feed.feed_type == "cryptoscdb":
                result = await self._sync_cryptoscdb_feed(feed, api_key)
            elif feed.feed_type == "chainalysis":
                result = await self._sync_chainalysis_feed(feed, api_key)
            elif feed.feed_type == "trmlabs":
                result = await self._sync_trmlabs_feed(feed, api_key)
            elif feed.feed_type == "elliptic":
                result = await self.sync_elliptic_feed(feed, api_key)
            elif feed.feed_type == "cipherblade":
                result = await self.sync_cipherblade_feed(feed, api_key)
            else:
                result = await self._sync_generic_feed(feed, api_key)

            # Update feed last sync time
            await self._update_feed_sync_time(feed_id, start_time, result["status"])

            return result

        except Exception as e:
            logger.error(f"Error syncing feed {feed_id}: {e}")
            await self._update_feed_sync_time(feed_id, start_time, "error", str(e))
            return {"status": "error", "error": str(e)}

    async def _sync_cryptoscdb_feed(
        self, feed: ThreatFeed, api_key: str
    ) -> Dict[str, Any]:
        """Sync CryptoScamDB feed"""

        try:
            # Get addresses from CryptoScamDB
            url = f"{feed.api_endpoint}?limit=100"
            headers = {**feed.headers, "X-API-Key": api_key}

            async with self.http_session.get(url, headers=headers) as response:
                if response.status != 200:
                    return {
                        "status": "error",
                        "error": f"HTTP {response.status}: {response.text}",
                    }

                data = await response.json()

                records_processed = 0
                records_added = 0
                records_updated = 0
                records_removed = 0

                if data.get("addresses"):
                    for address_data in data["addresses"]:
                        records_processed += 1

                        # Convert to threat intelligence format
                        intelligence = self._convert_to_intelligence(
                            "cryptoscdb", address_data, ThreatType.SCAM
                        )

                        if intelligence:
                            # Check if already exists
                            existing = await self.get_intelligence_by_address(
                                intelligence.address
                            )
                            if existing:
                                # Update existing record
                                await self.update_intelligence(intelligence)
                                records_updated += 1
                            else:
                                # Add new record
                                await self.add_intelligence(intelligence)
                                records_added += 1

                return {
                    "status": "success",
                    "records_processed": records_processed,
                    "records_added": records_added,
                    "records_updated": records_updated,
                    "records_removed": records_removed,
                }

        except Exception as e:
            logger.error(f"Error syncing CryptoScamDB feed: {e}")
            return {"status": "error", "error": str(e)}

    async def _sync_chainalysis_feed(
        self, feed: ThreatFeed, api_key: str
    ) -> Dict[str, Any]:
        """Sync Chainalysis feed"""

        try:
            # Get address data from Chainalysis
            url = f"{feed.api_endpoint}/{feed.api_key}"
            headers = {**feed.headers, "X-API-Key": api_key}

            async with self.http_session.get(url, headers=headers) as response:
                if response.status != 200:
                    return {
                        "status": "error",
                        "error": f"HTTP {response.status}: {response.text}",
                    }

                data = await response.json()

                records_processed = 0
                records_added = 0
                records_updated = 0
                records_removed = 0

                if data.get("address"):
                    # Convert to threat intelligence format
                    intelligence = self._convert_to_intelligence(
                        "chainalysis", data, ThreatType.SCAM
                    )

                    if intelligence:
                        # Check if already exists
                        existing = await self.get_intelligence_by_address(
                            intelligence.address
                        )
                        if existing:
                            await self.update_intelligence(intelligence)
                            records_updated += 1
                        else:
                            await self.add_intelligence(intelligence)
                            records_added += 1
                        records_processed = 1

                return {
                    "status": "success",
                    "records_processed": records_processed,
                    "records_added": records_added,
                    "records_updated": records_updated,
                    "records_removed": records_removed,
                }

        except Exception as e:
            logger.error(f"Error syncing Chainalysis feed: {e}")
            return {"status": "error", "error": str(e)}

    async def _sync_trmlabs_feed(
        self, feed: ThreatFeed, api_key: str
    ) -> Dict[str, Any]:
        """Sync TRM Labs feed"""

        try:
            # Get address data from TRM Labs
            url = f"{feed.api_endpoint}/{feed.api_key}"
            headers = {**feed.headers, "X-API-Key": api_key}

            async with self.http_session.get(url, headers=headers) as response:
                if response.status != 200:
                    return {
                        "status": "error",
                        "error": f"HTTP {response.status}: {response.text}",
                    }

                data = await response.json()

                records_processed = 0
                records_added = 0
                records_updated = 0
                records_removed = 0

                if data.get("data"):
                    # Convert to threat intelligence format
                    intelligence = self._convert_to_intelligence(
                        "trmlabs", data["data"], ThreatType.SCAM
                    )

                    if intelligence:
                        # Check if already exists
                        existing = await self.get_intelligence_by_address(
                            intelligence.address
                        )
                        if existing:
                            await self.update_intelligence(intelligence)
                            records_updated += 1
                        else:
                            await self.add_intelligence(intelligence)
                            records_added += 1
                        records_processed = 1

                return {
                    "status": "success",
                    "records_processed": records_processed,
                    "records_added": records_added,
                    "records_updated": records_updated,
                    "records_removed": records_removed,
                }

        except Exception as e:
            logger.error(f"Error syncing TRM Labs feed: {e}")
            return {"status": "error", "error": str(e)}

    async def _sync_elliptic_feed(
        self, feed: ThreatFeed, api_key: str
    ) -> Dict[str, Any]:
        """Sync Elliptic feed"""

        try:
            # Get address data from Elliptic
            url = f"{feed.api_endpoint}/{feed.api_key}"
            headers = {**feed.headers, "X-API-Key": api_key}

            async with self.http_session.get(url, headers=headers) as response:
                if response.status != 200:
                    return {
                        "status": "error",
                        "error": f"HTTP {response.status}: {response.text}",
                    }

                data = await response.json()

                records_processed = 0
                records_added = 0
                records_updated = 0
                records_removed = 0

                if data.get("data"):
                    # Convert to threat intelligence format
                    intelligence = self._convert_to_intelligence(
                        "elliptic", data["data"], ThreatType.SCAM
                    )

                    if intelligence:
                        # Check if already exists
                        existing = await self.get_intelligence_by_address(
                            intelligence.address
                        )
                        if existing:
                            await self.update_intelligence(intelligence)
                            records_updated += 1
                        else:
                            await self.add_intelligence(intelligence)
                            records_added += 1
                        records_processed = 1

                return {
                    "status": "success",
                    "records_processed": records_processed,
                    "records_added": records_added,
                    "records_updated": records_updated,
                    "records_removed": records_removed,
                }

        except Exception as e:
            logger.error(f"Error syncing Elliptic feed: {e}")
            return {"status": "error", "error": str(e)}

    async def _sync_cipherblade_feed(
        self, feed: ThreatFeed, api_key: str
    ) -> Dict[str, Any]:
        """Sync CipherBlade feed"""

        try:
            # Get address data from CipherBlade
            url = f"{feed.api_endpoint}/{feed.api_key}"
            headers = {**feed.headers, "X-API-Key": api_key}

            async with self.http_session.get(url, headers=headers) as response:
                if response.status != 200:
                    return {
                        "status": "error",
                        "error": f"HTTP {response.status}: {response.text}",
                    }

                data = await response.json()

                records_processed = 0
                records_added = 0
                records_updated = 0
                records_removed = 0

                if data.get("data"):
                    # Convert to threat intelligence format
                    intelligence = self._convert_to_intelligence(
                        "cipherblade", data["data"], ThreatType.SCAM
                    )

                    if intelligence:
                        # Check if already exists
                        existing = await self.get_intelligence_by_address(
                            intelligence.address
                        )
                        if existing:
                            await self.update_intelligence(intelligence)
                            records_updated += 1
                        else:
                            await self.add_intelligence(intelligence)
                            records_added += 1
                        records_processed = 1

                return {
                    "status": "success",
                    "records_processed": records_processed,
                    "records_added": records_added,
                    "records_updated": records_updated,
                    "records_removed": records_removed,
                }

        except Exception as e:
            logger.error(f"Error syncing CipherBlade feed: {e}")
            return {"status": "error", "error": str(e)}

    async def _sync_generic_feed(
        self, feed: ThreatFeed, api_key: str
    ) -> Dict[str, Any]:
        """Sync generic threat intelligence feed"""

        try:
            # Generic feed sync
            headers = {**feed.headers}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            async with self.http_session.get(
                feed.api_endpoint, headers=headers
            ) as response:
                if response.status != 200:
                    return {
                        "status": "error",
                        "error": f"HTTP {response.status}: {response.text}",
                    }

                data = await response.json()

                records_processed = 0
                records_added = 0
                records_updated = 0
                records_removed = 0

                # Generic processing - would need to be customized per feed
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "address" in item:
                            records_processed += 1

                            intelligence = ThreatIntelligence(
                                id=str(
                                    hashlib.sha256(
                                        f"{feed.id}:{item['address']}"
                                    ).hexdigest()
                                ),
                                feed_source=feed.id,
                                threat_type=ThreatType.SCAM,  # Default
                                threat_level=ThreatLevel.MEDIUM,
                                address=item["address"],
                                entity=item.get("entity"),
                                description=item.get("description"),
                                confidence_score=1.0,
                                raw_data=item,
                            )

                            # Check if already exists
                            existing = await self.get_intelligence_by_address(
                                intelligence.address
                            )
                            if existing:
                                await self.update_intelligence(intelligence)
                                records_updated += 1
                            else:
                                await self.add_intelligence(intelligence)
                                records_added += 1

                return {
                    "status": "success",
                    "records_processed": records_processed,
                    "records_added": records_added,
                    "records_updated": records_updated,
                    "records_removed": records_removed,
                }

        except Exception as e:
            logger.error(f"Error syncing generic feed {feed.id}: {e}")
            return {"status": "error", "error": str(e)}

    def _convert_to_intelligence(
        self, source: str, data: Any, threat_type: ThreatType
    ) -> Optional[ThreatIntelligence]:
        """Convert feed data to threat intelligence format"""

        # This would need to be customized based on the specific feed format
        if not data:
            return None

        # Default conversion - would need to be adapted per feed
        if isinstance(data, dict):
            address = data.get("address")
            if not address:
                return None

            return ThreatIntelligence(
                id=str(hashlib.sha256(f"{source}:{address}").hexdigest()),
                feed_source=source,
                threat_type=threat_type,
                threat_level=ThreatLevel.MEDIUM,
                address=address,
                entity=data.get("entity"),
                description=data.get("description"),
                confidence_score=data.get("confidence", 1.0),
                tags=data.get("tags", []),
                raw_data=data,
            )

        return None

    async def add_intelligence(self, intelligence: ThreatIntelligence) -> str:
        """Add threat intelligence to database"""

        insert_query = """
        INSERT INTO threat_intelligence (
            id, feed_source, threat_type, threat_level, address, entity,
            description, confidence_score, first_seen, last_seen, is_active,
            tags, evidence, raw_data
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        RETURNING id
        """

        conn = await get_postgres_connection()
        try:
            result = await conn.fetchrow(
                insert_query,
                intelligence.id,
                intelligence.feed_source,
                intelligence.threat_type.value,
                intelligence.threat_level.value,
                intelligence.address,
                intelligence.entity,
                intelligence.description,
                intelligence.confidence_score,
                intelligence.first_seen,
                intelligence.last_seen,
                intelligence.is_active,
                intelligence.tags or [],
                json.dumps(intelligence.evidence or []),
                json.dumps(intelligence.raw_data or {}),
            )

            await conn.commit()

            # Update cache
            self.intelligence_cache[intelligence.address] = intelligence

            logger.info(
                f"Added threat intelligence for {intelligence.address} from {intelligence.feed_source}"
            )
            return str(result["id"])

        except Exception as e:
            logger.error(f"Error adding threat intelligence: {e}")
            await conn.rollback()
            raise
        finally:
            await conn.close()

    async def update_intelligence(self, intelligence: ThreatIntelligence) -> bool:
        """Update existing threat intelligence"""

        update_query = """
        UPDATE threat_intelligence
        SET threat_type = $1, threat_level = $2, entity = $3, description = $4,
            confidence_score = $5, last_seen = $6, is_active = $7,
            tags = $8, evidence = $9, raw_data = $10, updated_at = NOW()
        WHERE address = $11
        """

        conn = await get_postgres_connection()
        try:
            result = await conn.execute(
                update_query,
                intelligence.threat_type.value,
                intelligence.threat_level.value,
                intelligence.entity,
                intelligence.description,
                intelligence.confidence_score,
                intelligence.last_seen,
                intelligence.is_active,
                intelligence.tags or [],
                json.dumps(intelligence.evidence or []),
                json.dumps(intelligence.raw_data or {}),
                intelligence.address,
            )

            await conn.commit()

            # Update cache
            self.intelligence_cache[intelligence.address] = intelligence

            success = result == "UPDATE 1"
            if success:
                logger.info(f"Updated threat intelligence for {intelligence.address}")

            return success

        except Exception as e:
            logger.error(f"Error updating threat intelligence: {e}")
            await conn.rollback()
            return False
        finally:
            await conn.close()

    async def get_intelligence_by_address(
        self, address: str
    ) -> Optional[ThreatIntelligence]:
        """Get threat intelligence by address"""

        # Check cache first
        if address in self.intelligence_cache:
            return self.intelligence_cache[address]

        select_query = """
        SELECT id, feed_source, threat_type, threat_level, address, entity,
               description, confidence_score, first_seen, last_seen, is_active,
               tags, evidence, raw_data, created_at, updated_at
        FROM threat_intelligence
        WHERE address = $1
        """

        conn = await get_postgres_connection()
        try:
            result = await conn.fetchrow(select_query, address.lower())

            if result:
                intelligence = ThreatIntelligence(
                    id=result["id"],
                    feed_source=result["feed_source"],
                    threat_type=ThreatType(result["threat_type"]),
                    threat_level=ThreatLevel(result["threat_level"]),
                    address=result["address"],
                    entity=result["entity"],
                    description=result["description"],
                    confidence_score=float(result["confidence_score"]),
                    first_seen=result["first_seen"],
                    last_seen=result["last_seen"],
                    is_active=result["is_active"],
                    tags=result["tags"],
                    evidence=result["evidence"],
                    raw_data=result["raw_data"],
                    created_at=result["created_at"],
                    updated_at=result["updated_at"],
                )

                # Update cache
                self.intelligence_cache[intelligence.address] = intelligence
                return intelligence

            return None

        except Exception as e:
            logger.error(f"Error getting threat intelligence for {address}: {e}")
            return None
        finally:
            await conn.close()

    async def search_intelligence(
        self,
        threat_types: Optional[List[ThreatType]] = None,
        threat_levels: Optional[List[ThreatLevel]] = None,
        addresses: Optional[List[str]] = None,
        entities: Optional[List[str]] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ThreatIntelligence]:
        """Search threat intelligence with filters"""

        # Build WHERE clause
        conditions = []
        params = []
        param_count = 0

        if threat_types:
            placeholders = ",".join([f"${i + 1}" for i in range(len(threat_types))])
            conditions.append(f"threat_type IN ({placeholders})")
            params.extend([t.value for t in threat_types])
            param_count += len(threat_types)

        if threat_levels:
            placeholders = ",".join(
                [f"${i + param_count + 1}" for i in range(len(threat_levels))]
            )
            conditions.append(f"threat_level IN ({placeholders})")
            params.extend([l.value for l in threat_levels])
            param_count += len(threat_levels)

        if addresses:
            placeholders = ",".join(
                [f"${i + param_count + 1}" for i in range(len(addresses))]
            )
            conditions.append(f"address ILIKE ANY ({placeholders})")
            params.extend([addr.lower() for addr in addresses])
            param_count += len(addresses)

        if entities:
            placeholders = ",".join(
                [f"${i + param_count + 1}" for i in range(len(entities))]
            )
            conditions.append(f"entity ILIKE ANY ({placeholders})")
            params.extend([entity.lower() for entity in entities])
            param_count += len(entities)

        if is_active is not None:
            conditions.append(f"is_active = ${param_count + 1}")
            params.append(is_active)
            param_count += 1

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        select_query = f"""
        SELECT id, feed_source, threat_type, threat_level, address, entity,
               description, confidence_score, first_seen, last_seen, is_active,
               tags, evidence, raw_data, created_at, updated_at
        FROM threat_intelligence
        {where_clause}
        ORDER BY last_seen DESC, confidence_score DESC
        LIMIT ${param_count + 1} OFFSET ${param_count + 2}
        """

        params.extend([limit, offset])

        conn = await get_postgres_connection()
        try:
            results = await conn.fetch(select_query, *params)

            intelligence_list = []
            for result in results:
                intelligence = ThreatIntelligence(
                    id=result["id"],
                    feed_source=result["feed_source"],
                    threat_type=ThreatType(result["threat_type"]),
                    threat_level=ThreatLevel(result["threat_level"]),
                    address=result["address"],
                    entity=result["entity"],
                    description=result["description"],
                    confidence_score=float(result["confidence_score"]),
                    first_seen=result["first_seen"],
                    last_seen=result["last_seen"],
                    is_active=result["is_active"],
                    tags=result["tags"],
                    evidence=result["evidence"],
                    raw_data=result["raw_data"],
                    created_at=result["created_at"],
                    updated_at=result["updated_at"],
                )
                intelligence_list.append(intelligence)

            return intelligence_list

        except Exception as e:
            logger.error(f"Error searching threat intelligence: {e}")
            return []
        finally:
            await conn.close()

    async def get_statistics(self) -> Dict[str, Any]:
        """Get threat intelligence statistics"""

        stats_query = """
        SELECT 
            COUNT(*) as total_intelligence,
            COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_intelligence,
            COUNT(DISTINCT feed_source) as active_feeds,
            COUNT(DISTINCT address) as unique_addresses,
            threat_type,
            threat_level,
            AVG(confidence_score) as avg_confidence
        FROM threat_intelligence
        GROUP BY threat_type, threat_level
        """

        conn = await get_postgres_connection()
        try:
            results = await conn.fetch(stats_query)

            total_intelligence = sum(row["total_intelligence"] for row in results)
            active_intelligence = sum(row["active_intelligence"] for row in results)
            unique_addresses = sum(row["unique_addresses"] for row in results)
            active_feeds = sum(row["active_feeds"] for row in results)

            return {
                "total_intelligence": total_intelligence,
                "active_intelligence": active_intelligence,
                "active_feeds": active_feeds,
                "unique_addresses": unique_addresses,
                "breakdown_by_type": [
                    {
                        "threat_type": row["threat_type"],
                        "threat_level": row["threat_level"],
                        "count": row["total_intelligence"],
                        "avg_confidence": float(row["avg_confidence"]),
                    }
                    for row in results
                ],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting threat intelligence statistics: {e}")
            return {}
        finally:
            await conn.close()

    async def _update_feed_sync_time(
        self, feed_id: str, start_time: datetime, status: str, error_message: str = ""
    ):
        """Update feed sync time and log results"""

        sync_duration_ms = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )

        # Update feed in database
        update_query = """
        UPDATE threat_feeds
        SET last_sync = $1, error_count = CASE 
            WHEN $2 = 'error' THEN error_count + 1
            ELSE 0
        END, last_error = CASE 
            WHEN $2 = 'error' THEN $3
            ELSE NULL
        END, updated_at = NOW()
        WHERE feed_id = $4
        """

        # Log sync result
        log_query = """
        INSERT INTO threat_feed_sync_log (
            feed_id, sync_status, records_processed, records_added,
            records_updated, records_removed, sync_duration_ms,
            error_message, sync_timestamp
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """

        conn = await get_postgres_connection()
        try:
            await conn.execute(update_query, start_time, status, error_message, feed_id)
            await conn.execute(
                log_query,
                feed_id,
                status,
                0,
                0,
                0,
                0,
                sync_duration_ms,
                error_message,
                start_time,
            )
            await conn.commit()

            # Update feed in memory
            if feed_id in self.feeds:
                self.feeds[feed_id].last_sync = start_time
                if status == "error":
                    self.feeds[feed_id].error_count += 1
                else:
                    self.feeds[feed_id].error_count = 0

        except Exception as e:
            logger.error(f"Error updating feed sync time for {feed_id}: {e}")
            await conn.rollback()
        finally:
            await conn.close()


# Global threat intelligence manager instance
_threat_intelligence_manager = None


def get_threat_intelligence_manager() -> ThreatIntelligenceManager:
    """Get the global threat intelligence manager instance"""
    global _threat_intelligence_manager
    if _threat_intelligence_manager is None:
        _threat_intelligence_manager = ThreatIntelligenceManager()
    return _threat_intelligence_manager


# Aliases and additional types for API compatibility
ThreatIntelligenceItem = ThreatIntelligence


@dataclass
class FeedStatistics:
    """Aggregate statistics for threat intelligence feeds"""

    total_feeds: int = 0
    active_feeds: int = 0
    feeds_by_status: Dict[str, int] = field(default_factory=dict)
    total_indicators: int = 0
    indicators_by_type: Dict[str, int] = field(default_factory=dict)
    last_sync_date: Optional[datetime] = None


class FeedHealthStatus(str, Enum):
    """Health status of a threat intelligence feed"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    OFFLINE = "offline"
