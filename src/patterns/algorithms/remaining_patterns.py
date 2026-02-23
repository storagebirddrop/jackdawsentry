"""
Remaining Pattern Detection Algorithms
Custody Change, Synchronized Transfers, Off-Peak Activity, Round Amounts
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from ..models import PatternEvidence
from ..models import PatternResult
from ..models import PatternSeverity

logger = logging.getLogger(__name__)


@dataclass
class Transaction:
    """Transaction data structure for pattern analysis"""

    hash: str
    address: str
    amount: float
    timestamp: datetime
    recipient: str
    sender: str
    blockchain: str
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    gas_price: Optional[float] = None


class CustodyChangeDetector:
    """Detects potential changes in wallet custody or control"""

    def __init__(self):
        self.min_transactions = 10
        self.inactivity_threshold_days = 7
        self.amount_change_threshold = 2.0
        self.pattern_change_threshold = 0.6
        self.time_window_hours = 168  # 7 days

    async def detect_custody_change(
        self, transactions: List[Transaction], address: str, min_confidence: float = 0.5
    ) -> PatternResult:
        """Detect custody change patterns"""

        if len(transactions) < self.min_transactions:
            return self._create_empty_result(
                "Insufficient transactions for custody analysis"
            )

        # Sort transactions by timestamp
        sorted_txs = sorted(transactions, key=lambda x: x.timestamp)

        # Analyze behavior patterns
        behavior_change = self._analyze_behavior_change(sorted_txs)
        inactivity_change = self._analyze_inactivity_change(sorted_txs)
        amount_change = self._analyze_amount_change(sorted_txs)

        # Calculate overall confidence
        confidence = (behavior_change + inactivity_change + amount_change) / 3

        if confidence < min_confidence:
            return self._create_empty_result(
                f"Confidence {confidence:.2f} below threshold {min_confidence}"
            )

        # Create evidence
        evidence = self._create_custody_evidence(
            sorted_txs, address, behavior_change, inactivity_change, amount_change
        )

        indicators_met = []
        if behavior_change > 0.6:
            indicators_met.append("behavior_pattern_change")
        if inactivity_change > 0.6:
            indicators_met.append("inactivity_pattern_change")
        if amount_change > 0.6:
            indicators_met.append("amount_pattern_change")

        return PatternResult(
            pattern_id="custody_change",
            pattern_name="Custody Change Detection",
            detected=True,
            confidence_score=confidence,
            severity=self._determine_severity(confidence),
            evidence=evidence,
            indicators_met=indicators_met,
            indicators_missed=[],
            transaction_count=len(sorted_txs),
            time_window_hours=self.time_window_hours,
            metadata={
                "behavior_change_score": behavior_change,
                "inactivity_change_score": inactivity_change,
                "amount_change_score": amount_change,
                "algorithm_version": "1.0",
            },
        )

    def _analyze_behavior_change(self, transactions: List[Transaction]) -> float:
        """Analyze changes in transaction behavior patterns"""

        if len(transactions) < 20:
            return 0.0

        # Split into two halves
        mid_point = len(transactions) // 2
        first_half = transactions[:mid_point]
        second_half = transactions[mid_point:]

        # Compare patterns
        pattern_score = 0.0

        # Amount variance comparison
        first_variance = self._calculate_amount_variance(first_half)
        second_variance = self._calculate_amount_variance(second_half)

        if first_variance > 0 and second_variance > 0:
            variance_change = abs(first_variance - second_variance) / max(
                first_variance, second_variance
            )
            pattern_score += variance_change * 0.4

        # Timing pattern comparison
        first_timing = self._calculate_timing_pattern(first_half)
        second_timing = self._calculate_timing_pattern(second_half)

        timing_change = abs(first_timing - second_timing)
        pattern_score += timing_change * 0.3

        # Counterparty diversity comparison
        first_diversity = len(set(tx.recipient for tx in first_half))
        second_diversity = len(set(tx.recipient for tx in second_half))

        diversity_change = abs(first_diversity - second_diversity) / max(
            first_diversity, second_diversity, 1
        )
        pattern_score += diversity_change * 0.3

        return min(pattern_score, 1.0)

    def _analyze_inactivity_change(self, transactions: List[Transaction]) -> float:
        """Analyze inactivity patterns"""

        if len(transactions) < 5:
            return 0.0

        # Find longest inactivity gap
        max_gap = 0
        for i in range(1, len(transactions)):
            gap = (transactions[i].timestamp - transactions[i - 1].timestamp).days
            max_gap = max(max_gap, gap)

        # Score based on inactivity duration
        if max_gap >= self.inactivity_threshold_days:
            return min(1.0, max_gap / 30.0)  # Normalize to 30 days max

        return 0.0

    def _analyze_amount_change(self, transactions: List[Transaction]) -> float:
        """Analyze changes in transaction amounts"""

        if len(transactions) < 10:
            return 0.0

        # Compare recent vs historical amounts
        recent_txs = transactions[-5:]  # Last 5 transactions
        historical_txs = transactions[:-5]  # Earlier transactions

        if not historical_txs:
            return 0.0

        recent_avg = sum(tx.amount for tx in recent_txs) / len(recent_txs)
        historical_avg = sum(tx.amount for tx in historical_txs) / len(historical_txs)

        if historical_avg > 0:
            change_ratio = abs(recent_avg - historical_avg) / historical_avg
            return min(1.0, change_ratio / self.amount_change_threshold)

        return 0.0

    def _calculate_amount_variance(self, transactions: List[Transaction]) -> float:
        """Calculate variance in transaction amounts"""

        if len(transactions) < 2:
            return 0.0

        amounts = [tx.amount for tx in transactions]
        avg = sum(amounts) / len(amounts)

        variance = sum((amount - avg) ** 2 for amount in amounts) / len(amounts)
        return variance**0.5  # Standard deviation

    def _calculate_timing_pattern(self, transactions: List[Transaction]) -> float:
        """Calculate timing pattern regularity"""

        if len(transactions) < 3:
            return 0.0

        intervals = []
        for i in range(1, len(transactions)):
            interval = (
                transactions[i].timestamp - transactions[i - 1].timestamp
            ).total_seconds()
            intervals.append(interval)

        if not intervals:
            return 0.0

        avg_interval = sum(intervals) / len(intervals)
        variance = sum((interval - avg_interval) ** 2 for interval in intervals) / len(
            intervals
        )

        # Lower variance = more regular pattern
        if avg_interval > 0:
            score = 1.0 - (variance**0.5) / avg_interval
            return min(1.0, max(0.0, score))

        return 0.0

    def _determine_severity(self, confidence: float) -> PatternSeverity:
        """Determine severity based on confidence"""

        if confidence >= 0.8:
            return PatternSeverity.HIGH
        elif confidence >= 0.6:
            return PatternSeverity.MEDIUM
        else:
            return PatternSeverity.LOW

    def _create_custody_evidence(
        self,
        transactions: List[Transaction],
        address: str,
        behavior_change: float,
        inactivity_change: float,
        amount_change: float,
    ) -> List[PatternEvidence]:
        """Create evidence for custody change detection"""

        evidence = []

        if behavior_change > 0.6:
            evidence.append(
                PatternEvidence(
                    evidence_type="behavior_change",
                    description=f"Behavior pattern change detected (score: {behavior_change:.2f})",
                    confidence_contribution=0.4,
                    transaction_hash=transactions[0].hash,
                    address=address,
                )
            )

        if inactivity_change > 0.6:
            evidence.append(
                PatternEvidence(
                    evidence_type="inactivity_change",
                    description=f"Inactivity pattern change detected (score: {inactivity_change:.2f})",
                    confidence_contribution=0.3,
                    transaction_hash=transactions[-1].hash,
                    address=address,
                )
            )

        if amount_change > 0.6:
            evidence.append(
                PatternEvidence(
                    evidence_type="amount_change",
                    description=f"Transaction amount change detected (score: {amount_change:.2f})",
                    confidence_contribution=0.3,
                    transaction_hash=transactions[len(transactions) // 2].hash,
                    address=address,
                )
            )

        return evidence

    def _create_empty_result(self, reason: str) -> PatternResult:
        """Create empty result when pattern not detected"""

        return PatternResult(
            pattern_id="custody_change",
            pattern_name="Custody Change Detection",
            detected=False,
            confidence_score=0.0,
            severity=PatternSeverity.LOW,
            evidence=[],
            indicators_met=[],
            indicators_missed=[],
            transaction_count=0,
            time_window_hours=self.time_window_hours,
            metadata={"detection_reason": reason, "algorithm_version": "1.0"},
        )


class SynchronizedTransferDetector:
    """Detects coordinated transfers across multiple addresses"""

    def __init__(self):
        self.sync_window_seconds = 300  # 5 minutes
        self.amount_tolerance = 0.1  # 10%
        self.min_addresses = 2
        self.min_transfers = 2
        self.time_window_hours = 1

    async def detect_synchronized_transfers(
        self, transactions: List[Transaction], address: str, min_confidence: float = 0.5
    ) -> PatternResult:
        """Detect synchronized transfer patterns"""

        if len(transactions) < self.min_transfers:
            return self._create_empty_result(
                "Insufficient transactions for sync analysis"
            )

        # Find synchronized transfer groups
        sync_groups = self._find_synchronized_groups(transactions)

        if not sync_groups:
            return self._create_empty_result("No synchronized transfers detected")

        # Analyze best group
        best_group = max(
            sync_groups, key=lambda group: self._calculate_group_confidence(group)
        )
        confidence = self._calculate_group_confidence(best_group)

        if confidence < min_confidence:
            return self._create_empty_result(
                f"Confidence {confidence:.2f} below threshold {min_confidence}"
            )

        # Create evidence
        evidence = self._create_sync_evidence(best_group, address)

        return PatternResult(
            pattern_id="synchronized_transfers",
            pattern_name="Synchronized Transfer Analysis",
            detected=True,
            confidence_score=confidence,
            severity=self._determine_severity(confidence, len(best_group)),
            evidence=evidence,
            indicators_met=[
                "timing_synchronization",
                "amount_similarity",
                "multiple_addresses",
            ],
            indicators_missed=[],
            transaction_count=len(best_group),
            time_window_hours=self.time_window_hours,
            metadata={
                "unique_addresses": len(set(tx.sender for tx in best_group)),
                "sync_window_seconds": self.sync_window_seconds,
                "total_amount": sum(tx.amount for tx in best_group),
                "algorithm_version": "1.0",
            },
        )

    def _find_synchronized_groups(
        self, transactions: List[Transaction]
    ) -> List[List[Transaction]]:
        """Find groups of synchronized transfers"""

        groups = []
        used_transactions = set()

        for i, tx1 in enumerate(transactions):
            if tx1.hash in used_transactions:
                continue

            current_group = [tx1]

            for j, tx2 in enumerate(transactions):
                if i == j or tx2.hash in used_transactions:
                    continue

                if self._is_synchronized(tx1, tx2):
                    current_group.append(tx2)
                    used_transactions.add(tx2.hash)

            if len(current_group) >= self.min_transfers:
                groups.append(current_group)
                used_transactions.add(tx1.hash)

        return groups

    def _is_synchronized(self, tx1: Transaction, tx2: Transaction) -> bool:
        """Check if two transactions are synchronized"""

        # Check time window
        time_diff = abs((tx1.timestamp - tx2.timestamp).total_seconds())
        if time_diff > self.sync_window_seconds:
            return False

        # Check amount similarity
        if tx1.amount == 0 or tx2.amount == 0:
            return False

        amount_diff = abs(tx1.amount - tx2.amount) / max(tx1.amount, tx2.amount)
        if amount_diff > self.amount_tolerance:
            return False

        return True

    def _calculate_group_confidence(self, group: List[Transaction]) -> float:
        """Calculate confidence score for synchronized group"""

        base_confidence = 0.6

        # Size bonus (more transfers = higher confidence)
        size_bonus = min(0.3, (len(group) - self.min_transfers) * 0.1)

        # Address diversity bonus
        unique_addresses = len(set(tx.sender for tx in group))
        diversity_bonus = min(0.1, (unique_addresses - self.min_addresses) * 0.05)

        return min(base_confidence + size_bonus + diversity_bonus, 1.0)

    def _determine_severity(
        self, confidence: float, group_size: int
    ) -> PatternSeverity:
        """Determine severity based on confidence and group size"""

        if confidence >= 0.8 and group_size >= 3:
            return PatternSeverity.HIGH
        elif confidence >= 0.6:
            return PatternSeverity.MEDIUM
        else:
            return PatternSeverity.LOW

    def _create_sync_evidence(
        self, group: List[Transaction], address: str
    ) -> List[PatternEvidence]:
        """Create evidence for synchronized transfers"""

        evidence = []

        evidence.append(
            PatternEvidence(
                evidence_type="synchronized_transfers",
                description=f"Detected {len(group)} synchronized transfers",
                confidence_contribution=0.4,
                transaction_hash=group[0].hash,
                address=address,
                metadata={
                    "group_size": len(group),
                    "unique_addresses": len(set(tx.sender for tx in group)),
                },
            )
        )

        evidence.append(
            PatternEvidence(
                evidence_type="timing_synchronization",
                description=f"Transfers synchronized within {self.sync_window_seconds} seconds",
                confidence_contribution=0.3,
                transaction_hash=group[0].hash,
                address=address,
            )
        )

        evidence.append(
            PatternEvidence(
                evidence_type="amount_similarity",
                description=f"Amounts similar within {self.amount_tolerance*100:.0f}% tolerance",
                confidence_contribution=0.3,
                transaction_hash=group[0].hash,
                address=address,
            )
        )

        return evidence

    def _create_empty_result(self, reason: str) -> PatternResult:
        """Create empty result when pattern not detected"""

        return PatternResult(
            pattern_id="synchronized_transfers",
            pattern_name="Synchronized Transfer Analysis",
            detected=False,
            confidence_score=0.0,
            severity=PatternSeverity.LOW,
            evidence=[],
            indicators_met=[],
            indicators_missed=[],
            transaction_count=0,
            time_window_hours=self.time_window_hours,
            metadata={"detection_reason": reason, "algorithm_version": "1.0"},
        )


class OffPeakActivityDetector:
    """Detects unusual activity during low-traffic periods"""

    def __init__(self):
        self.off_peak_hours = [22, 23, 0, 1, 2, 3, 4, 5, 6]  # 10 PM - 6 AM UTC
        self.off_peak_ratio_threshold = 0.3
        self.min_transactions = 5
        self.high_value_threshold = 1000.0  # USD
        self.time_window_hours = 168  # 7 days

    async def detect_off_peak_activity(
        self, transactions: List[Transaction], address: str, min_confidence: float = 0.5
    ) -> PatternResult:
        """Detect off-peak hours activity patterns"""

        if len(transactions) < self.min_transactions:
            return self._create_empty_result(
                "Insufficient transactions for off-peak analysis"
            )

        # Analyze off-peak activity
        off_peak_ratio = self._calculate_off_peak_ratio(transactions)
        high_value_off_peak = self._count_high_value_off_peak(transactions)

        # Calculate confidence
        confidence = (off_peak_ratio * 0.6) + (high_value_off_peak * 0.4)

        if confidence < min_confidence:
            return self._create_empty_result(
                f"Confidence {confidence:.2f} below threshold {min_confidence}"
            )

        # Create evidence
        evidence = self._create_off_peak_evidence(
            transactions, address, off_peak_ratio, high_value_off_peak
        )

        return PatternResult(
            pattern_id="off_peak_activity",
            pattern_name="Off-Peak Hours Activity",
            detected=True,
            confidence_score=confidence,
            severity=self._determine_severity(confidence),
            evidence=evidence,
            indicators_met=["off_peak_timing", "minimum_transactions"],
            indicators_missed=[],
            transaction_count=len(transactions),
            time_window_hours=self.time_window_hours,
            metadata={
                "off_peak_ratio": off_peak_ratio,
                "high_value_off_peak": high_value_off_peak,
                "off_peak_hours": self.off_peak_hours,
                "algorithm_version": "1.0",
            },
        )

    def _calculate_off_peak_ratio(self, transactions: List[Transaction]) -> float:
        """Calculate ratio of transactions during off-peak hours"""

        off_peak_count = 0
        for tx in transactions:
            hour = tx.timestamp.hour
            if hour in self.off_peak_hours:
                off_peak_count += 1

        return off_peak_count / len(transactions)

    def _count_high_value_off_peak(self, transactions: List[Transaction]) -> float:
        """Count high-value transactions during off-peak hours"""

        high_value_count = 0
        for tx in transactions:
            hour = tx.timestamp.hour
            if hour in self.off_peak_hours and tx.amount >= self.high_value_threshold:
                high_value_count += 1

        return high_value_count / len(transactions)

    def _determine_severity(self, confidence: float) -> PatternSeverity:
        """Determine severity based on confidence"""

        if confidence >= 0.8:
            return PatternSeverity.HIGH
        elif confidence >= 0.6:
            return PatternSeverity.MEDIUM
        else:
            return PatternSeverity.LOW

    def _create_off_peak_evidence(
        self,
        transactions: List[Transaction],
        address: str,
        off_peak_ratio: float,
        high_value_off_peak: float,
    ) -> List[PatternEvidence]:
        """Create evidence for off-peak activity"""

        evidence = []

        evidence.append(
            PatternEvidence(
                evidence_type="off_peak_timing",
                description=f"{off_peak_ratio:.1%} of transactions during off-peak hours",
                confidence_contribution=0.6,
                transaction_hash=transactions[0].hash,
                address=address,
                metadata={
                    "off_peak_hours": self.off_peak_hours,
                    "total_transactions": len(transactions),
                    "off_peak_count": int(off_peak_ratio * len(transactions)),
                },
            )
        )

        if high_value_off_peak > 0:
            evidence.append(
                PatternEvidence(
                    evidence_type="high_value_off_peak",
                    description=f"{high_value_off_peak:.1%} high-value transactions during off-peak",
                    confidence_contribution=0.4,
                    transaction_hash=transactions[0].hash,
                    address=address,
                    metadata={
                        "high_value_threshold": self.high_value_threshold,
                        "high_value_count": int(
                            high_value_off_peak * len(transactions)
                        ),
                    },
                )
            )

        return evidence

    def _create_empty_result(self, reason: str) -> PatternResult:
        """Create empty result when pattern not detected"""

        return PatternResult(
            pattern_id="off_peak_activity",
            pattern_name="Off-Peak Hours Activity",
            detected=False,
            confidence_score=0.0,
            severity=PatternSeverity.LOW,
            evidence=[],
            indicators_met=[],
            indicators_missed=[],
            transaction_count=0,
            time_window_hours=self.time_window_hours,
            metadata={"detection_reason": reason, "algorithm_version": "1.0"},
        )


class RoundAmountDetector:
    """Detects suspicious round-number transactions"""

    def __init__(self):
        self.round_amounts = [0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0, 500.0, 1000.0]
        self.tolerance = 0.05  # 5%
        self.min_transactions = 3
        self.time_window_hours = 168  # 7 days

    async def detect_round_amounts(
        self, transactions: List[Transaction], address: str, min_confidence: float = 0.5
    ) -> PatternResult:
        """Detect round amount patterns"""

        if len(transactions) < self.min_transactions:
            return self._create_empty_result(
                "Insufficient transactions for round amount analysis"
            )

        # Find round amount transactions
        round_txs = self._find_round_amount_transactions(transactions)

        if len(round_txs) < self.min_transactions:
            return self._create_empty_result("Insufficient round amount transactions")

        # Calculate confidence
        round_ratio = len(round_txs) / len(transactions)
        confidence = min(0.9, round_ratio * 1.5)  # Boost confidence for higher ratios

        if confidence < min_confidence:
            return self._create_empty_result(
                f"Confidence {confidence:.2f} below threshold {min_confidence}"
            )

        # Create evidence
        evidence = self._create_round_evidence(
            round_txs, address, round_ratio, len(transactions)
        )

        return PatternResult(
            pattern_id="round_amount_patterns",
            pattern_name="Round Amount Analysis",
            detected=True,
            confidence_score=confidence,
            severity=self._determine_severity(confidence, len(round_txs)),
            evidence=evidence,
            indicators_met=["round_amount_detection", "minimum_transactions"],
            indicators_missed=[],
            transaction_count=len(round_txs),
            time_window_hours=self.time_window_hours,
            metadata={
                "round_amount_ratio": round_ratio,
                "common_round_amounts": self._get_common_round_amounts(round_txs),
                "algorithm_version": "1.0",
            },
        )

    def _find_round_amount_transactions(
        self, transactions: List[Transaction]
    ) -> List[Transaction]:
        """Find transactions with round amounts"""

        round_txs = []

        for tx in transactions:
            if self._is_round_amount(tx.amount):
                round_txs.append(tx)

        return round_txs

    def _is_round_amount(self, amount: float) -> bool:
        """Check if amount is a round number"""

        for round_amount in self.round_amounts:
            tolerance = round_amount * self.tolerance
            if abs(amount - round_amount) <= tolerance:
                return True

        return False

    def _get_common_round_amounts(self, round_txs: List[Transaction]) -> List[str]:
        """Get most common round amounts in transactions"""

        amount_counts = {}
        for tx in round_txs:
            for round_amount in self.round_amounts:
                if abs(tx.amount - round_amount) <= round_amount * self.tolerance:
                    amount_counts[str(round_amount)] = (
                        amount_counts.get(str(round_amount), 0) + 1
                    )

        # Sort by count and return top amounts
        sorted_amounts = sorted(amount_counts.items(), key=lambda x: x[1], reverse=True)
        return [amount for amount, count in sorted_amounts[:5]]

    def _determine_severity(
        self, confidence: float, round_count: int
    ) -> PatternSeverity:
        """Determine severity based on confidence and count"""

        if confidence >= 0.8 and round_count >= 5:
            return PatternSeverity.MEDIUM
        else:
            return PatternSeverity.LOW

    def _create_round_evidence(
        self,
        round_txs: List[Transaction],
        address: str,
        round_ratio: float,
        total_transactions: int,
    ) -> List[PatternEvidence]:
        """Create evidence for round amount detection"""

        evidence = []

        evidence.append(
            PatternEvidence(
                evidence_type="round_amount_detection",
                description=f"{round_ratio:.1%} of transactions are round amounts",
                confidence_contribution=0.6,
                transaction_hash=round_txs[0].hash,
                address=address,
                metadata={
                    "round_transaction_count": len(round_txs),
                    "total_transactions": total_transactions,
                    "common_round_amounts": self._get_common_round_amounts(round_txs),
                },
            )
        )

        return evidence

    def _create_empty_result(self, reason: str) -> PatternResult:
        """Create empty result when pattern not detected"""

        return PatternResult(
            pattern_id="round_amount_patterns",
            pattern_name="Round Amount Analysis",
            detected=False,
            confidence_score=0.0,
            severity=PatternSeverity.LOW,
            evidence=[],
            indicators_met=[],
            indicators_missed=[],
            transaction_count=0,
            time_window_hours=self.time_window_hours,
            metadata={"detection_reason": reason, "algorithm_version": "1.0"},
        )
