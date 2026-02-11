"""
Jackdaw Sentry - Threat Intelligence Aggregation System
Aggregates and correlates threat intelligence from multiple sources
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib

from src.api.database import get_neo4j_session, get_redis_connection
from src.api.config import settings
from .sanctions import SanctionsManager, get_sanctions_manager, SanctionsMatch
from .dark_web import DarkWebMonitor, get_dark_web_monitor, ThreatIndicator

logger = logging.getLogger(__name__)


class IntelligenceSourceType(Enum):
    """Intelligence source types"""
    SANCTIONS = "sanctions"
    DARK_WEB = "dark_web"
    BLOCKCHAIN_ANALYSIS = "blockchain_analysis"
    OPEN_SOURCE = "open_source"
    COMMERCIAL = "commercial"
    GOVERNMENT = "government"
    LAW_ENFORCEMENT = "law_enforcement"
    FINANCIAL_INSTITUTION = "financial_institution"
    EXCHANGE_REPORT = "exchange_report"
    RESEARCH = "research"
    HONEYPOT = "honeypot"
    MALWARE_ANALYSIS = "malware_analysis"
    NETWORK_MONITORING = "network_monitoring"
    SOCIAL_MEDIA = "social_media"
    FORUM_MONITORING = "forum_monitoring"


class IntelligenceConfidence(Enum):
    """Intelligence confidence levels"""
    VERY_HIGH = "very_high"  # 0.9 - 1.0
    HIGH = "high"          # 0.7 - 0.9
    MEDIUM = "medium"      # 0.5 - 0.7
    LOW = "low"            # 0.3 - 0.5
    VERY_LOW = "very_low"  # 0.1 - 0.3
    UNKNOWN = "unknown"    # 0.0 - 0.1


class CorrelationType(Enum):
    """Correlation types between intelligence items"""
    EXACT_MATCH = "exact_match"
    PARTIAL_MATCH = "partial_match"
    RELATED_ENTITY = "related_entity"
    TEMPORAL_CORRELATION = "temporal_correlation"
    GEOGRAPHIC_CORRELATION = "geographic_correlation"
    BEHAVIORAL_CORRELATION = "behavioral_correlation"
    NETWORK_CORRELATION = "network_correlation"
    FINANCIAL_CORRELATION = "financial_correlation"
    CONTEXTUAL_CORRELATION = "contextual_correlation"


@dataclass
class IntelligenceItem:
    """Individual intelligence item"""
    item_id: str
    source_type: IntelligenceSourceType
    source_name: str
    item_type: str  # address, transaction, entity, etc.
    value: str
    confidence: float
    severity: str
    description: str
    first_seen: datetime
    last_seen: datetime
    tags: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntelligenceCorrelation:
    """Correlation between intelligence items"""
    correlation_id: str
    item1_id: str
    item2_id: str
    correlation_type: CorrelationType
    confidence: float
    description: str
    evidence: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedIntelligence:
    """Aggregated intelligence for a target"""
    target_id: str
    target_type: str  # address, transaction, entity
    target_value: str
    intelligence_items: List[IntelligenceItem]
    correlations: List[IntelligenceCorrelation]
    overall_risk_score: float
    risk_level: str
    confidence: float
    sources: List[str]
    threat_types: List[str]
    recommendations: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntelligenceSummary:
    """Intelligence summary for reporting"""
    summary_id: str
    time_range: str
    total_targets: int
    total_intelligence_items: int
    total_correlations: int
    source_breakdown: Dict[str, int]
    threat_type_breakdown: Dict[str, int]
    risk_level_distribution: Dict[str, int]
    high_risk_targets: List[str]
    emerging_threats: List[str]
    created_at: datetime = field(default_factory=datetime.utcnow)


class IntelligenceAggregator:
    """Threat intelligence aggregation and correlation system"""
    
    def __init__(self):
        self.intelligence_items = {}  # All intelligence items
        self.correlations = {}  # Correlations between items
        self.aggregated_intelligence = {}  # Aggregated results
        self.sources = {}  # Source configurations
        
        # Initialize sub-systems
        self.sanctions_manager = get_sanctions_manager()
        self.dark_web_monitor = get_dark_web_monitor()
        
        # Aggregation configuration
        self.min_confidence_threshold = 0.3
        self.correlation_threshold = 0.5
        self.max_items_per_target = 100
        self.cache_ttl = 1800  # 30 minutes
        
        # Initialize sources
        self._initialize_sources()
        
        # Initialize with sample data
        self._initialize_sample_intelligence()
    
    def _initialize_sources(self):
        """Initialize intelligence source configurations"""
        self.sources = {
            IntelligenceSourceType.SANCTIONS: {
                'name': 'Sanctions Lists',
                'confidence_weight': 0.9,
                'severity_weight': 0.8,
                'description': 'Official sanctions lists from governments and international bodies'
            },
            IntelligenceSourceType.DARK_WEB: {
                'name': 'Dark Web Monitoring',
                'confidence_weight': 0.7,
                'severity_weight': 0.8,
                'description': 'Threat intelligence from dark web monitoring'
            },
            IntelligenceSourceType.BLOCKCHAIN_ANALYSIS: {
                'name': 'Blockchain Analysis',
                'confidence_weight': 0.8,
                'severity_weight': 0.6,
                'description': 'Analysis of blockchain transactions and patterns'
            },
            IntelligenceSourceType.OPEN_SOURCE: {
                'name': 'Open Source Intelligence',
                'confidence_weight': 0.6,
                'severity_weight': 0.5,
                'description': 'Publicly available threat intelligence'
            },
            IntelligenceSourceType.COMMERCIAL: {
                'name': 'Commercial Feeds',
                'confidence_weight': 0.8,
                'severity_weight': 0.7,
                'description': 'Commercial threat intelligence feeds'
            },
            IntelligenceSourceType.GOVERNMENT: {
                'name': 'Government Sources',
                'confidence_weight': 0.9,
                'severity_weight': 0.8,
                'description': 'Government threat intelligence sources'
            },
            IntelligenceSourceType.LAW_ENFORCEMENT: {
                'name': 'Law Enforcement',
                'confidence_weight': 0.9,
                'severity_weight': 0.9,
                'description': 'Law enforcement intelligence sources'
            },
            IntelligenceSourceType.FINANCIAL_INSTITUTION: {
                'name': 'Financial Institutions',
                'confidence_weight': 0.7,
                'severity_weight': 0.6,
                'description': 'Intelligence from financial institutions'
            },
            IntelligenceSourceType.EXCHANGE_REPORT: {
                'name': 'Exchange Reports',
                'confidence_weight': 0.6,
                'severity_weight': 0.5,
                'description': 'Reports from cryptocurrency exchanges'
            },
            IntelligenceSourceType.RESEARCH: {
                'name': 'Research Organizations',
                'confidence_weight': 0.7,
                'severity_weight': 0.6,
                'description': 'Research organization intelligence'
            }
        }
    
    def _initialize_sample_intelligence(self):
        """Initialize with sample intelligence data"""
        # Sample intelligence items
        sample_items = [
            {
                'item_id': 'INT-001',
                'source_type': IntelligenceSourceType.SANCTIONS,
                'source_name': 'OFAC',
                'item_type': 'address',
                'value': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
                'confidence': 0.95,
                'severity': 'high',
                'description': 'Bitcoin address on OFAC sanctions list',
                'tags': ['sanctions', 'bitcoin', 'ofac'],
                'context': {'sanctions_program': 'terrorism', 'list_date': '2020-01-15'}
            },
            {
                'item_id': 'INT-002',
                'source_type': IntelligenceSourceType.DARK_WEB,
                'source_name': 'Dark Web Monitor',
                'item_type': 'address',
                'value': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
                'confidence': 0.8,
                'severity': 'medium',
                'description': 'Bitcoin address mentioned in dark web forum',
                'tags': ['dark_web', 'bitcoin', 'forum'],
                'context': {'platform': 'tor', 'forum': 'hacker_forum'}
            },
            {
                'item_id': 'INT-003',
                'source_type': IntelligenceSourceType.BLOCKCHAIN_ANALYSIS,
                'source_name': 'Chain Analysis',
                'item_type': 'address',
                'value': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
                'confidence': 0.7,
                'severity': 'medium',
                'description': 'Address shows suspicious transaction patterns',
                'tags': ['blockchain', 'suspicious', 'patterns'],
                'context': {'pattern_type': 'mixing', 'transaction_count': 1500}
            },
            {
                'item_id': 'INT-004',
                'source_type': IntelligenceSourceType.OPEN_SOURCE,
                'source_name': 'OSINT Feed',
                'item_type': 'address',
                'value': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
                'confidence': 0.6,
                'severity': 'low',
                'description': 'Address mentioned in public report',
                'tags': ['osint', 'public', 'report'],
                'context': {'report_title': 'Crypto Crime Report', 'date': '2023-06-01'}
            }
        ]
        
        # Load sample intelligence items
        for item_data in sample_items:
            item_data['first_seen'] = datetime.utcnow() - timedelta(days=30)
            item_data['last_seen'] = datetime.utcnow()
            item = IntelligenceItem(**item_data)
            self.intelligence_items[item.item_id] = item
    
    async def aggregate_intelligence(self, target_value: str, target_type: str = 'address') -> AggregatedIntelligence:
        """Aggregate intelligence for a specific target"""
        try:
            # Check cache first
            cache_key = f"agg_{target_value}_{target_type}"
            cached_result = await self.get_cached_aggregation(cache_key)
            if cached_result:
                return cached_result
            
            # Collect intelligence from all sources
            intelligence_items = await self._collect_intelligence(target_value, target_type)
            
            # Find correlations
            correlations = await self._find_correlations(intelligence_items)
            
            # Calculate overall risk score
            overall_risk_score = self._calculate_overall_risk(intelligence_items, correlations)
            
            # Determine risk level
            risk_level = self._determine_risk_level(overall_risk_score)
            
            # Calculate confidence
            confidence = self._calculate_confidence(intelligence_items)
            
            # Extract sources and threat types
            sources = list(set(item.source_name for item in intelligence_items))
            threat_types = list(set(item.tags for item in intelligence_items))
            threat_types = [tag for sublist in threat_types for tag in sublist]  # Flatten
            
            # Generate recommendations
            recommendations = self._generate_recommendations(intelligence_items, correlations, risk_level)
            
            # Create aggregated intelligence
            target_id = hashlib.md5(f"{target_value}_{target_type}".encode()).hexdigest()
            aggregated = AggregatedIntelligence(
                target_id=target_id,
                target_type=target_type,
                target_value=target_value,
                intelligence_items=intelligence_items,
                correlations=correlations,
                overall_risk_score=overall_risk_score,
                risk_level=risk_level,
                confidence=confidence,
                sources=sources,
                threat_types=threat_types,
                recommendations=recommendations,
                metadata={
                    'total_items': len(intelligence_items),
                    'total_correlations': len(correlations),
                    'aggregation_timestamp': datetime.utcnow().isoformat()
                }
            )
            
            # Cache result
            await self.cache_aggregation(cache_key, aggregated)
            
            return aggregated
            
        except Exception as e:
            logger.error(f"Error aggregating intelligence for {target_value}: {e}")
            return AggregatedIntelligence(
                target_id="error",
                target_type=target_type,
                target_value=target_value,
                intelligence_items=[],
                correlations=[],
                overall_risk_score=0.0,
                risk_level="unknown",
                confidence=0.0,
                sources=[],
                threat_types=[],
                recommendations=[],
                metadata={'error': str(e)}
            )
    
    async def _collect_intelligence(self, target_value: str, target_type: str) -> List[IntelligenceItem]:
        """Collect intelligence from all sources"""
        intelligence_items = []
        
        # Collect from sanctions
        sanctions_result = await self.sanctions_manager.screen_address(target_value)
        if sanctions_result.matches:
            for match in sanctions_result.matches:
                item = IntelligenceItem(
                    item_id=f"sanctions_{match.entity_id}",
                    source_type=IntelligenceSourceType.SANCTIONS,
                    source_name=match.list_type.value.upper(),
                    item_type=target_type,
                    value=target_value,
                    confidence=match.confidence,
                    severity=match.risk_level,
                    description=f"Sanctions match: {match.entity_name}",
                    tags=[match.list_type.value, 'sanctions'] + [p.value for p in match.programs],
                    context={
                        'entity_id': match.entity_id,
                        'entity_name': match.entity_name,
                        'programs': [p.value for p in match.programs],
                        'match_score': match.match_score
                    }
                )
                intelligence_items.append(item)
        
        # Collect from dark web monitoring
        dark_web_result = await self.dark_web_monitor.check_address(target_value)
        if dark_web_result['matches'] > 0:
            for indicator in dark_web_result['matched_indicators']:
                item = IntelligenceItem(
                    item_id=f"darkweb_{indicator['indicator_id']}",
                    source_type=IntelligenceSourceType.DARK_WEB,
                    source_name=indicator['source'],
                    item_type=target_type,
                    value=target_value,
                    confidence=indicator['confidence'],
                    severity=indicator['severity'],
                    description=f"Dark web threat: {indicator['description']}",
                    tags=[indicator['threat_type'], 'dark_web'] + indicator['tags'],
                    context={
                        'indicator_id': indicator['indicator_id'],
                        'threat_type': indicator['threat_type'],
                        'platform': indicator['platform']
                    }
                )
                intelligence_items.append(item)
        
        # Collect from existing intelligence items
        for item in self.intelligence_items.values():
            if item.item_type == target_type and item.value.lower() == target_value.lower():
                intelligence_items.append(item)
        
        # Filter by confidence threshold
        intelligence_items = [item for item in intelligence_items if item.confidence >= self.min_confidence_threshold]
        
        # Sort by confidence
        intelligence_items.sort(key=lambda x: x.confidence, reverse=True)
        
        # Limit to max items per target
        if len(intelligence_items) > self.max_items_per_target:
            intelligence_items = intelligence_items[:self.max_items_per_target]
        
        return intelligence_items
    
    async def _find_correlations(self, intelligence_items: List[IntelligenceItem]) -> List[IntelligenceCorrelation]:
        """Find correlations between intelligence items"""
        correlations = []
        
        # Find exact matches
        for i, item1 in enumerate(intelligence_items):
            for j, item2 in enumerate(intelligence_items[i+1:], i+1):
                correlation = await self._correlate_items(item1, item2)
                if correlation:
                    correlations.append(correlation)
        
        # Sort by confidence
        correlations.sort(key=lambda x: x.confidence, reverse=True)
        
        return correlations
    
    async def _correlate_items(self, item1: IntelligenceItem, item2: IntelligenceItem) -> Optional[IntelligenceCorrelation]:
        """Correlate two intelligence items"""
        # Check for exact match
        if item1.value == item2.value:
            return IntelligenceCorrelation(
                correlation_id=f"exact_{item1.item_id}_{item2.item_id}",
                item1_id=item1.item_id,
                item2_id=item2.item_id,
                correlation_type=CorrelationType.EXACT_MATCH,
                confidence=min(item1.confidence, item2.confidence),
                description=f"Exact match between {item1.source_name} and {item2.source_name}",
                evidence=[f"Both sources report on {item1.value}"]
            )
        
        # Check for related tags
        common_tags = set(item1.tags) & set(item2.tags)
        if len(common_tags) >= 2:
            return IntelligenceCorrelation(
                correlation_id=f"tags_{item1.item_id}_{item2.item_id}",
                item1_id=item1.item_id,
                item2_id=item2.item_id,
                correlation_type=CorrelationType.CONTEXTUAL_CORRELATION,
                confidence=0.6,
                description=f"Contextual correlation via common tags",
                evidence=[f"Common tags: {list(common_tags)}"]
            )
        
        # Check for related sources
        if item1.source_type == item2.source_type:
            return IntelligenceCorrelation(
                correlation_id=f"source_{item1.item_id}_{item2.item_id}",
                item1_id=item1.item_id,
                item2_id=item2.item_id,
                correlation_type=CorrelationType.RELATED_ENTITY,
                confidence=0.5,
                description=f"Related entities from same source type",
                evidence=[f"Both from {item1.source_type.value}"]
            )
        
        return None
    
    def _calculate_overall_risk(self, intelligence_items: List[IntelligenceItem], correlations: List[IntelligenceCorrelation]) -> float:
        """Calculate overall risk score"""
        if not intelligence_items:
            return 0.0
        
        # Base risk from intelligence items
        item_risks = []
        for item in intelligence_items:
            source_weight = self.sources.get(item.source_type, {}).get('severity_weight', 0.5)
            severity_weight = self._get_severity_weight(item.severity)
            item_risk = item.confidence * source_weight * severity_weight
            item_risks.append(item_risk)
        
        # Average item risk
        avg_item_risk = sum(item_risks) / len(item_risks) if item_risks else 0.0
        
        # Correlation boost
        correlation_boost = min(len(correlations) * 0.05, 0.2)
        
        # Source diversity boost
        source_diversity = len(set(item.source_type for item in intelligence_items))
        diversity_boost = min(source_diversity * 0.05, 0.15)
        
        overall_risk = avg_item_risk + correlation_boost + diversity_boost
        return min(overall_risk, 1.0)
    
    def _get_severity_weight(self, severity: str) -> float:
        """Get weight for severity level"""
        severity_weights = {
            'critical': 1.0,
            'high': 0.8,
            'medium': 0.6,
            'low': 0.4,
            'info': 0.2,
            'very_low': 0.1
        }
        return severity_weights.get(severity, 0.5)
    
    def _determine_risk_level(self, risk_score: float) -> str:
        """Determine risk level from score"""
        if risk_score >= 0.9:
            return "critical"
        elif risk_score >= 0.7:
            return "high"
        elif risk_score >= 0.5:
            return "medium"
        elif risk_score >= 0.3:
            return "low"
        else:
            return "very_low"
    
    def _calculate_confidence(self, intelligence_items: List[IntelligenceItem]) -> float:
        """Calculate overall confidence"""
        if not intelligence_items:
            return 0.0
        
        # Weight by source confidence
        weighted_confidences = []
        for item in intelligence_items:
            source_weight = self.sources.get(item.source_type, {}).get('confidence_weight', 0.5)
            weighted_confidence = item.confidence * source_weight
            weighted_confidences.append(weighted_confidence)
        
        # Average weighted confidence
        avg_confidence = sum(weighted_confidences) / len(weighted_confidences) if weighted_confidences else 0.0
        
        # Source diversity boost
        source_diversity = len(set(item.source_type for item in intelligence_items))
        diversity_boost = min(source_diversity * 0.05, 0.1)
        
        overall_confidence = avg_confidence + diversity_boost
        return min(overall_confidence, 1.0)
    
    def _generate_recommendations(self, intelligence_items: List[IntelligenceItem], correlations: List[IntelligenceCorrelation], risk_level: str) -> List[str]:
        """Generate recommendations based on intelligence"""
        recommendations = []
        
        if not intelligence_items:
            recommendations.append("No intelligence found")
            return recommendations
        
        # Base recommendations by risk level
        if risk_level == "critical":
            recommendations.append("IMMEDIATE INVESTIGATION REQUIRED")
            recommendations.append("Block all associated activities")
            recommendations.append("Report to compliance and security teams")
        elif risk_level == "high":
            recommendations.append("Enhanced monitoring required")
            recommendations.append("Review transaction patterns")
            recommendations.append("Consider additional verification")
        elif risk_level == "medium":
            recommendations.append("Standard monitoring with alerts")
            recommendations.append("Periodic review recommended")
        else:
            recommendations.append("Standard monitoring sufficient")
        
        # Source-specific recommendations
        source_types = set(item.source_type for item in intelligence_items)
        if IntelligenceSourceType.SANCTIONS in source_types:
            recommendations.append("Sanctions compliance required")
        if IntelligenceSourceType.DARK_WEB in source_types:
            recommendations.append("Dark web activity detected")
        if IntelligenceSourceType.BLOCKCHAIN_ANALYSIS in source_types:
            recommendations.append("Suspicious blockchain patterns")
        
        # Correlation-specific recommendations
        if len(correlations) >= 3:
            recommendations.append("Multiple correlations detected - high confidence")
        
        return recommendations
    
    async def add_intelligence_item(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add new intelligence item"""
        try:
            # Validate required fields
            required_fields = ['item_id', 'source_type', 'source_name', 'item_type', 'value', 'confidence', 'severity', 'description']
            for field in required_fields:
                if field not in item_data:
                    return {'error': f'Missing required field: {field}'}
            
            # Convert enum fields
            item_data['source_type'] = IntelligenceSourceType(item_data['source_type'])
            
            if 'first_seen' in item_data and item_data['first_seen']:
                item_data['first_seen'] = datetime.fromisoformat(item_data['first_seen'])
            
            if 'last_seen' in item_data and item_data['last_seen']:
                item_data['last_seen'] = datetime.fromisoformat(item_data['last_seen'])
            
            # Create intelligence item
            item = IntelligenceItem(**item_data)
            
            # Add to collection
            self.intelligence_items[item.item_id] = item
            
            # Cache update
            await self.cache_intelligence_data()
            
            return {
                'item_id': item.item_id,
                'status': 'added',
                'added_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error adding intelligence item: {e}")
            return {'error': str(e)}
    
    async def get_intelligence_summary(self, time_range: int = 24) -> IntelligenceSummary:
        """Get intelligence summary for reporting"""
        try:
            # Calculate summary metrics
            total_targets = len(set(item.value for item in self.intelligence_items.values()))
            total_intelligence_items = len(self.intelligence_items)
            total_correlations = len(self.correlations)
            
            # Source breakdown
            source_breakdown = {}
            for item in self.intelligence_items.values():
                source_name = item.source_name
                source_breakdown[source_name] = source_breakdown.get(source_name, 0) + 1
            
            # Threat type breakdown
            threat_type_breakdown = {}
            for item in self.intelligence_items.values():
                for tag in item.tags:
                    threat_type_breakdown[tag] = threat_type_breakdown.get(tag, 0) + 1
            
            # Risk level distribution
            risk_level_distribution = {}
            for item in self.intelligence_items.values():
                risk_level = item.severity
                risk_level_distribution[risk_level] = risk_level_distribution.get(risk_level, 0) + 1
            
            # High risk targets
            high_risk_targets = []
            for item in self.intelligence_items.values():
                if item.severity in ['critical', 'high']:
                    high_risk_targets.append(item.value)
            
            # Emerging threats (recent items with high confidence)
            emerging_threats = []
            recent_threshold = datetime.utcnow() - timedelta(hours=time_range)
            for item in self.intelligence_items.values():
                if item.last_seen > recent_threshold and item.confidence > 0.7:
                    emerging_threats.append(item.value)
            
            summary = IntelligenceSummary(
                summary_id=f"summary_{datetime.utcnow().timestamp()}",
                time_range=f"{time_range}h",
                total_targets=total_targets,
                total_intelligence_items=total_intelligence_items,
                total_correlations=total_correlations,
                source_breakdown=source_breakdown,
                threat_type_breakdown=threat_type_breakdown,
                risk_level_distribution=risk_level_distribution,
                high_risk_targets=list(set(high_risk_targets)),
                emerging_threats=list(set(emerging_threats))
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting intelligence summary: {e}")
            return IntelligenceSummary(
                summary_id="error",
                time_range=f"{time_range}h",
                total_targets=0,
                total_intelligence_items=0,
                total_correlations=0,
                source_breakdown={},
                threat_type_breakdown={},
                risk_level_distribution={},
                high_risk_targets=[],
                emerging_threats=[]
            )
    
    async def cache_aggregation(self, key: str, aggregation: AggregatedIntelligence):
        """Cache aggregation result in Redis"""
        try:
            async with get_redis_connection() as redis:
                # Convert to dict for JSON serialization
                agg_dict = {
                    'target_id': aggregation.target_id,
                    'target_type': aggregation.target_type,
                    'target_value': aggregation.target_value,
                    'intelligence_items': [item.__dict__ for item in aggregation.intelligence_items],
                    'correlations': [corr.__dict__ for corr in aggregation.correlations],
                    'overall_risk_score': aggregation.overall_risk_score,
                    'risk_level': aggregation.risk_level,
                    'confidence': aggregation.confidence,
                    'sources': aggregation.sources,
                    'threat_types': aggregation.threat_types,
                    'recommendations': aggregation.recommendations,
                    'created_at': aggregation.created_at.isoformat(),
                    'updated_at': aggregation.updated_at.isoformat(),
                    'metadata': aggregation.metadata
                }
                
                await redis.setex(f"intelligence_agg:{key}", self.cache_ttl, json.dumps(agg_dict))
        except Exception as e:
            logger.error(f"Error caching aggregation: {e}")
    
    async def get_cached_aggregation(self, key: str) -> Optional[AggregatedIntelligence]:
        """Get cached aggregation from Redis"""
        try:
            async with get_redis_connection() as redis:
                cached = await redis.get(f"intelligence_agg:{key}")
                if cached:
                    agg_dict = json.loads(cached)
                    return AggregatedIntelligence(
                        target_id=agg_dict['target_id'],
                        target_type=agg_dict['target_type'],
                        target_value=agg_dict['target_value'],
                        intelligence_items=[IntelligenceItem(**item) for item in agg_dict['intelligence_items']],
                        correlations=[IntelligenceCorrelation(**corr) for corr in agg_dict['correlations']],
                        overall_risk_score=agg_dict['overall_risk_score'],
                        risk_level=agg_dict['risk_level'],
                        confidence=agg_dict['confidence'],
                        sources=agg_dict['sources'],
                        threat_types=agg_dict['threat_types'],
                        recommendations=agg_dict['recommendations'],
                        created_at=datetime.fromisoformat(agg_dict['created_at']),
                        updated_at=datetime.fromisoformat(agg_dict['updated_at']),
                        metadata=agg_dict['metadata']
                    )
        except Exception as e:
            logger.error(f"Error getting cached aggregation: {e}")
        
        return None
    
    async def cache_intelligence_data(self):
        """Cache intelligence data in Redis"""
        try:
            async with get_redis_connection() as redis:
                # Cache basic statistics
                stats = {
                    'total_items': len(self.intelligence_items),
                    'total_correlations': len(self.correlations),
                    'source_types': list(set(item.source_type.value for item in self.intelligence_items.values())),
                    'last_updated': datetime.utcnow().isoformat()
                }
                await redis.setex("intelligence_stats", self.cache_ttl, json.dumps(stats))
        except Exception as e:
            logger.error(f"Error caching intelligence data: {e}")


# Global intelligence aggregator instance
_intelligence_aggregator: Optional[IntelligenceAggregator] = None


def get_intelligence_aggregator() -> IntelligenceAggregator:
    """Get global intelligence aggregator instance"""
    global _intelligence_aggregator
    if _intelligence_aggregator is None:
        _intelligence_aggregator = IntelligenceAggregator()
    return _intelligence_aggregator
