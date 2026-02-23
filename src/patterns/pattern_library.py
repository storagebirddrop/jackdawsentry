"""
Jackdaw Sentry - Pattern Library
Advanced pattern signatures for suspicious behavior detection
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json

from .models import (
    PatternSignature, PatternIndicator, PatternType, PatternSeverity,
    IndicatorType
)


class PatternLibrary:
    """Library of advanced pattern signatures"""
    
    def __init__(self):
        self.patterns: Dict[str, PatternSignature] = {}
        self._load_default_patterns()
    
    def _load_default_patterns(self):
        """Load default advanced patterns"""
        
        # Peeling Chain Pattern
        peeling_chain = PatternSignature(
            pattern_id="peeling_chain",
            name="Peeling Chain Detection",
            description="Detects sequential transactions with decreasing amounts typical of chain peeling",
            pattern_type=PatternType.PEELING_CHAIN,
            severity=PatternSeverity.HIGH,
            indicators=[
                PatternIndicator(
                    indicator_type=IndicatorType.SEQUENCE,
                    threshold=0.95,
                    weight=0.4,
                    description="Sequential decreasing amounts (5% tolerance)"
                ),
                PatternIndicator(
                    indicator_type=IndicatorType.TIMING,
                    threshold=24.0,
                    weight=0.3,
                    description="Transactions within 24 hours"
                ),
                PatternIndicator(
                    indicator_type=IndicatorType.COUNTERPARTY,
                    threshold=3.0,
                    weight=0.3,
                    description="Minimum 3 sequential transactions"
                )
            ],
            min_transactions=3,
            time_window_hours=24,
            metadata={
                "typical_amounts": [0.1, 0.05, 0.025, 0.0125, 0.00625],
                "confidence_boost": 0.1,
                "false_positive_rate": 0.15
            }
        )
        
        # Advanced Layering Pattern
        layering = PatternSignature(
            pattern_id="advanced_layering",
            name="Advanced Layering Detection",
            description="Identifies complex multi-hop layering across different services",
            pattern_type=PatternType.LAYERING,
            severity=PatternSeverity.CRITICAL,
            indicators=[
                PatternIndicator(
                    indicator_type=IndicatorType.SEQUENCE,
                    threshold=5.0,
                    weight=0.35,
                    description="Minimum 5 hops in transaction chain"
                ),
                PatternIndicator(
                    indicator_type=IndicatorType.COUNTERPARTY,
                    threshold=3.0,
                    weight=0.25,
                    description="At least 3 different counterparties"
                ),
                PatternIndicator(
                    indicator_type=IndicatorType.BEHAVIORAL,
                    threshold=0.7,
                    weight=0.4,
                    description="No direct business relationship between endpoints"
                )
            ],
            min_transactions=5,
            time_window_hours=72,
            metadata={
                "max_hops": 10,
                "cross_service_detection": True,
                "amount_obfuscation_threshold": 0.3
            }
        )
        
        # Custody Change Detection
        custody_change = PatternSignature(
            pattern_id="custody_change",
            name="Custody Change Detection",
            description="Detects potential changes in wallet custody or control",
            pattern_type=PatternType.CUSTODY_CHANGE,
            severity=PatternSeverity.MEDIUM,
            indicators=[
                PatternIndicator(
                    indicator_type=IndicatorType.BEHAVIORAL,
                    threshold=0.8,
                    weight=0.4,
                    description="Sudden change in transaction patterns"
                ),
                PatternIndicator(
                    indicator_type=IndicatorType.TIMING,
                    threshold=168.0,
                    weight=0.3,
                    description="Inactivity period followed by activity (7 days)"
                ),
                PatternIndicator(
                    indicator_type=IndicatorType.AMOUNT,
                    threshold=2.0,
                    weight=0.3,
                    description="Significant change in transaction amounts"
                )
            ],
            min_transactions=10,
            time_window_hours=168,  # 7 days
            metadata={
                "inactivity_threshold_days": 7,
                "pattern_change_threshold": 0.6,
                "requires_historical_data": True
            }
        )
        
        # Synchronized Transfer Analysis
        synchronized_transfers = PatternSignature(
            pattern_id="synchronized_transfers",
            name="Synchronized Transfer Analysis",
            description="Identifies coordinated transfers across multiple addresses",
            pattern_type=PatternType.SYNCHRONIZED_TRANSFERS,
            severity=PatternSeverity.HIGH,
            indicators=[
                PatternIndicator(
                    indicator_type=IndicatorType.TIMING,
                    threshold=300.0,
                    weight=0.4,
                    description="Transfers within 5 minutes (300 seconds)"
                ),
                PatternIndicator(
                    indicator_type=IndicatorType.COUNTERPARTY,
                    threshold=2.0,
                    weight=0.3,
                    description="Multiple addresses involved"
                ),
                PatternIndicator(
                    indicator_type=IndicatorType.AMOUNT,
                    threshold=0.1,
                    weight=0.3,
                    description="Similar amounts (10% tolerance)"
                )
            ],
            min_transactions=2,
            time_window_hours=1,
            metadata={
                "sync_window_seconds": 300,
                "amount_tolerance": 0.1,
                "min_addresses": 2
            }
        )
        
        # Off-Peak Hours Activity
        off_peak_activity = PatternSignature(
            pattern_id="off_peak_activity",
            name="Off-Peak Hours Activity",
            description="Detects unusual activity during low-traffic periods",
            pattern_type=PatternType.OFF_PEAK_ACTIVITY,
            severity=PatternSeverity.MEDIUM,
            indicators=[
                PatternIndicator(
                    indicator_type=IndicatorType.TIMING,
                    threshold=0.3,
                    weight=0.5,
                    description="30% of transactions during off-peak hours"
                ),
                PatternIndicator(
                    indicator_type=IndicatorType.FREQUENCY,
                    threshold=5.0,
                    weight=0.3,
                    description="Minimum 5 transactions during off-peak"
                ),
                PatternIndicator(
                    indicator_type=IndicatorType.AMOUNT,
                    threshold=1000.0,
                    weight=0.2,
                    description="High-value transactions (> $1000 USD)"
                )
            ],
            min_transactions=5,
            time_window_hours=168,  # 7 days
            metadata={
                "off_peak_hours": [22, 23, 0, 1, 2, 3, 4, 5, 6],  # 10 PM - 6 AM
                "timezone": "UTC",
                "weekend_multiplier": 1.5
            }
        )
        
        # Round Amount Patterns
        round_amounts = PatternSignature(
            pattern_id="round_amount_patterns",
            name="Round Amount Analysis",
            description="Identifies suspicious round-number transactions",
            pattern_type=PatternType.ROUND_AMOUNTS,
            severity=PatternSeverity.LOW,
            indicators=[
                PatternIndicator(
                    indicator_type=IndicatorType.AMOUNT,
                    threshold=0.95,
                    weight=0.6,
                    description="95% round number similarity"
                ),
                PatternIndicator(
                    indicator_type=IndicatorType.FREQUENCY,
                    threshold=3.0,
                    weight=0.4,
                    description="Minimum 3 round amount transactions"
                )
            ],
            min_transactions=3,
            time_window_hours=168,  # 7 days
            metadata={
                "round_thresholds": [0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0, 500.0, 1000.0],
                "tolerance": 0.05,
                "common_round_amounts": [1.0, 10.0, 100.0, 1000.0]
            }
        )
        
        # High Frequency Trading
        high_frequency = PatternSignature(
            pattern_id="high_frequency_trading",
            name="High Frequency Trading Pattern",
            description="Detects unusually high transaction frequency",
            pattern_type=PatternType.HIGH_FREQUENCY,
            severity=PatternSeverity.MEDIUM,
            indicators=[
                PatternIndicator(
                    indicator_type=IndicatorType.FREQUENCY,
                    threshold=100.0,
                    weight=0.5,
                    description="100+ transactions in time window"
                ),
                PatternIndicator(
                    indicator_type=IndicatorType.TIMING,
                    threshold=1.0,
                    weight=0.3,
                    description="Average interval < 1 second"
                ),
                PatternIndicator(
                    indicator_type=IndicatorType.AMOUNT,
                    threshold=0.01,
                    weight=0.2,
                    description="Any amount (frequency-based pattern)"
                )
            ],
            min_transactions=100,
            time_window_hours=1,
            metadata={
                "frequency_threshold": 100,
                "interval_threshold_seconds": 1.0,
                "bot_behavior_indicators": True
            }
        )
        
        # Structuring Pattern
        structuring = PatternSignature(
            pattern_id="structuring",
            name="Transaction Structuring",
            description="Detects deliberate structuring to avoid reporting thresholds",
            pattern_type=PatternType.STRUCTURING,
            severity=PatternSeverity.HIGH,
            indicators=[
                PatternIndicator(
                    indicator_type=IndicatorType.AMOUNT,
                    threshold=0.95,
                    weight=0.4,
                    description="Amounts just below reporting thresholds"
                ),
                PatternIndicator(
                    indicator_type=IndicatorType.FREQUENCY,
                    threshold=5.0,
                    weight=0.3,
                    description="Multiple similar small transactions"
                ),
                PatternIndicator(
                    indicator_type=IndicatorType.TIMING,
                    threshold=24.0,
                    weight=0.3,
                    description="Within 24 hour period"
                )
            ],
            min_transactions=5,
            time_window_hours=24,
            metadata={
                "reporting_thresholds": [10000, 5000, 1000],  # USD
                "structuring_tolerance": 0.05,
                "time_window_days": 1
            }
        )
        
        # Mixer Usage Pattern
        mixer_usage = PatternSignature(
            pattern_id="mixer_usage",
            name="Mixer Usage Detection",
            description="Identifies transactions involving cryptocurrency mixers",
            pattern_type=PatternType.MIXER_USAGE,
            severity=PatternSeverity.CRITICAL,
            indicators=[
                PatternIndicator(
                    indicator_type=IndicatorType.COUNTERPARTY,
                    threshold=1.0,
                    weight=0.6,
                    description="Direct transaction to known mixer"
                ),
                PatternIndicator(
                    indicator_type=IndicatorType.BEHAVIORAL,
                    threshold=0.8,
                    weight=0.4,
                    description="Mixer-like transaction patterns"
                )
            ],
            min_transactions=1,
            time_window_hours=168,  # 7 days
            metadata={
                "known_mixers": [
                    "tornado_cash", "wasabi", "joinmarket", 
                    "samourai", "whirlpool", "coinjoin"
                ],
                "mixer_indicators": [
                    "equal_amount_distribution",
                    "delayed_withdrawals",
                    "multiple_intermediate_addresses"
                ]
            }
        )
        
        # Bridge Hopping Pattern
        bridge_hopping = PatternSignature(
            pattern_id="bridge_hopping",
            name="Bridge Hopping Detection",
            description="Detects rapid movement across multiple blockchain bridges",
            pattern_type=PatternType.BRIDGE_HOPPING,
            severity=PatternSeverity.MEDIUM,
            indicators=[
                PatternIndicator(
                    indicator_type=IndicatorType.SEQUENCE,
                    threshold=2.0,
                    weight=0.4,
                    description="Multiple bridge transactions"
                ),
                PatternIndicator(
                    indicator_type=IndicatorType.TIMING,
                    threshold=60.0,
                    weight=0.3,
                    description="Within 1 hour time window"
                ),
                PatternIndicator(
                    indicator_type=IndicatorType.GEOGRAPHIC,
                    threshold=2.0,
                    weight=0.3,
                    description="Cross-jurisdiction bridges"
                )
            ],
            min_transactions=2,
            time_window_hours=24,
            metadata={
                "known_bridges": [
                    "ethereum_bridge", "polygon_bridge", "arbitrum_bridge",
                    "base_bridge", "avalanche_bridge", "optimism_bridge"
                ],
                "suspicious_threshold": 3,  # 3+ bridges in 24h
                "rapid_hop_threshold": 300  # 5 minutes
            }
        )
        
        # Add all patterns to library
        self.patterns = {
            peeling_chain.pattern_id: peeling_chain,
            layering.pattern_id: layering,
            custody_change.pattern_id: custody_change,
            synchronized_transfers.pattern_id: synchronized_transfers,
            off_peak_activity.pattern_id: off_peak_activity,
            round_amounts.pattern_id: round_amounts,
            high_frequency.pattern_id: high_frequency,
            structuring.pattern_id: structuring,
            mixer_usage.pattern_id: mixer_usage,
            bridge_hopping.pattern_id: bridge_hopping
        }
    
    def get_pattern(self, pattern_id: str) -> Optional[PatternSignature]:
        """Get pattern by ID"""
        return self.patterns.get(pattern_id)
    
    def get_all_patterns(self) -> Dict[str, PatternSignature]:
        """Get all patterns"""
        return self.patterns.copy()
    
    def get_patterns_by_type(self, pattern_type: PatternType) -> List[PatternSignature]:
        """Get patterns by type"""
        return [p for p in self.patterns.values() if p.pattern_type == pattern_type]
    
    def get_patterns_by_severity(self, severity: PatternSeverity) -> List[PatternSignature]:
        """Get patterns by severity"""
        return [p for p in self.patterns.values() if p.severity == severity]
    
    def get_enabled_patterns(self) -> Dict[str, PatternSignature]:
        """Get only enabled patterns"""
        return {pid: p for pid, p in self.patterns.items() if p.enabled}
    
    def add_pattern(self, pattern: PatternSignature) -> None:
        """Add a new pattern to the library"""
        self.patterns[pattern.pattern_id] = pattern
    
    def update_pattern(self, pattern_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing pattern"""
        if pattern_id not in self.patterns:
            return False
        
        pattern = self.patterns[pattern_id]
        for key, value in updates.items():
            if hasattr(pattern, key):
                setattr(pattern, key, value)
        
        pattern.updated_at = datetime.now(timezone.utc)
        return True
    
    def enable_pattern(self, pattern_id: str) -> bool:
        """Enable a pattern"""
        return self.update_pattern(pattern_id, {"enabled": True})
    
    def disable_pattern(self, pattern_id: str) -> bool:
        """Disable a pattern"""
        return self.update_pattern(pattern_id, {"enabled": False})
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get statistics about the pattern library"""
        patterns = list(self.patterns.values())
        
        stats = {
            "total_patterns": len(patterns),
            "enabled_patterns": len([p for p in patterns if p.enabled]),
            "patterns_by_type": {},
            "patterns_by_severity": {},
            "avg_indicators_per_pattern": 0.0,
            "avg_time_window_hours": 0.0
        }
        
        # Count by type
        for pattern in patterns:
            ptype = pattern.pattern_type.value
            stats["patterns_by_type"][ptype] = stats["patterns_by_type"].get(ptype, 0) + 1
        
        # Count by severity
        for pattern in patterns:
            severity = pattern.severity.value
            stats["patterns_by_severity"][severity] = stats["patterns_by_severity"].get(severity, 0) + 1
        
        # Calculate averages
        if patterns:
            stats["avg_indicators_per_pattern"] = sum(len(p.indicators) for p in patterns) / len(patterns)
            stats["avg_time_window_hours"] = sum(p.time_window_hours for p in patterns) / len(patterns)
        
        return stats


# Global pattern library instance
_pattern_library = None

def get_pattern_library() -> PatternLibrary:
    """Get the global pattern library instance"""
    global _pattern_library
    if _pattern_library is None:
        _pattern_library = PatternLibrary()
    return _pattern_library


# Export ADVANCED_PATTERNS for backward compatibility
def get_advanced_patterns() -> Dict[str, PatternSignature]:
    """Get advanced patterns dictionary"""
    library = get_pattern_library()
    return library.get_all_patterns()


# Create global ADVANCED_PATTERNS reference
ADVANCED_PATTERNS = get_advanced_patterns()
