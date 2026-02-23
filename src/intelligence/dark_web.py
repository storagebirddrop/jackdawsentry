"""
Jackdaw Sentry - Dark Web Monitoring and Threat Intelligence
Dark web monitoring, threat intelligence aggregation, and analysis
"""

import asyncio
import hashlib
import json
import logging
import re
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
from typing import Tuple
from urllib.parse import urlparse

from src.api.config import settings
from src.api.database import get_neo4j_session
from src.api.database import get_redis_connection

logger = logging.getLogger(__name__)


class ThreatType(Enum):
    """Threat intelligence types"""

    HACKING_GROUP = "hacking_group"
    RANSOMWARE = "ransomware"
    PHISHING = "phishing"
    MALWARE = "malware"
    BOTNET = "botnet"
    MONEY_LAUNDERING = "money_laundering"
    TERRORISM_FINANCING = "terrorism_financing"
    DARKNET_MARKET = "darknet_market"
    CARDING = "carding"
    CRYPTOCURRENCY_FRAUD = "cryptocurrency_fraud"
    INSIDER_TRADING = "insider_trading"
    PII_THEFT = "pii_theft"
    IDENTITY_THEFT = "identity_theft"
    CYBER_ESPIONAGE = "cyber_espionage"
    DDOS_ATTACK = "ddos_attack"
    DATA_BREACH = "data_breach"
    SOCIAL_ENGINEERING = "social_engineering"
    ADVANCED_PERSISTENT_THREAT = "advanced_persistent_threat"


class DarkWebPlatform(Enum):
    """Dark web platforms"""

    TOR = "tor"
    I2P = "i2p"
    FREEDOM = "freedom"
    ZERONET = "zeronet"
    GNUNET = "gnunet"
    LOKI = "loki"
    YGGDRASIL = "yggdrasil"
    UNKNOWN = "unknown"


class ThreatSeverity(Enum):
    """Threat severity levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ThreatIndicator:
    """Threat intelligence indicator"""

    indicator_id: str
    indicator_type: str  # ip, domain, email, address, hash, etc.
    value: str
    threat_type: ThreatType
    severity: ThreatSeverity
    confidence: float
    source: str
    description: str
    first_seen: datetime
    last_seen: datetime
    tags: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    related_indicators: List[str] = field(default_factory=list)
    platform: DarkWebPlatform = DarkWebPlatform.UNKNOWN
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DarkWebActivity:
    """Dark web activity record"""

    activity_id: str
    platform: DarkWebPlatform
    activity_type: str
    threat_type: ThreatType
    severity: ThreatSeverity
    description: str
    source_url: str
    onion_address: Optional[str] = None
    indicators: List[ThreatIndicator] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThreatIntelligenceReport:
    """Threat intelligence report"""

    report_id: str
    title: str
    threat_type: ThreatType
    severity: ThreatSeverity
    confidence: float
    sources: List[str]
    indicators: List[ThreatIndicator]
    activities: List[DarkWebActivity]
    summary: str
    detailed_analysis: str
    recommendations: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DarkWebMonitor:
    """Dark web monitoring and threat intelligence system"""

    def __init__(self):
        self.indicators = {}  # threat indicators
        self.activities = {}  # dark web activities
        self.reports = {}  # threat intelligence reports
        self.platforms = {}  # platform configurations

        # Monitoring configuration
        self.monitoring_enabled = True
        self.confidence_threshold = 0.6
        self.max_indicators_per_type = 10000
        self.cache_ttl = 3600  # 1 hour

        # Initialize platform configurations
        self._initialize_platforms()

        # Initialize sample threat data
        self._initialize_sample_data()

    def _initialize_platforms(self):
        """Initialize dark web platform configurations"""
        self.platforms = {
            DarkWebPlatform.TOR: {
                "name": "Tor Network",
                "domains": [".onion"],
                "ports": [80, 443, 8080, 9001, 9002, 9003],
                "protocols": ["http", "https"],
                "description": "The Onion Router - anonymous communication network",
            },
            DarkWebPlatform.I2P: {
                "name": "I2P Network",
                "domains": [".i2p"],
                "ports": [80, 443, 8080],
                "protocols": ["http", "https"],
                "description": "Invisible Internet Project - anonymous network layer",
            },
            DarkWebPlatform.FREEDOM: {
                "name": "Freedom Network",
                "domains": [".freedom"],
                "ports": [80, 443],
                "protocols": ["http", "https"],
                "description": "Freedom Hosting - anonymous hosting service",
            },
            DarkWebPlatform.ZERONET: {
                "name": "ZeroNet",
                "domains": [".bit"],
                "ports": [80, 443],
                "protocols": ["http", "https"],
                "description": "ZeroNet - decentralized peer-to-peer network",
            },
        }

    def _initialize_sample_data(self):
        """Initialize with sample threat intelligence data"""
        # Sample threat indicators
        sample_indicators = [
            {
                "indicator_id": "THREAT-001",
                "indicator_type": "domain",
                "value": "malicious-marketplace.onion",
                "threat_type": ThreatType.DARKNET_MARKET,
                "severity": ThreatSeverity.HIGH,
                "confidence": 0.9,
                "source": "dark_web_monitor",
                "description": "Known darknet marketplace for illegal goods",
                "tags": ["marketplace", "illicit_goods", "cryptocurrency"],
                "platform": DarkWebPlatform.TOR,
            },
            {
                "indicator_id": "THREAT-002",
                "indicator_type": "address",
                "value": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                "threat_type": ThreatType.CRYPTOCURRENCY_FRAUD,
                "severity": ThreatSeverity.MEDIUM,
                "confidence": 0.7,
                "source": "blockchain_analysis",
                "description": "Bitcoin address associated with fraudulent activities",
                "tags": ["bitcoin", "fraud", "suspicious"],
                "platform": DarkWebPlatform.TOR,
            },
            {
                "indicator_id": "THREAT-003",
                "indicator_type": "email",
                "value": "hacker@darkweb.onion",
                "threat_type": ThreatType.PHISHING,
                "severity": ThreatSeverity.HIGH,
                "confidence": 0.8,
                "source": "phishing_monitor",
                "description": "Email address used in phishing campaigns",
                "tags": ["phishing", "email", "credentials"],
                "platform": DarkWebPlatform.TOR,
            },
            {
                "indicator_id": "THREAT-004",
                "indicator_type": "ip",
                "value": "192.168.1.100",
                "threat_type": ThreatType.BOTNET,
                "severity": ThreatSeverity.HIGH,
                "confidence": 0.85,
                "source": "network_monitoring",
                "description": "IP address hosting botnet C&C server",
                "tags": ["botnet", "c2", "malware"],
                "platform": DarkWebPlatform.UNKNOWN,
            },
        ]

        # Load sample indicators
        for indicator_data in sample_indicators:
            indicator = ThreatIndicator(**indicator_data)
            self._add_indicator(indicator)

        # Sample dark web activities
        sample_activities = [
            {
                "activity_id": "ACTIVITY-001",
                "platform": DarkWebPlatform.TOR,
                "activity_type": "marketplace_listing",
                "threat_type": ThreatType.DARKNET_MARKET,
                "severity": ThreatSeverity.HIGH,
                "description": "New listing for stolen credit cards on darknet marketplace",
                "source_url": "http://malicious-marketplace.onion/listings/123",
                "onion_address": "malicious-marketplace.onion",
                "tags": ["marketplace", "credit_cards", "stolen_data"],
                "confidence": 0.9,
            },
            {
                "activity_id": "ACTIVITY-002",
                "platform": DarkWebPlatform.TOR,
                "activity_type": "ransomware_payment",
                "threat_type": ThreatType.RANSOMWARE,
                "severity": ThreatSeverity.CRITICAL,
                "description": "Ransomware payment processing activity detected",
                "source_url": "http://ransomware-gang.onion/payments",
                "onion_address": "ransomware-gang.onion",
                "tags": ["ransomware", "payment", "bitcoin"],
                "confidence": 0.95,
            },
        ]

        # Load sample activities
        for activity_data in sample_activities:
            activity = DarkWebActivity(**activity_data)
            self._add_activity(activity)

    def _add_indicator(self, indicator: ThreatIndicator):
        """Add threat indicator to collection"""
        self.indicators[indicator.indicator_id] = indicator

        # Add to type-specific index
        indicator_type = indicator.indicator_type
        if indicator_type not in self.indicators:
            self.indicators[indicator_type] = []
        self.indicators[indicator_type].append(indicator)

    def _add_activity(self, activity: DarkWebActivity):
        """Add dark web activity to collection"""
        self.activities[activity.activity_id] = activity

    async def check_indicator(
        self, indicator_value: str, indicator_type: str
    ) -> List[ThreatIndicator]:
        """Check if value matches any threat indicators"""
        try:
            matches = []

            # Check exact matches
            if indicator_type in self.indicators:
                for indicator in self.indicators[indicator_type]:
                    if indicator.value.lower() == indicator_value.lower():
                        matches.append(indicator)

            # Check partial matches for certain types
            if indicator_type in ["domain", "address", "email"]:
                for indicator in self.indicators.get(indicator_type, []):
                    if self._partial_match(indicator_value, indicator.value):
                        # Create a partial match with lower confidence
                        partial_indicator = ThreatIndicator(
                            indicator_id=indicator.indicator_id,
                            indicator_type=indicator.indicator_type,
                            value=indicator.value,
                            threat_type=indicator.threat_type,
                            severity=indicator.severity,
                            confidence=indicator.confidence
                            * 0.7,  # Lower confidence for partial match
                            source=indicator.source,
                            description=f"Partial match: {indicator.description}",
                            first_seen=indicator.first_seen,
                            last_seen=indicator.last_seen,
                            tags=indicator.tags + ["partial_match"],
                            context=indicator.context,
                            platform=indicator.platform,
                            metadata={"original_value": indicator_value},
                        )
                        matches.append(partial_indicator)

            return matches

        except Exception as e:
            logger.error(f"Error checking indicator {indicator_value}: {e}")
            return []

    def _partial_match(self, value1: str, value2: str) -> bool:
        """Check if two values partially match"""
        if not value1 or not value2:
            return False

        # Remove common prefixes/suffixes
        value1_clean = re.sub(r"^(www\.|http://|https://)", "", value1.lower())
        value2_clean = re.sub(r"^(www\.|http://|https://)", "", value2.lower())

        # Check if one is substring of the other
        if value1_clean in value2_clean or value2_clean in value1_clean:
            return True

        # Check for similar patterns (simplified)
        if len(value1_clean) > 3 and len(value2_clean) > 3:
            # Check if they share a significant substring
            for i in range(min(len(value1_clean), len(value2_clean)) - 2):
                substring = value1_clean[i : i + 4]  # 4-character substrings
                if substring in value2_clean:
                    return True

        return False

    async def check_address(
        self, address: str, blockchain: str = None
    ) -> Dict[str, Any]:
        """Check address against threat intelligence"""
        try:
            # Check against address indicators
            address_matches = await self.check_indicator(address, "address")

            # Check against domain indicators (in case address looks like domain)
            domain_matches = await self.check_indicator(address, "domain")

            # Combine matches
            all_matches = address_matches + domain_matches

            # Calculate overall risk score
            overall_risk_score = 0.0
            if all_matches:
                overall_risk_score = max(match.confidence for match in all_matches)

            # Determine risk level
            if overall_risk_score >= 0.9:
                risk_level = "critical"
            elif overall_risk_score >= 0.7:
                risk_level = "high"
            elif overall_risk_score >= 0.5:
                risk_level = "medium"
            elif overall_risk_score >= 0.3:
                risk_level = "low"
            else:
                risk_level = "info"

            # Generate recommendations
            recommendations = []
            if all_matches:
                recommendations.append("Address flagged in threat intelligence")
                if risk_level in ["critical", "high"]:
                    recommendations.append("Enhanced monitoring required")
                    recommendations.append("Consider blocking or flagging")
                    recommendations.append("Investigate related transactions")

                # Specific recommendations based on threat types
                threat_types = set(match.threat_type for match in all_matches)
                if ThreatType.RANSOMWARE in threat_types:
                    recommendations.append("Ransomware-related - highest priority")
                elif ThreatType.MONEY_LAUNDERING in threat_types:
                    recommendations.append("Money laundering - high priority")
                elif ThreatType.TERRORISM_FINANCING in threat_types:
                    recommendations.append("Terrorism financing - highest priority")
            else:
                recommendations.append("No threat intelligence matches found")

            return {
                "address": address,
                "blockchain": blockchain or "unknown",
                "check_timestamp": datetime.now(timezone.utc).isoformat(),
                "matches": len(all_matches),
                "address_matches": len(address_matches),
                "domain_matches": len(domain_matches),
                "overall_risk_score": overall_risk_score,
                "risk_level": risk_level,
                "matched_indicators": [match.__dict__ for match in all_matches],
                "recommendations": recommendations,
                "threat_types": list(
                    set(match.threat_type.value for match in all_matches)
                ),
                "platforms": list(set(match.platform.value for match in all_matches)),
            }

        except Exception as e:
            logger.error(f"Error checking address {address}: {e}")
            return {
                "error": str(e),
                "check_timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def check_transaction(
        self, from_address: str, to_address: str, blockchain: str, amount: float = 0.0
    ) -> Dict[str, Any]:
        """Check transaction against threat intelligence"""
        try:
            # Check both addresses
            from_check = await self.check_address(from_address, blockchain)
            to_check = await self.check_address(to_address, blockchain)

            # Combine results
            total_matches = from_check["matches"] + to_check["matches"]
            overall_risk_score = max(
                from_check["overall_risk_score"], to_check["overall_risk_score"]
            )

            # Determine overall risk level
            if overall_risk_score >= 0.9:
                risk_level = "critical"
            elif overall_risk_score >= 0.7:
                risk_level = "high"
            elif overall_risk_score >= 0.5:
                risk_level = "medium"
            else:
                risk_level = "low"

            # Generate transaction-specific recommendations
            recommendations = []
            if total_matches > 0:
                recommendations.append("Transaction involves flagged address")
                if risk_level in ["critical", "high"]:
                    recommendations.append("Enhanced monitoring required")
                    recommendations.append("Consider transaction blocking")
                    recommendations.append("Investigate transaction pattern")

            # Add amount-based recommendations
            if amount > 10000:  # High value threshold
                recommendations.append(
                    "High-value transaction - additional verification"
                )

            # Check for suspicious patterns
            threat_types = set(
                from_check.get("threat_types", []) + to_check.get("threat_types", [])
            )
            if ThreatType.MONEY_LAUNDERING in threat_types:
                recommendations.append("Potential money laundering detected")
            elif ThreatType.RANSOMWARE in threat_types:
                recommendations.append("Potential ransomware payment")
            elif ThreatType.DARKNET_MARKET in threat_types:
                recommendations.append("Darknet marketplace activity detected")

            return {
                "from_address": from_address,
                "to_address": to_address,
                "blockchain": blockchain,
                "amount": amount,
                "check_timestamp": datetime.now(timezone.utc).isoformat(),
                "from_address_threats": {
                    "matches": from_check["matches"],
                    "risk_score": from_check["overall_risk_score"],
                    "risk_level": from_check["risk_level"],
                    "threat_types": from_check.get("threat_types", []),
                },
                "to_address_threats": {
                    "matches": to_check["matches"],
                    "risk_score": to_check["overall_risk_score"],
                    "risk_level": to_check["risk_level"],
                    "threat_types": to_check.get("threat_types", []),
                },
                "overall_risk_score": overall_risk_score,
                "risk_level": risk_level,
                "total_matches": total_matches,
                "recommendations": recommendations,
                "threat_types": list(threat_types),
                "platforms": list(
                    set(from_check.get("platforms", []) + to_check.get("platforms", []))
                ),
            }

        except Exception as e:
            logger.error(f"Error checking transaction: {e}")
            return {
                "error": str(e),
                "check_timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def add_threat_indicator(
        self, indicator_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add new threat intelligence indicator"""
        try:
            # Validate required fields
            required_fields = [
                "indicator_id",
                "indicator_type",
                "value",
                "threat_type",
                "severity",
                "confidence",
                "source",
                "description",
            ]
            for field in required_fields:
                if field not in indicator_data:
                    return {"error": f"Missing required field: {field}"}

            # Convert enum fields
            indicator_data["threat_type"] = ThreatType(indicator_data["threat_type"])
            indicator_data["severity"] = ThreatSeverity(indicator_data["severity"])

            if "platform" in indicator_data:
                indicator_data["platform"] = DarkWebPlatform(indicator_data["platform"])

            if "first_seen" in indicator_data and indicator_data["first_seen"]:
                indicator_data["first_seen"] = datetime.fromisoformat(
                    indicator_data["first_seen"]
                )

            if "last_seen" in indicator_data and indicator_data["last_seen"]:
                indicator_data["last_seen"] = datetime.fromisoformat(
                    indicator_data["last_seen"]
                )

            # Create indicator
            indicator = ThreatIndicator(**indicator_data)

            # Add to collection
            self._add_indicator(indicator)

            # Cache update
            await self.cache_threat_data()

            return {
                "indicator_id": indicator.indicator_id,
                "status": "added",
                "added_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error adding threat indicator: {e}")
            return {"error": str(e)}

    async def add_dark_web_activity(
        self, activity_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add dark web activity record"""
        try:
            # Validate required fields
            required_fields = [
                "activity_id",
                "platform",
                "activity_type",
                "threat_type",
                "severity",
                "description",
                "source_url",
            ]
            for field in required_fields:
                if field not in activity_data:
                    return {"error": f"Missing required field: {field}"}

            # Convert enum fields
            activity_data["platform"] = DarkWebPlatform(activity_data["platform"])
            activity_data["threat_type"] = ThreatType(activity_data["threat_type"])
            activity_data["severity"] = ThreatSeverity(activity_data["severity"])

            if "timestamp" in activity_data and activity_data["timestamp"]:
                activity_data["timestamp"] = datetime.fromisoformat(
                    activity_data["timestamp"]
                )

            # Create activity
            activity = DarkWebActivity(**activity_data)

            # Add to collection
            self._add_activity(activity)

            # Cache update
            await self.cache_threat_data()

            return {
                "activity_id": activity.activity_id,
                "status": "added",
                "added_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error adding dark web activity: {e}")
            return {"error": str(e)}

    async def get_threat_statistics(self) -> Dict[str, Any]:
        """Get threat intelligence statistics"""
        try:
            stats = {
                "total_indicators": len(self.indicators),
                "total_activities": len(self.activities),
                "indicator_types": {},
                "threat_types": {},
                "severity_distribution": {},
                "platform_distribution": {},
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            # Indicator type breakdown
            for indicator_type, indicators in self.indicators.items():
                if isinstance(indicators, list):
                    stats["indicator_types"][indicator_type] = len(indicators)

            # Threat type breakdown
            threat_type_counts = {}
            for indicator in self.indicators.values():
                if isinstance(indicator, ThreatIndicator):
                    threat_type = indicator.threat_type.value
                    threat_type_counts[threat_type] = (
                        threat_type_counts.get(threat_type, 0) + 1
                    )
            stats["threat_types"] = threat_type_counts

            # Severity distribution
            severity_counts = {}
            for indicator in self.indicators.values():
                if isinstance(indicator, ThreatIndicator):
                    severity = indicator.severity.value
                    severity_counts[severity] = severity_counts.get(severity, 0) + 1
            stats["severity_distribution"] = severity_counts

            # Platform distribution
            platform_counts = {}
            for indicator in self.indicators.values():
                if isinstance(indicator, ThreatIndicator):
                    platform = indicator.platform.value
                    platform_counts[platform] = platform_counts.get(platform, 0) + 1
            stats["platform_distribution"] = platform_counts

            return stats

        except Exception as e:
            logger.error(f"Error getting threat statistics: {e}")
            return {"error": str(e)}

    async def search_threat_indicators(
        self, query: str, indicator_type: str = None, threat_type: str = None
    ) -> List[Dict[str, Any]]:
        """Search threat indicators"""
        try:
            results = []
            query_lower = query.lower()

            for indicator in self.indicators.values():
                if isinstance(indicator, ThreatIndicator):
                    # Apply filters
                    if indicator_type and indicator.indicator_type != indicator_type:
                        continue
                    if threat_type and indicator.threat_type.value != threat_type:
                        continue

                    # Search in various fields
                    if (
                        query_lower in indicator.value.lower()
                        or query_lower in indicator.description.lower()
                        or any(query_lower in tag.lower() for tag in indicator.tags)
                    ):

                        results.append(
                            {
                                "indicator_id": indicator.indicator_id,
                                "indicator_type": indicator.indicator_type,
                                "value": indicator.value,
                                "threat_type": indicator.threat_type.value,
                                "severity": indicator.severity.value,
                                "confidence": indicator.confidence,
                                "source": indicator.source,
                                "description": indicator.description,
                                "tags": indicator.tags,
                                "platform": indicator.platform.value,
                                "first_seen": (
                                    indicator.first_seen.isoformat()
                                    if indicator.first_seen
                                    else None
                                ),
                                "last_seen": (
                                    indicator.last_seen.isoformat()
                                    if indicator.last_seen
                                    else None
                                ),
                            }
                        )

            return results

        except Exception as e:
            logger.error(f"Error searching threat indicators: {e}")
            return []

    async def cache_threat_data(self):
        """Cache threat intelligence data in Redis"""
        try:
            async with get_redis_connection() as redis:
                # Cache statistics
                stats = await self.get_threat_statistics()
                await redis.setex("threat_stats", self.cache_ttl, json.dumps(stats))

                # Cache indicators count by type
                indicator_counts = {}
                for indicator_type, indicators in self.indicators.items():
                    if isinstance(indicators, list):
                        indicator_counts[indicator_type] = len(indicators)
                await redis.setex(
                    "indicator_counts", self.cache_ttl, json.dumps(indicator_counts)
                )

                # Cache activities count
                await redis.setex(
                    "activity_count", self.cache_ttl, str(len(self.activities))
                )

        except Exception as e:
            logger.error(f"Error caching threat data: {e}")

    async def get_cached_threat_data(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached threat intelligence data from Redis"""
        try:
            async with get_redis_connection() as redis:
                cached = await redis.get(cache_key)
                return json.loads(cached) if cached else None
        except Exception as e:
            logger.error(f"Error getting cached threat data: {e}")
            return None


# Global dark web monitor instance
_dark_web_monitor: Optional[DarkWebMonitor] = None


def get_dark_web_monitor() -> DarkWebMonitor:
    """Get global dark web monitor instance"""
    global _dark_web_monitor
    if _dark_web_monitor is None:
        _dark_web_monitor = DarkWebMonitor()
    return _dark_web_monitor
