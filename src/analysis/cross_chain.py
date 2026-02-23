"""
Jackdaw Sentry - Cross-Chain Transaction Analysis Engine
Analyzes transactions across multiple blockchains to identify patterns and flows
"""

import asyncio
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
from typing import Tuple

from src.api.config import settings
from src.api.database import get_neo4j_session
from src.api.database import get_redis_connection

logger = logging.getLogger(__name__)


class TransactionPattern(Enum):
    """Transaction pattern types"""

    BRIDGE_TRANSFER = "bridge_transfer"
    DEX_SWAP = "dex_swap"
    MIXER_USAGE = "mixer_usage"
    PRIVACY_TOOL = "privacy_tool"
    CIRCULAR_TRADING = "circular_trading"
    LAYER_HOPPING = "layer_hopping"
    STABLECOIN_FLOW = "stablecoin_flow"
    SUSPICIOUS_TIMING = "suspicious_timing"
    HIGH_FREQUENCY = "high_frequency"
    LARGE_AMOUNT = "large_amount"


@dataclass
class CrossChainTransaction:
    """Cross-chain transaction representation"""

    tx_hash: str
    blockchain: str
    from_address: str
    to_address: str
    amount: float
    token_symbol: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    fee: Optional[float] = None
    memo: Optional[str] = None
    related_transactions: List[str] = field(default_factory=list)
    patterns: List[TransactionPattern] = field(default_factory=list)
    risk_score: float = 0.0
    confidence: float = 0.0


@dataclass
class TransactionFlow:
    """Transaction flow analysis result"""

    flow_id: str
    start_address: str
    end_address: str
    total_amount: float
    path: List[CrossChainTransaction]
    blockchains: List[str]
    duration: timedelta
    patterns: List[TransactionPattern]
    risk_score: float
    confidence: float
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CrossChainAnalyzer:
    """Cross-chain transaction analysis engine"""

    def __init__(self):
        self.bridge_contracts = self._get_bridge_contracts()
        self.dex_contracts = self._get_dex_contracts()
        self.mixer_contracts = self._get_mixer_contracts()
        self.privacy_tools = self._get_privacy_tools()

        # Process logger for validation warnings
        self._logger = logger

        # Analysis thresholds
        self.large_amount_threshold = 100000  # USD
        self.high_frequency_threshold = 10  # transactions per hour
        self.suspicious_timing_window = timedelta(minutes=5)

        # Cache for analysis results
        self.analysis_cache = {}
        self.cache_ttl = 3600  # 1 hour

    def _get_bridge_contracts(self) -> Dict[str, Dict[str, str]]:
        """Get known bridge contracts across blockchains"""
        return {
            "ethereum": {
                "multichain": "0x83e6dFcA28B1C7996839C0D7c9b68cAa67eBc40C",
                "layerzero": "0x3E4bA8F9b1b2F1B6c9e8d7f6a5b4c3d2e1f0a9b",
                "wormhole": "0x9893bF1a1f2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d",
            },
            "bsc": {
                "multichain": "0x83e6dFcA28B1C7996839C0D7c9b68cAa67eBc40C",
                "layerzero": "0x3E4bA8F9b1b2F1B6c9e8d7f6a5b4c3d2e1f0a9b",
            },
            "polygon": {
                "multichain": "0x83e6dFcA28B1C7996839C0D7c9b68cAa67eBc40C",
                "polygon_bridge": "0xa0b86a33E6441b6e8F9c2c2c4c4c4c4c4c4c4c4c",
            },
            "arbitrum": {
                "arbitrum_bridge": "0x8315177aB297bA92A96050f27273d9E53d88C14D",
                "layerzero": "0x3E4bA8F9b1b2F1B6c9e8d7f6a5b4c3d2e1f0a9b",
            },
            "avalanche": {
                "avalanche_bridge": "0x1bAa5C5eF5F7d8A9b6c4d3e2f1a0b9c8d7e6f5a4"
            },
        }

    def _get_dex_contracts(self) -> Dict[str, Dict[str, str]]:
        """Get known DEX contracts across blockchains"""
        return {
            "ethereum": {
                "uniswap_v2": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
                "uniswap_v3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                "curve": "0x99E921Ad2c4DbF743735b9BEa3682dB22F7A7A3f",
                "sushiswap": "0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac",
            },
            "bsc": {
                "pancakeswap": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
                "biswap": "0x858E3312ed3Aef7616796b5F386D0A0eE9Be0F64",
                "apeswap": "0xcF0feBd3f17CEf5b47b0cD257aCf6025c5BFf3b7",
            },
            "polygon": {
                "quickswap": "0xa5E0829CaCEd155fF79577b4A2d8A2362770bF5c",
                "sushiswap": "0xc35DADB65012eC5796536bD9864eD8773aBc74C4",
            },
            "arbitrum": {
                "uniswap_v3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                "sushiswap": "0xc35DADB65012eC5796536bD9864eD8773aBc74C4",
            },
            "avalanche": {
                "traderjoe": "0x60aE616a2155Ee3d9A68541Ba4544862310933d4",
                "pangolin": "0xE54Ca86531e17Ab36b9e8b6951Af8DacD308352f",
            },
        }

    def _get_mixer_contracts(self) -> Dict[str, Dict[str, str]]:
        """Get known mixer contracts across blockchains"""
        return {
            "ethereum": {
                "tornado_cash": "0x12D66f61A03b2C4055F6789d6635A2cD4035F59A",
                "mixertools": "0x8A8257b3a5F8E0a7b8C8c8a8a8a8a8a8a8a8a8a8",
            },
            "bsc": {"tornado_cash": "0x12D66f61A03b2C4055F6789d6635A2cD4035F59A"},
            "polygon": {"tornado_cash": "0x12D66f61A03b2C4055F6789d6635A2cD4035F59A"},
        }

    def _get_privacy_tools(self) -> Dict[str, Dict[str, str]]:
        """Get known privacy tool contracts"""
        return {
            "ethereum": {
                "aztec": "0x8A8257b3a5F8E0a7b8C8c8a8a8a8a8a8a8a8a8a8",
                "ironfish": "0x7B6B8f8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8F8",
            },
            "bitcoin": {"joinmarket": "privacy_tool", "wasabi": "privacy_tool"},
        }

    def _parse_timestamp(self, ts: Any) -> datetime:
        """Safely parse a timestamp from Neo4j or string data.

        Handles: None, datetime objects, strings (including trailing 'Z').
        Returns UTC datetime.
        """
        if ts is None:
            return datetime.now(timezone.utc)
        if isinstance(ts, datetime):
            return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
        if isinstance(ts, str):
            try:
                if ts.endswith("Z"):
                    ts = ts[:-1] + "+00:00"
                result = datetime.fromisoformat(ts)
                return result if result.tzinfo else result.replace(tzinfo=timezone.utc)
            except ValueError:
                return datetime.now(timezone.utc)
        return datetime.now(timezone.utc)

    async def analyze_transaction(
        self, tx_hash: str, blockchain: str
    ) -> Optional[CrossChainTransaction]:
        """Analyze a single transaction for cross-chain patterns"""
        try:
            # Get transaction from database
            tx_data = await self._get_transaction(tx_hash, blockchain)
            if not tx_data:
                return None

            # Validate critical address fields
            from_addr = tx_data.get("from_address")
            to_addr = tx_data.get("to_address")
            if not from_addr or not to_addr:
                self._logger.warning(
                    "Transaction %s on %s missing address fields: from_address=%r, to_address=%r",
                    tx_hash,
                    blockchain,
                    from_addr,
                    to_addr,
                )
                return None

            # Create cross-chain transaction object
            cross_chain_tx = CrossChainTransaction(
                tx_hash=tx_hash,
                blockchain=blockchain,
                from_address=from_addr,
                to_address=to_addr,
                amount=tx_data.get("value", 0),
                token_symbol=tx_data.get("token_symbol"),
                timestamp=self._parse_timestamp(tx_data.get("timestamp")),
                block_number=tx_data.get("block_number"),
                gas_used=tx_data.get("gas_used"),
                fee=tx_data.get("fee"),
                memo=tx_data.get("memo"),
            )

            # Detect patterns
            patterns = await self._detect_patterns(cross_chain_tx)
            cross_chain_tx.patterns = patterns

            # Calculate risk score
            risk_score = await self._calculate_risk_score(cross_chain_tx)
            cross_chain_tx.risk_score = risk_score

            # Find related transactions (before confidence, which checks related_transactions)
            related_txs = await self._find_related_transactions(cross_chain_tx)
            cross_chain_tx.related_transactions = related_txs

            # Calculate confidence
            confidence = await self._calculate_confidence(cross_chain_tx)
            cross_chain_tx.confidence = confidence

            return cross_chain_tx

        except Exception as e:
            logger.error(f"Error analyzing transaction {tx_hash}: {e}")
            return None

    async def _get_transaction(self, tx_hash: str, blockchain: str) -> Optional[Dict]:
        """Get transaction data from database"""
        query = """
        MATCH (t:Transaction {hash: $tx_hash, blockchain: $blockchain})
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
            .memo,
            .token_symbol
        } as tx_data
        """

        async with get_neo4j_session() as session:
            result = await session.run(query, tx_hash=tx_hash, blockchain=blockchain)
            record = await result.single()
            return record["tx_data"] if record else None

    async def _detect_patterns(
        self, tx: CrossChainTransaction
    ) -> List[TransactionPattern]:
        """Detect patterns in transaction"""
        patterns = []

        # Check for bridge transfer
        if await self._is_bridge_transfer(tx):
            patterns.append(TransactionPattern.BRIDGE_TRANSFER)

        # Check for DEX swap
        if await self._is_dex_swap(tx):
            patterns.append(TransactionPattern.DEX_SWAP)

        # Check for mixer usage
        if await self._is_mixer_usage(tx):
            patterns.append(TransactionPattern.MIXER_USAGE)

        # Check for privacy tool usage
        if await self._is_privacy_tool_usage(tx):
            patterns.append(TransactionPattern.PRIVACY_TOOL)

        # Check for large amount
        if await self._is_large_amount(tx):
            patterns.append(TransactionPattern.LARGE_AMOUNT)

        # Check for high frequency
        if await self._is_high_frequency(tx):
            patterns.append(TransactionPattern.HIGH_FREQUENCY)

        # Check for suspicious timing
        if await self._has_suspicious_timing(tx):
            patterns.append(TransactionPattern.SUSPICIOUS_TIMING)

        # Check for stablecoin flow
        if await self._is_stablecoin_flow(tx):
            patterns.append(TransactionPattern.STABLECOIN_FLOW)

        return patterns

    async def _is_bridge_transfer(self, tx: CrossChainTransaction) -> bool:
        """Check if transaction is a bridge transfer"""
        if not tx.to_address:
            return False

        bridge_contracts = self.bridge_contracts.get(tx.blockchain, {})
        return tx.to_address.lower() in [
            addr.lower() for addr in bridge_contracts.values()
        ]

    async def _is_dex_swap(self, tx: CrossChainTransaction) -> bool:
        """Check if transaction is a DEX swap"""
        if not tx.to_address:
            return False

        dex_contracts = self.dex_contracts.get(tx.blockchain, {})
        return tx.to_address.lower() in [
            addr.lower() for addr in dex_contracts.values()
        ]

    async def _is_mixer_usage(self, tx: CrossChainTransaction) -> bool:
        """Check if transaction uses a mixer"""
        if not tx.to_address:
            return False

        mixer_contracts = self.mixer_contracts.get(tx.blockchain, {})
        return tx.to_address.lower() in [
            addr.lower() for addr in mixer_contracts.values()
        ]

    async def _is_privacy_tool_usage(self, tx: CrossChainTransaction) -> bool:
        """Check if transaction uses privacy tools"""
        if not tx.to_address:
            return False

        privacy_tools = self.privacy_tools.get(tx.blockchain, {})
        return tx.to_address.lower() in [
            addr.lower() for addr in privacy_tools.values()
        ]

    async def _is_large_amount(self, tx: CrossChainTransaction) -> bool:
        """Check if transaction amount is large"""
        # Convert to USD equivalent (simplified)
        if tx.token_symbol and tx.token_symbol in [
            "USDT",
            "USDC",
            "USDe",
            "USDS",
            "USD1",
            "BUSD",
        ]:
            return tx.amount > self.large_amount_threshold

        # For other tokens, use a simplified conversion
        return tx.amount > 10  # 10 ETH/BNB/etc. threshold

    async def _is_high_frequency(self, tx: CrossChainTransaction) -> bool:
        """Check if address has high frequency transactions"""
        query = """
        MATCH (t:Transaction {from_address: $address})
        WHERE t.timestamp > datetime() - duration('PT1H')
        RETURN count(t) as tx_count
        """

        async with get_neo4j_session() as session:
            result = await session.run(query, address=tx.from_address)
            record = await result.single()
            tx_count = record["tx_count"] if record else 0
            return tx_count > self.high_frequency_threshold

    async def _has_suspicious_timing(self, tx: CrossChainTransaction) -> bool:
        """Check for suspicious timing patterns"""
        # Look for multiple transactions from same address within short time window
        query = """
        MATCH (t:Transaction {from_address: $address})
        WHERE t.timestamp > datetime() - duration('PT5M')
        AND t.timestamp < $timestamp
        RETURN count(t) as recent_tx_count
        """

        async with get_neo4j_session() as session:
            result = await session.run(
                query, address=tx.from_address, timestamp=tx.timestamp
            )
            record = await result.single()
            recent_tx_count = record["recent_tx_count"] if record else 0
            return recent_tx_count > 3

    async def _is_stablecoin_flow(self, tx: CrossChainTransaction) -> bool:
        """Check if transaction involves stablecoin flow"""
        return tx.token_symbol in [
            "USDT",
            "USDC",
            "USDe",
            "USDS",
            "USD1",
            "BUSD",
            "EURC",
            "EURT",
            "EURS",
            "RLUSD",
            "BRZ",
        ]

    async def _calculate_risk_score(self, tx: CrossChainTransaction) -> float:
        """Calculate risk score for transaction"""
        risk_score = 0.0

        # Base risk for each pattern
        pattern_risks = {
            TransactionPattern.BRIDGE_TRANSFER: 0.3,
            TransactionPattern.DEX_SWAP: 0.2,
            TransactionPattern.MIXER_USAGE: 0.8,
            TransactionPattern.PRIVACY_TOOL: 0.7,
            TransactionPattern.CIRCULAR_TRADING: 0.9,
            TransactionPattern.LAYER_HOPPING: 0.4,
            TransactionPattern.STABLECOIN_FLOW: 0.1,
            TransactionPattern.SUSPICIOUS_TIMING: 0.5,
            TransactionPattern.HIGH_FREQUENCY: 0.6,
            TransactionPattern.LARGE_AMOUNT: 0.4,
        }

        # Add risk for each detected pattern
        for pattern in tx.patterns:
            risk_score += pattern_risks.get(pattern, 0.0)

        # Cap at 1.0
        return min(risk_score, 1.0)

    async def _calculate_confidence(self, tx: CrossChainTransaction) -> float:
        """Calculate confidence score for analysis"""
        confidence = 0.5  # Base confidence

        # Increase confidence based on number of patterns
        confidence += min(len(tx.patterns) * 0.1, 0.3)

        # Increase confidence if we have related transactions
        if tx.related_transactions:
            confidence += 0.2

        # Cap at 1.0
        return min(confidence, 1.0)

    async def _find_related_transactions(self, tx: CrossChainTransaction) -> List[str]:
        """Find transactions related to this transaction"""
        related_txs = []

        # Find transactions from same address
        query = """
        MATCH (t:Transaction {from_address: $address})
        WHERE t.hash <> $tx_hash
        AND t.timestamp > datetime() - duration('PT24H')
        RETURN t.hash as related_tx
        LIMIT 10
        """

        async with get_neo4j_session() as session:
            result = await session.run(
                query, address=tx.from_address, tx_hash=tx.tx_hash
            )
            async for record in result:
                related_txs.append(record["related_tx"])

        return related_txs

    async def analyze_transaction_flow(
        self, start_address: str, end_address: str, max_depth: int = 5
    ) -> Optional[TransactionFlow]:
        """Analyze transaction flow between two addresses"""
        try:
            # Find transaction path
            path = await self._find_transaction_path(
                start_address, end_address, max_depth
            )
            if not path:
                return None

            # Calculate flow metrics
            total_amount = sum(tx.amount for tx in path)
            blockchains = list(set(tx.blockchain for tx in path))
            duration = (
                path[-1].timestamp - path[0].timestamp
                if len(path) > 1
                else timedelta(0)
            )

            # Collect all patterns
            all_patterns = []
            for tx in path:
                all_patterns.extend(tx.patterns)
            patterns = list(set(all_patterns))

            # Calculate overall risk score
            risk_score = sum(tx.risk_score for tx in path) / len(path)

            # Calculate confidence
            confidence = sum(tx.confidence for tx in path) / len(path)

            return TransactionFlow(
                flow_id=f"{start_address}_{end_address}_{datetime.now(timezone.utc).timestamp()}",
                start_address=start_address,
                end_address=end_address,
                total_amount=total_amount,
                path=path,
                blockchains=blockchains,
                duration=duration,
                patterns=patterns,
                risk_score=risk_score,
                confidence=confidence,
            )

        except Exception as e:
            logger.error(f"Error analyzing transaction flow: {e}")
            return None

    async def _find_transaction_path(
        self, start_address: str, end_address: str, max_depth: int
    ) -> List[CrossChainTransaction]:
        """Find transaction path between addresses using BFS"""
        # This is a simplified implementation
        # In production, you'd use graph algorithms in Neo4j

        query = """
        MATCH path = shortestPath((a:Address {address: $start_address})-[:SENT*1..5]->(b:Address {address: $end_address}))
        WHERE length(path) <= $max_depth
        RETURN [rel in relationships(path) | {
            tx_hash: rel.transaction_hash,
            blockchain: rel.blockchain,
            from_address: startNode(rel).address,
            to_address: endNode(rel).address,
            value: rel.value,
            timestamp: rel.timestamp,
            block_number: rel.block_number,
            fee: rel.fee
        }] as transactions
        """

        async with get_neo4j_session() as session:
            result = await session.run(
                query,
                start_address=start_address,
                end_address=end_address,
                max_depth=max_depth,
            )
            record = await result.single()

            if not record:
                return []

            # Convert to CrossChainTransaction objects
            path = []
            for tx_data in record["transactions"]:
                cross_chain_tx = CrossChainTransaction(
                    tx_hash=tx_data["tx_hash"],
                    blockchain=tx_data["blockchain"],
                    from_address=tx_data["from_address"],
                    to_address=tx_data["to_address"],
                    amount=tx_data["value"],
                    timestamp=tx_data["timestamp"],
                    block_number=tx_data["block_number"],
                    fee=tx_data["fee"],
                )

                # Detect patterns for each transaction
                cross_chain_tx.patterns = await self._detect_patterns(cross_chain_tx)
                cross_chain_tx.risk_score = await self._calculate_risk_score(
                    cross_chain_tx
                )
                cross_chain_tx.confidence = await self._calculate_confidence(
                    cross_chain_tx
                )

                path.append(cross_chain_tx)

            return path

    async def get_cross_chain_analysis(
        self, address: str, time_range: int = 24
    ) -> Dict[str, Any]:
        """Get comprehensive cross-chain analysis for an address"""
        try:
            # Get all transactions for address
            transactions = await self._get_address_transactions(address, time_range)

            # Analyze each transaction
            analyzed_txs = []
            for tx_data in transactions:
                cross_chain_tx = CrossChainTransaction(
                    tx_hash=tx_data["hash"],
                    blockchain=tx_data["blockchain"],
                    from_address=tx_data["from_address"],
                    to_address=tx_data["to_address"],
                    amount=tx_data["value"],
                    token_symbol=tx_data.get("token_symbol"),
                    timestamp=datetime.fromisoformat(tx_data["timestamp"]),
                    block_number=tx_data.get("block_number"),
                    gas_used=tx_data.get("gas_used"),
                    fee=tx_data.get("fee"),
                )

                # Detect patterns
                cross_chain_tx.patterns = await self._detect_patterns(cross_chain_tx)
                cross_chain_tx.risk_score = await self._calculate_risk_score(
                    cross_chain_tx
                )
                cross_chain_tx.confidence = await self._calculate_confidence(
                    cross_chain_tx
                )

                analyzed_txs.append(cross_chain_tx)

            # Calculate aggregate metrics
            total_transactions = len(analyzed_txs)
            total_amount = sum(tx.amount for tx in analyzed_txs)
            avg_risk_score = (
                sum(tx.risk_score for tx in analyzed_txs) / total_transactions
                if total_transactions > 0
                else 0
            )
            avg_confidence = (
                sum(tx.confidence for tx in analyzed_txs) / total_transactions
                if total_transactions > 0
                else 0
            )

            # Count patterns
            pattern_counts = {}
            for tx in analyzed_txs:
                for pattern in tx.patterns:
                    pattern_counts[pattern.value] = (
                        pattern_counts.get(pattern.value, 0) + 1
                    )

            # Get blockchain distribution
            blockchain_counts = {}
            for tx in analyzed_txs:
                blockchain_counts[tx.blockchain] = (
                    blockchain_counts.get(tx.blockchain, 0) + 1
                )

            return {
                "address": address,
                "time_range_hours": time_range,
                "total_transactions": total_transactions,
                "total_amount": total_amount,
                "average_risk_score": avg_risk_score,
                "average_confidence": avg_confidence,
                "pattern_distribution": pattern_counts,
                "blockchain_distribution": blockchain_counts,
                "high_risk_transactions": [
                    tx.tx_hash for tx in analyzed_txs if tx.risk_score > 0.7
                ],
                "recent_transactions": [
                    self._serialize_transaction(tx) for tx in analyzed_txs[-10:]
                ],  # Last 10 transactions
            }

        except Exception as e:
            logger.error(
                f"Error getting cross-chain analysis for address {address}: {e}"
            )
            return {}

    def _serialize_transaction(self, tx: CrossChainTransaction) -> Dict[str, Any]:
        """Serialize a CrossChainTransaction to JSON-safe dict"""
        return {
            "tx_hash": tx.tx_hash,
            "blockchain": tx.blockchain,
            "from_address": tx.from_address,
            "to_address": tx.to_address,
            "amount": tx.amount,
            "token_symbol": tx.token_symbol,
            "timestamp": tx.timestamp.isoformat(),
            "block_number": tx.block_number,
            "gas_used": tx.gas_used,
            "fee": tx.fee,
            "memo": tx.memo,
            "related_transactions": tx.related_transactions,
            "patterns": [p.value for p in tx.patterns],
            "risk_score": tx.risk_score,
            "confidence": tx.confidence,
        }

    async def _get_address_transactions(
        self, address: str, time_range: int
    ) -> List[Dict]:
        """Get transactions for address within time range"""
        query = """
        MATCH (a:Address {address: $address})-[r:SENT]->(t:Transaction)
        WHERE t.timestamp > datetime() - duration({hours: $time_range})
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
        ORDER BY t.timestamp DESC
        LIMIT 100
        """

        async with get_neo4j_session() as session:
            result = await session.run(query, address=address, time_range=time_range)
            transactions = []
            async for record in result:
                transactions.append(record["tx_data"])
            return transactions

    async def cache_analysis_result(self, key: str, result: Dict[str, Any]):
        """Cache analysis result in Redis"""
        try:
            async with get_redis_connection() as redis:
                await redis.setex(f"analysis:{key}", self.cache_ttl, json.dumps(result))
        except Exception as e:
            logger.error(f"Error caching analysis result: {e}")

    async def get_cached_analysis(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis result from Redis"""
        try:
            async with get_redis_connection() as redis:
                cached = await redis.get(f"analysis:{key}")
                return json.loads(cached) if cached else None
        except Exception as e:
            logger.error(f"Error getting cached analysis: {e}")
            return None


# Global analyzer instance
_cross_chain_analyzer: Optional[CrossChainAnalyzer] = None


def get_cross_chain_analyzer() -> CrossChainAnalyzer:
    """Get global cross-chain analyzer instance"""
    global _cross_chain_analyzer
    if _cross_chain_analyzer is None:
        _cross_chain_analyzer = CrossChainAnalyzer()
    return _cross_chain_analyzer
