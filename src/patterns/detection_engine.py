"""
Jackdaw Sentry - Pattern Detection Engine
Advanced pattern detection engine with real-time analysis capabilities
"""

import asyncio
import logging
import time as _time
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from src.api.database import get_postgres_connection

from .algorithms import CustodyChangeDetector
from .algorithms import LayeringDetector
from .algorithms import OffPeakActivityDetector
from .algorithms import PeelingChainDetector
from .algorithms import RoundAmountDetector
from .algorithms import SynchronizedTransferDetector
from .models import PatternAnalysisResult
from .models import PatternEvidence
from .models import PatternRequest
from .models import PatternResponse
from .models import PatternResult
from .models import PatternSeverity
from .models import PatternSignature
from .models import PatternType
from .pattern_library import get_pattern_library

logger = logging.getLogger(__name__)


class AdvancedPatternDetector:
    """Advanced pattern detection engine with real-time analysis"""

    def __init__(self):
        self.pattern_library = get_pattern_library()
        self.detectors = {
            PatternType.PEELING_CHAIN: PeelingChainDetector(),
            PatternType.LAYERING: LayeringDetector(),
            PatternType.CUSTODY_CHANGE: CustodyChangeDetector(),
            PatternType.SYNCHRONIZED_TRANSFERS: SynchronizedTransferDetector(),
            PatternType.OFF_PEAK_ACTIVITY: OffPeakActivityDetector(),
            PatternType.ROUND_AMOUNTS: RoundAmountDetector(),
        }
        self.cache = {}
        self.cache_ttl = 1800  # 30 minutes
        self._initialized = False
        self.metrics = {
            "total_detections": 0,
            "total_analyses": 0,
            "patterns_detected": {},
            "avg_processing_time": 0.0,
            "cache_hit_rate": 0.0,
            "last_update": None,
        }

    async def initialize(self):
        """Initialize the pattern detection engine"""
        if self._initialized:
            return

        logger.info("Initializing Pattern Detection Engine...")
        await self._create_pattern_tables()
        self._initialized = True
        logger.info("Pattern Detection Engine initialized successfully")

    async def _create_pattern_tables(self):
        """Create pattern detection tables"""

        create_patterns_table = """
        CREATE TABLE IF NOT EXISTS pattern_detections (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            address VARCHAR(255) NOT NULL,
            blockchain VARCHAR(50) NOT NULL,
            pattern_id VARCHAR(100) NOT NULL,
            pattern_name VARCHAR(255) NOT NULL,
            detected BOOLEAN NOT NULL DEFAULT FALSE,
            confidence_score DECIMAL(5,4) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            evidence JSONB DEFAULT '[]',
            indicators_met TEXT[] DEFAULT '{}',
            indicators_missed TEXT[] DEFAULT '{}',
            transaction_count INTEGER NOT NULL DEFAULT 0,
            time_window_hours INTEGER NOT NULL DEFAULT 24,
            metadata JSONB DEFAULT '{}',
            analysis_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_pattern_detections_address ON pattern_detections(address);
        CREATE INDEX IF NOT EXISTS idx_pattern_detections_blockchain ON pattern_detections(blockchain);
        CREATE INDEX IF NOT EXISTS idx_pattern_detections_pattern ON pattern_detections(pattern_id);
        CREATE INDEX IF NOT EXISTS idx_pattern_detections_confidence ON pattern_detections(confidence_score);
        CREATE INDEX IF NOT EXISTS idx_pattern_detections_timestamp ON pattern_detections(analysis_timestamp);
        CREATE INDEX IF NOT EXISTS idx_pattern_detections_severity ON pattern_detections(severity);
        """

        create_alerts_table = """
        CREATE TABLE IF NOT EXISTS pattern_alerts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            address VARCHAR(255) NOT NULL,
            blockchain VARCHAR(50) NOT NULL,
            pattern_id VARCHAR(100) NOT NULL,
            pattern_name VARCHAR(255) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            confidence_score DECIMAL(5,4) NOT NULL,
            evidence_summary TEXT NOT NULL,
            transaction_count INTEGER NOT NULL DEFAULT 0,
            first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            assigned_to VARCHAR(255),
            notes TEXT,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_pattern_alerts_address ON pattern_alerts(address);
        CREATE INDEX IF NOT EXISTS idx_pattern_alerts_pattern ON pattern_alerts(pattern_id);
        CREATE INDEX IF NOT EXISTS idx_pattern_alerts_severity ON pattern_alerts(severity);
        CREATE INDEX IF NOT EXISTS idx_pattern_alerts_status ON pattern_alerts(status);
        """

        create_metrics_table = """
        CREATE TABLE IF NOT EXISTS pattern_metrics (
            pattern_id VARCHAR(100) PRIMARY KEY,
            pattern_name VARCHAR(255) NOT NULL,
            total_detections INTEGER NOT NULL DEFAULT 0,
            true_positives INTEGER NOT NULL DEFAULT 0,
            false_positives INTEGER NOT NULL DEFAULT 0,
            precision DECIMAL(5,4) NOT NULL DEFAULT 0.0,
            recall DECIMAL(5,4) NOT NULL DEFAULT 0.0,
            f1_score DECIMAL(5,4) NOT NULL DEFAULT 0.0,
            avg_confidence DECIMAL(5,4) NOT NULL DEFAULT 0.0,
            avg_processing_time_ms DECIMAL(10,2) NOT NULL DEFAULT 0.0,
            last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """

        conn = await get_postgres_connection()
        try:
            await conn.execute(create_patterns_table)
            await conn.execute(create_alerts_table)
            await conn.execute(create_metrics_table)
            await conn.commit()
            logger.info("Pattern detection tables created/verified")
        except Exception as e:
            logger.error(f"Error creating pattern tables: {e}")
            await conn.rollback()
            raise
        finally:
            await conn.close()

    async def analyze_address_patterns(
        self,
        address: str,
        blockchain: str,
        pattern_types: Optional[List[PatternType]] = None,
        min_severity: Optional[PatternSeverity] = None,
        time_range_hours: int = 24,
        include_evidence: bool = True,
        min_confidence: float = 0.5,
    ) -> PatternAnalysisResult:
        """Comprehensive pattern analysis for an address"""

        start_time = _time.time()

        # Check cache first
        cache_key = f"{address}:{blockchain}:{time_range_hours}:{min_confidence}:{','.join(pattern_types or [])}:{min_severity or ''}"
        if cache_key in self.cache:
            cached_result = self.cache[cache_key]
            if (
                datetime.now(timezone.utc) - cached_result["timestamp"]
            ).total_seconds() < self.cache_ttl:
                logger.debug(f"Cache hit for pattern analysis: {address}")
                self._update_cache_hit_rate(True)
                return cached_result["result"]

        self._update_cache_hit_rate(False)

        logger.info(f"Analyzing patterns for address: {address} on {blockchain}")

        try:
            # Get transaction history for address
            transactions = await self._get_transaction_history(
                address, blockchain, time_range_hours
            )

            if not transactions:
                return self._create_empty_analysis_result(
                    address, blockchain, "No transactions found"
                )

            # Run pattern detection algorithms
            pattern_results = []
            enabled_patterns = self.pattern_library.get_enabled_patterns()

            for pattern_type, detector in self.detectors.items():
                # Skip if pattern type not requested
                if pattern_types and pattern_type not in pattern_types:
                    continue

                # Skip if pattern not enabled
                pattern = enabled_patterns.get(pattern_type.value)
                if not pattern or not pattern.enabled:
                    continue

                # Skip if severity below threshold
                if min_severity and pattern.severity.value < min_severity.value:
                    continue

                # Run detection
                try:
                    if pattern_type == PatternType.PEELING_CHAIN:
                        result = await detector.detect_peeling_chain(
                            transactions, address, min_confidence
                        )
                    elif pattern_type == PatternType.LAYERING:
                        result = await detector.detect_layering(
                            transactions, address, min_confidence
                        )
                    elif pattern_type == PatternType.CUSTODY_CHANGE:
                        result = await detector.detect_custody_change(
                            transactions, address, min_confidence
                        )
                    elif pattern_type == PatternType.SYNCHRONIZED_TRANSFERS:
                        result = await detector.detect_synchronized_transfers(
                            transactions, address, min_confidence
                        )
                    elif pattern_type == PatternType.OFF_PEAK_ACTIVITY:
                        result = await detector.detect_off_peak_activity(
                            transactions, address, min_confidence
                        )
                    elif pattern_type == PatternType.ROUND_AMOUNTS:
                        result = await detector.detect_round_amounts(
                            transactions, address, min_confidence
                        )
                    else:
                        continue

                    if result.detected:
                        pattern_results.append(result)
                        self._update_pattern_metrics(pattern.pattern_id, result)

                except Exception as e:
                    logger.error(f"Error in {pattern_type.value} detection: {e}")
                    continue

            # Calculate overall risk score
            overall_risk_score = self._calculate_overall_risk_score(pattern_results)

            processing_time = (_time.time() - start_time) * 1000
            self._update_processing_metrics(processing_time)

            result = PatternAnalysisResult(
                address=address,
                blockchain=blockchain,
                patterns=pattern_results,
                overall_risk_score=overall_risk_score,
                total_transactions_analyzed=len(transactions),
                time_range_hours=time_range_hours,
                analysis_timestamp=datetime.now(timezone.utc),
                processing_time_ms=processing_time,
                metadata={
                    "algorithms_used": [ptype.value for ptype in self.detectors.keys()],
                    "patterns_detected": len(pattern_results),
                    "cache_hit": False,
                },
            )

            # Cache result
            self.cache[cache_key] = {
                "result": result,
                "timestamp": datetime.now(timezone.utc),
            }

            logger.info(
                f"Pattern analysis complete for {address}: {len(pattern_results)} patterns detected"
            )
            return result

        except Exception as e:
            logger.error(f"Error analyzing patterns for {address}: {e}")
            processing_time = (_time.time() - start_time) * 1000

            return PatternAnalysisResult(
                address=address,
                blockchain=blockchain,
                patterns=[],
                overall_risk_score=0.0,
                total_transactions_analyzed=0,
                time_range_hours=time_range_hours,
                analysis_timestamp=datetime.now(timezone.utc),
                processing_time_ms=processing_time,
                metadata={"error": str(e), "cache_hit": False},
            )

    async def batch_analyze_patterns(
        self, request: PatternRequest
    ) -> Dict[str, PatternAnalysisResult]:
        """Batch pattern analysis for multiple addresses"""

        logger.info(f"Batch analyzing patterns for {len(request.addresses)} addresses")

        start_time = _time.time()

        # Process addresses concurrently with limit
        max_concurrent = 10
        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_single_address(
            address: str,
        ) -> Tuple[str, Optional[PatternAnalysisResult]]:
            async with semaphore:
                try:
                    result = await self.analyze_address_patterns(
                        address=address,
                        blockchain=request.blockchain,
                        pattern_types=request.pattern_types,
                        min_severity=request.min_severity,
                        time_range_hours=request.time_range_hours,
                        include_evidence=request.include_evidence,
                        min_confidence=request.min_confidence,
                    )
                    return address, result
                except Exception as e:
                    logger.error(f"Error analyzing patterns for {address}: {e}")
                    return address, None

        # Execute all analyses concurrently
        tasks = [analyze_single_address(address) for address in request.addresses]

        results = await asyncio.gather(*tasks)

        # Build results dictionary
        analysis_results = {}
        failed_addresses = []

        for address, result in results:
            if isinstance(result, Exception):
                logger.error(f"Error analyzing patterns for {address}: {result}")
                failed_addresses.append(address)
            elif result is not None:
                analysis_results[address] = result

        processing_time = (_time.time() - start_time) * 1000

        # Update metrics
        total_patterns = sum(
            len(result.patterns) for result in analysis_results.values() if result
        )
        high_risk_findings = sum(
            1
            for result in analysis_results.values()
            if result and result.overall_risk_score >= 0.7
        )

        logger.info(
            f"Batch pattern analysis complete: {len(analysis_results)} successful, {len(failed_addresses)} failed"
        )

        return analysis_results

    async def _get_transaction_history(
        self, address: str, blockchain: str, time_range_hours: int
    ) -> List:
        """Get transaction history for address (placeholder implementation)"""

        # This would integrate with the existing blockchain collectors
        # For now, return empty list as placeholder
        logger.debug(
            f"Transaction history not yet implemented for {address} on {blockchain}"
        )
        return []

    def _calculate_overall_risk_score(
        self, pattern_results: List[PatternResult]
    ) -> float:
        """Calculate overall risk score from pattern results"""

        if not pattern_results:
            return 0.0

        # Weight patterns by severity
        severity_weights = {
            PatternSeverity.LOW: 0.1,
            PatternSeverity.MEDIUM: 0.3,
            PatternSeverity.HIGH: 0.6,
            PatternSeverity.CRITICAL: 0.9,
            PatternSeverity.SEVERE: 1.0,
        }

        weighted_scores = []
        for result in pattern_results:
            weight = severity_weights.get(result.severity, 0.5)
            weighted_score = result.confidence_score * weight
            weighted_scores.append(weighted_score)

        # Return maximum weighted score (most severe pattern)
        return max(weighted_scores) if weighted_scores else 0.0

    def _create_empty_analysis_result(
        self, address: str, blockchain: str, reason: str
    ) -> PatternAnalysisResult:
        """Create empty analysis result"""

        return PatternAnalysisResult(
            address=address,
            blockchain=blockchain,
            patterns=[],
            overall_risk_score=0.0,
            total_transactions_analyzed=0,
            time_range_hours=24,
            analysis_timestamp=datetime.now(timezone.utc),
            processing_time_ms=0.0,
            metadata={"analysis_reason": reason, "cache_hit": False},
        )

    def _update_pattern_metrics(self, pattern_id: str, result: PatternResult):
        """Update pattern detection metrics"""

        self.metrics["total_detections"] += 1

        if pattern_id not in self.metrics["patterns_detected"]:
            self.metrics["patterns_detected"][pattern_id] = 0

        self.metrics["patterns_detected"][pattern_id] += 1
        self.metrics["last_update"] = datetime.now(timezone.utc)

    def _update_processing_metrics(self, processing_time_ms: float):
        """Update processing time metrics"""

        # Increment total analyses counter
        self.metrics["total_analyses"] += 1

        current_avg = self.metrics["avg_processing_time"]
        total_analyses = self.metrics["total_analyses"]

        if total_analyses > 0:
            self.metrics["avg_processing_time"] = (
                current_avg * (total_analyses - 1) + processing_time_ms
            ) / total_analyses

        self.metrics["last_update"] = datetime.now(timezone.utc)

    def _update_cache_hit_rate(self, hit: bool):
        """Update cache hit rate metrics"""

        # Simple moving average for cache hit rate
        if not hasattr(self, "_cache_requests"):
            self._cache_requests = 0
            self._cache_hits = 0

        self._cache_requests += 1
        if hit:
            self._cache_hits += 1

        self.metrics["cache_hit_rate"] = self._cache_hits / self._cache_requests

    def get_metrics(self) -> Dict[str, Any]:
        """Get pattern detection metrics"""

        return {
            **self.metrics,
            "enabled_patterns": len(self.pattern_library.get_enabled_patterns()),
            "total_algorithms": len(self.detectors),
            "cache_size": len(self.cache),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def clear_cache(self):
        """Clear the pattern detection cache"""
        self.cache.clear()
        logger.info("Pattern detection cache cleared")


# Global pattern detector instance
_pattern_detector = None


def get_pattern_detector() -> AdvancedPatternDetector:
    """Get the global pattern detector instance"""
    global _pattern_detector
    if _pattern_detector is None:
        _pattern_detector = AdvancedPatternDetector()
    return _pattern_detector
