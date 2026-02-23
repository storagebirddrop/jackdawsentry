"""
Jackdaw Sentry - Advanced Analytics Models
Pydantic models for advanced analytics features
"""

import uuid
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Union

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator


class PathfindingAlgorithm(str, Enum):
    """Pathfinding algorithms"""

    SHORTEST_PATH = "shortest_path"
    ALL_PATHS = "all_paths"
    DISCONNECTED_PATHS = "disconnected_paths"
    FUNNEL_ANALYSIS = "funnel_analysis"
    CIRCULAR_PATHS = "circular_paths"


class DerivationType(str, Enum):
    """Wallet derivation types"""

    BIP44 = "bip44"  # Standard hierarchical deterministic
    BIP49 = "bip49"  # SegWit compatible
    BIP84 = "bip84"  # Native SegWit
    BIP32 = "bip32"  # Hierarchical deterministic
    CUSTOM = "custom"  # Custom derivation patterns


class FingerprintType(str, Enum):
    """Transaction fingerprint types"""

    AMOUNT_PATTERN = "amount_pattern"
    TIMING_PATTERN = "timing_pattern"
    ADDRESS_PATTERN = "address_pattern"
    SEQUENCE_PATTERN = "sequence_pattern"
    BEHAVIORAL_PATTERN = "behavioral_pattern"
    NETWORK_PATTERN = "network_pattern"


class TransactionNode(BaseModel):
    """Transaction graph node"""

    address: str
    blockchain: str
    label: Optional[str] = None
    entity_type: Optional[str] = None
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TransactionEdge(BaseModel):
    """Transaction graph edge"""

    from_address: str
    to_address: str
    transaction_hash: str
    amount: float
    timestamp: datetime
    blockchain: str
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    gas_price: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TransactionPath(BaseModel):
    """Single path between addresses"""

    path_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    addresses: List[str]
    transactions: List[TransactionEdge]
    total_amount: float
    hop_count: int
    path_length: float  # Total amount or time
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    path_type: str = Field(default="unknown")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PathfindingResult(BaseModel):
    """Result of pathfinding analysis"""

    query_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_address: str
    target_address: str
    blockchain: str
    algorithm: PathfindingAlgorithm
    paths: List[TransactionPath]
    total_paths_found: int
    analysis_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    processing_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("paths")
    @classmethod
    def validate_paths(cls, v):
        if not isinstance(v, list):
            raise ValueError("Paths must be a list")
        return v


class PathfindingRequest(BaseModel):
    """Request for pathfinding analysis"""

    source_address: str
    target_address: str
    blockchain: str
    algorithm: PathfindingAlgorithm = PathfindingAlgorithm.ALL_PATHS
    max_paths: int = Field(default=100, ge=1, le=1000)
    max_hops: int = Field(default=10, ge=1, le=50)
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    time_window_hours: int = Field(default=168, ge=1, le=8760)  # Max 1 year
    include_intermediate: bool = Field(default=True)
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("source_address", "target_address")
    @classmethod
    def validate_addresses(cls, v):
        if not v or not v.strip():
            raise ValueError("Address cannot be empty")
        return v.strip().lower()

    @field_validator("blockchain")
    @classmethod
    def validate_blockchain(cls, v):
        if not v or not v.strip():
            raise ValueError("Blockchain cannot be empty")
        return v.strip().lower()


class WalletDerivation(BaseModel):
    """Single wallet derivation from seed phrase"""

    derivation_path: str
    address: str
    blockchain: str
    address_type: str  # P2PKH, P2SH, P2WPKH, etc.
    derivation_type: DerivationType
    index: int
    balance: Optional[float] = None
    transaction_count: Optional[int] = None
    first_seen: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SeedAnalysisResult(BaseModel):
    """Result of seed phrase analysis"""

    analysis_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    seed_phrase_hash: str  # Hash of the seed phrase for privacy
    derivations: List[WalletDerivation]
    total_wallets: int
    active_wallets: int
    total_balance: float
    blockchains: Set[str]
    analysis_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    processing_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SeedAnalysisRequest(BaseModel):
    """Request for seed phrase analysis"""

    seed_phrase: str  # 12 or 24 word seed phrase
    derivation_types: List[DerivationType] = Field(default=[DerivationType.BIP44])
    blockchains: List[str] = Field(default=["bitcoin", "ethereum"])
    max_derivations: int = Field(default=100, ge=1, le=1000)
    check_balances: bool = Field(default=True)
    include_inactive: bool = Field(default=True)

    @field_validator("seed_phrase")
    @classmethod
    def validate_seed_phrase(cls, v):
        if not v or not v.strip():
            raise ValueError("Seed phrase cannot be empty")

        words = v.strip().split()
        if len(words) not in [12, 24]:
            raise ValueError("Seed phrase must be 12 or 24 words")

        return v.strip().lower()


class FingerprintPattern(BaseModel):
    """Transaction fingerprint pattern"""

    pattern_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pattern_type: FingerprintType
    name: str
    description: str
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    pattern_data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FingerprintResult(BaseModel):
    """Result of transaction fingerprinting"""

    fingerprint_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query_parameters: Dict[str, Any]
    matched_patterns: List[FingerprintPattern]
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    match_count: int
    analysis_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    processing_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FingerprintingRequest(BaseModel):
    """Request for transaction fingerprinting"""

    query_type: FingerprintType
    parameters: Dict[str, Any] = Field(default_factory=dict)
    blockchain: Optional[str] = None
    time_window_hours: int = Field(default=168, ge=1, le=8760)
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    max_results: int = Field(default=100, ge=1, le=1000)

    @field_validator("parameters")
    @classmethod
    def validate_parameters(cls, v):
        if not isinstance(v, dict):
            raise ValueError("Parameters must be a dictionary")
        return v


class AnalyticsRequest(BaseModel):
    """Combined analytics request"""

    request_type: str  # pathfinding, seed_analysis, fingerprinting
    parameters: Dict[str, Any] = Field(default_factory=dict)
    priority: str = Field(default="normal")  # low, normal, high, urgent
    callback_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnalyticsResponse(BaseModel):
    """Combined analytics response"""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_type: str
    status: str  # pending, processing, completed, failed
    result: Optional[
        Union[PathfindingResult, SeedAnalysisResult, FingerprintResult]
    ] = None
    error_message: Optional[str] = None
    processing_time_ms: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphCustomization(BaseModel):
    """Graph customization settings"""

    node_colors: Dict[str, str] = Field(default_factory=dict)
    node_sizes: Dict[str, float] = Field(default_factory=dict)
    node_labels: Dict[str, str] = Field(default_factory=dict)
    edge_colors: Dict[str, str] = Field(default_factory=dict)
    edge_widths: Dict[str, float] = Field(default_factory=dict)
    layout_algorithm: str = Field(default="force_directed")
    clustering_enabled: bool = Field(default=True)
    show_labels: bool = Field(default=True)
    show_amounts: bool = Field(default=True)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphExport(BaseModel):
    """Graph export configuration"""

    format: str = Field(default="json")  # json, csv, gephi, cytoscape
    include_metadata: bool = Field(default=True)
    include_addresses: bool = Field(default=True)
    include_amounts: bool = Field(default=True)
    include_timestamps: bool = Field(default=True)
    compression: bool = Field(default=False)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FunnelAnalysis(BaseModel):
    """Funnel analysis result"""

    funnel_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_address: str
    target_addresses: List[str]
    convergence_points: List[str]
    total_amount_converged: float
    convergence_rate: float
    analysis_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CircularPath(BaseModel):
    """Circular path detection result"""

    circular_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    addresses: List[str]
    transactions: List[TransactionEdge]
    cycle_length: int
    total_amount: float
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    detection_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AdvancedAnalyticsMetrics(BaseModel):
    """Metrics for advanced analytics"""

    total_pathfinding_requests: int = Field(default=0, ge=0)
    total_seed_analyses: int = Field(default=0, ge=0)
    total_fingerprint_queries: int = Field(default=0, ge=0)
    avg_processing_time_ms: float = Field(default=0.0, ge=0.0)
    cache_hit_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    most_common_algorithms: Dict[str, int] = Field(default_factory=dict)
    blockchain_distribution: Dict[str, int] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Request/Response models for API
class PathfindingResponse(BaseModel):
    """Pathfinding API response"""

    success: bool
    result: Optional[PathfindingResult] = None
    error: Optional[str] = None
    processing_time_ms: Optional[float] = None


class SeedAnalysisResponse(BaseModel):
    """Seed analysis API response"""

    success: bool
    result: Optional[SeedAnalysisResult] = None
    error: Optional[str] = None
    processing_time_ms: Optional[float] = None


class FingerprintingResponse(BaseModel):
    """Fingerprinting API response"""

    success: bool
    result: Optional[FingerprintResult] = None
    error: Optional[str] = None
    processing_time_ms: Optional[float] = None


class BatchAnalyticsRequest(BaseModel):
    """Batch analytics request"""

    requests: List[AnalyticsRequest]
    parallel_processing: bool = Field(default=True)
    max_concurrent: int = Field(default=5, ge=1, le=20)


class BatchAnalyticsResponse(BaseModel):
    """Batch analytics response"""

    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    results: List[AnalyticsResponse]
    successful_requests: int
    failed_requests: int
    total_processing_time_ms: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
