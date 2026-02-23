"""
Jackdaw Sentry - Cross-Platform Attribution
Unified intelligence from various providers
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

from src.api.database import get_postgres_connection
from src.attribution import get_attribution_engine
from src.intelligence.threat_feeds import get_threat_intelligence_manager
from src.intelligence.victim_reports import get_victim_reports_db

logger = logging.getLogger(__name__)


class AttributionConfidence(str, Enum):
    """Confidence levels for cross-platform attribution"""

    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
    DEFINITIVE = "definitive"


class AttributionSource(str, Enum):
    """Sources for attribution intelligence"""

    VICTIM_REPORTS = "victim_reports"
    THREAT_INTELLIGENCE = "threat_intelligence"
    VASP_REGISTRY = "vasp_registry"
    ON_CHAIN_ANALYSIS = "on_chain_analysis"
    USER_REPORTS = "user_reports"
    EXTERNAL_API = "external_api"
    MANUAL_INVESTIGATION = "manual_investigation"


@dataclass
class CrossPlatformAttribution:
    """Cross-platform attribution result"""

    id: str
    address: str
    blockchain: str
    entity: Optional[str] = None
    entity_type: Optional[str] = None
    confidence: AttributionConfidence = AttributionConfidence.MEDIUM
    sources: List[Dict[str, Any]] = None
    evidence: List[Dict[str, Any]] = None
    risk_score: float = 0.0
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    updated_at: datetime = None


@dataclass
class AttributionConsolidation:
    """Result of consolidating multiple attributions"""

    address: str
    blockchain: str
    attributions: List[CrossPlatformAttribution]
    consolidated_entity: Optional[str] = None
    consolidated_entity_type: Optional[str] = None
    overall_confidence: AttributionConfidence = AttributionConfidence.MEDIUM
    conflicting_sources: List[str] = None
    supporting_sources: List[str] = None
    evidence: List[Dict[str, Any]] = None
    consolidation_score: float = 0.0
    metadata: Dict[str, Any] = None


class CrossPlatformAttributionEngine:
    """Engine for cross-platform attribution consolidation"""

    def __init__(self):
        self.victim_reports_db = get_victim_reports_db()
        self.threat_intelligence_manager = get_threat_intelligence_manager()
        self.attribution_engine = get_attribution_engine()
        self.cache = {}
        self.cache_ttl = 1800  # 30 minutes
        self._initialized = False

        # Source weights for confidence calculation
        self.source_weights = {
            AttributionSource.VICTIM_REPORTS: 0.8,
            AttributionSource.THREAT_INTELLIGENCE: 0.9,
            AttributionSource.VASP_REGISTRY: 0.7,
            AttributionSource.ON_CHAIN_ANALYSIS: 0.6,
            AttributionSource.USER_REPORTS: 0.5,
            AttributionSource.EXTERNAL_API: 0.8,
            AttributionSource.MANUAL_INVESTIGATION: 1.0,
        }

        # Confidence thresholds
        self.confidence_thresholds = {
            AttributionConfidence.VERY_LOW: 0.1,
            AttributionConfidence.LOW: 0.3,
            AttributionConfidence.MEDIUM: 0.5,
            AttributionConfidence.HIGH: 0.7,
            AttributionConfidence.VERY_HIGH: 0.9,
            AttributionConfidence.DEFINITIVE: 0.95,
        }

    async def initialize(self):
        """Initialize the cross-platform attribution engine"""
        if self._initialized:
            return

        logger.info("Initializing Cross-Platform Attribution Engine...")
        await self._create_cross_platform_tables()
        self._initialized = True
        logger.info("Cross-Platform Attribution Engine initialized successfully")

    async def _create_cross_platform_tables(self):
        """Create cross-platform attribution tables"""

        create_attributions_table = """
        CREATE TABLE IF NOT EXISTS cross_platform_attributions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            address VARCHAR(255) NOT NULL,
            blockchain VARCHAR(50) NOT NULL,
            entity VARCHAR(255),
            entity_type VARCHAR(100),
            confidence VARCHAR(20) NOT NULL DEFAULT 'medium',
            sources JSONB NOT NULL DEFAULT '[]',
            evidence JSONB DEFAULT '[]',
            risk_score DECIMAL(5,4) NOT NULL DEFAULT 0.0,
            tags TEXT[] DEFAULT '{}',
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_cross_attributions_address ON cross_platform_attributions(address);
        CREATE INDEX IF NOT EXISTS idx_cross_attributions_blockchain ON cross_platform_attributions(blockchain);
        CREATE INDEX IF NOT EXISTS idx_cross_attributions_entity ON cross_platform_attributions(entity);
        CREATE INDEX IF NOT EXISTS idx_cross_attributions_confidence ON cross_platform_attributions(confidence);
        CREATE INDEX IF NOT EXISTS idx_cross_attributions_created ON cross_platform_attributions(created_at);
        """

        create_consolidations_table = """
        CREATE TABLE IF NOT EXISTS attribution_consolidations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            address VARCHAR(255) NOT NULL,
            blockchain VARCHAR(50) NOT NULL,
            attributions JSONB NOT NULL DEFAULT '[]',
            consolidated_entity VARCHAR(255),
            consolidated_entity_type VARCHAR(100),
            overall_confidence VARCHAR(20) NOT NULL DEFAULT 'medium',
            conflicting_sources TEXT[] DEFAULT '{}',
            supporting_sources TEXT[] DEFAULT '{}',
            evidence JSONB DEFAULT '[]',
            consolidation_score DECIMAL(5,4) NOT NULL DEFAULT 0.0,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_consolidations_address ON attribution_consolidations(address);
        CREATE INDEX IF NOT EXISTS idx_consolidations_blockchain ON attribution_consolidations(blockchain);
        CREATE INDEX IF NOT EXISTS idx_consolidations_entity ON attribution_consolidations(consolidated_entity);
        CREATE INDEX IF NOT EXISTS idx_consolidations_confidence ON attribution_consolidations(overall_confidence);
        """

        create_sources_table = """
        CREATE TABLE IF NOT EXISTS attribution_sources (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_name VARCHAR(100) NOT NULL,
            source_type VARCHAR(50) NOT NULL,
            reliability_score DECIMAL(5,4) NOT NULL DEFAULT 0.5,
            last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_attribution_sources_type ON attribution_sources(source_type);
        CREATE INDEX IF NOT EXISTS idx_attribution_sources_reliability ON attribution_sources(reliability_score);
        """

        conn = await get_postgres_connection()
        try:
            await conn.execute(create_attributions_table)
            await conn.execute(create_consolidations_table)
            await conn.execute(create_sources_table)
            await conn.commit()
            logger.info("Cross-platform attribution tables created/verified")
        except Exception as e:
            logger.error(f"Error creating cross-platform attribution tables: {e}")
            await conn.rollback()
            raise
        finally:
            await conn.close()

    async def get_cross_platform_attribution(
        self,
        address: str,
        blockchain: str,
        include_sources: Optional[List[AttributionSource]] = None,
        min_confidence: Optional[AttributionConfidence] = None,
    ) -> Optional[CrossPlatformAttribution]:
        """
        Get consolidated cross-platform attribution for an address

        Args:
            address: Address to analyze
            blockchain: Blockchain network
            include_sources: Sources to include (all if None)
            min_confidence: Minimum confidence threshold

        Returns:
            Consolidated attribution or None if no attribution found
        """

        # Check cache first
        cache_key = f"{address}:{blockchain}:{min_confidence or 'all'}:{include_sources or 'all'}"
        if cache_key in self.cache:
            cached_result = self.cache[cache_key]
            if (
                datetime.now(timezone.utc) - cached_result["timestamp"]
            ).seconds < self.cache_ttl:
                logger.debug(f"Cache hit for cross-platform attribution: {address}")
                return cached_result["result"]

        logger.info(f"Getting cross-platform attribution for {address} on {blockchain}")

        try:
            # Collect attributions from all sources
            all_attributions = []

            # Get victim reports
            if (
                not include_sources
                or AttributionSource.VICTIM_REPORTS in include_sources
            ):
                victim_attributions = await self._get_victim_report_attributions(
                    address, blockchain
                )
                all_attributions.extend(victim_attributions)

            # Get threat intelligence
            if (
                not include_sources
                or AttributionSource.THREAT_INTELLIGENCE in include_sources
            ):
                threat_attributions = await self._get_threat_intelligence_attributions(
                    address, blockchain
                )
                all_attributions.extend(threat_attributions)

            # Get VASP registry attributions
            if (
                not include_sources
                or AttributionSource.VASP_REGISTRY in include_sources
            ):
                vasp_attributions = await self._get_vasp_registry_attributions(
                    address, blockchain
                )
                all_attributions.extend(vasp_attributions)

            # Get on-chain analysis attributions
            if (
                not include_sources
                or AttributionSource.ON_CHAIN_ANALYSIS in include_sources
            ):
                onchain_attributions = await self._get_onchain_analysis_attributions(
                    address, blockchain
                )
                all_attributions.extend(onchain_attributions)

            if not all_attributions:
                return None

            # Consolidate attributions
            consolidated = self._consolidate_attributions(all_attributions)

            # Apply confidence threshold
            if min_confidence and consolidated.confidence.value < min_confidence.value:
                return None

            # Cache result
            self.cache[cache_key] = {
                "result": consolidated,
                "timestamp": datetime.now(timezone.utc),
            }

            logger.info(
                f"Cross-platform attribution complete for {address}: {consolidated.entity}"
            )
            return consolidated

        except Exception as e:
            logger.error(f"Error getting cross-platform attribution for {address}: {e}")
            return None

    async def _get_victim_report_attributions(
        self, address: str, blockchain: str
    ) -> List[CrossPlatformAttribution]:
        """Get attributions from victim reports database"""

        try:
            # Search for reports involving this address
            reports = await self.victim_reports_db.search_victim_reports(
                victim_address=address, limit=50
            )

            attributions = []
            for report in reports:
                if (
                    report.scammer_address
                    and report.scammer_address.lower() == address.lower()
                ):
                    attribution = CrossPlatformAttribution(
                        id=str(
                            hashlib.sha256(
                                f"victim_reports:{address}:{report.report_id}"
                            ).hexdigest()
                        ),
                        address=address,
                        blockchain=blockchain,
                        entity=report.scammer_entity,
                        entity_type="scammer",
                        confidence=self._calculate_confidence(
                            report.status.value, report.severity.value
                        ),
                        sources=[
                            {
                                "source": AttributionSource.VICTIM_REPORTS.value,
                                "report_id": report.report_id,
                                "report_type": report.report_type.value,
                                "severity": report.severity.value,
                                "platform": report.platform,
                                "amount_lost": report.amount_lost,
                            }
                        ],
                        evidence=report.evidence or [],
                        risk_score=self._calculate_risk_score(
                            report.severity.value, report.amount_lost
                        ),
                        tags=["victim_report", "scam", "fraud"],
                        metadata={
                            "victim_reports": True,
                            "report_date": (
                                report.reported_date.isoformat()
                                if report.reported_date
                                else None
                            ),
                            "incident_date": (
                                report.incident_date.isoformat()
                                if report.incident_date
                                else None
                            ),
                        },
                    )
                    attributions.append(attribution)

            return attributions

        except Exception as e:
            logger.error(f"Error getting victim report attributions: {e}")
            return []

    async def _get_threat_intelligence_attributions(
        self, address: str, blockchain: str
    ) -> List[CrossPlatformAttribution]:
        """Get attributions from threat intelligence feeds"""

        try:
            # Search threat intelligence for this address
            threat_intelligence = (
                await self.threat_intelligence_manager.search_intelligence(
                    addresses=[address]
                )
            )

            attributions = []
            for intel in threat_intelligence:
                if intel.address.lower() == address.lower():
                    attribution = CrossPlatformAttribution(
                        id=str(
                            hashlib.sha256(
                                f"threat_intelligence:{address}:{intel.id}"
                            ).hexdigest()
                        ),
                        address=address,
                        blockchain=blockchain,
                        entity=intel.entity,
                        entity_type="threat_actor",
                        confidence=self._calculate_confidence_from_threat_level(
                            intel.threat_level.value, intel.confidence_score
                        ),
                        sources=[
                            {
                                "source": AttributionSource.THREAT_INTELLIGENCE.value,
                                "feed_source": intel.feed_source,
                                "threat_type": intel.threat_type.value,
                                "threat_level": intel.threat_level.value,
                                "confidence_score": intel.confidence_score,
                            }
                        ],
                        evidence=intel.evidence or [],
                        risk_score=self._calculate_risk_score_from_threat_level(
                            intel.threat_level.value
                        ),
                        tags=["threat_intelligence", intel.threat_type.value],
                        metadata={
                            "threat_intelligence": True,
                            "first_seen": (
                                intel.first_seen.isoformat()
                                if intel.first_seen
                                else None
                            ),
                            "last_seen": (
                                intel.last_seen.isoformat() if intel.last_seen else None
                            ),
                        },
                    )
                    attributions.append(attribution)

            return attributions

        except Exception as e:
            logger.error(f"Error getting threat intelligence attributions: {e}")
            return []

    async def _get_vasp_registry_attributions(
        self, address: str, blockchain: str
    ) -> List[CrossPlatformAttribution]:
        """Get attributions from VASP registry"""

        try:
            # Use attribution engine to get VASP attribution
            result = await self.attribution_engine.attribute_address(
                address=address, blockchain=blockchain, min_confidence=0.3
            )

            attributions = []
            if result.attributions:
                for attribution in result.attributions:
                    vasp_attribution = CrossPlatformAttribution(
                        id=str(
                            hashlib.sha256(
                                f"vasp_registry:{address}:{attribution.id}"
                            ).hexdigest()
                        ),
                        address=address,
                        blockchain=blockchain,
                        entity=attribution.vasp_id,
                        entity_type=(
                            attribution.entity_type.value
                            if attribution.entity_type
                            else "unknown"
                        ),
                        confidence=self._convert_confidence(
                            attribution.confidence_score
                        ),
                        sources=[
                            {
                                "source": AttributionSource.VASP_REGISTRY.value,
                                "attribution_id": attribution.id,
                                "verification_status": attribution.verification_status.value,
                                "confidence_score": attribution.confidence_score,
                            }
                        ],
                        evidence=attribution.evidence or [],
                        risk_score=attribution.risk_score,
                        tags=["vasp_registry", "exchange", "financial"],
                        metadata={
                            "vasp_registry": True,
                            "verification_status": attribution.verification_status.value,
                        },
                    )
                    attributions.append(vasp_attribution)

            return attributions

        except Exception as e:
            logger.error(f"Error getting VASP registry attributions: {e}")
            return []

    async def _get_onchain_analysis_attributions(
        self, address: str, blockchain: str
    ) -> List[CrossPlatformAttribution]:
        """Get attributions from on-chain analysis"""

        try:
            # This would integrate with existing on-chain analysis
            # For now, return empty list as placeholder
            logger.debug(
                f"On-chain analysis attributions not yet implemented for {address}"
            )
            return []

        except Exception as e:
            logger.error(f"Error getting on-chain analysis attributions: {e}")
            return []

    def _consolidate_attributions(
        self, attributions: List[CrossPlatformAttribution]
    ) -> AttributionConsolidation:
        """Consolidate multiple attributions into unified result"""

        if not attributions:
            return AttributionConsolidation(
                address="", blockchain="", attributions=[], consolidation_score=0.0
            )

        address = attributions[0].address
        blockchain = attributions[0].blockchain

        # Group by entity
        entity_groups = defaultdict(list)
        for attribution in attributions:
            entity_key = attribution.entity or "unknown"
            entity_groups[entity_key].append(attribution)

        # Calculate best entity
        best_entity = None
        best_score = 0.0

        for entity, entity_attributions in entity_groups.items():
            score = self._calculate_entity_consensus_score(entity_attributions)
            if score > best_score:
                best_score = score
                best_entity = entity

        # Determine entity type
        entity_type = None
        if best_entity and entity_groups[best_entity]:
            entity_type = entity_groups[best_entity][0].entity_type

        # Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(
            attributions, best_score
        )

        # Identify supporting and conflicting sources
        all_sources = set()
        supporting_sources = []
        conflicting_sources = []

        for attribution in attributions:
            for source_info in attribution.sources:
                source_name = source_info["source"]
                all_sources.add(source_name)

        # Check for conflicts
        entity_entities = set(entity_groups.keys())
        if len(entity_entities) > 1:
            # Multiple entities - mark as conflicting
            conflicting_sources = list(all_sources)
        else:
            # Single entity or no entity - mark as supporting
            supporting_sources = list(all_sources)

        # Collect all evidence
        all_evidence = []
        for attribution in attributions:
            if attribution.evidence:
                all_evidence.extend(attribution.evidence)

        return AttributionConsolidation(
            address=address,
            blockchain=blockchain,
            attributions=attributions,
            consolidated_entity=best_entity,
            consolidated_entity_type=entity_type,
            overall_confidence=overall_confidence,
            conflicting_sources=conflicting_sources,
            supporting_sources=supporting_sources,
            evidence=all_evidence,
            consolidation_score=best_score,
            metadata={
                "entity_count": len(entity_groups),
                "source_count": len(all_sources),
                "has_conflicts": len(conflicting_sources) > 0,
            },
        )

    def _calculate_entity_consensus_score(
        self, entity_attributions: List[CrossPlatformAttribution]
    ) -> float:
        """Calculate consensus score for an entity"""

        if not entity_attributions:
            return 0.0

        # Weight sources by reliability
        weighted_confidence = 0.0
        total_weight = 0.0

        for attribution in entity_attributions:
            for source_info in attribution.sources:
                source_name = source_info["source"]
                weight = self.source_weights.get(AttributionSource(source_name), 0.5)
                confidence = self._confidence_to_numeric(attribution.confidence)

                weighted_confidence += weight * confidence
                total_weight += weight

        if total_weight == 0:
            return 0.0

        return weighted_confidence / total_weight

    def _calculate_overall_confidence(
        self, attributions: List[CrossPlatformAttribution], consensus_score: float
    ) -> AttributionConfidence:
        """Calculate overall confidence from attributions and consensus"""

        if not attributions:
            return AttributionConfidence.VERY_LOW

        # Base confidence from consensus
        base_confidence = consensus_score

        # Boost confidence based on number of sources
        source_count = len(
            set(
                source_info["source"]
                for attribution in attributions
                for source_info in attribution.sources
            )
        )

        source_boost = min(0.2, source_count * 0.05)  # Max 20% boost

        # Boost confidence based on evidence
        evidence_count = sum(
            len(attribution.evidence or []) for attribution in attributions
        )
        evidence_boost = min(0.1, evidence_count * 0.02)  # Max 10% boost

        # Calculate final confidence
        final_confidence = base_confidence + source_boost + evidence_boost

        # Convert to AttributionConfidence enum
        if (
            final_confidence
            >= self.confidence_thresholds[AttributionConfidence.DEFINITIVE]
        ):
            return AttributionConfidence.DEFINITIVE
        elif (
            final_confidence
            >= self.confidence_thresholds[AttributionConfidence.VERY_HIGH]
        ):
            return AttributionConfidence.VERY_HIGH
        elif final_confidence >= self.confidence_thresholds[AttributionConfidence.HIGH]:
            return AttributionConfidence.HIGH
        elif (
            final_confidence >= self.confidence_thresholds[AttributionConfidence.MEDIUM]
        ):
            return AttributionConfidence.MEDIUM
        elif final_confidence >= self.confidence_thresholds[AttributionConfidence.LOW]:
            return AttributionConfidence.LOW
        else:
            return AttributionConfidence.VERY_LOW

    def _calculate_confidence(
        self, status: str, severity: str
    ) -> AttributionConfidence:
        """Calculate confidence from status and severity"""

        # Base confidence from status
        status_confidence = {
            "verified": 0.9,
            "investigating": 0.6,
            "pending": 0.3,
            "false_positive": 0.1,
            "resolved": 0.8,
        }.get(status, 0.5)

        # Adjust based on severity
        severity_adjustment = {
            "severe": 0.1,
            "critical": 0.05,
            "high": 0.0,
            "medium": -0.05,
            "low": -0.1,
        }.get(severity, 0.0)

        final_confidence = status_confidence + severity_adjustment
        final_confidence = max(0.0, min(1.0, final_confidence))

        # Convert to AttributionConfidence enum
        if (
            final_confidence
            >= self.confidence_thresholds[AttributionConfidence.DEFINITIVE]
        ):
            return AttributionConfidence.DEFINITIVE
        elif (
            final_confidence
            >= self.confidence_thresholds[AttributionConfidence.VERY_HIGH]
        ):
            return AttributionConfidence.VERY_HIGH
        elif final_confidence >= self.confidence_thresholds[AttributionConfidence.HIGH]:
            return AttributionConfidence.HIGH
        elif (
            final_confidence >= self.confidence_thresholds[AttributionConfidence.MEDIUM]
        ):
            return AttributionConfidence.MEDIUM
        elif final_confidence >= self.confidence_thresholds[AttributionConfidence.LOW]:
            return AttributionConfidence.LOW
        else:
            return AttributionConfidence.VERY_LOW

    def _calculate_confidence_from_threat_level(
        self, threat_level: str, confidence_score: float
    ) -> AttributionConfidence:
        """Calculate confidence from threat level and confidence score"""

        # Base confidence from threat level
        level_confidence = {
            "severe": 0.9,
            "critical": 0.85,
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4,
        }.get(threat_level, 0.5)

        # Adjust by confidence score
        final_confidence = level_confidence * confidence_score
        final_confidence = max(0.0, min(1.0, final_confidence))

        # Convert to AttributionConfidence enum
        if (
            final_confidence
            >= self.confidence_thresholds[AttributionConfidence.DEFINITIVE]
        ):
            return AttributionConfidence.DEFINITIVE
        elif (
            final_confidence
            >= self.confidence_thresholds[AttributionConfidence.VERY_HIGH]
        ):
            return AttributionConfidence.VERY_HIGH
        elif final_confidence >= self.confidence_thresholds[AttributionConfidence.HIGH]:
            return AttributionConfidence.HIGH
        elif (
            final_confidence >= self.confidence_thresholds[AttributionConfidence.MEDIUM]
        ):
            return AttributionConfidence.MEDIUM
        elif final_confidence >= self.confidence_thresholds[AttributionConfidence.LOW]:
            return AttributionConfidence.LOW
        else:
            return AttributionConfidence.VERY_LOW

    def _convert_confidence(self, confidence_score: float) -> AttributionConfidence:
        """Convert numeric confidence to AttributionConfidence enum"""

        if (
            confidence_score
            >= self.confidence_thresholds[AttributionConfidence.DEFINITIVE]
        ):
            return AttributionConfidence.DEFINITIVE
        elif (
            confidence_score
            >= self.confidence_thresholds[AttributionConfidence.VERY_HIGH]
        ):
            return AttributionConfidence.VERY_HIGH
        elif confidence_score >= self.confidence_thresholds[AttributionConfidence.HIGH]:
            return AttributionConfidence.HIGH
        elif (
            confidence_score >= self.confidence_thresholds[AttributionConfidence.MEDIUM]
        ):
            return AttributionConfidence.MEDIUM
        elif confidence_score >= self.confidence_thresholds[AttributionConfidence.LOW]:
            return AttributionConfidence.LOW
        else:
            return AttributionConfidence.VERY_LOW

    def _confidence_to_numeric(self, confidence: AttributionConfidence) -> float:
        """Convert AttributionConfidence enum to numeric value"""

        return {
            AttributionConfidence.VERY_LOW: 0.1,
            AttributionConfidence.LOW: 0.3,
            AttributionConfidence.MEDIUM: 0.5,
            AttributionConfidence.HIGH: 0.7,
            AttributionConfidence.VERY_HIGH: 0.9,
            AttributionConfidence.DEFINITIVE: 0.95,
        }.get(confidence, 0.5)

    def _calculate_risk_score(
        self, severity: str, amount_lost: Optional[float] = None
    ) -> float:
        """Calculate risk score from severity and amount"""

        # Base risk from severity
        severity_risk = {
            "severe": 0.9,
            "critical": 0.95,
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4,
        }.get(severity, 0.5)

        # Adjust for amount lost
        if amount_lost:
            amount_risk = min(0.9, amount_lost / 100000)  # Normalize to $100k
            return (severity_risk + amount_risk) / 2

        return severity_risk

    def _calculate_risk_score_from_threat_level(self, threat_level: str) -> float:
        """Calculate risk score from threat level"""

        return {
            "severe": 0.9,
            "critical": 0.95,
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4,
        }.get(threat_level, 0.5)

    async def batch_cross_platform_attribution(
        self,
        addresses: List[str],
        blockchain: str,
        include_sources: Optional[List[AttributionSource]] = None,
        min_confidence: Optional[AttributionConfidence] = None,
        max_concurrent: int = 10,
    ) -> Dict[str, Optional[CrossPlatformAttribution]]:
        """Batch cross-platform attribution for multiple addresses"""

        logger.info(f"Batch cross-platform attribution for {len(addresses)} addresses")

        # Process addresses concurrently
        semaphore = asyncio.Semaphore(max_concurrent)

        async def get_single_attribution(
            address: str,
        ) -> Tuple[str, Optional[CrossPlatformAttribution]]:
            async with semaphore:
                try:
                    attribution = await self.get_cross_platform_attribution(
                        address=address,
                        blockchain=blockchain,
                        include_sources=include_sources,
                        min_confidence=min_confidence,
                    )
                    return address, attribution
                except Exception as e:
                    logger.error(f"Error getting attribution for {address}: {e}")
                    return address, None

        # Execute all requests concurrently
        tasks = [get_single_attribution(addr) for addr in addresses]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build results dictionary
        attributions = {}
        for address, attribution in results:
            if isinstance(attribution, Exception):
                logger.error(f"Error in batch attribution for {address}: {attribution}")
                attributions[address] = None
            else:
                attributions[address] = attribution

        return attributions

    async def get_statistics(self) -> Dict[str, Any]:
        """Get cross-platform attribution statistics"""

        try:
            conn = await get_postgres_connection()

            # Get attribution statistics
            stats_query = """
            SELECT 
                COUNT(*) as total_attributions,
                COUNT(DISTINCT address) as unique_addresses,
                COUNT(DISTINCT entity) as unique_entities,
                COUNT(DISTINCT blockchain) as unique_blockchains,
                AVG(risk_score) as avg_risk_score,
                confidence,
                COUNT(*) as count
            FROM cross_platform_attributions
            GROUP BY confidence
            """

            results = await conn.fetch(stats_query)

            total_attributions = sum(row["count"] for row in results)
            unique_addresses = results[0]["unique_addresses"] if results else 0
            unique_entities = results[0]["unique_entities"] if results else 0
            unique_blockchains = results[0]["unique_blockchains"] if results else 0
            avg_risk_score = (
                float(results[0]["avg_risk_score"])
                if results and results[0]["avg_risk_score"]
                else 0.0
            )

            # Get consolidation statistics
            consolidation_query = """
            SELECT 
                COUNT(*) as total_consolidations,
                AVG(consolidation_score) as avg_consolidation_score,
                COUNT(CASE WHEN conflicting_sources IS NOT NULL AND array_length(conflicting_sources) > 0 THEN 1 END) as with_conflicts,
                COUNT(CASE WHEN supporting_sources IS NOT NULL AND array_length(supporting_sources) > 0 THEN 1 END) as with_support
            FROM attribution_consolidations
            """

            consolidation_results = await conn.fetchrow(consolidation_query)

            return {
                "total_attributions": total_attributions,
                "unique_addresses": unique_addresses,
                "unique_entities": unique_entities,
                "unique_blockchains": unique_blockchains,
                "avg_risk_score": avg_risk_score,
                "total_consolidations": (
                    consolidation_results["total_consolidations"]
                    if consolidation_results
                    else 0
                ),
                "avg_consolidation_score": (
                    float(consolidation_results["avg_consolidation_score"])
                    if consolidation_results
                    and consolidation_results["avg_consolidation_score"]
                    else 0.0
                ),
                "with_conflicts": (
                    consolidation_results["with_conflicts"]
                    if consolidation_results
                    else 0
                ),
                "with_support": (
                    consolidation_results["with_support"]
                    if consolidation_results
                    else 0
                ),
                "confidence_distribution": [
                    {"confidence": row["confidence"], "count": row["count"]}
                    for row in results
                ],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting cross-platform attribution statistics: {e}")
            return {}
        finally:
            await conn.close()

    def clear_cache(self):
        """Clear the cross-platform attribution cache"""
        self.cache.clear()
        logger.info("Cross-platform attribution cache cleared")


# Global cross-platform attribution engine instance
_cross_platform_engine = None


def get_cross_platform_engine() -> CrossPlatformAttributionEngine:
    """Get the global cross-platform attribution engine instance"""
    global _cross_platform_engine
    if _cross_platform_engine is None:
        _cross_platform_engine = CrossPlatformAttributionEngine()
    return _cross_platform_engine
