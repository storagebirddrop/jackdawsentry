"""
Jackdaw Sentry - Transaction Fingerprinting
Advanced transaction pattern matching and fingerprinting
"""

import asyncio
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Pattern
from typing import Set
from typing import Tuple

from src.api.database import get_postgres_connection

from .models import FingerprintingRequest
from .models import FingerprintPattern
from .models import FingerprintResult
from .models import FingerprintType

logger = logging.getLogger(__name__)


class TransactionFingerprinter:
    """Advanced transaction fingerprinting and pattern matching"""

    def __init__(self):
        self.patterns = {}
        self.cache = {}
        self.cache_ttl = 1800  # 30 minutes
        self._initialized = False

        # Initialize with default patterns
        self._load_default_patterns()

    async def initialize(self):
        """Initialize the transaction fingerprinter"""
        if self._initialized:
            return

        logger.info("Initializing Transaction Fingerprinter...")
        await self._create_fingerprinting_tables()
        self._initialized = True
        logger.info("Transaction Fingerprinter initialized successfully")

    async def _create_fingerprinting_tables(self):
        """Create fingerprinting tables"""

        create_fingerprints_table = """
        CREATE TABLE IF NOT EXISTS transaction_fingerprints (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            fingerprint_id VARCHAR(255) NOT NULL,
            query_type VARCHAR(50) NOT NULL,
            parameters JSONB NOT NULL,
            matched_patterns JSONB DEFAULT '[]',
            confidence_score DECIMAL(5,4) NOT NULL,
            match_count INTEGER NOT NULL DEFAULT 0,
            processing_time_ms DECIMAL(10,2),
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_fingerprints_query ON transaction_fingerprints(query_type);
        CREATE INDEX IF NOT EXISTS idx_fingerprints_confidence ON transaction_fingerprints(confidence_score);
        CREATE INDEX IF NOT EXISTS idx_fingerprints_created ON transaction_fingerprints(created_at);
        """

        create_patterns_table = """
        CREATE TABLE IF NOT EXISTS fingerprint_patterns (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            pattern_id VARCHAR(255) NOT NULL,
            pattern_type VARCHAR(50) NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            pattern_data JSONB NOT NULL,
            confidence_score DECIMAL(5,4) NOT NULL DEFAULT 1.0,
            enabled BOOLEAN DEFAULT TRUE,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_fingerprint_patterns_type ON fingerprint_patterns(pattern_type);
        CREATE INDEX IF NOT EXISTS idx_fingerprint_patterns_enabled ON fingerprint_patterns(enabled);
        """

        conn = await get_postgres_connection()
        try:
            await conn.execute(create_fingerprints_table)
            await conn.execute(create_patterns_table)
            await conn.commit()
            logger.info("Fingerprinting tables created/verified")
        except Exception as e:
            logger.error(f"Error creating fingerprinting tables: {e}")
            await conn.rollback()
            raise
        finally:
            await conn.close()

    def _load_default_patterns(self):
        """Load default fingerprint patterns"""

        # Amount patterns
        self.patterns["round_amounts"] = FingerprintPattern(
            pattern_type=FingerprintType.AMOUNT_PATTERN,
            name="Round Amount Pattern",
            description="Transactions with round number amounts (e.g., 1.0, 10.0, 100.0)",
            confidence_score=0.7,
            pattern_data={
                "round_amounts": [0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0, 500.0, 1000.0],
                "tolerance": 0.05,
            },
        )

        self.patterns["structured_amounts"] = FingerprintPattern(
            pattern_type=FingerprintType.AMOUNT_PATTERN,
            name="Structured Amount Pattern",
            description="Transactions structured to avoid reporting thresholds",
            confidence_score=0.8,
            pattern_data={"thresholds": [10000, 5000, 1000], "avoidance_margin": 0.05},
        )

        # Timing patterns
        self.patterns["off_peak_timing"] = FingerprintPattern(
            pattern_type=FingerprintType.TIMING_PATTERN,
            name="Off-Peak Timing Pattern",
            description="Transactions occurring during off-peak hours",
            confidence_score=0.6,
            pattern_data={
                "off_peak_hours": [22, 23, 0, 1, 2, 3, 4, 5, 6],
                "timezone": "UTC",
            },
        )

        self.patterns["rapid_succession"] = FingerprintPattern(
            pattern_type=FingerprintType.TIMING_PATTERN,
            name="Rapid Succession Pattern",
            description="Multiple transactions in quick succession",
            confidence_score=0.7,
            pattern_data={
                "max_interval_seconds": 300,  # 5 minutes
                "min_transactions": 3,
            },
        )

        # Address patterns
        self.patterns["sequential_addresses"] = FingerprintPattern(
            pattern_type=FingerprintType.ADDRESS_PATTERN,
            name="Sequential Address Pattern",
            description="Transactions to sequentially numbered addresses",
            confidence_score=0.8,
            pattern_data={
                "pattern": r"0x[a-fA-F0-9]{40}0*[1-9]\d*$",
                "sequential_count": 3,
            },
        )

        self.patterns["mixing_addresses"] = FingerprintPattern(
            pattern_type=FingerprintType.ADDRESS_PATTERN,
            name="Mixing Service Address Pattern",
            description="Transactions to known mixing service addresses",
            confidence_score=0.9,
            pattern_data={
                "known_mixers": [
                    "tornado",
                    "wasabi",
                    "joinmarket",
                    "samourai",
                    "whirlpool",
                    "coinjoin",
                    "monero",
                    "zcash",
                ]
            },
        )

        # Sequence patterns
        self.patterns["peeling_chain"] = FingerprintPattern(
            pattern_type=FingerprintType.SEQUENCE_PATTERN,
            name="Peeling Chain Sequence",
            description="Sequential transactions with decreasing amounts",
            confidence_score=0.8,
            pattern_data={
                "min_transactions": 3,
                "decrease_tolerance": 0.1,
                "time_window_hours": 24,
            },
        )

        self.patterns["layering_sequence"] = FingerprintPattern(
            pattern_type=FingerprintType.SEQUENCE_PATTERN,
            name="Layering Sequence",
            description="Complex multi-hop transaction sequences",
            confidence_score=0.7,
            pattern_data={"min_hops": 5, "max_hops": 20, "time_window_hours": 72},
        )

        # Behavioral patterns
        self.patterns["synchronized_behavior"] = FingerprintPattern(
            pattern_type=FingerprintType.BEHAVIORAL_PATTERN,
            name="Synchronized Behavior",
            description="Coordinated transaction behavior across multiple addresses",
            confidence_score=0.8,
            pattern_data={
                "sync_window_seconds": 300,
                "min_addresses": 2,
                "amount_similarity": 0.1,
            },
        )

        self.patterns["custody_change"] = FingerprintPattern(
            pattern_type=FingerprintType.BEHAVIORAL_PATTERN,
            name="Custody Change Behavior",
            description="Sudden changes in transaction behavior patterns",
            confidence_score=0.6,
            pattern_data={
                "inactivity_threshold_days": 7,
                "pattern_change_threshold": 0.6,
            },
        )

        # Network patterns
        self.patterns["bridge_hopping"] = FingerprintPattern(
            pattern_type=FingerprintType.NETWORK_PATTERN,
            name="Bridge Hopping Pattern",
            description="Rapid movement across multiple blockchain bridges",
            confidence_score=0.7,
            pattern_data={
                "min_bridges": 2,
                "time_window_hours": 24,
                "known_bridges": [
                    "ethereum_bridge",
                    "polygon_bridge",
                    "arbitrum_bridge",
                    "base_bridge",
                    "avalanche_bridge",
                    "optimism_bridge",
                ],
            },
        )

        self.patterns["cross_chain_arbitrage"] = FingerprintPattern(
            pattern_type=FingerprintType.NETWORK_PATTERN,
            name="Cross-Chain Arbitrage Pattern",
            description="Arbitrage patterns across multiple blockchains",
            confidence_score=0.6,
            pattern_data={
                "min_chains": 2,
                "profit_margin_threshold": 0.01,
                "time_window_minutes": 60,
            },
        )

    async def fingerprint_transactions(
        self, request: FingerprintingRequest
    ) -> FingerprintResult:
        """
        Fingerprint transactions based on query parameters

        Args:
            request: Fingerprinting request with query type and parameters

        Returns:
            FingerprintResult with matched patterns
        """

        start_time = datetime.now(timezone.utc)

        # Check cache first
        cache_key = self._generate_cache_key(request)
        if cache_key in self.cache:
            cached_result = self.cache[cache_key]
            if (
                datetime.now(timezone.utc) - cached_result["timestamp"]
            ).seconds < self.cache_ttl:
                logger.debug(f"Cache hit for fingerprinting: {request.query_type}")
                return cached_result["result"]

        logger.info(f"Fingerprinting transactions: {request.query_type}")

        try:
            # Get transactions based on query
            transactions = await self._get_transactions_for_query(request)

            if not transactions:
                logger.debug("No transactions found for fingerprinting query")
                return self._create_empty_result(request)

            # Match patterns against transactions
            matched_patterns = []

            for pattern_name, pattern in self.patterns.items():
                if pattern.pattern_type == request.query_type:
                    matches = await self._match_pattern(pattern, transactions, request)
                    matched_patterns.extend(matches)

            # Filter by minimum confidence
            filtered_patterns = [
                p
                for p in matched_patterns
                if p.confidence_score >= request.min_confidence
            ]

            # Limit results
            limited_patterns = filtered_patterns[: request.max_results]

            # Calculate overall confidence
            overall_confidence = self._calculate_overall_confidence(limited_patterns)

            # Calculate processing time
            processing_time = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000

            # Create result
            result = FingerprintResult(
                query_parameters=request.parameters,
                matched_patterns=limited_patterns,
                confidence_score=overall_confidence,
                match_count=len(limited_patterns),
                processing_time_ms=processing_time,
                metadata={
                    "query_type": request.query_type.value,
                    "blockchain": request.blockchain,
                    "total_transactions": len(transactions),
                    "cache_hit": False,
                    "algorithm_version": "1.0",
                },
            )

            # Cache result
            self.cache[cache_key] = {
                "result": result,
                "timestamp": datetime.now(timezone.utc),
            }

            # Store in database
            await self._store_fingerprint_result(result)

            logger.info(
                f"Fingerprinting complete: {len(limited_patterns)} patterns matched in {processing_time:.2f}ms"
            )
            return result

        except Exception as e:
            logger.error(f"Error in transaction fingerprinting: {e}")
            processing_time = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000

            return FingerprintResult(
                query_parameters=request.parameters,
                matched_patterns=[],
                confidence_score=0.0,
                match_count=0,
                processing_time_ms=processing_time,
                metadata={"error": str(e), "cache_hit": False},
            )

    async def _get_transactions_for_query(
        self, request: FingerprintingRequest
    ) -> List[Dict]:
        """Get transactions based on query parameters"""

        # This would integrate with existing transaction collectors
        # For now, return empty list as placeholder
        logger.debug(f"Transaction query not yet implemented for {request.query_type}")
        return []

    async def _match_pattern(
        self,
        pattern: FingerprintPattern,
        transactions: List[Dict],
        request: FingerprintingRequest,
    ) -> List[FingerprintPattern]:
        """Match a specific pattern against transactions"""

        matched = []

        try:
            if pattern.pattern_type == FingerprintType.AMOUNT_PATTERN:
                matched = await self._match_amount_pattern(pattern, transactions)
            elif pattern.pattern_type == FingerprintType.TIMING_PATTERN:
                matched = await self._match_timing_pattern(pattern, transactions)
            elif pattern.pattern_type == FingerprintType.ADDRESS_PATTERN:
                matched = await self._match_address_pattern(pattern, transactions)
            elif pattern.pattern_type == FingerprintType.SEQUENCE_PATTERN:
                matched = await self._match_sequence_pattern(pattern, transactions)
            elif pattern.pattern_type == FingerprintType.BEHAVIORAL_PATTERN:
                matched = await self._match_behavioral_pattern(pattern, transactions)
            elif pattern.pattern_type == FingerprintType.NETWORK_PATTERN:
                matched = await self._match_network_pattern(pattern, transactions)

        except Exception as e:
            logger.error(f"Error matching pattern {pattern.name}: {e}")

        return matched

    async def _match_amount_pattern(
        self, pattern: FingerprintPattern, transactions: List[Dict]
    ) -> List[FingerprintPattern]:
        """Match amount-based patterns"""

        matched = []
        pattern_data = pattern.pattern_data

        if pattern.name == "Round Amount Pattern":
            round_amounts = pattern_data.get("round_amounts", [])
            tolerance = pattern_data.get("tolerance", 0.05)

            for tx in transactions:
                amount = tx.get("amount", 0.0)

                for round_amount in round_amounts:
                    if abs(amount - round_amount) <= round_amount * tolerance:
                        matched_pattern = FingerprintPattern(
                            pattern_type=pattern.pattern_type,
                            name=f"{pattern.name} - {round_amount}",
                            description=f"Round amount {round_amount} detected",
                            confidence_score=pattern.confidence_score,
                            pattern_data={
                                "detected_amount": amount,
                                "expected_amount": round_amount,
                                "transaction_hash": tx.get("hash"),
                            },
                        )
                        matched.append(matched_pattern)
                        break

        elif pattern.name == "Structured Amount Pattern":
            thresholds = pattern_data.get("thresholds", [])
            avoidance_margin = pattern_data.get("avoidance_margin", 0.05)

            for tx in transactions:
                amount = tx.get("amount", 0.0)

                for threshold in thresholds:
                    avoidance_amount = threshold * (1 - avoidance_margin)
                    if abs(amount - avoidance_amount) <= threshold * 0.01:
                        matched_pattern = FingerprintPattern(
                            pattern_type=pattern.pattern_type,
                            name=f"{pattern.name} - Below {threshold}",
                            description=f"Amount structured below {threshold} threshold",
                            confidence_score=pattern.confidence_score,
                            pattern_data={
                                "detected_amount": amount,
                                "threshold": threshold,
                                "transaction_hash": tx.get("hash"),
                            },
                        )
                        matched.append(matched_pattern)
                        break

        return matched

    async def _match_timing_pattern(
        self, pattern: FingerprintPattern, transactions: List[Dict]
    ) -> List[FingerprintPattern]:
        """Match timing-based patterns"""

        matched = []
        pattern_data = pattern.pattern_data

        if pattern.name == "Off-Peak Timing Pattern":
            off_peak_hours = pattern_data.get("off_peak_hours", [])

            for tx in transactions:
                timestamp = tx.get("timestamp")
                if timestamp:
                    hour = timestamp.hour
                    if hour in off_peak_hours:
                        matched_pattern = FingerprintPattern(
                            pattern_type=pattern.pattern_type,
                            name=pattern.name,
                            description=f"Off-peak transaction at {hour}:00",
                            confidence_score=pattern.confidence_score,
                            pattern_data={
                                "hour": hour,
                                "transaction_hash": tx.get("hash"),
                            },
                        )
                        matched.append(matched_pattern)

        elif pattern.name == "Rapid Succession Pattern":
            max_interval = pattern_data.get("max_interval_seconds", 300)
            min_transactions = pattern_data.get("min_transactions", 3)

            # Sort transactions by timestamp
            sorted_txs = sorted(
                transactions, key=lambda x: x.get("timestamp", datetime.min)
            )

            # Find rapid sequences
            for i in range(len(sorted_txs) - min_transactions + 1):
                sequence = sorted_txs[i : i + min_transactions]

                # Check if all transactions are within the time window
                time_diff = (
                    sequence[-1]["timestamp"] - sequence[0]["timestamp"]
                ).total_seconds()

                if time_diff <= max_interval:
                    matched_pattern = FingerprintPattern(
                        pattern_type=pattern.pattern_type,
                        name=pattern.name,
                        description=f"{min_transactions} transactions in {time_diff:.0f} seconds",
                        confidence_score=pattern.confidence_score,
                        pattern_data={
                            "transaction_count": min_transactions,
                            "time_span_seconds": time_diff,
                            "transaction_hashes": [tx.get("hash") for tx in sequence],
                        },
                    )
                    matched.append(matched_pattern)

        return matched

    async def _match_address_pattern(
        self, pattern: FingerprintPattern, transactions: List[Dict]
    ) -> List[FingerprintPattern]:
        """Match address-based patterns"""

        matched = []
        pattern_data = pattern.pattern_data

        if pattern.name == "Sequential Address Pattern":
            pattern_regex = pattern_data.get("pattern", "")
            sequential_count = pattern_data.get("sequential_count", 3)

            try:
                regex = re.compile(pattern_regex, re.IGNORECASE)

                for tx in transactions:
                    address = tx.get("to_address", "")

                    if regex.match(address):
                        matched_pattern = FingerprintPattern(
                            pattern_type=pattern.pattern_type,
                            name=pattern.name,
                            description=f"Sequential address pattern detected",
                            confidence_score=pattern.confidence_score,
                            pattern_data={
                                "address": address,
                                "transaction_hash": tx.get("hash"),
                            },
                        )
                        matched.append(matched_pattern)

            except re.error as e:
                logger.error(f"Invalid regex pattern: {e}")

        elif pattern.name == "Mixing Service Address Pattern":
            known_mixers = pattern_data.get("known_mixers", [])

            for tx in transactions:
                address = tx.get("to_address", "").lower()

                for mixer in known_mixers:
                    if mixer in address:
                        matched_pattern = FingerprintPattern(
                            pattern_type=pattern.pattern_type,
                            name=f"{pattern.name} - {mixer}",
                            description=f"Transaction to {mixer} mixing service",
                            confidence_score=pattern.confidence_score,
                            pattern_data={
                                "address": address,
                                "mixer": mixer,
                                "transaction_hash": tx.get("hash"),
                            },
                        )
                        matched.append(matched_pattern)
                        break

        return matched

    async def _match_sequence_pattern(
        self, pattern: FingerprintPattern, transactions: List[Dict]
    ) -> List[FingerprintPattern]:
        """Match sequence-based patterns"""

        matched = []
        pattern_data = pattern.pattern_data

        if pattern.name == "Peeling Chain Sequence":
            min_transactions = pattern_data.get("min_transactions", 3)
            decrease_tolerance = pattern_data.get("decrease_tolerance", 0.1)

            # Sort transactions by timestamp
            sorted_txs = sorted(
                transactions, key=lambda x: x.get("timestamp", datetime.min)
            )

            # Look for peeling sequences
            for i in range(len(sorted_txs) - min_transactions + 1):
                sequence = sorted_txs[i : i + min_transactions]

                # Check if amounts are decreasing
                amounts = [tx.get("amount", 0.0) for tx in sequence]
                is_peeling = True

                for j in range(1, len(amounts)):
                    expected_max = amounts[j - 1] * (1 - decrease_tolerance)
                    if amounts[j] > expected_max:
                        is_peeling = False
                        break

                if is_peeling:
                    matched_pattern = FingerprintPattern(
                        pattern_type=pattern.pattern_type,
                        name=pattern.name,
                        description=f"Peeling chain of {min_transactions} transactions",
                        confidence_score=pattern.confidence_score,
                        pattern_data={
                            "transaction_count": min_transactions,
                            "amounts": amounts,
                            "transaction_hashes": [tx.get("hash") for tx in sequence],
                        },
                    )
                    matched.append(matched_pattern)

        return matched

    async def _match_behavioral_pattern(
        self, pattern: FingerprintPattern, transactions: List[Dict]
    ) -> List[FingerprintPattern]:
        """Match behavioral patterns"""

        matched = []

        # Behavioral patterns would require more complex analysis
        # For now, return empty list as placeholder
        logger.debug(
            f"Behavioral pattern matching not yet implemented for {pattern.name}"
        )

        return matched

    async def _match_network_pattern(
        self, pattern: FingerprintPattern, transactions: List[Dict]
    ) -> List[FingerprintPattern]:
        """Match network-based patterns"""

        matched = []

        # Network patterns would require cross-chain analysis
        # For now, return empty list as placeholder
        logger.debug(f"Network pattern matching not yet implemented for {pattern.name}")

        return matched

    def _calculate_overall_confidence(
        self, patterns: List[FingerprintPattern]
    ) -> float:
        """Calculate overall confidence score from matched patterns"""

        if not patterns:
            return 0.0

        # Use weighted average based on pattern confidence
        total_confidence = sum(p.confidence_score for p in patterns)
        return min(total_confidence / len(patterns), 1.0)

    def _generate_cache_key(self, request: FingerprintingRequest) -> str:
        """Generate cache key for request"""

        key_parts = [
            request.query_type.value,
            str(request.blockchain or ""),
            str(request.time_window_hours),
            str(request.min_confidence),
            str(request.max_results),
        ]

        # Add sorted parameters
        if request.parameters:
            param_str = json.dumps(request.parameters, sort_keys=True)
            key_parts.append(param_str)

        return ":".join(key_parts)

    def _create_empty_result(self, request: FingerprintingRequest) -> FingerprintResult:
        """Create empty result when no matches found"""

        return FingerprintResult(
            query_parameters=request.parameters,
            matched_patterns=[],
            confidence_score=0.0,
            match_count=0,
            processing_time_ms=0.0,
            metadata={
                "query_type": request.query_type.value,
                "blockchain": request.blockchain,
                "cache_hit": False,
            },
        )

    async def _store_fingerprint_result(self, result: FingerprintResult):
        """Store fingerprint result in database"""

        insert_query = """
        INSERT INTO transaction_fingerprints (
            fingerprint_id, query_type, parameters, matched_patterns,
            confidence_score, match_count, processing_time_ms, metadata
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """

        conn = await get_postgres_connection()
        try:
            await conn.execute(
                insert_query,
                result.fingerprint_id,
                result.metadata.get("query_type"),
                result.query_parameters,
                [p.model_dump() for p in result.matched_patterns],
                result.confidence_score,
                result.match_count,
                result.processing_time_ms,
                result.metadata,
            )
            await conn.commit()
        except Exception as e:
            logger.error(f"Error storing fingerprint result: {e}")
            await conn.rollback()
        finally:
            await conn.close()

    def add_pattern(self, pattern: FingerprintPattern):
        """Add a custom fingerprint pattern"""

        self.patterns[pattern.name] = pattern
        logger.info(f"Added custom pattern: {pattern.name}")

    def remove_pattern(self, pattern_name: str):
        """Remove a fingerprint pattern"""

        if pattern_name in self.patterns:
            del self.patterns[pattern_name]
            logger.info(f"Removed pattern: {pattern_name}")

    def get_patterns(
        self, pattern_type: Optional[FingerprintType] = None
    ) -> List[FingerprintPattern]:
        """Get all patterns or patterns of specific type"""

        if pattern_type:
            return [p for p in self.patterns.values() if p.pattern_type == pattern_type]

        return list(self.patterns.values())

    def clear_cache(self):
        """Clear the fingerprinting cache"""
        self.cache.clear()
        logger.info("Fingerprinting cache cleared")


# Global fingerprinter instance
_fingerprinter = None


def get_transaction_fingerprinter() -> TransactionFingerprinter:
    """Get the global transaction fingerprinter instance"""
    global _fingerprinter
    if _fingerprinter is None:
        _fingerprinter = TransactionFingerprinter()
    return _fingerprinter
