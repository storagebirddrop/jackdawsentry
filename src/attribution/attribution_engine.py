"""
Jackdaw Sentry - Attribution Engine
Core attribution logic with confidence scoring and source tracking
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

import asyncpg

from src.api.database import get_neo4j_session
from src.api.database import get_postgres_connection

from .confidence_scoring import Evidence
from .confidence_scoring import EvidenceType
from .confidence_scoring import get_confidence_scorer
from .models import VASP
from .models import AddressAttribution
from .models import AttributionRequest
from .models import AttributionResult
from .models import AttributionSource
from .models import EntityType
from .models import VerificationStatus
from .vasp_registry import get_vasp_registry

logger = logging.getLogger(__name__)


class AttributionEngine:
    """Core attribution engine with glass box transparency"""

    def __init__(self):
        self.vasp_registry = get_vasp_registry()
        self.confidence_scorer = get_confidence_scorer()
        self.cache = {}
        self.cache_ttl = 1800  # 30 minutes
        self._initialized = False

    async def initialize(self):
        """Initialize the attribution engine"""
        if self._initialized:
            return

        logger.info("Initializing Attribution Engine...")
        await self.vasp_registry.initialize()
        await self._create_attribution_tables()
        self._initialized = True
        logger.info("Attribution Engine initialized successfully")

    def _normalize_address(self, address: str, blockchain: str) -> str:
        """Normalize address based on blockchain case sensitivity"""
        # Case-insensitive chains (EVM-compatible)
        case_insensitive_chains = {
            "ethereum",
            "polygon",
            "bsc",
            "avalanche",
            "fantom",
            "arbitrum",
            "optimism",
            "base",
            "celo",
            "moonbeam",
        }

        if blockchain.lower() in case_insensitive_chains:
            return address.lower()
        else:
            # Case-sensitive chains (Bitcoin, Solana, etc.)
            return address

    async def _create_attribution_tables(self):
        """Create attribution-specific tables"""

        create_attributions_table = """
        CREATE TABLE IF NOT EXISTS address_attributions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            address VARCHAR(255) NOT NULL,
            blockchain VARCHAR(50) NOT NULL,
            vasp_id INTEGER NOT NULL REFERENCES vasp_registry(id),
            confidence_score DECIMAL(5,4) NOT NULL,
            attribution_source_id INTEGER NOT NULL REFERENCES attribution_sources(id),
            verification_status VARCHAR(20) DEFAULT 'pending',
            evidence JSONB DEFAULT '{}',
            corroborating_sources INTEGER[] DEFAULT '{}',
            first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            last_verified TIMESTAMP WITH TIME ZONE,
            notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(address, blockchain, vasp_id, attribution_source_id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_attributions_address ON address_attributions(address);
        CREATE INDEX IF NOT EXISTS idx_attributions_blockchain ON address_attributions(blockchain);
        CREATE INDEX IF NOT EXISTS idx_attributions_vasp ON address_attributions(vasp_id);
        CREATE INDEX IF NOT EXISTS idx_attributions_confidence ON address_attributions(confidence_score);
        CREATE INDEX IF NOT EXISTS idx_attributions_status ON address_attributions(verification_status);
        CREATE INDEX IF NOT EXISTS idx_attributions_last_verified ON address_attributions(last_verified);
        """

        create_evidence_table = """
        CREATE TABLE IF NOT EXISTS attribution_evidence (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            attribution_id UUID NOT NULL REFERENCES address_attributions(id),
            evidence_type VARCHAR(50) NOT NULL,
            description TEXT NOT NULL,
            confidence_contribution DECIMAL(5,4) NOT NULL,
            source_reference VARCHAR(255),
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_evidence_attribution ON attribution_evidence(attribution_id);
        CREATE INDEX IF NOT EXISTS idx_evidence_type ON attribution_evidence(evidence_type);
        """

        conn = await get_postgres_connection()
        try:
            await conn.execute(create_attributions_table)
            await conn.execute(create_evidence_table)
            await conn.commit()
            logger.info("Attribution tables created/verified")
        except Exception as e:
            logger.error(f"Error creating attribution tables: {e}")
            await conn.rollback()
            raise
        finally:
            await conn.close()

    async def attribute_address(
        self,
        address: str,
        blockchain: str,
        include_evidence: bool = True,
        min_confidence: float = 0.5,
    ) -> AttributionResult:
        """Attribute single address with full confidence scoring"""

        self.metrics["last_update"] = datetime.now(timezone.utc)

        address = self._normalize_address(address, blockchain)

        start_time = datetime.now(timezone.utc)

        # Check cache first
        cache_key = f"{address}:{blockchain}:{min_confidence}"
        if cache_key in self.cache:
            cached_result = self.cache[cache_key]
            if (
                datetime.now(timezone.utc) - cached_result["timestamp"]
            ).total_seconds() < self.cache_ttl:
                logger.debug(f"Cache hit for attribution: {address}")
                return cached_result["result"]

        logger.info(f"Attributing address: {address} on {blockchain}")

        try:
            # Step 1: Find exact matches in database
            exact_matches = await self._find_exact_matches(address, blockchain)

            # Step 2: Check cluster relationships
            cluster_matches = await self._find_cluster_attributions(address, blockchain)

            # Step 3: Analyze on-chain patterns
            pattern_matches = await self._analyze_on_chain_patterns(address, blockchain)

            # Step 4: Consolidate and score
            consolidated = await self._consolidate_attributions(
                exact_matches, cluster_matches, pattern_matches
            )

            # Step 5: Filter by minimum confidence
            filtered_attributions = [
                attr
                for attr in consolidated.attributions
                if attr.confidence_score >= min_confidence
            ]

            # Step 6: Get sources if requested
            sources = []
            if include_evidence and filtered_attributions:
                source_ids = list(
                    set(attr.attribution_source_id for attr in filtered_attributions)
                )
                sources = await self._get_attribution_sources(source_ids)

            processing_time = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000

            result = AttributionResult(
                address=address,
                blockchain=blockchain,
                attributions=filtered_attributions,
                confidence_score=consolidated.confidence_score,
                sources=sources,
                evidence=consolidated.evidence,
                analysis_timestamp=datetime.now(timezone.utc),
                processing_time_ms=processing_time,
            )

            # Cache result
            self.cache[cache_key] = {
                "result": result,
                "timestamp": datetime.now(timezone.utc),
            }

            logger.info(
                f"Attribution complete for {address}: {len(filtered_attributions)} attributions"
            )
            return result

        except Exception as e:
            logger.error(f"Error attributing address {address}: {e}")
            processing_time = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000

            return AttributionResult(
                address=address,
                blockchain=blockchain,
                attributions=[],
                confidence_score=0.0,
                sources=[],
                evidence={"error": str(e)},
                analysis_timestamp=datetime.now(timezone.utc),
                processing_time_ms=processing_time,
            )

    async def batch_attribute_addresses(
        self, request: AttributionRequest
    ) -> Dict[str, AttributionResult]:
        """Attribute multiple addresses efficiently"""

        logger.info(f"Batch attributing {len(request.addresses)} addresses")

        # Process addresses concurrently
        tasks = []
        for address in request.addresses:
            task = self.attribute_address(
                address=address,
                blockchain=request.blockchain,
                include_evidence=request.include_evidence,
                min_confidence=request.min_confidence,
            )
            tasks.append(task)

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build results dictionary
        attribution_results = {}
        failed_addresses = []

        for i, result in enumerate(results):
            address = request.addresses[i]

            if isinstance(result, Exception):
                logger.error(f"Error attributing {address}: {result}")
                failed_addresses.append(address)
            else:
                attribution_results[address] = result

        logger.info(
            f"Batch attribution complete: {len(attribution_results)} successful, {len(failed_addresses)} failed"
        )

        return attribution_results

    async def _find_exact_matches(
        self, address: str, blockchain: str
    ) -> List[AddressAttribution]:
        """Find exact address matches in database"""

        query = """
        SELECT id, address, blockchain, vasp_id, confidence_score, attribution_source_id,
               verification_status, evidence, corroborating_sources, first_seen, last_verified, notes
        FROM address_attributions
        WHERE address = $1 AND blockchain = $2
        ORDER BY confidence_score DESC
        """

        conn = await get_postgres_connection()
        try:
            rows = await conn.fetch(query, address.lower(), blockchain)

            attributions = []
            for row in rows:
                attribution = AddressAttribution(
                    id=row["id"],
                    address=row["address"],
                    blockchain=row["blockchain"],
                    vasp_id=row["vasp_id"],
                    confidence_score=float(row["confidence_score"]),
                    attribution_source_id=row["attribution_source_id"],
                    verification_status=VerificationStatus(row["verification_status"]),
                    evidence=row["evidence"],
                    corroborating_sources=row["corroborating_sources"],
                    first_seen=row["first_seen"],
                    last_verified=row["last_verified"],
                    notes=row["notes"],
                )
                attributions.append(attribution)

            return attributions

        except Exception as e:
            logger.error(f"Error finding exact matches: {e}")
            return []
        finally:
            await conn.close()

    async def _find_cluster_attributions(
        self, address: str, blockchain: str
    ) -> List[AddressAttribution]:
        """Find attributions through cluster relationships"""

        # This would use Neo4j to find connected addresses in the same cluster
        # For now, return empty list as placeholder
        logger.debug(f"Cluster attribution not yet implemented for {address}")
        return []

    async def _analyze_on_chain_patterns(
        self, address: str, blockchain: str
    ) -> List[AddressAttribution]:
        """Analyze on-chain patterns for attribution clues"""

        # This would analyze transaction patterns, timing, amounts, etc.
        # For now, return empty list as placeholder
        logger.debug(f"On-chain pattern analysis not yet implemented for {address}")
        return []

    async def _consolidate_attributions(
        self,
        exact_matches: List[AddressAttribution],
        cluster_matches: List[AddressAttribution],
        pattern_matches: List[AddressAttribution],
    ) -> "ConsolidatedAttribution":
        """Consolidate attributions from multiple sources"""

        all_attributions = exact_matches + cluster_matches + pattern_matches

        if not all_attributions:
            return ConsolidatedAttribution(
                attributions=[], confidence_score=0.0, evidence={}
            )

        # Group by VASP to avoid duplicates
        vasp_attributions = {}
        for attr in all_attributions:
            if attr.vasp_id not in vasp_attributions:
                vasp_attributions[attr.vasp_id] = []
            vasp_attributions[attr.vasp_id].append(attr)

        # Consolidate each VASP's attributions
        consolidated_attributions = []
        for vasp_id, attrs in vasp_attributions.items():
            # Take the highest confidence attribution as primary
            primary_attr = max(attrs, key=lambda x: x.confidence_score)

            # Merge corroborating sources
            all_sources = set()
            all_evidence = {}

            for attr in attrs:
                all_sources.add(attr.attribution_source_id)
                if attr.evidence:
                    all_evidence.update(attr.evidence)

            # Update consolidated attribution
            primary_attr.corroborating_sources = list(
                all_sources - {primary_attr.attribution_source_id}
            )
            primary_attr.evidence = all_evidence

            # Recalculate confidence if we have multiple sources
            if len(attrs) > 1:
                # This would use the confidence scorer to recalculate
                # For now, slightly boost confidence for corroboration
                primary_attr.confidence_score = min(
                    1.0, primary_attr.confidence_score * 1.1
                )

            consolidated_attributions.append(primary_attr)

        # Calculate overall confidence score
        overall_confidence = (
            max(attr.confidence_score for attr in consolidated_attributions)
            if consolidated_attributions
            else 0.0
        )

        # Merge all evidence
        all_evidence = {}
        for attr in consolidated_attributions:
            if attr.evidence:
                all_evidence.update(attr.evidence)

        return ConsolidatedAttribution(
            attributions=consolidated_attributions,
            confidence_score=overall_confidence,
            evidence=all_evidence,
        )

    async def _get_attribution_sources(
        self, source_ids: List[int]
    ) -> List[AttributionSource]:
        """Get attribution sources by IDs"""

        if not source_ids:
            return []

        placeholders = ",".join(f"${i+1}" for i in range(len(source_ids)))
        query = f"""
        SELECT id, name, source_type, reliability_score, description, url,
               api_endpoint, authentication_required, rate_limit_per_hour, last_updated
        FROM attribution_sources
        WHERE id IN ({placeholders})
        ORDER BY reliability_score DESC
        """

        conn = await get_postgres_connection()
        try:
            rows = await conn.fetch(query, *source_ids)

            sources = []
            for row in rows:
                source = AttributionSource(
                    id=row["id"],
                    name=row["name"],
                    source_type=row["source_type"],
                    reliability_score=float(row["reliability_score"]),
                    description=row["description"],
                    url=row["url"],
                    api_endpoint=row["api_endpoint"],
                    authentication_required=row["authentication_required"],
                    rate_limit_per_hour=row["rate_limit_per_hour"],
                    last_updated=row["last_updated"],
                )
                sources.append(source)

            return sources

        except Exception as e:
            logger.error(f"Error getting attribution sources: {e}")
            return []
        finally:
            await conn.close()

    async def add_attribution(
        self, attribution: AddressAttribution, evidence: List[Evidence] = None
    ) -> AddressAttribution:
        """Add a new attribution with evidence"""

        insert_query = """
        INSERT INTO address_attributions (
            address, blockchain, vasp_id, confidence_score, attribution_source_id,
            verification_status, evidence, corroborating_sources, notes
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id, created_at, updated_at
        """

        conn = await get_postgres_connection()
        try:
            # Insert attribution
            result = await conn.fetchrow(
                insert_query,
                attribution.address.lower(),  # Normalize to lowercase
                attribution.blockchain,
                attribution.vasp_id,
                attribution.confidence_score,
                attribution.attribution_source_id,
                attribution.verification_status.value,
                json.dumps(attribution.evidence),
                attribution.corroborating_sources,
                attribution.notes,
            )

            attribution.id = result["id"]
            attribution.created_at = result["created_at"]
            attribution.updated_at = result["updated_at"]

            # Insert evidence if provided
            if evidence:
                await self._add_evidence(attribution.id, evidence, conn)

            await conn.commit()
            logger.info(f"Added attribution for {attribution.address}")

            # Clear cache for this address (all confidence levels)
            keys_to_remove = []
            normalized_address = self._normalize_address(
                attribution.address, attribution.blockchain
            )
            prefix = f"{normalized_address}:{attribution.blockchain}:"
            for cache_key in self.cache:
                if cache_key.startswith(prefix):
                    keys_to_remove.append(cache_key)

            for key in keys_to_remove:
                del self.cache[key]

            return attribution

        except Exception as e:
            logger.error(f"Error adding attribution: {e}")
            await conn.rollback()
            raise
        finally:
            await conn.close()

    async def _add_evidence(
        self,
        attribution_id: uuid.UUID,
        evidence: List[Evidence],
        conn: Optional[asyncpg.Connection] = None,
    ):
        """Add evidence for attribution"""

        insert_evidence_query = """
        INSERT INTO attribution_evidence (
            attribution_id, evidence_type, description, confidence_contribution,
            source_reference, metadata
        ) VALUES ($1, $2, $3, $4, $5, $6)
        """

        # Use provided connection or create a new one
        should_close = False
        if conn is None:
            conn = await get_postgres_connection()
            should_close = True

        try:
            for ev in evidence:
                await conn.execute(
                    insert_evidence_query,
                    attribution_id,
                    ev.evidence_type.value,
                    ev.description,
                    ev.confidence_contribution,
                    ev.source_reference,
                    json.dumps(ev.metadata),
                )
        except Exception as e:
            logger.error(f"Error adding evidence: {e}")
            raise
        finally:
            if should_close:
                await conn.close()


class ConsolidatedAttribution:
    """Helper class for consolidated attribution results"""

    def __init__(
        self,
        attributions: List[AddressAttribution],
        confidence_score: float,
        evidence: Dict[str, Any],
    ):
        self.attributions = attributions
        self.confidence_score = confidence_score
        self.evidence = evidence


# Global attribution engine instance
_attribution_engine = None


def get_attribution_engine() -> AttributionEngine:
    """Get the global attribution engine instance"""
    global _attribution_engine
    if _attribution_engine is None:
        _attribution_engine = AttributionEngine()
    return _attribution_engine
