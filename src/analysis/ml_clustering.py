"""
Jackdaw Sentry - ML-Powered Address Clustering and Risk Scoring
Machine learning-based address clustering and risk assessment
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum
import json
import math
import statistics

from src.api.database import get_neo4j_session, get_redis_connection
from src.api.config import settings

logger = logging.getLogger(__name__)


class ClusterType(Enum):
    """Address cluster types"""
    EXCHANGE = "exchange"
    MIXER = "mixer"
    PRIVACY_TOOL = "privacy_tool"
    INSTITUTIONAL = "institutional"
    RETAIL = "retail"
    WHALE = "whale"
    DEVELOPER = "developer"
    SCAM = "scam"
    GAMBLING = "gambling"
    DEFI = "defi"
    MINING = "mining"
    UNKNOWN = "unknown"


class RiskLevel(Enum):
    """Risk levels"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
    CRITICAL = "critical"


@dataclass
class AddressFeatures:
    """Address features for ML analysis"""
    address: str
    blockchain: str
    transaction_count: int
    total_received: float
    total_sent: float
    balance: float
    avg_transaction_amount: float
    avg_transaction_frequency: float
    unique_counterparties: int
    first_seen: datetime
    last_seen: datetime
    active_days: int
    mixer_usage: bool
    privacy_tool_usage: bool
    bridge_usage: bool
    dex_usage: bool
    large_transactions: int
    round_amount_transactions: int
    off_peak_transactions: int
    high_frequency_periods: int
    cross_chain_activity: bool
    cluster_connections: int
    risk_indicators: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AddressCluster:
    """Address cluster representation"""
    cluster_id: str
    cluster_type: ClusterType
    addresses: List[str]
    blockchain: str
    size: int
    total_volume: float
    avg_risk_score: float
    confidence: float
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    characteristics: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskAssessment:
    """Risk assessment result"""
    address: str
    blockchain: str
    risk_score: float
    risk_level: RiskLevel
    confidence: float
    primary_risk_factors: List[str]
    secondary_risk_factors: List[str]
    cluster_affiliation: Optional[str] = None
    recommended_actions: List[str] = field(default_factory=list)
    assessment_date: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MLClusteringEngine:
    """Machine learning clustering and risk scoring engine"""
    
    def __init__(self):
        # Feature weights for risk scoring
        self.feature_weights = {
            'transaction_frequency': 0.15,
            'amount_variance': 0.12,
            'counterparty_diversity': 0.10,
            'temporal_patterns': 0.08,
            'mixer_usage': 0.20,
            'privacy_tool_usage': 0.15,
            'cross_chain_activity': 0.10,
            'large_amounts': 0.10
        }
        
        # Risk thresholds
        self.risk_thresholds = {
            RiskLevel.VERY_LOW: 0.0,
            RiskLevel.LOW: 0.2,
            RiskLevel.MEDIUM: 0.4,
            RiskLevel.HIGH: 0.6,
            RiskLevel.VERY_HIGH: 0.8,
            RiskLevel.CRITICAL: 0.9
        }
        
        # Clustering parameters
        self.min_cluster_size = 3
        self.similarity_threshold = 0.7
        self.max_cluster_size = 1000
        
        # Cache for analysis results
        self.feature_cache = {}
        self.cluster_cache = {}
        self.risk_cache = {}
        self.cache_ttl = 3600  # 1 hour
    
    async def extract_address_features(self, address: str, blockchain: str, time_range: int = 30) -> AddressFeatures:
        """Extract features for address analysis"""
        try:
            # Check cache first
            cache_key = f"{address}_{blockchain}_{time_range}"
            if cache_key in self.feature_cache:
                cached_time = self.feature_cache[cache_key].get('cached_at')
                if cached_time and (datetime.now(timezone.utc) - cached_time).total_seconds() < self.cache_ttl:
                    return self.feature_cache[cache_key]['features']
            
            # Get transaction data
            transactions = await self._get_address_transactions(address, blockchain, time_range)
            
            if not transactions:
                return AddressFeatures(
                    address=address,
                    blockchain=blockchain,
                    transaction_count=0,
                    total_received=0.0,
                    total_sent=0.0,
                    balance=0.0,
                    avg_transaction_amount=0.0,
                    avg_transaction_frequency=0.0,
                    unique_counterparties=0,
                    first_seen=datetime.now(timezone.utc),
                    last_seen=datetime.now(timezone.utc),
                    active_days=0,
                    mixer_usage=False,
                    privacy_tool_usage=False,
                    bridge_usage=False,
                    dex_usage=False,
                    large_transactions=0,
                    round_amount_transactions=0,
                    off_peak_transactions=0,
                    high_frequency_periods=0,
                    cross_chain_activity=False,
                    cluster_connections=0
                )
            
            # Calculate basic features
            transaction_count = len(transactions)
            total_received = sum(tx['value'] for tx in transactions if tx['to_address'] == address)
            total_sent = sum(tx['value'] for tx in transactions if tx['from_address'] == address)
            balance = total_received - total_sent
            
            # Calculate transaction amounts
            amounts = [tx['value'] for tx in transactions]
            avg_transaction_amount = statistics.mean(amounts) if amounts else 0.0
            
            # Calculate transaction frequency
            if transaction_count > 1:
                time_span = (transactions[-1]['timestamp'] - transactions[0]['timestamp']).total_seconds() / 3600
                avg_transaction_frequency = transaction_count / max(time_span, 1)
            else:
                avg_transaction_frequency = 0.0
            
            # Calculate unique counterparties
            counterparties = set()
            for tx in transactions:
                counterparties.add(tx['from_address'])
                counterparties.add(tx['to_address'])
            unique_counterparties = len(counterparties) - 1  # Exclude self
            
            # Time-based features
            first_seen = min(tx['timestamp'] for tx in transactions)
            last_seen = max(tx['timestamp'] for tx in transactions)
            active_days = (last_seen - first_seen).days + 1
            
            # Behavioral features
            mixer_usage = await self._check_mixer_usage(transactions)
            privacy_tool_usage = await self._check_privacy_tool_usage(transactions)
            bridge_usage = await self._check_bridge_usage(transactions)
            dex_usage = await self._check_dex_usage(transactions)
            
            # Risk indicators
            large_transactions = len([tx for tx in transactions if tx['value'] > 100])
            round_amount_transactions = len([tx for tx in transactions if self._is_round_amount(tx['value'])])
            off_peak_transactions = len([tx for tx in transactions if self._is_off_peak(tx['timestamp'])])
            high_frequency_periods = await self._count_high_frequency_periods(transactions)
            cross_chain_activity = await self._check_cross_chain_activity(address, blockchain)
            cluster_connections = await self._count_cluster_connections(address, blockchain)
            
            # Risk indicators
            risk_indicators = []
            if mixer_usage:
                risk_indicators.append("mixer_usage")
            if privacy_tool_usage:
                risk_indicators.append("privacy_tool_usage")
            if large_transactions > 5:
                risk_indicators.append("high_value_transactions")
            if avg_transaction_frequency > 10:
                risk_indicators.append("high_frequency")
            if unique_counterparties > 100:
                risk_indicators.append("high_counterparty_diversity")
            
            features = AddressFeatures(
                address=address,
                blockchain=blockchain,
                transaction_count=transaction_count,
                total_received=total_received,
                total_sent=total_sent,
                balance=balance,
                avg_transaction_amount=avg_transaction_amount,
                avg_transaction_frequency=avg_transaction_frequency,
                unique_counterparties=unique_counterparties,
                first_seen=first_seen,
                last_seen=last_seen,
                active_days=active_days,
                mixer_usage=mixer_usage,
                privacy_tool_usage=privacy_tool_usage,
                bridge_usage=bridge_usage,
                dex_usage=dex_usage,
                large_transactions=large_transactions,
                round_amount_transactions=round_amount_transactions,
                off_peak_transactions=off_peak_transactions,
                high_frequency_periods=high_frequency_periods,
                cross_chain_activity=cross_chain_activity,
                cluster_connections=cluster_connections,
                risk_indicators=risk_indicators,
                metadata={
                    'amount_variance': statistics.variance(amounts) if len(amounts) > 1 else 0,
                    'median_amount': statistics.median(amounts) if amounts else 0,
                    'max_amount': max(amounts) if amounts else 0,
                    'min_amount': min(amounts) if amounts else 0
                }
            )
            
            # Cache features
            self.feature_cache[cache_key] = {
                'features': features,
                'cached_at': datetime.now(timezone.utc)
            }
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features for address {address}: {e}")
            return AddressFeatures(
                address=address,
                blockchain=blockchain,
                transaction_count=0,
                total_received=0.0,
                total_sent=0.0,
                balance=0.0,
                avg_transaction_amount=0.0,
                avg_transaction_frequency=0.0,
                unique_counterparties=0,
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc),
                active_days=0,
                mixer_usage=False,
                privacy_tool_usage=False,
                bridge_usage=False,
                dex_usage=False,
                large_transactions=0,
                round_amount_transactions=0,
                off_peak_transactions=0,
                high_frequency_periods=0,
                cross_chain_activity=False,
                cluster_connections=0
            )
    
    async def _get_address_transactions(self, address: str, blockchain: str, time_range: int) -> List[Dict]:
        """Get transactions for address within time range"""
        query = """
        MATCH (a:Address {address: $address, blockchain: $blockchain})-[r:SENT|RECEIVED]->(t:Transaction)
        WHERE t.timestamp > datetime() - duration({hours: $time_range})
        RETURN t {
            .hash,
            .blockchain,
            .from_address,
            .to_address,
            .value,
            .timestamp,
            .block_number,
            .fee,
            .token_symbol
        } as tx_data
        ORDER BY t.timestamp ASC
        """
        
        async with get_neo4j_session() as session:
            result = await session.run(query, address=address, blockchain=blockchain, time_range=time_range)
            transactions = []
            async for record in result:
                transactions.append(record['tx_data'])
            return transactions
    
    async def _check_mixer_usage(self, transactions: List[Dict]) -> bool:
        """Check if address uses mixers"""
        # This would check against known mixer addresses
        # Simplified implementation
        return any(tx.get('mixing', False) for tx in transactions)
    
    async def _check_privacy_tool_usage(self, transactions: List[Dict]) -> bool:
        """Check if address uses privacy tools"""
        # This would check against known privacy tool addresses
        # Simplified implementation
        return any(tx.get('privacy_tool', False) for tx in transactions)
    
    async def _check_bridge_usage(self, transactions: List[Dict]) -> bool:
        """Check if address uses bridges"""
        # This would check against known bridge addresses
        # Simplified implementation
        return any(tx.get('bridge', False) for tx in transactions)
    
    async def _check_dex_usage(self, transactions: List[Dict]) -> bool:
        """Check if address uses DEXs"""
        # This would check against known DEX addresses
        # Simplified implementation
        return any(tx.get('dex', False) for tx in transactions)
    
    def _is_round_amount(self, amount: float) -> bool:
        """Check if amount is a round number"""
        # Common round amounts
        round_amounts = [1, 5, 10, 25, 50, 100, 500, 1000, 5000, 10000]
        
        for round_num in round_amounts:
            if abs(amount - round_num) / round_num < 0.01:  # 1% tolerance
                return True
        
        return False
    
    def _is_off_peak(self, timestamp: datetime) -> bool:
        """Check if timestamp is during off-peak hours"""
        hour = timestamp.hour
        return hour >= 22 or hour <= 6
    
    async def _count_high_frequency_periods(self, transactions: List[Dict]) -> int:
        """Count periods of high transaction frequency"""
        if len(transactions) < 5:
            return 0
        
        # Group transactions by hour
        hourly_counts = {}
        for tx in transactions:
            hour = tx['timestamp'].replace(minute=0, second=0, microsecond=0)
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
        
        # Count hours with high frequency (>10 transactions)
        return sum(1 for count in hourly_counts.values() if count > 10)
    
    async def _check_cross_chain_activity(self, address: str, blockchain: str) -> bool:
        """Check if address has activity on other blockchains"""
        query = """
        MATCH (a:Address {address: $address})-[]->(t:Transaction)
        WHERE t.blockchain <> $blockchain
        RETURN count(t) > 0 as has_cross_chain
        """
        
        async with get_neo4j_session() as session:
            result = await session.run(query, address=address, blockchain=blockchain)
            record = await result.single()
            return record['has_cross_chain'] if record else False
    
    async def _count_cluster_connections(self, address: str, blockchain: str) -> int:
        """Count cluster connections for address"""
        query = """
        MATCH (a:Address {address: $address, blockchain: $blockchain})-[]->(c:Cluster)
        RETURN count(c) as cluster_count
        """
        
        async with get_neo4j_session() as session:
            result = await session.run(query, address=address, blockchain=blockchain)
            record = await result.single()
            return record['cluster_count'] if record else 0
    
    async def calculate_risk_score(self, features: AddressFeatures) -> RiskAssessment:
        """Calculate risk score using ML features"""
        try:
            # Calculate feature scores
            feature_scores = {}
            
            # Transaction frequency score
            freq_score = min(features.avg_transaction_frequency / 20, 1.0)
            feature_scores['transaction_frequency'] = freq_score
            
            # Amount variance score
            amount_variance = features.metadata.get('amount_variance', 0)
            variance_score = min(math.log(amount_variance + 1) / 10, 1.0)
            feature_scores['amount_variance'] = variance_score
            
            # Counterparty diversity score
            diversity_score = min(features.unique_counterparties / 50, 1.0)
            feature_scores['counterparty_diversity'] = diversity_score
            
            # Temporal patterns score
            temporal_score = 0.0
            if features.off_peak_transactions > 5:
                temporal_score += 0.3
            if features.high_frequency_periods > 0:
                temporal_score += 0.4
            if features.round_amount_transactions > 3:
                temporal_score += 0.3
            feature_scores['temporal_patterns'] = temporal_score
            
            # Behavioral risk scores
            feature_scores['mixer_usage'] = 1.0 if features.mixer_usage else 0.0
            feature_scores['privacy_tool_usage'] = 0.8 if features.privacy_tool_usage else 0.0
            feature_scores['cross_chain_activity'] = 0.3 if features.cross_chain_activity else 0.0
            feature_scores['large_amounts'] = min(features.large_transactions / 10, 1.0)
            
            # Calculate weighted risk score
            risk_score = 0.0
            for feature, score in feature_scores.items():
                weight = self.feature_weights.get(feature, 0.1)
                risk_score += score * weight
            
            # Determine risk level
            risk_level = self._determine_risk_level(risk_score)
            
            # Identify risk factors
            primary_risk_factors = []
            secondary_risk_factors = []
            
            for feature, score in feature_scores.items():
                if score > 0.7:
                    if self.feature_weights.get(feature, 0.1) > 0.15:
                        primary_risk_factors.append(feature)
                    else:
                        secondary_risk_factors.append(feature)
            
            # Generate recommended actions
            recommended_actions = self._generate_recommendations(risk_level, primary_risk_factors)
            
            # Calculate confidence
            confidence = self._calculate_confidence(features, feature_scores)
            
            return RiskAssessment(
                address=features.address,
                blockchain=features.blockchain,
                risk_score=risk_score,
                risk_level=risk_level,
                confidence=confidence,
                primary_risk_factors=primary_risk_factors,
                secondary_risk_factors=secondary_risk_factors,
                recommended_actions=recommended_actions,
                metadata={
                    'feature_scores': feature_scores,
                    'transaction_count': features.transaction_count,
                    'total_volume': features.total_sent + features.total_received
                }
            )
            
        except Exception as e:
            logger.error(f"Error calculating risk score for address {features.address}: {e}")
            return RiskAssessment(
                address=features.address,
                blockchain=features.blockchain,
                risk_score=0.0,
                risk_level=RiskLevel.LOW,
                confidence=0.0,
                primary_risk_factors=[],
                secondary_risk_factors=[],
                recommended_actions=[]
            )
    
    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Determine risk level from score"""
        for level, threshold in sorted(self.risk_thresholds.items(), key=lambda x: x[1], reverse=True):
            if risk_score >= threshold:
                return level
        return RiskLevel.VERY_LOW
    
    def _generate_recommendations(self, risk_level: RiskLevel, risk_factors: List[str]) -> List[str]:
        """Generate recommended actions based on risk level and factors"""
        recommendations = []
        
        if risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH, RiskLevel.CRITICAL]:
            recommendations.append("Immediate investigation required")
            recommendations.append("Enhanced monitoring recommended")
            
            if "mixer_usage" in risk_factors:
                recommendations.append("Review mixer transaction history")
            if "privacy_tool_usage" in risk_factors:
                recommendations.append("Investigate privacy tool usage patterns")
            if "high_frequency" in risk_factors:
                recommendations.append("Monitor for automated trading patterns")
            if "large_amounts" in risk_factors:
                recommendations.append("Verify source of large transactions")
        
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.append("Regular monitoring recommended")
            recommendations.append("Periodic risk assessment")
        
        elif risk_level in [RiskLevel.LOW, RiskLevel.VERY_LOW]:
            recommendations.append("Standard monitoring sufficient")
        
        return recommendations
    
    def _calculate_confidence(self, features: AddressFeatures, feature_scores: Dict[str, float]) -> float:
        """Calculate confidence in risk assessment"""
        confidence = 0.5  # Base confidence
        
        # Increase confidence with more data
        if features.transaction_count > 10:
            confidence += 0.2
        if features.transaction_count > 50:
            confidence += 0.1
        
        # Increase confidence with consistent patterns
        high_score_count = sum(1 for score in feature_scores.values() if score > 0.5)
        if high_score_count > 3:
            confidence += 0.1
        
        # Increase confidence with longer activity period
        if features.active_days > 7:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    async def cluster_addresses(self, addresses: List[str], blockchain: str) -> List[AddressCluster]:
        """Cluster addresses based on similarity"""
        try:
            # Extract features for all addresses
            features_dict = {}
            for address in addresses:
                features = await self.extract_address_features(address, blockchain)
                features_dict[address] = features
            
            # Calculate similarity matrix
            similarity_matrix = await self._calculate_similarity_matrix(features_dict)
            
            # Perform clustering (simplified hierarchical clustering)
            clusters = await self._perform_clustering(addresses, similarity_matrix)
            
            # Create cluster objects
            cluster_objects = []
            for cluster_id, cluster_addresses in clusters.items():
                if len(cluster_addresses) >= self.min_cluster_size:
                    cluster = await self._create_cluster(cluster_id, cluster_addresses, blockchain, features_dict)
                    cluster_objects.append(cluster)
            
            return cluster_objects
            
        except Exception as e:
            logger.error(f"Error clustering addresses: {e}")
            return []
    
    async def _calculate_similarity_matrix(self, features_dict: Dict[str, AddressFeatures]) -> Dict[str, Dict[str, float]]:
        """Calculate similarity matrix between addresses"""
        similarity_matrix = {}
        addresses = list(features_dict.keys())
        
        for i, addr1 in enumerate(addresses):
            similarity_matrix[addr1] = {}
            for j, addr2 in enumerate(addresses):
                if i == j:
                    similarity_matrix[addr1][addr2] = 1.0
                else:
                    similarity = await self._calculate_similarity(features_dict[addr1], features_dict[addr2])
                    similarity_matrix[addr1][addr2] = similarity
        
        return similarity_matrix
    
    async def _calculate_similarity(self, features1: AddressFeatures, features2: AddressFeatures) -> float:
        """Calculate similarity between two addresses"""
        similarity = 0.0
        total_weight = 0.0
        
        # Transaction behavior similarity
        if features1.transaction_count > 0 and features2.transaction_count > 0:
            freq_similarity = 1 - abs(features1.avg_transaction_frequency - features2.avg_transaction_frequency) / max(features1.avg_transaction_frequency, features2.avg_transaction_frequency, 1)
            similarity += freq_similarity * 0.2
            total_weight += 0.2
        
        # Amount similarity
        if features1.total_sent > 0 and features2.total_sent > 0:
            amount_similarity = 1 - abs(features1.avg_transaction_amount - features2.avg_transaction_amount) / max(features1.avg_transaction_amount, features2.avg_transaction_amount, 1)
            similarity += amount_similarity * 0.2
            total_weight += 0.2
        
        # Behavioral similarity
        behavior_similarity = 0.0
        if features1.mixer_usage == features2.mixer_usage:
            behavior_similarity += 0.25
        if features1.privacy_tool_usage == features2.privacy_tool_usage:
            behavior_similarity += 0.25
        if features1.bridge_usage == features2.bridge_usage:
            behavior_similarity += 0.25
        if features1.dex_usage == features2.dex_usage:
            behavior_similarity += 0.25
        
        similarity += behavior_similarity * 0.3
        total_weight += 0.3
        
        # Temporal similarity
        if features1.active_days > 0 and features2.active_days > 0:
            temporal_similarity = 1 - abs(features1.active_days - features2.active_days) / max(features1.active_days, features2.active_days)
            similarity += temporal_similarity * 0.15
            total_weight += 0.15
        
        # Counterparty similarity
        if features1.unique_counterparties > 0 and features2.unique_counterparties > 0:
            counterparty_similarity = 1 - abs(features1.unique_counterparties - features2.unique_counterparties) / max(features1.unique_counterparties, features2.unique_counterparties)
            similarity += counterparty_similarity * 0.15
            total_weight += 0.15
        
        return similarity / total_weight if total_weight > 0 else 0.0
    
    async def _perform_clustering(self, addresses: List[str], similarity_matrix: Dict[str, Dict[str, float]]) -> Dict[str, List[str]]:
        """Perform hierarchical clustering"""
        clusters = {}
        assigned = set()
        cluster_id = 0
        
        for address in addresses:
            if address in assigned:
                continue
            
            # Find similar addresses
            similar_addresses = [address]
            for other_addr in addresses:
                if other_addr == address:
                    continue
                if other_addr not in assigned and similarity_matrix[address][other_addr] > self.similarity_threshold:
                    similar_addresses.append(other_addr)
                    assigned.add(other_addr)
            
            if len(similar_addresses) >= self.min_cluster_size:
                clusters[f"cluster_{cluster_id}"] = similar_addresses
                cluster_id += 1
            
            assigned.add(address)
        
        return clusters
    
    async def _create_cluster(self, cluster_id: str, addresses: List[str], blockchain: str, features_dict: Dict[str, AddressFeatures]) -> AddressCluster:
        """Create cluster object"""
        # Filter features_dict to only cluster members
        cluster_features = {addr: features_dict[addr] for addr in addresses if addr in features_dict}
        if not cluster_features:
            cluster_features = features_dict
        
        # Calculate cluster metrics
        total_volume = sum(features.total_sent + features.total_received for features in cluster_features.values())
        avg_risk_score = sum(features.metadata.get('risk_score', 0) for features in cluster_features.values()) / len(cluster_features)
        
        # Determine cluster type
        cluster_type = await self._determine_cluster_type(cluster_features)
        
        # Calculate confidence
        confidence = min(len(addresses) / 10, 1.0)
        
        # Identify characteristics
        characteristics = await self._identify_cluster_characteristics(cluster_features)
        
        return AddressCluster(
            cluster_id=cluster_id,
            cluster_type=cluster_type,
            addresses=addresses,
            blockchain=blockchain,
            size=len(addresses),
            total_volume=total_volume,
            avg_risk_score=avg_risk_score,
            confidence=confidence,
            characteristics=characteristics,
            metadata={
                'address_count': len(addresses),
                'creation_method': 'ml_clustering'
            }
        )
    
    async def _determine_cluster_type(self, features_dict: Dict[str, AddressFeatures]) -> ClusterType:
        """Determine cluster type based on features"""
        # Count behavioral patterns
        mixer_count = sum(1 for f in features_dict.values() if f.mixer_usage)
        privacy_count = sum(1 for f in features_dict.values() if f.privacy_tool_usage)
        dex_count = sum(1 for f in features_dict.values() if f.dex_usage)
        bridge_count = sum(1 for f in features_dict.values() if f.bridge_usage)
        
        # Determine type based on dominant behavior
        if not features_dict:
            return ClusterType.UNKNOWN
        if mixer_count / len(features_dict) > 0.7:
            return ClusterType.MIXER
        elif privacy_count / len(features_dict) > 0.7:
            return ClusterType.PRIVACY_TOOL
        elif dex_count / len(features_dict) > 0.7:
            return ClusterType.DEFI
        elif bridge_count / len(features_dict) > 0.5:
            return ClusterType.INSTITUTIONAL
        else:
            return ClusterType.UNKNOWN
    
    async def _identify_cluster_characteristics(self, features_dict: Dict[str, AddressFeatures]) -> List[str]:
        """Identify cluster characteristics"""
        characteristics = []
        
        # Analyze common behaviors
        if all(f.mixer_usage for f in features_dict.values()):
            characteristics.append("all_mixers")
        elif any(f.mixer_usage for f in features_dict.values()):
            characteristics.append("partial_mixers")
        
        if all(f.privacy_tool_usage for f in features_dict.values()):
            characteristics.append("all_privacy_tools")
        elif any(f.privacy_tool_usage for f in features_dict.values()):
            characteristics.append("partial_privacy_tools")
        
        # Analyze transaction patterns
        avg_frequency = statistics.mean([f.avg_transaction_frequency for f in features_dict.values()])
        if avg_frequency > 10:
            characteristics.append("high_frequency")
        elif avg_frequency > 1:
            characteristics.append("moderate_frequency")
        else:
            characteristics.append("low_frequency")
        
        # Analyze volume
        total_volume = sum(f.total_sent + f.total_received for f in features_dict.values())
        if total_volume > 10000:
            characteristics.append("high_volume")
        elif total_volume > 1000:
            characteristics.append("moderate_volume")
        else:
            characteristics.append("low_volume")
        
        return characteristics
    
    async def get_address_risk_assessment(self, address: str, blockchain: str, time_range: int = 30) -> RiskAssessment:
        """Get comprehensive risk assessment for address"""
        try:
            # Extract features
            features = await self.extract_address_features(address, blockchain, time_range)
            
            # Calculate risk score
            risk_assessment = await self.calculate_risk_score(features)
            
            # Get cluster affiliation
            cluster_affiliation = await self._get_address_cluster_affiliation(address, blockchain)
            if cluster_affiliation:
                risk_assessment.cluster_affiliation = cluster_affiliation
            
            return risk_assessment
            
        except Exception as e:
            logger.error(f"Error getting risk assessment for address {address}: {e}")
            return RiskAssessment(
                address=address,
                blockchain=blockchain,
                risk_score=0.0,
                risk_level=RiskLevel.LOW,
                confidence=0.0,
                primary_risk_factors=[],
                secondary_risk_factors=[],
                recommended_actions=[]
            )
    
    async def _get_address_cluster_affiliation(self, address: str, blockchain: str) -> Optional[str]:
        """Get cluster affiliation for address"""
        query = """
        MATCH (a:Address {address: $address, blockchain: $blockchain})-[:MEMBER_OF]->(c:Cluster)
        RETURN c.cluster_id as cluster_id
        """
        
        async with get_neo4j_session() as session:
            result = await session.run(query, address=address, blockchain=blockchain)
            record = await result.single()
            return record['cluster_id'] if record else None
    
    async def cache_analysis_results(self, key: str, result: Dict[str, Any]):
        """Cache analysis results in Redis"""
        try:
            async with get_redis_connection() as redis:
                await redis.setex(f"ml_analysis:{key}", self.cache_ttl, json.dumps(result, default=str))
        except Exception as e:
            logger.error(f"Error caching analysis results for key={key}: {e}")
    
    async def get_cached_analysis_results(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis results from Redis"""
        try:
            async with get_redis_connection() as redis:
                cached = await redis.get(f"ml_analysis:{key}")
                return json.loads(cached) if cached else None
        except Exception as e:
            logger.error(f"Error getting cached analysis results: {e}")
            return None


# Global ML clustering engine instance
_ml_clustering_engine: Optional[MLClusteringEngine] = None


def get_ml_clustering_engine() -> MLClusteringEngine:
    """Get global ML clustering engine instance"""
    global _ml_clustering_engine
    if _ml_clustering_engine is None:
        _ml_clustering_engine = MLClusteringEngine()
    return _ml_clustering_engine
