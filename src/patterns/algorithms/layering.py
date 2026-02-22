"""
Advanced Layering Detection Algorithm
Identifies complex multi-hop layering across different services
"""

import logging
from typing import List, Dict, Any, Set, Optional
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


class LayeringDetector:
    """Detects advanced layering patterns in transaction chains"""
    
    def __init__(self):
        self.min_hops = 5
        self.max_hops = 10
        self.max_time_gap_hours = 72
        self.min_unique_counterparties = 3
        self.confidence_boost_per_hop = 0.05
        self.max_confidence = 0.95
        
        # Known mixing/privacy services
        self.known_mixing_services = {
            'tornado_cash', 'wasabi', 'joinmarket', 'samourai', 
            'whirlpool', 'coinjoin', 'monero', 'zcash'
        }
        
        # Known exchanges (for business relationship detection)
        self.known_exchanges = {
            'binance', 'coinbase', 'kraken', 'bitfinex', 'bittrex',
            'poloniex', 'kucoin', 'huobi', 'okx', 'bybit'
        }
    
    async def detect_layering(
        self,
        transactions: List[Transaction],
        address: str,
        min_confidence: float = 0.5
    ) -> PatternResult:
        """
        Detect advanced layering pattern for an address
        
        Args:
            transactions: List of transactions for the address
            address: Target address to analyze
            min_confidence: Minimum confidence threshold
            
        Returns:
            PatternResult with detection details
        """
        
        if len(transactions) < self.min_hops:
            return self._create_empty_result("Insufficient transactions for layering analysis")
        
        # Build transaction graph
        transaction_graph = self._build_transaction_graph(transactions, address)
        
        # Find potential layering paths
        layering_paths = self._find_layering_paths(transaction_graph, address)
        
        if not layering_paths:
            return self._create_empty_result("No layering paths detected")
        
        # Analyze best path
        best_path = max(layering_paths, key=lambda path: self._calculate_path_confidence(path))
        confidence = self._calculate_path_confidence(best_path)
        
        # Apply minimum confidence threshold
        if confidence < min_confidence:
            return self._create_empty_result(f"Confidence {confidence:.2f} below threshold {min_confidence}")
        
        # Create evidence
        evidence = self._create_evidence(best_path, address)
        
        # Calculate indicators met/missed
        indicators_met = [
            "minimum_hop_count",
            "unique_counterparties",
            "time_window_compliance"
        ]
        
        indicators_missed = []
        if len(best_path) < 7:
            indicators_missed.append("extended_hop_count")
        if self._has_business_relationships(best_path):
            indicators_missed.append("no_business_relationship")
        if not self._has_mixing_indicators(best_path):
            indicators_missed.append("mixing_service_usage")
        
        return PatternResult(
            pattern_id="advanced_layering",
            pattern_name="Advanced Layering Detection",
            detected=True,
            confidence_score=min(confidence, self.max_confidence),
            severity=self._determine_severity(confidence, len(best_path)),
            evidence=evidence,
            indicators_met=indicators_met,
            indicators_missed=indicators_missed,
            transaction_count=len(best_path),
            time_window_hours=self.max_time_gap_hours,
            metadata={
                "hop_count": len(best_path),
                "unique_counterparties": len(set(tx.recipient for tx in best_path)),
                "mixing_services_used": self._identify_mixing_services(best_path),
                "total_amount": sum(tx.amount for tx in best_path),
                "time_span_hours": self._calculate_time_span(best_path),
                "obfuscation_score": self._calculate_obfuscation_score(best_path),
                "algorithm_version": "1.0"
            }
        )
    
    def _build_transaction_graph(self, transactions: List[Transaction], address: str) -> Dict[str, List[Transaction]]:
        """Build a graph of transactions starting from the address"""
        
        graph = {address: []}
        visited = set()
        
        # Simple BFS to build transaction graph
        queue = [address]
        
        while queue and len(visited) < 100:  # Limit to prevent infinite loops
            current_addr = queue.pop(0)
            
            if current_addr in visited:
                continue
            
            visited.add(current_addr)
            
            # Find transactions from current address
            outgoing_txs = [
                tx for tx in transactions 
                if tx.sender.lower() == current_addr.lower()
            ]
            
            graph[current_addr] = outgoing_txs
            
            # Add recipients to queue
            for tx in outgoing_txs:
                recipient = tx.recipient.lower()
                if recipient not in visited and recipient not in graph:
                    queue.append(recipient)
                    graph[recipient] = []
        
        return graph
    
    def _find_layering_paths(self, graph: Dict[str, List[Transaction]], start_address: str) -> List[List[Transaction]]:
        """Find potential layering paths in the transaction graph"""
        
        paths = []
        
        def dfs(current_addr: str, path: List[Transaction], visited: Set[str]):
            # Check if path meets minimum requirements
            if len(path) >= self.min_hops:
                # Check if path is within time window
                if self._is_within_time_window(path):
                    paths.append(path.copy())
            
            # Stop if path too long or visited too many nodes
            if len(path) >= self.max_hops or len(visited) >= 20:
                return
            
            # Explore outgoing transactions
            for tx in graph.get(current_addr, []):
                next_addr = tx.recipient.lower()
                
                if next_addr not in visited:
                    visited.add(next_addr)
                    path.append(tx)
                    dfs(next_addr, path, visited)
                    path.pop()
                    visited.remove(next_addr)
        
        # Start DFS from start address
        dfs(start_address.lower(), [], set())
        
        return paths
    
    def _is_within_time_window(self, path: List[Transaction]) -> bool:
        """Check if path is within the maximum time window"""
        
        if len(path) < 2:
            return True
        
        time_span = path[-1].timestamp - path[0].timestamp
        return time_span <= timedelta(hours=self.max_time_gap_hours)
    
    def _calculate_path_confidence(self, path: List[Transaction]) -> float:
        """Calculate confidence score for a layering path"""
        
        base_confidence = 0.4
        
        # Hop count bonus (more hops = higher confidence)
        hop_bonus = min(0.3, (len(path) - self.min_hops) * 0.06)
        
        # Counterparty diversity bonus
        unique_counterparties = len(set(tx.recipient for tx in path))
        diversity_bonus = min(0.2, (unique_counterparties - self.min_unique_counterparties) * 0.05)
        
        # Mixing service bonus
        mixing_services = self._identify_mixing_services(path)
        mixing_bonus = min(0.2, len(mixing_services) * 0.07)
        
        # No business relationship bonus
        no_business_bonus = 0.1 if not self._has_business_relationships(path) else 0.0
        
        # Time compression bonus (faster = higher confidence)
        time_compression = self._calculate_time_compression(path)
        compression_bonus = time_compression * 0.1
        
        # Total confidence
        confidence = base_confidence + hop_bonus + diversity_bonus + mixing_bonus + no_business_bonus + compression_bonus
        
        return min(confidence, self.max_confidence)
    
    def _identify_mixing_services(self, path: List[Transaction]) -> List[str]:
        """Identify mixing services used in the path"""
        
        mixing_services = []
        
        for tx in path:
            recipient = tx.recipient.lower()
            sender = tx.sender.lower()
            
            # Check if recipient or sender is a known mixing service
            for service in self.known_mixing_services:
                if service in recipient or service in sender:
                    mixing_services.append(service)
        
        return list(set(mixing_services))
    
    def _has_business_relationships(self, path: List[Transaction]) -> bool:
        """Check if path has obvious business relationships"""
        
        addresses = set()
        for tx in path:
            addresses.add(tx.sender.lower())
            addresses.add(tx.recipient.lower())
        
        # Check for exchange-to-exchange transfers
        exchange_count = 0
        for addr in addresses:
            for exchange in self.known_exchanges:
                if exchange in addr:
                    exchange_count += 1
        
        # If multiple exchanges involved, likely business relationship
        return exchange_count >= 2
    
    def _has_mixing_indicators(self, path: List[Transaction]) -> bool:
        """Check if path shows mixing service usage indicators"""
        
        mixing_services = self._identify_mixing_services(path)
        if mixing_services:
            return True
        
        # Check for other mixing indicators
        # 1. Round amounts (common in mixing)
        round_amounts = sum(1 for tx in path if self._is_round_amount(tx.amount))
        if round_amounts >= len(path) * 0.6:
            return True
        
        # 2. Similar amounts (common in mixing)
        if len(path) >= 3 and self._has_similar_amounts(path):
            return True
        
        # 3. Rapid succession (common in mixing)
        if self._is_rapid_succession(path):
            return True
        
        return False
    
    def _is_round_amount(self, amount: float) -> bool:
        """Check if amount is a round number"""
        
        # Common round amounts
        round_amounts = [0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0, 500.0, 1000.0]
        
        for round_amount in round_amounts:
            tolerance = round_amount * 0.01  # 1% tolerance
            if abs(amount - round_amount) <= tolerance:
                return True
        
        return False
    
    def _has_similar_amounts(self, path: List[Transaction]) -> bool:
        """Check if transactions have similar amounts"""
        
        if len(path) < 2:
            return False
        
        amounts = [tx.amount for tx in path]
        avg_amount = sum(amounts) / len(amounts)
        
        # Check if most amounts are close to average
        similar_count = sum(1 for amount in amounts if abs(amount - avg_amount) / avg_amount <= 0.1)
        
        return similar_count >= len(path) * 0.7
    
    def _is_rapid_succession(self, path: List[Transaction]) -> bool:
        """Check if transactions are in rapid succession"""
        
        if len(path) < 2:
            return True
        
        # Calculate average time between transactions
        time_intervals = []
        for i in range(1, len(path)):
            interval = (path[i].timestamp - path[i-1].timestamp).total_seconds()
            time_intervals.append(interval)
        
        avg_interval = sum(time_intervals) / len(time_intervals)
        
        # Rapid succession = less than 5 minutes average
        return avg_interval < 300  # 5 minutes
    
    def _calculate_time_compression(self, path: List[Transaction]) -> float:
        """Calculate time compression score"""
        
        if len(path) < 2:
            return 0.0
        
        time_span = self._calculate_time_span(path)
        
        if time_span <= 1:
            return 1.0
        elif time_span <= 6:
            return 0.8
        elif time_span <= 12:
            return 0.6
        elif time_span <= 24:
            return 0.4
        elif time_span <= 48:
            return 0.2
        else:
            return 0.1
    
    def _calculate_time_span(self, path: List[Transaction]) -> float:
        """Calculate time span in hours"""
        
        if len(path) < 2:
            return 0.0
        
        time_span = path[-1].timestamp - path[0].timestamp
        return time_span.total_seconds() / 3600
    
    def _calculate_obfuscation_score(self, path: List[Transaction]) -> float:
        """Calculate obfuscation score based on path characteristics"""
        
        score = 0.0
        
        # Hop count contribution
        score += min(0.4, len(path) / self.max_hops * 0.4)
        
        # Counterparty diversity contribution
        unique_counterparties = len(set(tx.recipient for tx in path))
        score += min(0.3, unique_counterparties / 10 * 0.3)
        
        # Mixing services contribution
        mixing_services = self._identify_mixing_services(path)
        score += min(0.3, len(mixing_services) / 5 * 0.3)
        
        return min(score, 1.0)
    
    def _determine_severity(self, confidence: float, hop_count: int) -> PatternSeverity:
        """Determine pattern severity based on confidence and characteristics"""
        
        # High confidence + many hops = Critical
        if confidence >= 0.9 and hop_count >= 7:
            return PatternSeverity.CRITICAL
        
        # High confidence or many hops = High
        if confidence >= 0.8 or hop_count >= 6:
            return PatternSeverity.HIGH
        
        # Medium confidence = Medium
        if confidence >= 0.6:
            return PatternSeverity.MEDIUM
        
        # Low confidence = Low
        return PatternSeverity.LOW
    
    def _create_evidence(self, path: List[Transaction], address: str) -> List[PatternEvidence]:
        """Create evidence list for the detected pattern"""
        
        evidence = []
        
        # Add path evidence
        evidence.append(PatternEvidence(
            evidence_type="layering_path",
            description=f"Detected layering path with {len(path)} hops",
            confidence_contribution=0.3,
            transaction_hash=path[0].hash,
            address=address,
            metadata={
                "hop_count": len(path),
                "total_amount": sum(tx.amount for tx in path),
                "time_span_hours": self._calculate_time_span(path)
            }
        ))
        
        # Add counterparty diversity evidence
        unique_counterparties = len(set(tx.recipient for tx in path))
        evidence.append(PatternEvidence(
            evidence_type="counterparty_diversity",
            description=f"Path involves {unique_counterparties} unique counterparties",
            confidence_contribution=0.2,
            transaction_hash=path[1].hash if len(path) > 1 else path[0].hash,
            address=address,
            metadata={
                "unique_counterparties": unique_counterparties,
                "counterparty_addresses": list(set(tx.recipient for tx in path))
            }
        ))
        
        # Add mixing service evidence
        mixing_services = self._identify_mixing_services(path)
        if mixing_services:
            evidence.append(PatternEvidence(
                evidence_type="mixing_service_usage",
                description=f"Path uses mixing services: {', '.join(mixing_services)}",
                confidence_contribution=0.3,
                transaction_hash=path[0].hash,
                address=address,
                metadata={
                    "mixing_services": mixing_services,
                    "service_count": len(mixing_services)
                }
            ))
        
        # Add obfuscation evidence
        obfuscation_score = self._calculate_obfuscation_score(path)
        evidence.append(PatternEvidence(
            evidence_type="obfuscation_techniques",
            description=f"Obfuscation score: {obfuscation_score:.2f}",
            confidence_contribution=0.2,
            transaction_hash=path[-1].hash,
            address=address,
            metadata={
                "obfuscation_score": obfuscation_score,
                "hop_count": len(path),
                "counterparty_diversity": unique_counterparties
            }
        ))
        
        return evidence
    
    def _create_empty_result(self, reason: str) -> PatternResult:
        """Create empty result when pattern not detected"""
        
        return PatternResult(
            pattern_id="advanced_layering",
            pattern_name="Advanced Layering Detection",
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
