"""
Jackdaw Sentry - Pattern Detection Models
Pydantic models for advanced pattern detection and analysis
"""

from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, field_validator
import uuid


class PatternType(str, Enum):
    """Types of suspicious patterns"""
    PEELING_CHAIN = "peeling_chain"
    LAYERING = "layering"
    CUSTODY_CHANGE = "custody_change"
    SYNCHRONIZED_TRANSFERS = "synchronized_transfers"
    OFF_PEAK_ACTIVITY = "off_peak_activity"
    ROUND_AMOUNTS = "round_amounts"
    HIGH_FREQUENCY = "high_frequency"
    STRUCTURING = "structuring"
    MIXER_USAGE = "mixer_usage"
    PRIVACY_TOOL_USAGE = "privacy_tool_usage"
    BRIDGE_HOPPING = "bridge_hopping"
    DEX_HOPPING = "dex_hopping"
    CIRCULAR_TRADING = "circular_trading"
    INSTANT_REDEPLOY = "instant_deploy"


class PatternSeverity(str, Enum):
    """Pattern severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    SEVERE = "severe"


class IndicatorType(str, Enum):
    """Types of pattern indicators"""
    TIMING = "timing"
    AMOUNT = "amount"
    FREQUENCY = "frequency"
    COUNTERPARTY = "counterparty"
    SEQUENCE = "sequence"
    GEOGRAPHIC = "geographic"
    BEHAVIORAL = "behavioral"


class PatternIndicator(BaseModel):
    """Individual indicator for pattern detection"""
    indicator_type: IndicatorType = Field(...)
    threshold: float = Field(..., gt=0.0)
    weight: float = Field(..., gt=0.0, le=1.0)
    description: str = Field(...)
    detection_function: Optional[str] = None  # Reference to detection function
    
    @field_validator('weight')
    @classmethod
    def validate_weight(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Weight must be between 0.0 and 1.0')
        return v


class PatternSignature(BaseModel):
    """Definition of a suspicious pattern"""
    pattern_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1, max_length=1000)
    pattern_type: PatternType = Field(...)
    severity: PatternSeverity = Field(default=PatternSeverity.MEDIUM)
    indicators: List[PatternIndicator] = Field(default_factory=list)
    confidence_algorithm: Optional[str] = None
    min_transactions: int = Field(default=3, ge=1)
    time_window_hours: int = Field(default=24, ge=1)
    enabled: bool = Field(default=True)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @field_validator('pattern_id')
    @classmethod
    def validate_pattern_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Pattern ID cannot be empty')
        return v.strip().lower()
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Pattern name cannot be empty')
        return v.strip()


class PatternEvidence(BaseModel):
    """Evidence supporting pattern detection"""
    evidence_type: str
    description: str
    confidence_contribution: float = Field(ge=0.0, le=1.0)
    transaction_hash: Optional[str] = None
    address: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PatternResult(BaseModel):
    """Result of pattern detection for a specific pattern"""
    pattern_id: str
    pattern_name: str
    detected: bool = Field(default=False)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    severity: PatternSeverity
    evidence: List[PatternEvidence] = Field(default_factory=list)
    indicators_met: List[str] = Field(default_factory=list)
    indicators_missed: List[str] = Field(default_factory=list)
    transaction_count: int = Field(default=0, ge=0)
    time_window_hours: int = Field(default=24, ge=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    detection_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PatternAnalysisResult(BaseModel):
    """Complete pattern analysis result for an address"""
    address: str
    blockchain: str
    patterns: List[PatternResult] = Field(default_factory=list)
    overall_risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    total_transactions_analyzed: int = Field(default=0, ge=0)
    time_range_hours: Optional[int] = None
    analysis_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processing_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PatternRequest(BaseModel):
    """Request for pattern analysis"""
    addresses: List[str] = Field(..., min_items=1, max_items=100)
    blockchain: str = Field(..., min_length=1)
    pattern_types: Optional[List[PatternType]] = None
    min_severity: Optional[PatternSeverity] = None
    time_range_hours: int = Field(default=24, ge=1, le=8760)  # Max 1 year
    include_evidence: bool = Field(default=True)
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    @field_validator('addresses')
    @classmethod
    def validate_addresses(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one address must be provided')
        return [addr.strip().lower() for addr in v if addr.strip()]
    
    @field_validator('blockchain')
    @classmethod
    def validate_blockchain(cls, v):
        if not v or not v.strip():
            raise ValueError('Blockchain cannot be empty')
        return v.strip().lower()
    
    @field_validator('min_confidence')
    @classmethod
    def validate_min_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('min_confidence must be between 0.0 and 1.0')
        return v


class PatternResponse(BaseModel):
    """Response for pattern analysis"""
    results: Dict[str, PatternAnalysisResult]
    total_addresses: int
    successful_analyses: int
    failed_addresses: List[str] = Field(default_factory=list)
    processing_time_ms: float
    patterns_detected: int
    high_risk_findings: int


class PatternConfig(BaseModel):
    """Configuration for pattern detection"""
    enabled_patterns: List[str] = Field(default_factory=list)
    confidence_thresholds: Dict[str, float] = Field(default_factory=dict)
    severity_weights: Dict[PatternSeverity, float] = Field(default_factory=dict)
    time_windows: Dict[str, int] = Field(default_factory=dict)
    custom_indicators: Dict[str, PatternIndicator] = Field(default_factory=dict)
    global_settings: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('confidence_thresholds')
    @classmethod
    def validate_confidence_thresholds(cls, v):
        for pattern_id, threshold in v.items():
            if not 0.0 <= threshold <= 1.0:
                raise ValueError(f'Confidence threshold for {pattern_id} must be between 0.0 and 1.0')
        return v


class PatternMetrics(BaseModel):
    """Metrics for pattern detection performance"""
    pattern_id: str
    pattern_name: str
    total_detections: int = Field(default=0, ge=0)
    true_positives: int = Field(default=0, ge=0)
    false_positives: int = Field(default=0, ge=0)
    precision: float = Field(default=0.0, ge=0.0, le=1.0)
    recall: float = Field(default=0.0, ge=0.0, le=1.0)
    f1_score: float = Field(default=0.0, ge=0.0, le=1.0)
    avg_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    avg_processing_time_ms: float = Field(default=0.0, ge=0.0)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BatchPatternRequest(BaseModel):
    """Request for batch pattern analysis"""
    addresses: List[str] = Field(..., min_items=1, max_items=1000)
    blockchain: str = Field(..., min_length=1)
    pattern_types: Optional[List[PatternType]] = None
    min_severity: Optional[PatternSeverity] = None
    time_range_hours: int = Field(default=24, ge=1, le=8760)
    include_evidence: bool = Field(default=False)  # Disabled for batch performance
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    parallel_processing: bool = Field(default=True)
    max_concurrent: int = Field(default=10, ge=1, le=50)


class BatchPatternResponse(BaseModel):
    """Response for batch pattern analysis"""
    results: Dict[str, PatternAnalysisResult]
    total_addresses: int
    successful_analyses: int
    failed_addresses: List[str] = Field(default_factory=list)
    processing_time_ms: float
    patterns_detected: int
    high_risk_findings: int
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class PatternAlert(BaseModel):
    """Alert generated from pattern detection"""
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    address: str
    blockchain: str
    pattern_id: str
    pattern_name: str
    severity: PatternSeverity
    confidence_score: float = Field(ge=0.0, le=1.0)
    evidence_summary: str
    transaction_count: int
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = Field(default="active")  # active, resolved, false_positive
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PatternStatistics(BaseModel):
    """Statistics for pattern detection system"""
    total_patterns: int = Field(default=0, ge=0)
    enabled_patterns: int = Field(default=0, ge=0)
    total_detections_24h: int = Field(default=0, ge=0)
    total_detections_7d: int = Field(default=0, ge=0)
    high_risk_detections_24h: int = Field(default=0, ge=0)
    avg_confidence_24h: float = Field(default=0.0, ge=0.0, le=1.0)
    most_detected_pattern: Optional[str] = None
    pattern_accuracy: Dict[str, float] = Field(default_factory=dict)
    processing_performance: Dict[str, float] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PatternTuningRequest(BaseModel):
    """Request for pattern tuning and optimization"""
    pattern_id: str
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    severity_override: Optional[PatternSeverity] = None
    indicator_adjustments: Dict[str, float] = Field(default_factory=dict)
    time_window_override: Optional[int] = Field(None, ge=1, le=8760)
    min_transactions_override: Optional[int] = Field(None, ge=1)
    enabled_override: Optional[bool] = None
    metadata_updates: Dict[str, Any] = Field(default_factory=dict)


class PatternTuningResponse(BaseModel):
    """Response for pattern tuning"""
    pattern_id: str
    previous_config: Dict[str, Any]
    new_config: Dict[str, Any]
    validation_results: Dict[str, Any]
    estimated_impact: Dict[str, float]
    applied_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
