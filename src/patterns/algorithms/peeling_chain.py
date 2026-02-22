"""
Peeling Chain Detection Algorithm
Detects sequential transactions with decreasing amounts typical of chain peeling
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

from ..models import PatternResult, PatternEvidence, PatternSeverity

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


class PeelingChainDetector:
    """Detects peeling chain patterns in transaction sequences"""
    
    def __init__(self):
        self.min_sequence_length = 3
        self.amount_tolerance = 0.05  # 5% tolerance for decreasing amounts
        self.max_time_gap_hours = 24
        self.confidence_boost_per_extra_tx = 0.05
        self.max_confidence = 0.95
    
    async def detect_peeling_chain(
        self,
        transactions: List[Transaction],
        address: str,
        min_confidence: float = 0.5
    ) -> PatternResult:
        """
        Detect peeling chain pattern for an address
        
        Args:
            transactions: List of transactions for the address
            address: Target address to analyze
            min_confidence: Minimum confidence threshold
            
        Returns:
            PatternResult with detection details
        """
        
        if len(transactions) < self.min_sequence_length:
            return self._create_empty_result("Insufficient transactions")
        
        # Sort transactions by timestamp
        sorted_txs = sorted(transactions, key=lambda x: x.timestamp)
        
        # Find peeling sequences
        peeling_sequences = self._find_peeling_sequences(sorted_txs, address)
        
        if not peeling_sequences:
            return self._create_empty_result("No peeling sequences found")
        
        # Calculate confidence based on best sequence
        best_sequence = max(peeling_sequences, key=lambda seq: self._calculate_sequence_confidence(seq))
        confidence = self._calculate_sequence_confidence(best_sequence)
        
        # Apply minimum confidence threshold
        if confidence < min_confidence:
            return self._create_empty_result(f"Confidence {confidence:.2f} below threshold {min_confidence}")
        
        # Create evidence
        evidence = self._create_evidence(best_sequence, address)
        
        # Calculate indicators met/missed
        indicators_met = [
            "sequential_decreasing_amounts",
            "time_window_compliance",
            "minimum_sequence_length"
        ]
        
        indicators_missed = []
        if confidence < 0.8:
            indicators_missed.append("strong_amount_decrease")
        if best_sequence[-1].timestamp - best_sequence[0].timestamp > timedelta(hours=self.max_time_gap_hours):
            indicators_missed.append("time_window_compliance")
        
        return PatternResult(
            pattern_id="peeling_chain",
            pattern_name="Peeling Chain Detection",
            detected=True,
            confidence_score=min(confidence, self.max_confidence),
            severity=self._determine_severity(confidence, len(best_sequence)),
            evidence=evidence,
            indicators_met=indicators_met,
            indicators_missed=indicators_missed,
            transaction_count=len(best_sequence),
            time_window_hours=self.max_time_gap_hours,
            metadata={
                "sequence_length": len(best_sequence),
                "total_amount_peeled": self._calculate_peeled_amount(best_sequence),
                "peeling_ratio": self._calculate_peeling_ratio(best_sequence),
                "time_span_hours": (best_sequence[-1].timestamp - best_sequence[0].timestamp).total_seconds() / 3600,
                "algorithm_version": "1.0"
            }
        )
    
    def _find_peeling_sequences(self, transactions: List[Transaction], address: str) -> List[List[Transaction]]:
        """Find all potential peeling sequences in transactions"""
        
        sequences = []
        n = len(transactions)
        
        # Look for sequences starting at each transaction
        for i in range(n - self.min_sequence_length + 1):
            current_sequence = [transactions[i]]
            
            # Try to extend sequence
            for j in range(i + 1, n):
                current_tx = transactions[j]
                prev_tx = current_sequence[-1]
                
                # Check if this continues the peeling pattern
                if self._is_peeling_step(prev_tx, current_tx):
                    current_sequence.append(current_tx)
                else:
                    break
            
            # Check if sequence meets minimum length
            if len(current_sequence) >= self.min_sequence_length:
                sequences.append(current_sequence)
        
        return sequences
    
    def _is_peeling_step(self, prev_tx: Transaction, current_tx: Transaction) -> bool:
        """Check if current transaction continues peeling pattern from previous"""
        
        # Check time gap
        time_gap = current_tx.timestamp - prev_tx.timestamp
        if time_gap > timedelta(hours=self.max_time_gap_hours):
            return False
        
        # Check amount decrease (within tolerance)
        expected_min_amount = prev_tx.amount * (1 - self.amount_tolerance)
        if current_tx.amount > expected_min_amount:
            return False
        
        # Check if recipient is different (peeling to new address)
        if current_tx.recipient == prev_tx.recipient:
            return False
        
        return True
    
    def _calculate_sequence_confidence(self, sequence: List[Transaction]) -> float:
        """Calculate confidence score for a peeling sequence"""
        
        base_confidence = 0.5
        
        # Length bonus (longer sequences = higher confidence)
        length_bonus = min(0.3, (len(sequence) - self.min_sequence_length) * 0.1)
        
        # Amount consistency bonus
        amount_consistency = self._calculate_amount_consistency(sequence)
        consistency_bonus = amount_consistency * 0.2
        
        # Time compression bonus (faster peeling = higher confidence)
        time_compression = self._calculate_time_compression(sequence)
        compression_bonus = time_compression * 0.1
        
        # Total confidence
        confidence = base_confidence + length_bonus + consistency_bonus + compression_bonus
        
        return min(confidence, self.max_confidence)
    
    def _calculate_amount_consistency(self, sequence: List[Transaction]) -> float:
        """Calculate how consistent the amount decreases are"""
        
        if len(sequence) < 2:
            return 0.0
        
        consistency_scores = []
        
        for i in range(1, len(sequence)):
            prev_amount = sequence[i-1].amount
            curr_amount = sequence[i].amount
            
            if prev_amount > 0:
                decrease_ratio = (prev_amount - curr_amount) / prev_amount
                
                # Ideal peeling has consistent decrease ratios
                # Score based on how close to ideal (0.5 = 50% decrease)
                ideal_ratio = 0.5
                ratio_diff = abs(decrease_ratio - ideal_ratio)
                consistency_score = max(0, 1 - ratio_diff * 2)  # Normalize to 0-1
                consistency_scores.append(consistency_score)
        
        return sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0.0
    
    def _calculate_time_compression(self, sequence: List[Transaction]) -> float:
        """Calculate time compression score (faster = higher confidence)"""
        
        if len(sequence) < 2:
            return 0.0
        
        total_time = sequence[-1].timestamp - sequence[0].timestamp
        total_hours = total_time.total_seconds() / 3600
        
        # Faster sequences get higher scores
        if total_hours <= 1:
            return 1.0
        elif total_hours <= 6:
            return 0.8
        elif total_hours <= 12:
            return 0.6
        elif total_hours <= 24:
            return 0.4
        else:
            return 0.2
    
    def _calculate_peeled_amount(self, sequence: List[Transaction]) -> float:
        """Calculate total amount peeled in the sequence"""
        
        if len(sequence) < 2:
            return 0.0
        
        first_amount = sequence[0].amount
        last_amount = sequence[-1].amount
        
        return first_amount - last_amount
    
    def _calculate_peeling_ratio(self, sequence: List[Transaction]) -> float:
        """Calculate the ratio of amount peeled"""
        
        if len(sequence) < 2 or sequence[0].amount == 0:
            return 0.0
        
        peeled_amount = self._calculate_peeled_amount(sequence)
        return peeled_amount / sequence[0].amount
    
    def _determine_severity(self, confidence: float, sequence_length: int) -> PatternSeverity:
        """Determine pattern severity based on confidence and characteristics"""
        
        # High confidence + long sequence = Critical
        if confidence >= 0.9 and sequence_length >= 5:
            return PatternSeverity.CRITICAL
        
        # High confidence = High
        if confidence >= 0.8:
            return PatternSeverity.HIGH
        
        # Medium confidence = Medium
        if confidence >= 0.6:
            return PatternSeverity.MEDIUM
        
        # Low confidence = Low
        return PatternSeverity.LOW
    
    def _create_evidence(self, sequence: List[Transaction], address: str) -> List[PatternEvidence]:
        """Create evidence list for the detected pattern"""
        
        evidence = []
        
        # Add sequence evidence
        evidence.append(PatternEvidence(
            evidence_type="peeling_sequence",
            description=f"Detected peeling chain of {len(sequence)} transactions",
            confidence_contribution=0.4,
            transaction_hash=sequence[0].hash,
            address=address,
            metadata={
                "sequence_length": len(sequence),
                "first_amount": sequence[0].amount,
                "last_amount": sequence[-1].amount,
                "total_peeled": self._calculate_peeled_amount(sequence)
            }
        ))
        
        # Add amount decrease evidence
        if len(sequence) >= 2:
            # Calculate valid decrease ratios only where previous amount > 0
            valid_ratios = []
            for i in range(1, len(sequence)):
                if sequence[i-1].amount > 0:
                    ratio = (sequence[i-1].amount - sequence[i].amount) / sequence[i-1].amount
                    valid_ratios.append(ratio)
            
            # Calculate average only from valid ratios
            if valid_ratios:
                avg_decrease = sum(valid_ratios) / len(valid_ratios)
            else:
                avg_decrease = 0.0
            
            evidence.append(PatternEvidence(
                evidence_type="amount_decrease",
                description=f"Average amount decrease: {avg_decrease:.1%}",
                confidence_contribution=0.3,
                transaction_hash=sequence[1].hash,
                address=address,
                metadata={
                    "average_decrease_ratio": avg_decrease,
                    "decrease_consistency": self._calculate_amount_consistency(sequence)
                }
            ))
        
        # Add timing evidence
        time_span = sequence[-1].timestamp - sequence[0].timestamp
        evidence.append(PatternEvidence(
            evidence_type="timing_pattern",
            description=f"Peeling completed over {time_span.total_seconds()/3600:.1f} hours",
            confidence_contribution=0.2,
            transaction_hash=sequence[-1].hash,
            address=address,
            metadata={
                "time_span_hours": time_span.total_seconds() / 3600,
                "time_compression_score": self._calculate_time_compression(sequence)
            }
        ))
        
        # Add counterparty evidence
        unique_recipients = set(tx.recipient for tx in sequence)
        evidence.append(PatternEvidence(
            evidence_type="counterparty_diversity",
            description=f"Peeling to {len(unique_recipients)} unique addresses",
            confidence_contribution=0.1,
            transaction_hash=sequence[0].hash,
            address=address,
            metadata={
                "unique_recipients": len(unique_recipients),
                "recipient_addresses": list(unique_recipients)
            }
        ))
        
        return evidence
    
    def _create_empty_result(self, reason: str) -> PatternResult:
        """Create empty result when pattern not detected"""
        
        return PatternResult(
            pattern_id="peeling_chain",
            pattern_name="Peeling Chain Detection",
            detected=False,
            confidence_score=0.0,
            severity=PatternSeverity.LOW,
            evidence=[],
            indicators_met=[],
            indicators_missed=[],
            transaction_count=0,
            time_window_hours=self.max_time_gap_hours,
            metadata={
                "detection_reason": reason,
                "algorithm_version": "1.0"
            }
        )
