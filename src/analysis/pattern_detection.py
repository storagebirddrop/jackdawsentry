"""
Jackdaw Sentry - Money Laundering Pattern Detection System
Detects suspicious patterns in blockchain transactions for AML compliance
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import statistics

from src.api.database import get_neo4j_session, get_redis_connection
from src.api.config import settings
from .cross_chain import CrossChainAnalyzer, TransactionPattern

logger = logging.getLogger(__name__)


class MLPatternType(Enum):
    """Money laundering pattern types"""
    STRUCTURING = "structuring"  # Breaking large amounts into smaller transactions
    LAYERING = "layering"  # Complex series of transactions to obscure origin
    INTEGRATION = "integration"  # Reintroducing funds into legitimate economy
    CIRCULAR_TRADING = "circular_trading"  # Circular transactions to create false volume
    MIXER_USAGE = "mixer_usage"  # Using mixing services
    PRIVACY_TOOL_USAGE = "privacy_tool_usage"  # Using privacy-enhancing tools
    BRIDGE_HOPPING = "bridge_hopping"  # Multiple bridge transfers
    DEX_HOPPING = "dex_hopping"  # Multiple DEX swaps
    HIGH_FREQUENCY = "high_frequency"  # Unusually high transaction frequency
    ROUND_AMOUNTS = "round_amounts"  # Suspicious round number amounts
    PEAK_OFF_HOURS = "peak_off_hours"  # Transactions during off-peak hours
    SYNCHRONIZED_TRANSFERS = "synchronized_transfers"  # Coordinated transfers
    RAPID_CHAIN_SWITCHING = "rapid_chain_switching"  # Quick blockchain switching
    SPLITTING_MERGING = "splitting_merging"  # Splitting and merging transactions


@dataclass
class PatternMatch:
    """Pattern match result"""
    pattern_type: MLPatternType
    confidence: float
    risk_score: float
    evidence: List[Dict[str, Any]]
    description: str
    severity: str  # low, medium, high, critical
    detected_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AddressPatternProfile:
    """Pattern profile for an address"""
    address: str
    blockchain: str
    total_transactions: int
    total_amount: float
    pattern_matches: List[PatternMatch]
    risk_score: float
    last_activity: datetime
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class MLPatternDetector:
    """Money laundering pattern detection system"""
    
    def __init__(self):
        self.cross_chain_analyzer = CrossChainAnalyzer()
        
        # Detection thresholds
        self.structuring_threshold = 10000  # USD
        self.structuring_max_amount = 50000  # USD
        self.high_frequency_threshold = 20  # transactions per hour
        self.round_amount_tolerance = 0.05  # 5% tolerance for round numbers
        self.off_peak_start = 22  # 10 PM
        self.off_peak_end = 6  # 6 AM
        self.rapid_switch_threshold = timedelta(minutes=30)
        self.synchronized_tolerance = timedelta(minutes=5)
        
        # Known suspicious addresses
        self.suspicious_addresses = set()
        self.known_mixers = set()
        self.known_privacy_tools = set()
        
        # Cache for pattern profiles
        self.profile_cache = {}
        self.cache_ttl = 3600  # 1 hour
    
    async def detect_patterns(self, address: str, blockchain: str, time_range: int = 24) -> List[PatternMatch]:
        """Detect money laundering patterns for an address"""
        try:
            # Get address transaction history
            transactions = await self._get_address_transactions(address, blockchain, time_range)
            if not transactions:
                return []
            
            pattern_matches = []
            
            # Detect each pattern type
            pattern_matches.extend(await self._detect_structuring(transactions))
            pattern_matches.extend(await self._detect_layering(transactions))
            pattern_matches.extend(await self._detect_integration(transactions))
            pattern_matches.extend(await self._detect_circular_trading(transactions))
            pattern_matches.extend(await self._detect_mixer_usage(transactions))
            pattern_matches.extend(await self._detect_privacy_tool_usage(transactions))
            pattern_matches.extend(await self._detect_bridge_hopping(transactions))
            pattern_matches.extend(await self._detect_dex_hopping(transactions))
            pattern_matches.extend(await self._detect_high_frequency(transactions))
            pattern_matches.extend(await self._detect_round_amounts(transactions))
            pattern_matches.extend(await self._detect_peak_off_hours(transactions))
            pattern_matches.extend(await self._detect_synchronized_transfers(transactions))
            pattern_matches.extend(await self._detect_rapid_chain_switching(transactions))
            pattern_matches.extend(await self._detect_splitting_merging(transactions))
            
            # Sort by risk score
            pattern_matches.sort(key=lambda x: x.risk_score, reverse=True)
            
            # Update address profile
            await self._update_address_profile(address, blockchain, pattern_matches)
            
            return pattern_matches
            
        except Exception as e:
            logger.error(f"Error detecting patterns for address {address}: {e}")
            return []
    
    async def _get_address_transactions(self, address: str, blockchain: str, time_range: int) -> List[Dict]:
        """Get transactions for address within time range"""
        query = """
        MATCH (a:Address {address: $address, blockchain: $blockchain})-[r:SENT]->(t:Transaction)
        WHERE t.timestamp > datetime() - duration('PT${time_range}H')
        RETURN t {
            .hash,
            .blockchain,
            .from_address,
            .to_address,
            .value,
            .timestamp,
            .block_number,
            .gas_used,
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
    
    async def _detect_structuring(self, transactions: List[Dict]) -> List[PatternMatch]:
        """Detect structuring pattern (breaking large amounts into smaller transactions)"""
        pattern_matches = []
        
        # Group transactions by hour
        hourly_groups = self._group_transactions_by_hour(transactions)
        
        for hour, hour_txs in hourly_groups.items():
            # Check if multiple small transactions add up to a large amount
            if len(hour_txs) >= 3:
                total_amount = sum(tx['value'] for tx in hour_txs)
                
                if (total_amount > self.structuring_threshold and 
                    all(tx['value'] < self.structuring_max_amount for tx in hour_txs)):
                    
                    confidence = min(len(hour_txs) / 10.0, 1.0)
                    risk_score = 0.6 + (total_amount / 100000)  # Scale with amount
                    
                    pattern_match = PatternMatch(
                        pattern_type=MLPatternType.STRUCTURING,
                        confidence=confidence,
                        risk_score=min(risk_score, 1.0),
                        evidence=[{
                            'timestamp': hour,
                            'transaction_count': len(hour_txs),
                            'total_amount': total_amount,
                            'average_amount': total_amount / len(hour_txs),
                            'transactions': [{'hash': tx['hash'], 'amount': tx['value']} for tx in hour_txs]
                        }],
                        description=f"Structuring detected: {len(hour_txs)} transactions totaling ${total_amount:,.2f} in one hour",
                        severity="high" if total_amount > 50000 else "medium"
                    )
                    pattern_matches.append(pattern_match)
        
        return pattern_matches
    
    async def _detect_layering(self, transactions: List[Dict]) -> List[PatternMatch]:
        """Detect layering pattern (complex transaction chains)"""
        pattern_matches = []
        
        # Look for chains of 3+ transactions
        if len(transactions) >= 3:
            # Analyze transaction chains
            chains = self._find_transaction_chains(transactions)
            
            for chain in chains:
                if len(chain) >= 3:
                    # Check for complexity indicators
                    unique_addresses = set()
                    unique_blockchains = set()
                    total_amount = 0
                    
                    for tx in chain:
                        unique_addresses.add(tx['from_address'])
                        unique_addresses.add(tx['to_address'])
                        unique_blockchains.add(tx['blockchain'])
                        total_amount += tx['value']
                    
                    # Calculate complexity score
                    complexity_score = (len(unique_addresses) * 0.2 + 
                                     len(unique_blockchains) * 0.3 +
                                     len(chain) * 0.1)
                    
                    if complexity_score > 0.5:
                        confidence = min(complexity_score, 1.0)
                        risk_score = min(0.5 + complexity_score, 1.0)
                        
                        pattern_match = PatternMatch(
                            pattern_type=MLPatternType.LAYERING,
                            confidence=confidence,
                            risk_score=risk_score,
                            evidence=[{
                                'chain_length': len(chain),
                                'unique_addresses': len(unique_addresses),
                                'unique_blockchains': len(unique_blockchains),
                                'total_amount': total_amount,
                                'transactions': [{'hash': tx['hash'], 'amount': tx['value']} for tx in chain]
                            }],
                            description=f"Layering detected: {len(chain)} transaction chain with {len(unique_addresses)} unique addresses",
                            severity="high" if complexity_score > 0.8 else "medium"
                        )
                        pattern_matches.append(pattern_match)
        
        return pattern_matches
    
    async def _detect_integration(self, transactions: List[Dict]) -> List[PatternMatch]:
        """Detect integration pattern (funds entering legitimate economy)"""
        pattern_matches = []
        
        # Look for transactions to known legitimate services
        legitimate_services = await self._get_legitimate_services()
        
        for tx in transactions:
            if tx['to_address'] in legitimate_services:
                # Check if this is the final step after suspicious activity
                previous_txs = [t for t in transactions if t['timestamp'] < tx['timestamp']]
                
                if len(previous_txs) >= 2:
                    # Calculate risk based on previous activity
                    previous_risk = sum(await self._calculate_transaction_risk(t) for t in previous_txs) / len(previous_txs)
                    
                    if previous_risk > 0.5:
                        confidence = min(previous_risk, 1.0)
                        risk_score = min(0.4 + previous_risk, 1.0)
                        
                        pattern_match = PatternMatch(
                            pattern_type=MLPatternType.INTEGRATION,
                            confidence=confidence,
                            risk_score=risk_score,
                            evidence=[{
                                'integration_amount': tx['value'],
                                'integration_service': tx['to_address'],
                                'previous_risk_score': previous_risk,
                                'previous_transactions': len(previous_txs)
                            }],
                            description=f"Integration detected: ${tx['value']:,.2f} transferred to legitimate service after suspicious activity",
                            severity="high" if previous_risk > 0.7 else "medium"
                        )
                        pattern_matches.append(pattern_match)
        
        return pattern_matches
    
    async def _detect_circular_trading(self, transactions: List[Dict]) -> List[PatternMatch]:
        """Detect circular trading pattern"""
        pattern_matches = []
        
        # Look for circular transaction patterns
        circular_paths = self._find_circular_paths(transactions)
        
        for path in circular_paths:
            if len(path) >= 3:
                # Calculate total volume
                total_volume = sum(tx['value'] for tx in path)
                
                # Check if amounts are similar (circular trading often uses similar amounts)
                amounts = [tx['value'] for tx in path]
                amount_variance = statistics.variance(amounts) if len(amounts) > 1 else 0
                amount_std = statistics.stdev(amounts) if len(amounts) > 1 else 0
                
                # Calculate circularity score
                circularity_score = 1.0 - (amount_std / statistics.mean(amounts)) if statistics.mean(amounts) > 0 else 0
                
                if circularity_score > 0.7:
                    confidence = circularity_score
                    risk_score = 0.6 + (total_volume / 100000)
                    
                    pattern_match = PatternMatch(
                        pattern_type=MLPatternType.CIRCULAR_TRADING,
                        confidence=confidence,
                        risk_score=min(risk_score, 1.0),
                        evidence=[{
                            'path_length': len(path),
                            'total_volume': total_volume,
                            'amount_variance': amount_variance,
                            'circularity_score': circularity_score,
                            'transactions': [{'hash': tx['hash'], 'amount': tx['value']} for tx in path]
                        }],
                        description=f"Circular trading detected: {len(path)} transactions with ${total_volume:,.2f} total volume",
                        severity="high" if total_volume > 50000 else "medium"
                    )
                    pattern_matches.append(pattern_match)
        
        return pattern_matches
    
    async def _detect_mixer_usage(self, transactions: List[Dict]) -> List[PatternMatch]:
        """Detect mixer usage pattern"""
        pattern_matches = []
        
        # Check for transactions to known mixers
        mixer_txs = [tx for tx in transactions if await self._is_mixer_transaction(tx)]
        
        if mixer_txs:
            total_amount = sum(tx['value'] for tx in mixer_txs)
            confidence = min(len(mixer_txs) / 5.0, 1.0)
            risk_score = 0.8  # Mixers are inherently suspicious
            
            pattern_match = PatternMatch(
                pattern_type=MLPatternType.MIXER_USAGE,
                confidence=confidence,
                risk_score=risk_score,
                evidence=[{
                    'mixer_transactions': len(mixer_txs),
                    'total_amount': total_amount,
                    'transactions': [{'hash': tx['hash'], 'amount': tx['value'], 'to_address': tx['to_address']} for tx in mixer_txs]
                }],
                description=f"Mixer usage detected: {len(mixer_txs)} transactions totaling ${total_amount:,.2f}",
                severity="critical"
            )
            pattern_matches.append(pattern_match)
        
        return pattern_matches
    
    async def _detect_privacy_tool_usage(self, transactions: List[Dict]) -> List[PatternMatch]:
        """Detect privacy tool usage pattern"""
        pattern_matches = []
        
        # Check for transactions to known privacy tools
        privacy_txs = [tx for tx in transactions if await self._is_privacy_tool_transaction(tx)]
        
        if privacy_txs:
            total_amount = sum(tx['value'] for tx in privacy_txs)
            confidence = min(len(privacy_txs) / 3.0, 1.0)
            risk_score = 0.7  # Privacy tools are suspicious
            
            pattern_match = PatternMatch(
                pattern_type=MLPatternType.PRIVACY_TOOL_USAGE,
                confidence=confidence,
                risk_score=risk_score,
                evidence=[{
                    'privacy_transactions': len(privacy_txs),
                    'total_amount': total_amount,
                    'transactions': [{'hash': tx['hash'], 'amount': tx['value'], 'to_address': tx['to_address']} for tx in privacy_txs]
                }],
                description=f"Privacy tool usage detected: {len(privacy_txs)} transactions totaling ${total_amount:,.2f}",
                severity="high"
            )
            pattern_matches.append(pattern_match)
        
        return pattern_matches
    
    async def _detect_bridge_hopping(self, transactions: List[Dict]) -> List[PatternMatch]:
        """Detect bridge hopping pattern"""
        pattern_matches = []
        
        # Look for multiple bridge transactions
        bridge_txs = [tx for tx in transactions if await self._is_bridge_transaction(tx)]
        
        if len(bridge_txs) >= 2:
            # Check if bridges are different
            unique_bridges = set()
            for tx in bridge_txs:
                bridge = await self._get_bridge_name(tx['to_address'])
                if bridge:
                    unique_bridges.add(bridge)
            
            if len(unique_bridges) >= 2:
                total_amount = sum(tx['value'] for tx in bridge_txs)
                confidence = min(len(unique_bridges) / 3.0, 1.0)
                risk_score = 0.4 + (len(unique_bridges) * 0.1)
                
                pattern_match = PatternMatch(
                    pattern_type=MLPatternType.BRIDGE_HOPPING,
                    confidence=confidence,
                    risk_score=min(risk_score, 1.0),
                    evidence=[{
                        'unique_bridges': len(unique_bridges),
                        'total_amount': total_amount,
                        'bridges': list(unique_bridges),
                        'transactions': [{'hash': tx['hash'], 'amount': tx['value']} for tx in bridge_txs]
                    }],
                    description=f"Bridge hopping detected: {len(unique_bridges)} different bridges used",
                    severity="medium"
                )
                pattern_matches.append(pattern_match)
        
        return pattern_matches
    
    async def _detect_dex_hopping(self, transactions: List[Dict]) -> List[PatternMatch]:
        """Detect DEX hopping pattern"""
        pattern_matches = []
        
        # Look for multiple DEX transactions
        dex_txs = [tx for tx in transactions if await self._is_dex_transaction(tx)]
        
        if len(dex_txs) >= 3:
            # Check if DEXs are different
            unique_dexs = set()
            for tx in dex_txs:
                dex = await self._get_dex_name(tx['to_address'])
                if dex:
                    unique_dexs.add(dex)
            
            if len(unique_dexs) >= 2:
                total_amount = sum(tx['value'] for tx in dex_txs)
                confidence = min(len(unique_dexs) / 4.0, 1.0)
                risk_score = 0.3 + (len(unique_dexs) * 0.1)
                
                pattern_match = PatternMatch(
                    pattern_type=MLPatternType.DEX_HOPPING,
                    confidence=confidence,
                    risk_score=min(risk_score, 1.0),
                    evidence=[{
                        'unique_dexs': len(unique_dexs),
                        'total_amount': total_amount,
                        'dexes': list(unique_dexs),
                        'transactions': [{'hash': tx['hash'], 'amount': tx['value']} for tx in dex_txs]
                    }],
                    description=f"DEX hopping detected: {len(unique_dexs)} different DEXs used",
                    severity="low"
                )
                pattern_matches.append(pattern_match)
        
        return pattern_matches
    
    async def _detect_high_frequency(self, transactions: List[Dict]) -> List[PatternMatch]:
        """Detect high frequency transaction pattern"""
        pattern_matches = []
        
        # Group transactions by hour
        hourly_groups = self._group_transactions_by_hour(transactions)
        
        for hour, hour_txs in hourly_groups.items():
            if len(hour_txs) > self.high_frequency_threshold:
                total_amount = sum(tx['value'] for tx in hour_txs)
                confidence = min(len(hour_txs) / (self.high_frequency_threshold * 2), 1.0)
                risk_score = 0.3 + (len(hour_txs) / 100)
                
                pattern_match = PatternMatch(
                    pattern_type=MLPatternType.HIGH_FREQUENCY,
                    confidence=confidence,
                    risk_score=min(risk_score, 1.0),
                    evidence=[{
                        'transaction_count': len(hour_txs),
                        'hour': hour,
                        'total_amount': total_amount,
                        'transactions': [{'hash': tx['hash'], 'amount': tx['value']} for tx in hour_txs]
                    }],
                    description=f"High frequency detected: {len(hour_txs)} transactions in one hour",
                    severity="medium" if len(hour_txs) > 50 else "low"
                )
                pattern_matches.append(pattern_match)
        
        return pattern_matches
    
    async def _detect_round_amounts(self, transactions: List[Dict]) -> List[PatternMatch]:
        """Detect round amount pattern"""
        pattern_matches = []
        
        # Look for transactions with round amounts
        round_txs = []
        for tx in transactions:
            if self._is_round_amount(tx['value']):
                round_txs.append(tx)
        
        if len(round_txs) >= 3:
            total_amount = sum(tx['value'] for tx in round_txs)
            confidence = min(len(round_txs) / 5.0, 1.0)
            risk_score = 0.2 + (len(round_txs) / 20)
            
            pattern_match = PatternMatch(
                pattern_type=MLPatternType.ROUND_AMOUNTS,
                confidence=confidence,
                risk_score=min(risk_score, 1.0),
                evidence=[{
                    'round_transactions': len(round_txs),
                    'total_amount': total_amount,
                    'transactions': [{'hash': tx['hash'], 'amount': tx['value']} for tx in round_txs]
                }],
                description=f"Round amounts detected: {len(round_txs)} transactions with round amounts",
                severity="low"
            )
            pattern_matches.append(pattern_match)
        
        return pattern_matches
    
    async def _detect_peak_off_hours(self, transactions: List[Dict]) -> List[PatternMatch]:
        """Detect peak/off hours pattern"""
        pattern_matches = []
        
        # Look for transactions during off-peak hours
        off_peak_txs = []
        for tx in transactions:
            hour = tx['timestamp'].hour
            if hour >= self.off_peak_start or hour <= self.off_peak_end:
                off_peak_txs.append(tx)
        
        if len(off_peak_txs) >= 5:
            total_amount = sum(tx['value'] for tx in off_peak_txs)
            confidence = min(len(off_peak_txs) / 10.0, 1.0)
            risk_score = 0.2 + (len(off_peak_txs) / 30)
            
            pattern_match = PatternMatch(
                pattern_type=MLPatternType.PEAK_OFF_HOURS,
                confidence=confidence,
                risk_score=min(risk_score, 1.0),
                evidence=[{
                    'off_peak_transactions': len(off_peak_txs),
                    'total_amount': total_amount,
                    'transactions': [{'hash': tx['hash'], 'amount': tx['value'], 'hour': tx['timestamp'].hour} for tx in off_peak_txs]
                }],
                description=f"Off-peak hours detected: {len(off_peak_txs)} transactions during off-peak hours",
                severity="low"
            )
            pattern_matches.append(pattern_match)
        
        return pattern_matches
    
    async def _detect_synchronized_transfers(self, transactions: List[Dict]) -> List[PatternMatch]:
        """Detect synchronized transfers pattern"""
        pattern_matches = []
        
        # Look for transfers happening at the same time
        time_groups = {}
        for tx in transactions:
            # Round to nearest 5 minutes
            time_key = tx['timestamp'].replace(second=0, microsecond=0)
            time_key = time_key - timedelta(minutes=time_key.minute % 5)
            
            if time_key not in time_groups:
                time_groups[time_key] = []
            time_groups[time_key].append(tx)
        
        for time_key, time_txs in time_groups.items():
            if len(time_txs) >= 3:
                total_amount = sum(tx['value'] for tx in time_txs)
                confidence = min(len(time_txs) / 5.0, 1.0)
                risk_score = 0.4 + (len(time_txs) / 20)
                
                pattern_match = PatternMatch(
                    pattern_type=MLPatternType.SYNCHRONIZED_TRANSFERS,
                    confidence=confidence,
                    risk_score=min(risk_score, 1.0),
                    evidence=[{
                        'synchronized_time': time_key,
                        'transaction_count': len(time_txs),
                        'total_amount': total_amount,
                        'transactions': [{'hash': tx['hash'], 'amount': tx['value']} for tx in time_txs]
                    }],
                    description=f"Synchronized transfers detected: {len(time_txs)} transactions at {time_key}",
                    severity="medium"
                )
                pattern_matches.append(pattern_match)
        
        return pattern_matches
    
    async def _detect_rapid_chain_switching(self, transactions: List[Dict]) -> List[PatternMatch]:
        """Detect rapid blockchain switching pattern"""
        pattern_matches = []
        
        # Look for rapid switches between blockchains
        if len(transactions) >= 2:
            for i in range(1, len(transactions)):
                prev_tx = transactions[i-1]
                curr_tx = transactions[i]
                
                if (prev_tx['blockchain'] != curr_tx['blockchain'] and
                    (curr_tx['timestamp'] - prev_tx['timestamp']) < self.rapid_switch_threshold):
                    
                    confidence = 0.7
                    risk_score = 0.5
                    
                    pattern_match = PatternMatch(
                        pattern_type=MLPatternType.RAPID_CHAIN_SWITCHING,
                        confidence=confidence,
                        risk_score=risk_score,
                        evidence=[{
                            'from_blockchain': prev_tx['blockchain'],
                            'to_blockchain': curr_tx['blockchain'],
                            'time_difference': (curr_tx['timestamp'] - prev_tx['timestamp']).total_seconds(),
                            'transactions': [{'hash': prev_tx['hash'], 'blockchain': prev_tx['blockchain']}, 
                                             {'hash': curr_tx['hash'], 'blockchain': curr_tx['blockchain']}]
                        }],
                        description=f"Rapid chain switching detected: {prev_tx['blockchain']} to {curr_tx['blockchain']} in {(curr_tx['timestamp'] - prev_tx['timestamp']).total_seconds():.0f} seconds",
                        severity="medium"
                    )
                    pattern_matches.append(pattern_match)
        
        return pattern_matches
    
    async def _detect_splitting_merging(self, transactions: List[Dict]) -> List[PatternMatch]:
        """Detect splitting and merging pattern"""
        pattern_matches = []
        
        # Look for splitting (one address to multiple) and merging (multiple to one)
        address_txs = {}
        for tx in transactions:
            if tx['from_address'] not in address_txs:
                address_txs[tx['from_address']] = []
            address_txs[tx['from_address']].append(tx)
        
        for address, addr_txs in address_txs.items():
            if len(addr_txs) >= 3:
                # Check if amounts are similar (splitting)
                amounts = [tx['value'] for tx in addr_txs]
                amount_std = statistics.stdev(amounts) if len(amounts) > 1 else 0
                amount_mean = statistics.mean(amounts)
                
                if amount_std / amount_mean < 0.1 if amount_mean > 0 else 0:  # Low variance
                    total_amount = sum(amounts)
                    confidence = min(len(addr_txs) / 5.0, 1.0)
                    risk_score = 0.3 + (len(addr_txs) / 20)
                    
                    pattern_match = PatternMatch(
                        pattern_type=MLPatternType.SPLITTING_MERGING,
                        confidence=confidence,
                        risk_score=min(risk_score, 1.0),
                        evidence=[{
                            'address': address,
                            'transaction_count': len(addr_txs),
                            'total_amount': total_amount,
                            'amount_variance': amount_std,
                            'transactions': [{'hash': tx['hash'], 'amount': tx['value']} for tx in addr_txs]
                        }],
                        description=f"Splitting detected: {len(addr_txs)} transactions from {address} with similar amounts",
                        severity="low"
                    )
                    pattern_matches.append(pattern_match)
        
        return pattern_matches
    
    # Helper methods
    def _group_transactions_by_hour(self, transactions: List[Dict]) -> Dict[datetime, List[Dict]]:
        """Group transactions by hour"""
        hourly_groups = {}
        for tx in transactions:
            hour = tx['timestamp'].replace(minute=0, second=0, microsecond=0)
            if hour not in hourly_groups:
                hourly_groups[hour] = []
            hourly_groups[hour].append(tx)
        return hourly_groups
    
    def _find_transaction_chains(self, transactions: List[Dict]) -> List[List[Dict]]:
        """Find transaction chains"""
        chains = []
        # Simplified implementation - in production, use graph algorithms
        for i in range(len(transactions) - 2):
            chain = [transactions[i], transactions[i+1], transactions[i+2]]
            # Check if this forms a valid chain
            if (chain[0]['to_address'] == chain[1]['from_address'] and 
                chain[1]['to_address'] == chain[2]['from_address']):
                chains.append(chain)
        return chains
    
    def _find_circular_paths(self, transactions: List[Dict]) -> List[List[Dict]]:
        """Find circular transaction paths"""
        paths = []
        # Simplified implementation - in production, use graph algorithms
        for i in range(len(transactions) - 2):
            path = [transactions[i], transactions[i+1], transactions[i+2]]
            # Check if this forms a circular path
            if (path[0]['from_address'] == path[2]['to_address']):
                paths.append(path)
        return paths
    
    def _is_round_amount(self, amount: float) -> bool:
        """Check if amount is a round number"""
        # Check for common round numbers
        round_numbers = [1000, 5000, 10000, 25000, 50000, 100000, 250000, 500000, 1000000]
        
        for round_num in round_numbers:
            if abs(amount - round_num) / round_num < self.round_amount_tolerance:
                return True
        
        return False
    
    async def _is_mixer_transaction(self, tx: Dict) -> bool:
        """Check if transaction is to a mixer"""
        # Check against known mixer addresses
        return tx['to_address'] in self.known_mixers
    
    async def _is_privacy_tool_transaction(self, tx: Dict) -> bool:
        """Check if transaction is to a privacy tool"""
        # Check against known privacy tool addresses
        return tx['to_address'] in self.known_privacy_tools
    
    async def _is_bridge_transaction(self, tx: Dict) -> bool:
        """Check if transaction is to a bridge"""
        # Check against known bridge contracts
        return await self.cross_chain_analyzer._is_bridge_transfer(tx)
    
    async def _is_dex_transaction(self, tx: Dict) -> bool:
        """Check if transaction is to a DEX"""
        # Check against known DEX contracts
        return await self.cross_chain_analyzer._is_dex_swap(tx)
    
    async def _get_bridge_name(self, address: str) -> Optional[str]:
        """Get bridge name from address"""
        # This would look up bridge contracts
        return "multichain"  # Placeholder
    
    async def _get_dex_name(self, address: str) -> Optional[str]:
        """Get DEX name from address"""
        # This would look up DEX contracts
        return "uniswap"  # Placeholder
    
    async def _get_legitimate_services(self) -> Set[str]:
        """Get list of legitimate service addresses"""
        # This would return known legitimate services
        return set()  # Placeholder
    
    async def _calculate_transaction_risk(self, tx: Dict) -> float:
        """Calculate risk score for a single transaction"""
        risk = 0.0
        
        # Base risk for amount
        if tx['value'] > 10000:
            risk += 0.2
        elif tx['value'] > 1000:
            risk += 0.1
        
        # Risk for suspicious patterns
        if await self._is_mixer_transaction(tx):
            risk += 0.8
        elif await self._is_privacy_tool_transaction(tx):
            risk += 0.7
        elif await self._is_bridge_transaction(tx):
            risk += 0.2
        elif await self._is_dex_transaction(tx):
            risk += 0.1
        
        return min(risk, 1.0)
    
    async def _update_address_profile(self, address: str, blockchain: str, pattern_matches: List[PatternMatch]):
        """Update address pattern profile"""
        profile = AddressPatternProfile(
            address=address,
            blockchain=blockchain,
            total_transactions=len(pattern_matches),
            total_amount=0,  # Would calculate from transactions
            pattern_matches=pattern_matches,
            risk_score=sum(match.risk_score for match in pattern_matches) / len(pattern_matches) if pattern_matches else 0,
            last_activity=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Store profile in database
        await self._store_profile(profile)
    
    async def _store_profile(self, profile: AddressPatternProfile):
        """Store address profile in database"""
        query = """
        MERGE (p:AddressPatternProfile {address: $address, blockchain: $blockchain})
        SET p.total_transactions = $total_transactions,
            p.total_amount = $total_amount,
            p.risk_score = $risk_score,
            p.last_activity = $last_activity,
            p.updated_at = timestamp(),
            p.pattern_matches = $pattern_matches
        """
        
        async with get_neo4j_session() as session:
            await session.run(query,
                address=profile.address,
                blockchain=profile.blockchain,
                total_transactions=profile.total_transactions,
                total_amount=profile.total_amount,
                risk_score=profile.risk_score,
                last_activity=profile.last_activity,
                pattern_matches=json.dumps([match.__dict__ for match in profile.pattern_matches])
            )
    
    async def get_address_risk_profile(self, address: str, blockchain: str) -> Optional[AddressPatternProfile]:
        """Get risk profile for an address"""
        query = """
        MATCH (p:AddressPatternProfile {address: $address, blockchain: $blockchain})
        RETURN p {
            .address,
            .blockchain,
            .total_transactions,
            .total_amount,
            .risk_score,
            .last_activity,
            .pattern_matches
        } as profile_data
        """
        
        async with get_neo4j_session() as session:
            result = await session.run(query, address=address, blockchain=blockchain)
            record = await result.single()
            
            if record:
                profile_data = record['profile_data']
                return AddressPatternProfile(
                    address=profile_data['address'],
                    blockchain=profile_data['blockchain'],
                    total_transactions=profile_data['total_transactions'],
                    total_amount=profile_data['total_amount'],
                    pattern_matches=[],
                    risk_score=profile_data['risk_score'],
                    last_activity=profile_data['last_activity']
                )
        
        return None
    
    async def cache_pattern_analysis(self, key: str, result: Dict[str, Any]):
        """Cache pattern analysis result in Redis"""
        try:
            async with get_redis_connection() as redis:
                await redis.setex(f"ml_pattern:{key}", self.cache_ttl, json.dumps(result))
        except Exception as e:
            logger.error(f"Error caching pattern analysis: {e}")
    
    async def get_cached_pattern_analysis(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached pattern analysis from Redis"""
        try:
            async with get_redis_connection() as redis:
                cached = await redis.get(f"ml_pattern:{key}")
                return json.loads(cached) if cached else None
        except Exception as e:
            logger.error(f"Error getting cached pattern analysis: {e}")
            return None


# Global pattern detector instance
_ml_pattern_detector: Optional[MLPatternDetector] = None


def get_ml_pattern_detector() -> MLPatternDetector:
    """Get global ML pattern detector instance"""
    global _ml_pattern_detector
    if _ml_pattern_detector is None:
        _ml_pattern_detector = MLPatternDetector()
    return _ml_pattern_detector
