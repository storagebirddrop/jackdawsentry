"""
Jackdaw Sentry - Cross-Platform Attribution API Router
REST endpoints for unified intelligence consolidation and attribution analysis
"""

import json as _json
import inspect
import logging
import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Set

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status
from pydantic import BaseModel
from pydantic import field_validator

from src.api.auth import PERMISSIONS
from src.api.auth import User
from src.api.auth import check_permissions
from src.api.database import get_postgres_connection
from src.api.exceptions import JackdawException
from src.intelligence.cross_platform import get_cross_platform_engine

logger = logging.getLogger(__name__)

router = APIRouter()


async def _resolve_dependency(value):
    """Resolve sync singletons and async factory calls uniformly."""
    if inspect.isawaitable(value):
        return await value
    return value


def get_attribution_engine():
    """Backward-compatible getter name used by older tests and callers."""
    return get_cross_platform_engine()


def _value(obj: Any, name: str, default: Any = None) -> Any:
    """Safely read attributes or dict keys from dataclasses, dicts, and mocks."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    try:
        value = getattr(obj, name)
    except Exception:
        return default
    if "Mock" in type(value).__name__:
        return default
    return value


def _attr_payload(result: Any) -> Dict[str, Any]:
    """Normalize attribution results into the legacy/public API shape."""
    confidence = _value(result, "overall_confidence")
    if confidence is None:
        confidence = _value(result, "confidence_score")
    if confidence is None:
        raw_confidence = _value(result, "confidence", "medium")
        confidence = {
            "very_low": 0.1,
            "low": 0.3,
            "medium": 0.5,
            "high": 0.7,
            "very_high": 0.9,
            "definitive": 0.95,
        }.get(getattr(raw_confidence, "value", raw_confidence), 0.5)

    return {
        "id": str(_value(result, "id", uuid.uuid4())),
        "address": _value(result, "address", ""),
        "blockchain": _value(result, "blockchain", "bitcoin"),
        "entity": _value(result, "entity"),
        "entity_type": _value(result, "entity_type"),
        "confidence_score": confidence,
        "confidence_level": getattr(_value(result, "confidence", "medium"), "value", _value(result, "confidence", "medium")),
        "sources": _value(result, "sources", []) or [],
        "source_details": _value(result, "source_details", _value(result, "metadata", {})) or {},
        "first_seen": _value(result, "first_seen", _value(result, "created_at")),
        "last_seen": _value(result, "last_seen", _value(result, "updated_at")),
        "verification_status": _value(result, "verification_status", "pending"),
        "verified_by": _value(result, "verified_by"),
        "verification_date": _value(result, "verification_date"),
        "created_date": _value(result, "created_date", _value(result, "created_at", datetime.now(timezone.utc))),
        "last_updated": _value(result, "last_updated", _value(result, "updated_at", datetime.now(timezone.utc))),
        "attributions": _value(result, "attributions", _value(result, "sources", []) or []),
        "consolidated_entity": _value(result, "consolidated_entity", _value(result, "entity")),
        "overall_confidence": confidence,
        "risk_level": _value(result, "risk_level"),
        "analysis_date": _value(result, "analysis_date", _value(result, "updated_at", datetime.now(timezone.utc))),
    }


def _source_payload(source: Any) -> Dict[str, Any]:
    """Normalize source metadata into the legacy/public API shape."""
    return {
        "name": _value(source, "name", _value(source, "source")),
        "display_name": _value(source, "display_name", _value(source, "name", "")),
        "description": _value(source, "description", ""),
        "supported_blockchains": list(_value(source, "supported_blockchains", []) or []),
        "confidence_reliability": _value(source, "confidence_reliability", _value(source, "reliability_score", 0.0)),
        "update_frequency": _value(source, "update_frequency"),
        "last_updated": _value(source, "last_updated", _value(source, "last_update", datetime.now(timezone.utc))),
        "status": _value(source, "status", "active"),
        "api_endpoint": _value(source, "api_endpoint"),
        "rate_limit": _value(source, "rate_limit"),
        "statistics": _value(source, "statistics", {}),
    }

# Allowed filter values
VALID_CONFIDENCE_LEVELS = {
    "very_low",
    "low",
    "medium",
    "high",
    "very_high",
    "definitive",
}
VALID_ATTRIBUTION_SOURCES = {
    "victim_reports",
    "threat_intelligence",
    "vasp_registry",
    "on_chain_analysis",
    "user_reports",
    "external_api",
    "manual_investigation",
}
VALID_BLOCKCHAINS = {
    "bitcoin",
    "ethereum",
    "binance_smart_chain",
    "polygon",
    "arbitrum",
    "optimism",
    "solana",
    "tron",
    "xrpl",
    "avalanche",
    "fantom",
    "heco",
}


# Pydantic models
class AttributionAnalysisRequest(BaseModel):
    address: str
    blockchain: str = "bitcoin"
    sources: List[str] = ["all"]
    include_confidence_scores: bool = True
    include_source_details: bool = True
    time_range_days: int = 30

    @field_validator("address")
    @classmethod
    def validate_address(cls, v):
        if not v or len(v) < 10 or len(v) > 64:
            raise ValueError("Invalid address format")
        if not all(ch.isalnum() or ch == "_" for ch in v):
            raise ValueError("Invalid address format")
        return v

    @field_validator("blockchain")
    @classmethod
    def validate_blockchain(cls, v):
        if v.lower() not in VALID_BLOCKCHAINS:
            raise ValueError(f"Invalid blockchain: {v}")
        return v.lower()

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, v):
        if "all" not in v:
            for source in v:
                if source not in VALID_ATTRIBUTION_SOURCES:
                    raise ValueError(f"Invalid attribution source: {source}")
        return v

    @field_validator("time_range_days")
    @classmethod
    def validate_time_range(cls, v):
        if v < 1 or v > 365:
            raise ValueError("Time range must be between 1 and 365 days")
        return v


class AttributionConsolidationRequest(BaseModel):
    address: Optional[str] = None
    addresses: List[str] = []
    blockchain: str = "bitcoin"
    sources: List[str] = ["all"]
    consolidation_method: str = (
        "weighted_average"  # weighted_average, highest_confidence, consensus
    )
    min_confidence_threshold: float = 0.3

    @field_validator("blockchain")
    @classmethod
    def validate_blockchain(cls, v):
        if v.lower() not in VALID_BLOCKCHAINS:
            raise ValueError(f"Invalid blockchain: {v}")
        return v.lower()

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, v):
        if "all" not in v:
            for source in v:
                if source not in VALID_ATTRIBUTION_SOURCES:
                    raise ValueError(f"Invalid attribution source: {source}")
        return v

    @field_validator("consolidation_method")
    @classmethod
    def validate_consolidation_method(cls, v):
        valid_methods = ["weighted_average", "highest_confidence", "consensus"]
        if v not in valid_methods:
            raise ValueError(f"Invalid consolidation method: {v}")
        return v

    @field_validator("min_confidence_threshold")
    @classmethod
    def validate_confidence_threshold(cls, v):
        if v < 0.0 or v > 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")
        return v


class AttributionVerification(BaseModel):
    attribution_id: str
    verified: bool
    confidence_adjustment: Optional[float] = None
    notes: Optional[str] = None
    additional_sources: List[str] = []

    @field_validator("confidence_adjustment")
    @classmethod
    def validate_confidence_adjustment(cls, v):
        if v is not None and (v < -1.0 or v > 1.0):
            raise ValueError("Confidence adjustment must be between -1.0 and 1.0")
        return v


class CrossPlatformAttribution(BaseModel):
    id: str
    address: str
    blockchain: str
    entity: Optional[str]
    entity_type: Optional[str]
    confidence_score: float
    confidence_level: str
    sources: List[str]
    source_details: Dict[str, Any]
    first_seen: Optional[datetime]
    last_seen: Optional[datetime]
    verification_status: str
    verified_by: Optional[str]
    verification_date: Optional[datetime]
    created_date: datetime
    last_updated: datetime


class AttributionSource(BaseModel):
    source: str
    confidence_score: float
    data: Dict[str, Any]
    last_updated: datetime
    reliability_score: float
    coverage_score: float


class ConsolidatedAttribution(BaseModel):
    addresses: List[str]
    blockchain: str
    consolidated_entity: Optional[str]
    consolidated_confidence: float
    individual_attributions: List[CrossPlatformAttribution]
    consolidation_method: str
    source_agreement: float  # Percentage of sources that agree
    confidence_distribution: Dict[str, int]  # Distribution of confidence levels
    gaps_conflicts: List[str]  # Description of gaps and conflicts
    created_date: datetime


class ConfidenceMetrics(BaseModel):
    total_attributions: int
    confidence_distribution: Dict[str, int]
    average_confidence: float
    source_coverage: Dict[str, float]
    verification_rate: float
    attribution_accuracy: Optional[float]  # If ground truth available


class AttributionSource(BaseModel):
    source: str
    description: str
    total_attributions: int
    average_confidence: float
    reliability_score: float
    last_update: datetime
    coverage: Dict[str, int]  # Coverage by blockchain/entity type


# API Endpoints
@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_attribution(
    request: AttributionAnalysisRequest,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Analyze attribution for a single address across multiple sources"""
    try:
        attribution_engine = await _resolve_dependency(get_attribution_engine())

        result = await attribution_engine.analyze_address(
            request.address,
            request.blockchain,
            request.sources,
            request.include_confidence_scores,
            request.include_source_details,
            request.time_range_days,
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No attribution found for address {request.address}",
            )

        logger.info(
            f"Analyzed attribution for address {request.address} on {request.blockchain} by user {current_user.id}"
        )
        return _attr_payload(result)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except TimeoutError as e:
        raise HTTPException(status_code=408, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to analyze attribution for {request.address}: {e}")
        raise JackdawException(message="Failed to analyze attribution", details=str(e))

@router.post("/batch-analyze", response_model=List[Dict[str, Any]])
async def batch_analyze_addresses(
    request: AttributionConsolidationRequest,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy batch-analysis endpoint."""
    try:
        addresses = request.addresses or ([request.address] if request.address else [])
        if len(addresses) > 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Maximum 100 addresses allowed per batch request",
            )
        attribution_engine = await _resolve_dependency(get_attribution_engine())
        results = await attribution_engine.batch_analyze_addresses(
            addresses, request.blockchain
        )
        return [_attr_payload(result) for result in results]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed batch attribution analysis: {e}")
        raise JackdawException(message="Failed to batch analyze addresses", details=str(e))


@router.get("/sources", response_model=List[Dict[str, Any]])
async def list_sources_legacy(
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy sources endpoint."""
    attribution_engine = await _resolve_dependency(get_attribution_engine())
    sources = await attribution_engine.get_available_sources()
    return [_source_payload(source) for source in sources]


@router.get("/sources/{source_name}", response_model=Dict[str, Any])
async def get_source_details(
    source_name: str,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy source-details endpoint."""
    attribution_engine = await _resolve_dependency(get_attribution_engine())
    source = await attribution_engine.get_source_details(source_name)
    if not source:
        raise HTTPException(status_code=404, detail=f"Source {source_name} not found")
    return _source_payload(source)


@router.get("/search", response_model=List[Dict[str, Any]])
async def search_attributions(
    entity: Optional[str] = Query(None, description="Entity name to search"),
    blockchain: Optional[str] = Query(None, description="Filter by blockchain"),
    risk_level: Optional[str] = Query(None, pattern="^(low|medium|high|critical)$"),
    limit: int = Query(100, ge=0, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy attribution-search endpoint."""
    attribution_engine = await _resolve_dependency(get_attribution_engine())
    results = await attribution_engine.search_attributions(
        entity=entity, blockchain=blockchain, risk_level=risk_level, limit=limit, offset=offset
    )
    return [_attr_payload(result) for result in results]


@router.get("/entity/{entity}", response_model=List[Dict[str, Any]])
async def search_entity_legacy(
    entity: str,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy entity-search endpoint."""
    attribution_engine = await _resolve_dependency(get_attribution_engine())
    results = await attribution_engine.search_by_entity(entity)
    return [_attr_payload(result) for result in results]


@router.get("/history/{address}", response_model=List[Dict[str, Any]])
async def attribution_history(
    address: str,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy attribution-history endpoint."""
    attribution_engine = await _resolve_dependency(get_attribution_engine())
    return await attribution_engine.get_attribution_history(address)


@router.get("/statistics", response_model=Dict[str, Any])
async def attribution_statistics_legacy(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy statistics endpoint."""
    attribution_engine = await _resolve_dependency(get_attribution_engine())
    return await attribution_engine.get_statistics(days)


@router.get("/confidence-metrics", response_model=Dict[str, Any])
async def confidence_metrics_legacy(
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy confidence-metrics endpoint."""
    attribution_engine = await _resolve_dependency(get_attribution_engine())
    return await attribution_engine.get_confidence_metrics()


@router.post("/detect-conflicts", response_model=List[Dict[str, Any]])
async def detect_conflicts_legacy(
    request: AttributionAnalysisRequest,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy conflict-detection endpoint."""
    attribution_engine = await _resolve_dependency(get_attribution_engine())
    return await attribution_engine.detect_conflicts(request.address, request.blockchain)


@router.post("/resolve-conflict/{conflict_id}", response_model=Dict[str, Any])
async def resolve_conflict_legacy(
    conflict_id: str,
    resolution_data: Dict[str, Any],
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"])),
):
    """Legacy conflict-resolution endpoint."""
    attribution_engine = await _resolve_dependency(get_attribution_engine())
    return await attribution_engine.resolve_conflict(conflict_id, resolution_data)


@router.get("/address/{address}", response_model=Dict[str, Any])
async def get_attribution(
    address: str,
    blockchain: str = Query(..., description="Blockchain network"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Get existing attribution data for an address"""
    try:
        if blockchain.lower() not in VALID_BLOCKCHAINS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid blockchain: {blockchain}",
            )

        attribution_engine = await _resolve_dependency(get_attribution_engine())

        result = await attribution_engine.get_attribution(address, blockchain.lower())
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No attribution found for address {address} on {blockchain}",
            )

        return _attr_payload(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get attribution for {address}: {e}")
        raise JackdawException(message="Failed to get attribution", details=str(e))


@router.get("/sources/available", response_model=List[AttributionSource])
async def get_attribution_sources(
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Get list of available attribution sources with their status"""
    try:
        attribution_engine = await _resolve_dependency(get_attribution_engine())

        sources = await attribution_engine.get_available_sources()

        return [AttributionSource(**source.__dict__) for source in sources]

    except Exception as e:
        logger.error(f"Failed to get attribution sources: {e}")
        raise JackdawException(
            message="Failed to get attribution sources", details=str(e)
        )


@router.post("/consolidate", response_model=Dict[str, Any])
async def consolidate_attributions(
    request: AttributionConsolidationRequest,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Consolidate attributions from multiple sources for multiple addresses"""
    try:
        attribution_engine = await _resolve_dependency(get_attribution_engine())
        addresses = request.addresses or ([request.address] if request.address else [])
        result = await attribution_engine.consolidate_attributions(
            addresses,
            request.blockchain,
            request.sources,
            request.consolidation_method,
            request.min_confidence_threshold,
        )

        logger.info(
            f"Consolidated attributions for {len(addresses)} addresses on {request.blockchain} by user {current_user.id}"
        )
        return {
            "id": _value(result, "id", str(uuid.uuid4())),
            "address": _value(result, "address", addresses[0] if addresses else ""),
            "blockchain": _value(result, "blockchain", request.blockchain),
            "source_attributions": _value(result, "source_attributions", []),
            "consolidated_entity": _value(result, "consolidated_entity"),
            "confidence_metrics": _value(result, "confidence_metrics", {}),
            "conflicts": _value(result, "conflicts", []),
            "consolidation_date": _value(result, "consolidation_date", datetime.now(timezone.utc)),
        }

    except Exception as e:
        logger.error(f"Failed to consolidate attributions: {e}")
        raise JackdawException(
            message="Failed to consolidate attributions", details=str(e)
        )


@router.get("/confidence/metrics", response_model=ConfidenceMetrics)
async def get_confidence_metrics(
    blockchain: Optional[str] = Query(None, description="Filter by blockchain"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Get confidence scoring metrics and statistics"""
    try:
        if blockchain and blockchain.lower() not in VALID_BLOCKCHAINS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid blockchain: {blockchain}",
            )

        attribution_engine = await _resolve_dependency(get_attribution_engine())

        metrics = await attribution_engine.get_confidence_metrics(
            blockchain.lower() if blockchain else None, days
        )

        return ConfidenceMetrics(**metrics)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get confidence metrics: {e}")
        raise JackdawException(
            message="Failed to get confidence metrics", details=str(e)
        )


@router.put("/verify/{attribution_id}", response_model=CrossPlatformAttribution)
async def verify_attribution(
    attribution_id: str,
    verification: AttributionVerification,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"])),
):
    """Verify or update attribution confidence"""
    try:
        attribution_engine = await _resolve_dependency(get_attribution_engine())

        # Check if attribution exists
        existing_attribution = await attribution_engine.get_attribution_by_id(
            attribution_id
        )
        if not existing_attribution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Attribution {attribution_id} not found",
            )

        verification_data = verification.model_dump()
        verification_data["verified_by"] = current_user.id
        verification_data["verification_date"] = datetime.now(timezone.utc)

        updated_attribution = await attribution_engine.verify_attribution(
            attribution_id, verification_data
        )

        logger.info(f"Verified attribution {attribution_id} by user {current_user.id}")
        return CrossPlatformAttribution(**updated_attribution.__dict__)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify attribution {attribution_id}: {e}")
        raise JackdawException(message="Failed to verify attribution", details=str(e))


@router.get("/search/entity", response_model=List[CrossPlatformAttribution])
async def search_by_entity(
    entity: str = Query(..., description="Entity name to search"),
    blockchain: Optional[str] = Query(None, description="Filter by blockchain"),
    confidence_level: Optional[str] = Query(
        None, description="Filter by confidence level"
    ),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Search attributions by entity name"""
    try:
        if blockchain and blockchain.lower() not in VALID_BLOCKCHAINS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid blockchain: {blockchain}",
            )

        if confidence_level and confidence_level not in VALID_CONFIDENCE_LEVELS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid confidence level: {confidence_level}",
            )

        attribution_engine = await _resolve_dependency(get_attribution_engine())

        results = await attribution_engine.search_by_entity(
            entity, blockchain.lower() if blockchain else None, confidence_level, limit
        )

        return [CrossPlatformAttribution(**result.__dict__) for result in results]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search attributions by entity {entity}: {e}")
        raise JackdawException(
            message="Failed to search attributions by entity", details=str(e)
        )


@router.get("/batch/{addresses}", response_model=List[CrossPlatformAttribution])
async def get_batch_attributions(
    addresses: str,
    blockchain: str = Query(..., description="Blockchain network"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Get attributions for multiple addresses (comma-separated)"""
    try:
        if blockchain.lower() not in VALID_BLOCKCHAINS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid blockchain: {blockchain}",
            )

        # Parse addresses
        address_list = [addr.strip() for addr in addresses.split(",") if addr.strip()]
        if len(address_list) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 100 addresses allowed per batch request",
            )

        attribution_engine = await _resolve_dependency(get_attribution_engine())

        results = await attribution_engine.get_batch_attributions(
            address_list, blockchain.lower()
        )

        return [CrossPlatformAttribution(**result.__dict__) for result in results]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get batch attributions: {e}")
        raise JackdawException(
            message="Failed to get batch attributions", details=str(e)
        )


@router.post("/refresh", response_model=Dict[str, str])
async def refresh_attributions(
    background_tasks: BackgroundTasks,
    sources: Optional[List[str]] = Query(
        None, description="Specific sources to refresh"
    ),
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"])),
):
    """Trigger refresh of attribution data from sources"""
    try:
        if sources:
            for source in sources:
                if source not in VALID_ATTRIBUTION_SOURCES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid attribution source: {source}",
                    )

        attribution_engine = await _resolve_dependency(get_attribution_engine())

        # Trigger refresh in background
        background_tasks.add_task(attribution_engine.refresh_sources, sources)

        logger.info(
            f"Triggered attribution refresh for sources {sources or 'all'} by user {current_user.id}"
        )

        return {"status": "refresh_triggered", "sources": sources or "all"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to refresh attributions: {e}")
        raise JackdawException(message="Failed to refresh attributions", details=str(e))


@router.get("/statistics/overview", response_model=Dict[str, Any])
async def get_attribution_statistics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Get comprehensive attribution statistics"""
    try:
        attribution_engine = await _resolve_dependency(get_attribution_engine())

        stats = await attribution_engine.get_statistics(days)

        return stats

    except Exception as e:
        logger.error(f"Failed to get attribution statistics: {e}")
        raise JackdawException(
            message="Failed to get attribution statistics", details=str(e)
        )


@router.get("/conflicts", response_model=List[Dict[str, Any]])
async def get_attribution_conflicts(
    blockchain: Optional[str] = Query(None, description="Filter by blockchain"),
    min_confidence_gap: float = Query(
        0.3,
        ge=0.0,
        le=1.0,
        description="Minimum confidence gap to consider as conflict",
    ),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Get attribution conflicts where sources disagree"""
    try:
        if blockchain and blockchain.lower() not in VALID_BLOCKCHAINS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid blockchain: {blockchain}",
            )

        attribution_engine = await _resolve_dependency(get_attribution_engine())

        conflicts = await attribution_engine.get_conflicts(
            blockchain.lower() if blockchain else None, min_confidence_gap
        )

        return conflicts

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get attribution conflicts: {e}")
        raise JackdawException(
            message="Failed to get attribution conflicts", details=str(e)
        )


@router.get("/{address}", response_model=Dict[str, Any])
async def get_attribution_legacy_alias(
    address: str,
    blockchain: str = Query("bitcoin", description="Blockchain network"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"])),
):
    """Legacy one-segment attribution lookup retained after adding static aliases."""
    return await get_attribution(address, blockchain, current_user)
