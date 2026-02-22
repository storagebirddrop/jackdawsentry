"""
Jackdaw Sentry - Attribution Models
Pydantic models for entity attribution and VASP screening
"""

from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, field_validator
import uuid


class EntityType(str, Enum):
    """Entity types for classification"""
    EXCHANGE = "exchange"
    MIXER = "mixer"
    DEFI = "defi"
    GAMBLING = "gambling"
    INSTITUTIONAL = "institutional"
    RETAIL = "retail"
    MINING_POOL = "mining_pool"
    PAYMENT_PROCESSOR = "payment_processor"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    """Risk classification levels - ordered from lowest to highest severity"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    # Note: SEVERE was removed to avoid ambiguity with CRITICAL


class VerificationStatus(str, Enum):
    """Attribution verification status"""
    PENDING = "pending"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    REJECTED = "rejected"


class SourceType(str, Enum):
    """Attribution source types"""
    ON_CHAIN = "on_chain"
    OFF_CHAIN = "off_chain"
    REGULATORY = "regulatory"
    INTELLIGENCE = "intelligence"
    CROWDSOURCED = "crowdsourced"
    EXCHANGE_DISCLOSURE = "exchange_disclosure"


class VASP(BaseModel):
    """Virtual Asset Service Provider entity"""
    id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=255)
    entity_type: EntityType = Field(...)
    risk_level: RiskLevel = Field(...)
    jurisdictions: List[str] = Field(default_factory=list)
    registration_numbers: Dict[str, str] = Field(default_factory=dict)
    website: Optional[str] = None
    description: Optional[str] = None
    founded_year: Optional[int] = None
    active_countries: List[str] = Field(default_factory=list)
    supported_blockchains: List[str] = Field(default_factory=list)
    compliance_program: Optional[bool] = None
    regulatory_licenses: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('VASP name cannot be empty')
        return v.strip()


class AttributionSource(BaseModel):
    """Source of attribution information"""
    id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=100)
    source_type: SourceType = Field(...)
    reliability_score: float = Field(..., ge=0.0, le=1.0)
    description: Optional[str] = None
    url: Optional[str] = None
    api_endpoint: Optional[str] = None
    authentication_required: bool = False
    rate_limit_per_hour: Optional[int] = None
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @field_validator('reliability_score')
    @classmethod
    def validate_reliability_score(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Reliability score must be between 0.0 and 1.0')
        return v


class AddressAttribution(BaseModel):
    """Attribution of an address to a VASP"""
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4)
    address: str = Field(..., min_length=1)
    blockchain: str = Field(..., min_length=1)
    vasp_id: int = Field(...)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    attribution_source_id: int = Field(...)
    verification_status: VerificationStatus = Field(default=VerificationStatus.PENDING)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    corroborating_sources: List[int] = Field(default_factory=list)
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_verified: Optional[datetime] = None
    notes: Optional[str] = None
    
    @field_validator('address')
    @classmethod
    def validate_address(cls, v):
        if not v or not v.strip():
            raise ValueError('Address cannot be empty')
        return v.strip().lower()
    
    @field_validator('confidence_score')
    @classmethod
    def validate_confidence_score(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence score must be between 0.0 and 1.0')
        return v


class AttributionRequest(BaseModel):
    """Request for address attribution"""
    addresses: List[str] = Field(..., min_items=1, max_items=1000)
    blockchain: str = Field(..., min_length=1)
    include_evidence: bool = Field(default=True)
    include_sources: bool = Field(default=True)
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    @field_validator('addresses')
    @classmethod
    def validate_addresses(cls, v):
        cleaned_addresses = []
        for addr in v:
            if addr and addr.strip():
                cleaned_addresses.append(addr.strip().lower())
        if not cleaned_addresses:
            raise ValueError('At least one valid address must be provided')
        return cleaned_addresses


class VASPResult(BaseModel):
    """VASP search result"""
    vasp: VASP
    attribution_count: int
    total_volume_usd: Optional[float] = None
    last_activity: Optional[datetime] = None
    risk_factors: List[str] = Field(default_factory=list)


class AttributionResult(BaseModel):
    """Result of address attribution analysis"""
    address: str
    blockchain: str
    attributions: List[AddressAttribution] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    sources: List[AttributionSource] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    analysis_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processing_time_ms: Optional[float] = None


class BatchAttributionResult(BaseModel):
    """Result of batch address attribution"""
    results: List[AttributionResult]
    total_addresses: int
    successful_attributions: int
    failed_addresses: List[str] = Field(default_factory=list)
    processing_time_ms: float
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class AttributionEvidence(BaseModel):
    """Evidence supporting attribution"""
    evidence_type: str  # transaction_pattern, public_disclosure, regulatory_filing, etc.
    description: str
    confidence_contribution: float = Field(ge=0.0, le=1.0)
    source_reference: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConfidenceFactors(BaseModel):
    """Factors contributing to confidence score"""
    source_reliability: float = Field(ge=0.0, le=1.0)
    evidence_strength: float = Field(ge=0.0, le=1.0)
    corroboration_count: int = Field(ge=0)
    recency_score: float = Field(ge=0.0, le=1.0)
    blockchain_analysis: float = Field(ge=0.0, le=1.0)
    historical_accuracy: float = Field(ge=0.0, le=1.0)


class AttributionSearchFilters(BaseModel):
    """Filters for VASP search"""
    entity_types: Optional[List[EntityType]] = None
    risk_levels: Optional[List[RiskLevel]] = Field(default=None)
    jurisdictions: Optional[List[str]] = None
    min_reliability: float = Field(default=0.0, ge=0.0, le=1.0)
    has_regulatory_license: Optional[bool] = None
    supported_blockchains: Optional[List[str]] = None
