"""
Jackdaw Sentry - Stablecoin Flow Tracking System
Tracks stablecoin movements across bridges, DEXs, and blockchains
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum
import json

from src.api.database import get_neo4j_session, get_redis_connection
from src.api.config import settings
from .cross_chain import CrossChainAnalyzer, TransactionPattern

logger = logging.getLogger(__name__)


class FlowType(Enum):
    """Stablecoin flow types"""
    BRIDGE_TRANSFER = "bridge_transfer"
    DEX_SWAP = "dex_swap"
    CROSS_CHAIN_SWAP = "cross_chain_swap"
    CIRCULAR_FLOW = "circular_flow"
    LAYER_HOPPING = "layer_hopping"
    MIXING_FLOW = "mixing_flow"
    PRIVACY_FLOW = "privacy_flow"
    HIGH_VOLUME_FLOW = "high_volume_flow"
    SUSPICIOUS_FLOW = "suspicious_flow"


@dataclass
class StablecoinFlow:
    """Stablecoin flow representation"""
    flow_id: str
    stablecoin_symbol: str
    start_address: str
    end_address: str
    total_amount: float
    path: List[Dict[str, Any]]
    blockchains: List[str]
    flow_type: FlowType
    duration: timedelta
    hop_count: int
    risk_score: float
    confidence: float
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BridgeFlow:
    """Bridge-specific flow information"""
    bridge_name: str
    from_blockchain: str
    to_blockchain: str
    amount: float
    fee: float
    timestamp: datetime
    tx_hash: str
    confirmations: int = 0


@dataclass
class DEXFlow:
    """DEX-specific flow information"""
    dex_name: str
    blockchain: str
    from_token: str
    to_token: str
    amount_in: float
    amount_out: float
    price_impact: float
    timestamp: datetime
    tx_hash: str


class StablecoinFlowTracker:
    """Stablecoin flow tracking and analysis system"""
    
    def __init__(self):
        self.supported_stablecoins = {
            'USDT', 'USDC', 'USDe', 'USDS', 'USD1', 'BUSD', 'A7A5',
            'EURC', 'EURT', 'EURS', 'RLUSD', 'BRZ'
        }
        
        self.cross_chain_analyzer = CrossChainAnalyzer()
        
        # Flow tracking thresholds
        self.min_flow_amount = 1000  # USD
        self.max_flow_duration = timedelta(hours=24)
        self.max_hops = 10
        self.high_volume_threshold = 100000  # USD
        
        # Cache for flow analysis
        self.flow_cache = {}
        self.cache_ttl = 1800  # 30 minutes
    
    async def track_stablecoin_flow(self, tx_hash: str, blockchain: str) -> Optional[StablecoinFlow]:
        """Track stablecoin flow for a specific transaction"""
        try:
            # Analyze the transaction
            tx_analysis = await self.cross_chain_analyzer.analyze_transaction(tx_hash, blockchain)
            if not tx_analysis:
                return None
            
            # Check if it's a stablecoin transaction
            if not await self._is_stablecoin_transaction(tx_analysis):
                return None
            
            # Determine flow type
            flow_type = await self._determine_flow_type(tx_analysis)
            
            # Build flow path
            flow_path = await self._build_flow_path(tx_analysis)
            
            # Calculate flow metrics
            total_amount = await self._calculate_total_amount(flow_path)
            blockchains = list(set(step['blockchain'] for step in flow_path))
            duration = await self._calculate_flow_duration(flow_path)
            hop_count = len(flow_path)
            
            # Calculate risk score
            risk_score = await self._calculate_flow_risk_score(flow_path, flow_type)
            
            # Calculate confidence
            confidence = await self._calculate_flow_confidence(flow_path)
            
            # Create flow object
            flow = StablecoinFlow(
                flow_id=f"{tx_hash}_{datetime.now(timezone.utc).timestamp()}",
                stablecoin_symbol=tx_analysis.token_symbol,
                start_address=tx_analysis.from_address,
                end_address=tx_analysis.to_address,
                total_amount=total_amount,
                path=flow_path,
                blockchains=blockchains,
                flow_type=flow_type,
                duration=duration,
                hop_count=hop_count,
                risk_score=risk_score,
                confidence=confidence,
                metadata=await self._extract_flow_metadata(flow_path)
            )
            
            # Store flow in database
            await self._store_flow(flow)
            
            return flow
            
        except Exception as e:
            logger.error(f"Error tracking stablecoin flow for {tx_hash}: {e}")
            return None
    
    async def _is_stablecoin_transaction(self, tx_analysis) -> bool:
        """Check if transaction involves stablecoins"""
        return (tx_analysis.token_symbol in self.supported_stablecoins or
                any(pattern == TransactionPattern.STABLECOIN_FLOW for pattern in tx_analysis.patterns))
    
    async def _determine_flow_type(self, tx_analysis) -> FlowType:
        """Determine the type of stablecoin flow"""
        patterns = tx_analysis.patterns
        
        if TransactionPattern.BRIDGE_TRANSFER in patterns:
            return FlowType.BRIDGE_TRANSFER
        elif TransactionPattern.DEX_SWAP in patterns:
            return FlowType.DEX_SWAP
        elif TransactionPattern.MIXER_USAGE in patterns:
            return FlowType.MIXING_FLOW
        elif TransactionPattern.PRIVACY_TOOL in patterns:
            return FlowType.PRIVACY_FLOW
        elif TransactionPattern.LAYER_HOPPING in patterns:
            return FlowType.LAYER_HOPPING
        elif TransactionPattern.CIRCULAR_TRADING in patterns:
            return FlowType.CIRCULAR_FLOW
        elif TransactionPattern.HIGH_FREQUENCY in patterns:
            return FlowType.HIGH_VOLUME_FLOW
        elif TransactionPattern.SUSPICIOUS_TIMING in patterns:
            return FlowType.SUSPICIOUS_FLOW
        else:
            return FlowType.CROSS_CHAIN_SWAP
    
    async def _build_flow_path(self, tx_analysis) -> List[Dict[str, Any]]:
        """Build the flow path for a transaction"""
        path = []
        
        # Add current transaction
        path.append({
            'tx_hash': tx_analysis.tx_hash,
            'blockchain': tx_analysis.blockchain,
            'from_address': tx_analysis.from_address,
            'to_address': tx_analysis.to_address,
            'amount': tx_analysis.amount,
            'token_symbol': tx_analysis.token_symbol,
            'timestamp': tx_analysis.timestamp,
            'type': await self._get_transaction_type(tx_analysis)
        })
        
        # Find related transactions
        for related_tx_hash in tx_analysis.related_transactions:
            related_tx = await self.cross_chain_analyzer.analyze_transaction(
                related_tx_hash, tx_analysis.blockchain
            )
            if related_tx and related_tx.token_symbol == tx_analysis.token_symbol:
                path.append({
                    'tx_hash': related_tx.tx_hash,
                    'blockchain': related_tx.blockchain,
                    'from_address': related_tx.from_address,
                    'to_address': related_tx.to_address,
                    'amount': related_tx.amount,
                    'token_symbol': related_tx.token_symbol,
                    'timestamp': related_tx.timestamp,
                    'type': await self._get_transaction_type(related_tx)
                })
        
        # Sort by timestamp
        path.sort(key=lambda x: x['timestamp'])
        
        return path
    
    async def _get_transaction_type(self, tx_analysis) -> str:
        """Get transaction type based on patterns"""
        if TransactionPattern.BRIDGE_TRANSFER in tx_analysis.patterns:
            return 'bridge'
        elif TransactionPattern.DEX_SWAP in tx_analysis.patterns:
            return 'dex_swap'
        elif TransactionPattern.MIXER_USAGE in tx_analysis.patterns:
            return 'mixer'
        elif TransactionPattern.PRIVACY_TOOL in tx_analysis.patterns:
            return 'privacy_tool'
        else:
            return 'transfer'
    
    async def _calculate_total_amount(self, flow_path: List[Dict[str, Any]]) -> float:
        """Calculate representative transfer amount (use max to avoid double-counting multi-hop)"""
        if not flow_path:
            return 0.0
        return max(step['amount'] for step in flow_path)
    
    async def _calculate_flow_duration(self, flow_path: List[Dict[str, Any]]) -> timedelta:
        """Calculate flow duration"""
        if len(flow_path) < 2:
            return timedelta(0)
        
        start_time = flow_path[0]['timestamp']
        end_time = flow_path[-1]['timestamp']
        return end_time - start_time
    
    async def _calculate_flow_risk_score(self, flow_path: List[Dict[str, Any]], flow_type: FlowType) -> float:
        """Calculate risk score for the flow"""
        risk_score = 0.0
        
        # Base risk by flow type
        flow_type_risks = {
            FlowType.BRIDGE_TRANSFER: 0.2,
            FlowType.DEX_SWAP: 0.1,
            FlowType.CROSS_CHAIN_SWAP: 0.3,
            FlowType.CIRCULAR_FLOW: 0.8,
            FlowType.LAYER_HOPPING: 0.4,
            FlowType.MIXING_FLOW: 0.9,
            FlowType.PRIVACY_FLOW: 0.8,
            FlowType.HIGH_VOLUME_FLOW: 0.3,
            FlowType.SUSPICIOUS_FLOW: 0.7
        }
        
        risk_score += flow_type_risks.get(flow_type, 0.3)
        
        # Add risk for hop count
        hop_count_risk = min(len(flow_path) * 0.05, 0.3)
        risk_score += hop_count_risk
        
        # Add risk for duration
        duration_hours = await self._calculate_flow_duration(flow_path).total_seconds() / 3600
        duration_risk = min(duration_hours * 0.01, 0.2)
        risk_score += duration_risk
        
        # Add risk for blockchain diversity
        blockchain_count = len(set(step['blockchain'] for step in flow_path))
        blockchain_risk = min(blockchain_count * 0.1, 0.3)
        risk_score += blockchain_risk
        
        # Add risk for suspicious transaction types
        suspicious_types = ['mixer', 'privacy_tool']
        suspicious_count = sum(1 for step in flow_path if step['type'] in suspicious_types)
        suspicious_risk = min(suspicious_count * 0.2, 0.4)
        risk_score += suspicious_risk
        
        return min(risk_score, 1.0)
    
    async def _calculate_flow_confidence(self, flow_path: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for the flow"""
        confidence = 0.5  # Base confidence
        
        # Increase confidence with more data points
        confidence += min(len(flow_path) * 0.05, 0.3)
        
        # Increase confidence if we have complete timestamps
        if all(step.get('timestamp') for step in flow_path):
            confidence += 0.1
        
        # Increase confidence if all transactions have the same token
        tokens = set(step['token_symbol'] for step in flow_path)
        if len(tokens) == 1:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    async def _extract_flow_metadata(self, flow_path: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract metadata from flow path"""
        metadata = {
            'bridge_count': 0,
            'dex_count': 0,
            'mixer_count': 0,
            'privacy_tool_count': 0,
            'unique_addresses': set(),
            'total_fees': 0.0,
            'average_hop_time': 0.0
        }
        
        # Count transaction types
        for step in flow_path:
            metadata['unique_addresses'].add(step['from_address'])
            metadata['unique_addresses'].add(step['to_address'])
            
            if step['type'] == 'bridge':
                metadata['bridge_count'] += 1
            elif step['type'] == 'dex_swap':
                metadata['dex_count'] += 1
            elif step['type'] == 'mixer':
                metadata['mixer_count'] += 1
            elif step['type'] == 'privacy_tool':
                metadata['privacy_tool_count'] += 1
        
        metadata['unique_addresses'] = len(metadata['unique_addresses'])
        
        # Calculate average hop time
        if len(flow_path) > 1:
            hop_times = []
            for i in range(1, len(flow_path)):
                hop_time = (flow_path[i]['timestamp'] - flow_path[i-1]['timestamp']).total_seconds()
                hop_times.append(hop_time)
            metadata['average_hop_time'] = sum(hop_times) / len(hop_times)
        
        return metadata
    
    async def _store_flow(self, flow: StablecoinFlow):
        """Store flow in database"""
        query = """
        MERGE (f:StablecoinFlow {flow_id: $flow_id})
        SET f.stablecoin_symbol = $stablecoin_symbol,
            f.start_address = $start_address,
            f.end_address = $end_address,
            f.total_amount = $total_amount,
            f.blockchains = $blockchains,
            f.flow_type = $flow_type,
            f.duration = $duration,
            f.hop_count = $hop_count,
            f.risk_score = $risk_score,
            f.confidence = $confidence,
            f.path = $path,
            f.metadata = $metadata,
            f.created_at = timestamp()
        """
        
        async with get_neo4j_session() as session:
            await session.run(query,
                flow_id=flow.flow_id,
                stablecoin_symbol=flow.stablecoin_symbol,
                start_address=flow.start_address,
                end_address=flow.end_address,
                total_amount=flow.total_amount,
                blockchains=flow.blockchains,
                flow_type=flow.flow_type.value,
                duration=flow.duration.total_seconds(),
                hop_count=flow.hop_count,
                risk_score=flow.risk_score,
                confidence=flow.confidence,
                path=json.dumps(flow.path, default=str),
                metadata=json.dumps(flow.metadata)
            )
    
    async def analyze_stablecoin_flows(self, address: str, time_range: int = 24) -> Dict[str, Any]:
        """Analyze all stablecoin flows for an address"""
        try:
            # Get all stablecoin transactions for address
            transactions = await self._get_stablecoin_transactions(address, time_range)
            
            # Group transactions by stablecoin symbol
            stablecoin_groups = {}
            for tx in transactions:
                symbol = tx['token_symbol']
                if symbol not in stablecoin_groups:
                    stablecoin_groups[symbol] = []
                stablecoin_groups[symbol].append(tx)
            
            # Analyze flows for each stablecoin
            flow_analysis = {}
            for symbol, txs in stablecoin_groups.items():
                flow_analysis[symbol] = await self._analyze_stablecoin_group_flows(address, symbol, txs)
            
            # Calculate overall metrics
            total_flows = sum(analysis['total_flows'] for analysis in flow_analysis.values())
            total_amount = sum(analysis['total_amount'] for analysis in flow_analysis.values())
            avg_risk_score = sum(analysis['average_risk_score'] for analysis in flow_analysis.values()) / len(flow_analysis) if flow_analysis else 0
            
            # Get flow type distribution
            flow_type_counts = {}
            for analysis in flow_analysis.values():
                for flow_type, count in analysis['flow_type_distribution'].items():
                    flow_type_counts[flow_type] = flow_type_counts.get(flow_type, 0) + count
            
            return {
                'address': address,
                'time_range_hours': time_range,
                'total_flows': total_flows,
                'total_amount': total_amount,
                'average_risk_score': avg_risk_score,
                'stablecoin_breakdown': flow_analysis,
                'flow_type_distribution': flow_type_counts,
                'high_risk_flows': await self._get_high_risk_flows(address, time_range),
                'recent_flows': await self._get_recent_flows(address, time_range)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing stablecoin flows for address {address}: {e}")
            return {}
    
    async def _get_stablecoin_transactions(self, address: str, time_range: int) -> List[Dict]:
        """Get stablecoin transactions for address"""
        query = """
        MATCH (a:Address {address: $address})-[r:SENT]->(t:Transaction)
        WHERE t.timestamp > datetime() - duration({hours: $time_range})
        AND EXISTS {
            MATCH (t)-[:STABLECOIN_TRANSFER]->(s:Stablecoin)
        }
        RETURN t {
            .hash,
            .blockchain,
            .from_address,
            .to_address,
            .value,
            .timestamp,
            .block_number,
            .fee
        } as tx_data
        ORDER BY t.timestamp DESC
        LIMIT 100
        """
        
        async with get_neo4j_session() as session:
            result = await session.run(query, address=address, time_range=time_range)
            transactions = []
            async for record in result:
                # Get stablecoin symbol for this transaction
                stablecoin_info = await self._get_transaction_stablecoin(record['tx_data']['hash'])
                if stablecoin_info:
                    record['tx_data']['token_symbol'] = stablecoin_info['symbol']
                    transactions.append(record['tx_data'])
            return transactions
    
    async def _get_transaction_stablecoin(self, tx_hash: str) -> Optional[Dict]:
        """Get stablecoin information for transaction"""
        query = """
        MATCH (t:Transaction {hash: $tx_hash})-[:STABLECOIN_TRANSFER]->(s:Stablecoin)
        RETURN s.symbol as symbol, s.amount as amount, s.decimals as decimals
        """
        
        async with get_neo4j_session() as session:
            result = await session.run(query, tx_hash=tx_hash)
            record = await result.single()
            return {
                'symbol': record['symbol'],
                'amount': record['amount'],
                'decimals': record['decimals']
            } if record else None
    
    async def _analyze_stablecoin_group_flows(self, address: str, symbol: str, transactions: List[Dict]) -> Dict[str, Any]:
        """Analyze flows for a specific stablecoin group"""
        flows = []
        total_amount = 0
        risk_scores = []
        
        for tx in transactions:
            # Track flow for this transaction
            flow = await self.track_stablecoin_flow(tx['hash'], tx['blockchain'])
            if flow:
                flows.append(flow)
                total_amount += flow.total_amount
                risk_scores.append(flow.risk_score)
        
        # Count flow types
        flow_type_counts = {}
        for flow in flows:
            flow_type = flow.flow_type.value
            flow_type_counts[flow_type] = flow_type_counts.get(flow_type, 0) + 1
        
        return {
            'stablecoin_symbol': symbol,
            'total_flows': len(flows),
            'total_amount': total_amount,
            'average_risk_score': sum(risk_scores) / len(risk_scores) if risk_scores else 0,
            'flow_type_distribution': flow_type_counts,
            'high_risk_flow_count': sum(1 for flow in flows if flow.risk_score > 0.7),
            'average_confidence': sum(flow.confidence for flow in flows) / len(flows) if flows else 0
        }
    
    async def _get_high_risk_flows(self, address: str, time_range: int) -> List[Dict]:
        """Get high-risk stablecoin flows for address"""
        query = """
        MATCH (a:Address {address: $address})-[r:SENT*1..5]->(f:StablecoinFlow)
        WHERE f.risk_score > 0.7
        AND f.created_at > datetime() - duration('PT${time_range}H')
        RETURN f {
            .flow_id,
            .stablecoin_symbol,
            .total_amount,
            .flow_type,
            .risk_score,
            .confidence,
            .hop_count,
            .duration,
            .created_at
        } as flow_data
        ORDER BY f.risk_score DESC
        LIMIT 10
        """
        
        async with get_neo4j_session() as session:
            result = await session.run(query, address=address, time_range=time_range)
            flows = []
            async for record in result:
                flows.append(record['flow_data'])
            return flows
    
    async def _get_recent_flows(self, address: str, time_range: int) -> List[Dict]:
        """Get recent stablecoin flows for address"""
        query = """
        MATCH (a:Address {address: $address})-[r:SENT*1..5]->(f:StablecoinFlow)
        WHERE f.created_at > datetime() - duration('PT${time_range}H')
        RETURN f {
            .flow_id,
            .stablecoin_symbol,
            .total_amount,
            .flow_type,
            .risk_score,
            .confidence,
            .hop_count,
            .duration,
            .created_at
        } as flow_data
        ORDER BY f.created_at DESC
        LIMIT 10
        """
        
        async with get_neo4j_session() as session:
            result = await session.run(query, address=address, time_range=time_range)
            flows = []
            async for record in result:
                flows.append(record['flow_data'])
            return flows
    
    async def get_bridge_flow_analysis(self, bridge_name: str, time_range: int = 24) -> Dict[str, Any]:
        """Get analysis for flows through a specific bridge"""
        try:
            # Get bridge contract addresses
            bridge_contracts = await self._get_bridge_contracts(bridge_name)
            
            query = """
            MATCH (f:StablecoinFlow)
            WHERE any(blockchain in f.blockchains WHERE blockchain IN $blockchains)
            AND f.created_at > datetime() - duration('PT${time_range}H')
            RETURN f {
                .flow_id,
                .stablecoin_symbol,
                .total_amount,
                .flow_type,
                .risk_score,
                .confidence,
                .hop_count,
                .duration,
                .blockchains
            } as flow_data
            ORDER BY f.total_amount DESC
            LIMIT 100
            """
            
            async with get_neo4j_session() as session:
                result = await session.run(query, blockchains=list(bridge_contracts.keys()), time_range=time_range)
                flows = []
                total_amount = 0
                risk_scores = []
                
                async for record in result:
                    flows.append(record['flow_data'])
                    total_amount += record['flow_data']['total_amount']
                    risk_scores.append(record['flow_data']['risk_score'])
                
                return {
                    'bridge_name': bridge_name,
                    'time_range_hours': time_range,
                    'total_flows': len(flows),
                    'total_amount': total_amount,
                    'average_risk_score': sum(risk_scores) / len(risk_scores) if risk_scores else 0,
                    'supported_blockchains': list(bridge_contracts.keys()),
                    'top_flows': flows[:10]
                }
                
        except Exception as e:
            logger.error(f"Error getting bridge flow analysis for {bridge_name}: {e}")
            return {}
    
    async def _get_bridge_contracts(self, bridge_name: str) -> Dict[str, str]:
        """Get bridge contract addresses"""
        # TODO: Wire to a real per-bridge contract registry or config source
        raise NotImplementedError(
            f"Bridge contract lookup not yet implemented for '{bridge_name}'. "
            "Provide a bridge registry data source."
        )
    
    async def cache_flow_analysis(self, key: str, result: Dict[str, Any]):
        """Cache flow analysis result in Redis"""
        try:
            async with get_redis_connection() as redis:
                await redis.setex(f"stablecoin_flow:{key}", self.cache_ttl, json.dumps(result))
        except Exception as e:
            logger.error(f"Error caching flow analysis: {e}")
    
    async def get_cached_flow_analysis(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached flow analysis from Redis"""
        try:
            async with get_redis_connection() as redis:
                cached = await redis.get(f"stablecoin_flow:{key}")
                return json.loads(cached) if cached else None
        except Exception as e:
            logger.error(f"Error getting cached flow analysis: {e}")
            return None


# Global flow tracker instance
_stablecoin_flow_tracker: Optional[StablecoinFlowTracker] = None


def get_stablecoin_flow_tracker() -> StablecoinFlowTracker:
    """Get global stablecoin flow tracker instance"""
    global _stablecoin_flow_tracker
    if _stablecoin_flow_tracker is None:
        _stablecoin_flow_tracker = StablecoinFlowTracker()
    return _stablecoin_flow_tracker
