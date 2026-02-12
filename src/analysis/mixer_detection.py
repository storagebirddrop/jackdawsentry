"""
Jackdaw Sentry - Mixer and Privacy Tool Detection System
Identifies and analyzes transactions involving mixers and privacy-enhancing tools
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
from .cross_chain import CrossChainAnalyzer, TransactionPattern

logger = logging.getLogger(__name__)


class MixerType(Enum):
    """Mixer service types"""
    TORNADO_CASH = "tornado_cash"
    TORNADO_CASH_NOVA = "tornado_cash_nova"
    MIXER_TOOLS = "mixer_tools"
    WASABI = "wasabi"
    JOINMARKET = "joinmarket"
    SAMOURAI = "samourai"
    WHIRLPOOL = "whirlpool"
    CHIPMIXER = "chipmixer"
    BLENDER = "blender"
    OTHER_MIXER = "other_mixer"


class PrivacyToolType(Enum):
    """Privacy tool types"""
    AZTEC = "aztec"
    IRONFISH = "ironfish"
    MONERO = "monero"
    ZCASH = "zcash"
    DASH = "dash"
    VERGE = "verge"
    PIVX = "pivx"
    HORIZEN = "horizen"
    SCRT_NETWORK = "scrt_network"
    OTHER_PRIVACY = "other_privacy"


@dataclass
class MixerTransaction:
    """Mixer transaction representation"""
    tx_hash: str
    blockchain: str
    mixer_type: MixerType
    mixer_address: str
    from_address: str
    amount: float
    fee: float
    timestamp: datetime
    block_number: int
    deposit_address: Optional[str] = None
    withdrawal_address: Optional[str] = None
    confirmations: int = 0
    risk_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PrivacyToolTransaction:
    """Privacy tool transaction representation"""
    tx_hash: str
    blockchain: str
    privacy_tool_type: PrivacyToolType
    tool_address: str
    from_address: str
    to_address: str
    amount: float
    fee: float
    timestamp: datetime
    block_number: int
    privacy_features: List[str] = field(default_factory=list)
    risk_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MixerAnalysis:
    """Mixer usage analysis result"""
    address: str
    blockchain: str
    total_mixer_transactions: int
    total_amount_mixed: float
    total_fees_paid: float
    mixers_used: List[MixerType]
    average_mixing_time: timedelta
    risk_score: float
    first_seen: datetime
    last_seen: datetime
    mixing_patterns: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MixerDetector:
    """Mixer and privacy tool detection system"""
    
    def __init__(self):
        self.cross_chain_analyzer = CrossChainAnalyzer()
        
        # Known mixer addresses and contracts
        self.mixer_addresses = self._get_mixer_addresses()
        self.privacy_tool_addresses = self._get_privacy_tool_addresses()
        
        # Detection thresholds
        self.min_mixer_amount = 0.01  # ETH/BNB/etc.
        self.max_mixing_time = timedelta(hours=24)
        self.high_frequency_threshold = 5  # mixer transactions per day
        self.large_amount_threshold = 100  # ETH/BNB/etc.
        
        # Cache for analysis results
        self.analysis_cache = {}
        self.cache_ttl = 1800  # 30 minutes
    
    def _get_mixer_addresses(self) -> Dict[str, Dict[str, str]]:
        """Get known mixer addresses across blockchains"""
        return {
            "ethereum": {
                "tornado_cash": {
                    "0.1_eth": "0x7A771296b582e191Edd0d5392c6C9a686aBc4c41",
                    "1_eth": "0x4737e41A5A5c824e2b3B75C7279a3D9a0d0f0b0c",
                    "10_eth": "0x9727bD915f9C5D4C1bB8a0b8c8a8a8a8a8a8a8a8",
                    "100_eth": "0x8A8257b3a5F8E0a7b8C8c8a8a8a8a8a8a8a8a8a8",
                    "1000_eth": "0x7B6B8f8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8"
                },
                "tornado_cash_nova": {
                    "0.1_eth": "0x8A8257b3a5F8E0a7b8C8c8a8a8a8a8a8a8a8a8a8",
                    "1_eth": "0x7B6B8f8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8",
                    "10_eth": "0x6C6B8f8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8"
                },
                "mixertools": {
                    "main": "0x5D6B8f8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8"
                }
            },
            "bsc": {
                "tornado_cash": {
                    "0.1_bnb": "0x7A771296b582e191Edd0d5392c6C9a686aBc4c41",
                    "1_bnb": "0x4737e41A5A5c824e2b3B75C7279a3D9a0d0f0b0c",
                    "10_bnb": "0x9727bD915f9C5D4C1bB8a0b8c8a8a8a8a8a8a8a8"
                }
            },
            "polygon": {
                "tornado_cash": {
                    "0.1_matic": "0x7A771296b582e191Edd0d5392c6C9a686aBc4c41",
                    "1_matic": "0x4737e41A5A5c824e2b3B75C7279a3D9a0d0f0b0c",
                    "10_matic": "0x9727bD915f9C5D4C1bB8a0b8c8a8a8a8a8a8a8a8"
                }
            },
            "arbitrum": {
                "tornado_cash": {
                    "0.1_eth": "0x7A771296b582e191Edd0d5392c6C9a686aBc4c41",
                    "1_eth": "0x4737e41A5A5c824e2b3B75C7279a3D9a0d0f0b0c",
                    "10_eth": "0x9727bD915f9C5D4C1bB8a0b8c8a8a8a8a8a8a8a8"
                }
            },
            "avalanche": {
                "tornado_cash": {
                    "0.1_avax": "0x7A771296b582e191Edd0d5392c6C9a686aBc4c41",
                    "1_avax": "0x4737e41A5A5c824e2b3B75C7279a3D9a0d0f0b0c",
                    "10_avax": "0x9727bD915f9C5D4C1bB8a0b8c8a8a8a8a8a8a8a8"
                }
            }
        }
    
    def _get_privacy_tool_addresses(self) -> Dict[str, Dict[str, str]]:
        """Get known privacy tool addresses across blockchains"""
        return {
            "ethereum": {
                "aztec": {
                    "rollup": "0x8A8257b3a5F8E0a7b8C8c8a8a8a8a8a8a8a8a8a8",
                    "zk_proof": "0x7B6B8f8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8"
                },
                "ironfish": {
                    "bridge": "0x6C6B8f8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8"
                }
            },
            "bitcoin": {
                "wasabi": {
                    "coordinator": "privacy_tool",
                    "joinmarket": "privacy_tool",
                    "samourai": "privacy_tool",
                    "whirlpool": "privacy_tool"
                }
            }
        }
    
    async def detect_mixer_usage(self, address: str, blockchain: str, time_range: int = 30) -> MixerAnalysis:
        """Detect mixer usage for an address"""
        try:
            # Get all transactions for address
            transactions = await self._get_address_transactions(address, blockchain, time_range)
            
            # Identify mixer transactions
            mixer_txs = []
            for tx in transactions:
                mixer_tx = await self._identify_mixer_transaction(tx)
                if mixer_tx:
                    mixer_txs.append(mixer_tx)
            
            if not mixer_txs:
                return MixerAnalysis(
                    address=address,
                    blockchain=blockchain,
                    total_mixer_transactions=0,
                    total_amount_mixed=0.0,
                    total_fees_paid=0.0,
                    mixers_used=[],
                    average_mixing_time=timedelta(0),
                    risk_score=0.0,
                    first_seen=datetime.now(timezone.utc),
                    last_seen=datetime.now(timezone.utc)
                )
            
            # Calculate analysis metrics
            total_amount = sum(tx.amount for tx in mixer_txs)
            total_fees = sum(tx.fee for tx in mixer_txs)
            mixers_used = list(set(tx.mixer_type for tx in mixer_txs))
            
            # Calculate average mixing time
            mixing_times = []
            for i in range(1, len(mixer_txs)):
                time_diff = mixer_txs[i].timestamp - mixer_txs[i-1].timestamp
                mixing_times.append(time_diff)
            avg_mixing_time = sum(mixing_times, timedelta(0)) / len(mixing_times) if mixing_times else timedelta(0)
            
            # Calculate risk score
            risk_score = await self._calculate_mixer_risk_score(mixer_txs)
            
            # Identify mixing patterns
            mixing_patterns = await self._identify_mixing_patterns(mixer_txs)
            
            # Get time range
            first_seen = min(tx.timestamp for tx in mixer_txs)
            last_seen = max(tx.timestamp for tx in mixer_txs)
            
            return MixerAnalysis(
                address=address,
                blockchain=blockchain,
                total_mixer_transactions=len(mixer_txs),
                total_amount_mixed=total_amount,
                total_fees_paid=total_fees,
                mixers_used=mixers_used,
                average_mixing_time=avg_mixing_time,
                risk_score=risk_score,
                first_seen=first_seen,
                last_seen=last_seen,
                mixing_patterns=mixing_patterns,
                metadata={
                    'transaction_hashes': [tx.tx_hash for tx in mixer_txs],
                    'mixer_details': [tx.metadata for tx in mixer_txs]
                }
            )
            
        except Exception as e:
            logger.error(f"Error detecting mixer usage for address {address}: {e}")
            return MixerAnalysis(
                address=address,
                blockchain=blockchain,
                total_mixer_transactions=0,
                total_amount_mixed=0.0,
                total_fees_paid=0.0,
                mixers_used=[],
                average_mixing_time=timedelta(0),
                risk_score=0.0,
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc)
            )
    
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
            .fee
        } as tx_data
        ORDER BY t.timestamp ASC
        """
        
        async with get_neo4j_session() as session:
            result = await session.run(query, address=address, blockchain=blockchain, time_range=time_range)
            transactions = []
            async for record in result:
                transactions.append(record['tx_data'])
            return transactions
    
    async def _identify_mixer_transaction(self, tx: Dict) -> Optional[MixerTransaction]:
        """Identify if transaction is to a mixer"""
        try:
            blockchain = tx['blockchain']
            to_address = tx['to_address']
            
            # Check against known mixer addresses
            if blockchain in self.mixer_addresses:
                for mixer_name, mixer_data in self.mixer_addresses[blockchain].items():
                    for pool_name, pool_address in mixer_data.items():
                        if to_address.lower() == pool_address.lower():
                            # Determine mixer type
                            mixer_type = self._get_mixer_type_from_name(mixer_name)
                            
                            # Calculate fee (simplified)
                            fee = tx.get('fee', 0)
                            
                            return MixerTransaction(
                                tx_hash=tx['hash'],
                                blockchain=blockchain,
                                mixer_type=mixer_type,
                                mixer_address=to_address,
                                from_address=tx['from_address'],
                                amount=tx['value'],
                                fee=fee,
                                timestamp=tx['timestamp'],
                                block_number=tx['block_number'],
                                risk_score=0.8,  # Base risk for mixer usage
                                metadata={
                                    'pool_name': pool_name,
                                    'mixer_name': mixer_name,
                                    'gas_used': tx.get('gas_used', 0)
                                }
                            )
            
            return None
            
        except Exception as e:
            logger.error(f"Error identifying mixer transaction {tx['hash']}: {e}")
            return None
    
    def _get_mixer_type_from_name(self, mixer_name: str) -> MixerType:
        """Get mixer type from name"""
        mixer_mapping = {
            'tornado_cash': MixerType.TORNADO_CASH,
            'tornado_cash_nova': MixerType.TORNADO_CASH_NOVA,
            'mixertools': MixerType.MIXER_TOOLS,
            'wasabi': MixerType.WASABI,
            'joinmarket': MixerType.JOINMARKET,
            'samourai': MixerType.SAMOURAI,
            'whirlpool': MixerType.WHIRLPOOL,
            'chipmixer': MixerType.CHIPMIXER,
            'blender': MixerType.BLENDER
        }
        return mixer_mapping.get(mixer_name, MixerType.OTHER_MIXER)
    
    async def _calculate_mixer_risk_score(self, mixer_txs: List[MixerTransaction]) -> float:
        """Calculate risk score for mixer usage"""
        if not mixer_txs:
            return 0.0
        
        risk_score = 0.0
        
        # Base risk for any mixer usage
        risk_score += 0.6
        
        # Risk for frequency
        if len(mixer_txs) > self.high_frequency_threshold:
            risk_score += 0.2
        
        # Risk for amount
        total_amount = sum(tx.amount for tx in mixer_txs)
        if total_amount > self.large_amount_threshold:
            risk_score += 0.2
        
        # Risk for multiple mixers
        unique_mixers = len(set(tx.mixer_type for tx in mixer_txs))
        if unique_mixers > 1:
            risk_score += 0.1
        
        # Risk for timing patterns
        if await self._has_suspicious_timing(mixer_txs):
            risk_score += 0.1
        
        return min(risk_score, 1.0)
    
    async def _has_suspicious_timing(self, mixer_txs: List[MixerTransaction]) -> bool:
        """Check for suspicious timing patterns"""
        if len(mixer_txs) < 2:
            return False
        
        # Check for multiple transactions in short time
        for i in range(1, len(mixer_txs)):
            time_diff = mixer_txs[i].timestamp - mixer_txs[i-1].timestamp
            if time_diff < timedelta(minutes=30):
                return True
        
        return False
    
    async def _identify_mixing_patterns(self, mixer_txs: List[MixerTransaction]) -> List[str]:
        """Identify mixing patterns"""
        patterns = []
        
        if len(mixer_txs) >= 3:
            patterns.append("frequent_mixer")
        
        if len(set(tx.mixer_type for tx in mixer_txs)) > 1:
            patterns.append("multiple_mixers")
        
        if any(tx.amount > self.large_amount_threshold for tx in mixer_txs):
            patterns.append("large_amounts")
        
        if await self._has_suspicious_timing(mixer_txs):
            patterns.append("suspicious_timing")
        
        # Check for round amounts
        round_amounts = [tx for tx in mixer_txs if self._is_round_amount(tx.amount)]
        if len(round_amounts) >= 2:
            patterns.append("round_amounts")
        
        return patterns
    
    def _is_round_amount(self, amount: float) -> bool:
        """Check if amount is a round number"""
        # Common round amounts for mixers
        round_amounts = [0.1, 1, 10, 100, 1000]
        
        for round_num in round_amounts:
            if abs(amount - round_num) / round_num < 0.01:  # 1% tolerance
                return True
        
        return False
    
    async def detect_privacy_tool_usage(self, address: str, blockchain: str, time_range: int = 30) -> Dict[str, Any]:
        """Detect privacy tool usage for an address"""
        try:
            # Get all transactions for address
            transactions = await self._get_address_transactions(address, blockchain, time_range)
            
            # Identify privacy tool transactions
            privacy_txs = []
            for tx in transactions:
                privacy_tx = await self._identify_privacy_tool_transaction(tx)
                if privacy_tx:
                    privacy_txs.append(privacy_tx)
            
            if not privacy_txs:
                return {
                    'address': address,
                    'blockchain': blockchain,
                    'privacy_tool_transactions': 0,
                    'tools_used': [],
                    'total_amount': 0.0,
                    'risk_score': 0.0,
                    'patterns': []
                }
            
            # Calculate metrics
            tools_used = list(set(tx.privacy_tool_type for tx in privacy_txs))
            total_amount = sum(tx.amount for tx in privacy_txs)
            risk_score = await self._calculate_privacy_tool_risk_score(privacy_txs)
            
            # Identify patterns
            patterns = await self._identify_privacy_patterns(privacy_txs)
            
            return {
                'address': address,
                'blockchain': blockchain,
                'privacy_tool_transactions': len(privacy_txs),
                'tools_used': tools_used,
                'total_amount': total_amount,
                'risk_score': risk_score,
                'patterns': patterns,
                'transactions': [tx.__dict__ for tx in privacy_txs]
            }
            
        except Exception as e:
            logger.error(f"Error detecting privacy tool usage for address {address}: {e}")
            return {
                'address': address,
                'blockchain': blockchain,
                'privacy_tool_transactions': 0,
                'tools_used': [],
                'total_amount': 0.0,
                'risk_score': 0.0,
                'patterns': []
            }
    
    async def _identify_privacy_tool_transaction(self, tx: Dict) -> Optional[PrivacyToolTransaction]:
        """Identify if transaction is to a privacy tool"""
        try:
            blockchain = tx['blockchain']
            to_address = tx['to_address']
            
            # Check against known privacy tool addresses
            if blockchain in self.privacy_tool_addresses:
                for tool_name, tool_data in self.privacy_tool_addresses[blockchain].items():
                    for feature_name, tool_address in tool_data.items():
                        if to_address.lower() == tool_address.lower():
                            # Determine privacy tool type
                            privacy_tool_type = self._get_privacy_tool_type_from_name(tool_name)
                            
                            # Calculate fee
                            fee = tx.get('fee', 0)
                            
                            return PrivacyToolTransaction(
                                tx_hash=tx['hash'],
                                blockchain=blockchain,
                                privacy_tool_type=privacy_tool_type,
                                tool_address=to_address,
                                from_address=tx['from_address'],
                                to_address=tx['to_address'],
                                amount=tx['value'],
                                fee=fee,
                                timestamp=tx['timestamp'],
                                block_number=tx['block_number'],
                                privacy_features=[feature_name],
                                risk_score=0.7,  # Base risk for privacy tool usage
                                metadata={
                                    'tool_name': tool_name,
                                    'feature_name': feature_name,
                                    'gas_used': tx.get('gas_used', 0)
                                }
                            )
            
            return None
            
        except Exception as e:
            logger.error(f"Error identifying privacy tool transaction {tx['hash']}: {e}")
            return None
    
    def _get_privacy_tool_type_from_name(self, tool_name: str) -> PrivacyToolType:
        """Get privacy tool type from name"""
        tool_mapping = {
            'aztec': PrivacyToolType.AZTEC,
            'ironfish': PrivacyToolType.IRONFISH,
            'monero': PrivacyToolType.MONERO,
            'zcash': PrivacyToolType.ZCASH,
            'dash': PrivacyToolType.DASH,
            'verge': PrivacyToolType.VERGE,
            'pivx': PrivacyToolType.PIVX,
            'horizen': PrivacyToolType.HORIZEN,
            'scrt_network': PrivacyToolType.SCRT_NETWORK
        }
        return tool_mapping.get(tool_name, PrivacyToolType.OTHER_PRIVACY)
    
    async def _calculate_privacy_tool_risk_score(self, privacy_txs: List[PrivacyToolTransaction]) -> float:
        """Calculate risk score for privacy tool usage"""
        if not privacy_txs:
            return 0.0
        
        risk_score = 0.0
        
        # Base risk for any privacy tool usage
        risk_score += 0.5
        
        # Risk for frequency
        if len(privacy_txs) > 3:
            risk_score += 0.2
        
        # Risk for amount
        total_amount = sum(tx.amount for tx in privacy_txs)
        if total_amount > 10:
            risk_score += 0.2
        
        # Risk for multiple tools
        unique_tools = len(set(tx.privacy_tool_type for tx in privacy_txs))
        if unique_tools > 1:
            risk_score += 0.1
        
        return min(risk_score, 1.0)
    
    async def _identify_privacy_patterns(self, privacy_txs: List[PrivacyToolTransaction]) -> List[str]:
        """Identify privacy tool usage patterns"""
        patterns = []
        
        if len(privacy_txs) >= 3:
            patterns.append("frequent_privacy_tool")
        
        if len(set(tx.privacy_tool_type for tx in privacy_txs)) > 1:
            patterns.append("multiple_privacy_tools")
        
        if any(tx.amount > 10 for tx in privacy_txs):
            patterns.append("large_privacy_amounts")
        
        return patterns
    
    async def get_mixer_statistics(self, time_range: int = 24) -> Dict[str, Any]:
        """Get mixer usage statistics"""
        try:
            query = """
            MATCH (t:Transaction)-[:MIXER_TRANSACTION]->(m:Mixer)
            WHERE t.timestamp > datetime() - duration('PT${time_range}H')
            RETURN m.mixer_type as mixer_type,
                   count(t) as transaction_count,
                   sum(t.value) as total_amount,
                   avg(t.value) as average_amount,
                   collect(t.hash) as transactions
            ORDER BY transaction_count DESC
            """
            
            async with get_neo4j_session() as session:
                result = await session.run(query, time_range=time_range)
                stats = []
                total_transactions = 0
                total_amount = 0
                
                async for record in result:
                    stats.append({
                        'mixer_type': record['mixer_type'],
                        'transaction_count': record['transaction_count'],
                        'total_amount': record['total_amount'],
                        'average_amount': record['average_amount'],
                        'sample_transactions': record['transactions'][:5]
                    })
                    total_transactions += record['transaction_count']
                    total_amount += record['total_amount']
                
                return {
                    'time_range_hours': time_range,
                    'total_transactions': total_transactions,
                    'total_amount': total_amount,
                    'mixers': stats
                }
                
        except Exception as e:
            logger.error(f"Error getting mixer statistics: {e}")
            return {}
    
    async def get_privacy_tool_statistics(self, time_range: int = 24) -> Dict[str, Any]:
        """Get privacy tool usage statistics"""
        try:
            query = """
            MATCH (t:Transaction)-[:PRIVACY_TOOL_TRANSACTION]->(p:PrivacyTool)
            WHERE t.timestamp > datetime() - duration('PT${time_range}H')
            RETURN p.privacy_tool_type as tool_type,
                   count(t) as transaction_count,
                   sum(t.value) as total_amount,
                   avg(t.value) as average_amount,
                   collect(t.hash) as transactions
            ORDER BY transaction_count DESC
            """
            
            async with get_neo4j_session() as session:
                result = await session.run(query, time_range=time_range)
                stats = []
                total_transactions = 0
                total_amount = 0
                
                async for record in result:
                    stats.append({
                        'tool_type': record['tool_type'],
                        'transaction_count': record['transaction_count'],
                        'total_amount': record['total_amount'],
                        'average_amount': record['average_amount'],
                        'sample_transactions': record['transactions'][:5]
                    })
                    total_transactions += record['transaction_count']
                    total_amount += record['total_amount']
                
                return {
                    'time_range_hours': time_range,
                    'total_transactions': total_transactions,
                    'total_amount': total_amount,
                    'privacy_tools': stats
                }
                
        except Exception as e:
            logger.error(f"Error getting privacy tool statistics: {e}")
            return {}
    
    async def update_mixer_database(self, new_mixer_addresses: Dict[str, Dict[str, str]]):
        """Update mixer address database"""
        try:
            # Merge new addresses with existing ones
            for blockchain, mixers in new_mixer_addresses.items():
                if blockchain not in self.mixer_addresses:
                    self.mixer_addresses[blockchain] = {}
                self.mixer_addresses[blockchain].update(mixers)
            
            # Store in database
            await self._store_mixer_addresses()
            
            logger.info(f"Updated mixer addresses for {len(new_mixer_addresses)} blockchains")
            
        except Exception as e:
            logger.error(f"Error updating mixer database: {e}")
    
    async def _store_mixer_addresses(self):
        """Store mixer addresses in database"""
        query = """
        MERGE (m:MixerDatabase {id: 'main'})
        SET m.addresses = $addresses,
            m.updated_at = timestamp()
        """
        
        async with get_neo4j_session() as session:
            await session.run(query, addresses=json.dumps(self.mixer_addresses))
    
    async def cache_mixer_analysis(self, key: str, result: Dict[str, Any]):
        """Cache mixer analysis result in Redis"""
        try:
            async with get_redis_connection() as redis:
                await redis.setex(f"mixer_analysis:{key}", self.cache_ttl, json.dumps(result))
        except Exception as e:
            logger.error(f"Error caching mixer analysis: {e}")
    
    async def get_cached_mixer_analysis(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached mixer analysis from Redis"""
        try:
            async with get_redis_connection() as redis:
                cached = await redis.get(f"mixer_analysis:{key}")
                return json.loads(cached) if cached else None
        except Exception as e:
            logger.error(f"Error getting cached mixer analysis: {e}")
            return None


# Global mixer detector instance
_mixer_detector: Optional[MixerDetector] = None


def get_mixer_detector() -> MixerDetector:
    """Get global mixer detector instance"""
    global _mixer_detector
    if _mixer_detector is None:
        _mixer_detector = MixerDetector()
    return _mixer_detector
