"""
Jackdaw Sentry - Cross-Platform Attribution API Router
REST endpoints for unified intelligence consolidation and attribution analysis
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from typing import List, Dict, Optional, Any, Set
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, field_validator
import logging
import uuid
import json as _json

from src.api.auth import User, check_permissions, PERMISSIONS
from src.api.database import get_postgres_connection
from src.api.exceptions import JackdawException
from src.intelligence.cross_platform import get_cross_platform_engine

logger = logging.getLogger(__name__)

router = APIRouter()

# Allowed filter values
VALID_CONFIDENCE_LEVELS = {"very_low", "low", "medium", "high", "very_high", "definitive"}
VALID_ATTRIBUTION_SOURCES = {"victim_reports", "threat_intelligence", "vasp_registry", "on_chain_analysis", "user_reports", "external_api", "manual_investigation"}
VALID_BLOCKCHAINS = {"bitcoin", "ethereum", "binance_smart_chain", "polygon", "arbitrum", "optimism", "solana", "tron", "xrpl", "avalanche", "fantom", "heco"}

# Pydantic models
class AttributionAnalysisRequest(BaseModel):
    address: str
    blockchain: str
    sources: List[str] = ["all"]
    include_confidence_scores: bool = True
    include_source_details: bool = True
    time_range_days: int = 30
    
    @field_validator('blockchain')
    @classmethod
    def validate_blockchain(cls, v):
        if v.lower() not in VALID_BLOCKCHAINS:
            raise ValueError(f'Invalid blockchain: {v}')
        return v.lower()
    
    @field_validator('sources')
    @classmethod
    def validate_sources(cls, v):
        if "all" not in v:
            for source in v:
                if source not in VALID_ATTRIBUTION_SOURCES:
                    raise ValueError(f'Invalid attribution source: {source}')
        return v
    
    @field_validator('time_range_days')
    @classmethod
    def validate_time_range(cls, v):
        if v < 1 or v > 365:
            raise ValueError('Time range must be between 1 and 365 days')
        return v

class AttributionConsolidationRequest(BaseModel):
    addresses: List[str]
    blockchain: str
    sources: List[str] = ["all"]
    consolidation_method: str = "weighted_average"  # weighted_average, highest_confidence, consensus
    min_confidence_threshold: float = 0.3
    
    @field_validator('blockchain')
    @classmethod
    def validate_blockchain(cls, v):
        if v.lower() not in VALID_BLOCKCHAINS:
            raise ValueError(f'Invalid blockchain: {v}')
        return v.lower()
    
    @field_validator('sources')
    @classmethod
    def validate_sources(cls, v):
        if "all" not in v:
            for source in v:
                if source not in VALID_ATTRIBUTION_SOURCES:
                    raise ValueError(f'Invalid attribution source: {source}')
        return v
    
    @field_validator('consolidation_method')
    @classmethod
    def validate_consolidation_method(cls, v):
        valid_methods = ["weighted_average", "highest_confidence", "consensus"]
        if v not in valid_methods:
            raise ValueError(f'Invalid consolidation method: {v}')
        return v
    
    @field_validator('min_confidence_threshold')
    @classmethod
    def validate_confidence_threshold(cls, v):
        if v < 0.0 or v > 1.0:
            raise ValueError('Confidence threshold must be between 0.0 and 1.0')
        return v

class AttributionVerification(BaseModel):
    attribution_id: str
    verified: bool
    confidence_adjustment: Optional[float] = None
    notes: Optional[str] = None
    additional_sources: List[str] = []
    
    @field_validator('confidence_adjustment')
    @classmethod
    def validate_confidence_adjustment(cls, v):
        if v is not None and (v < -1.0 or v > 1.0):
            raise ValueError('Confidence adjustment must be between -1.0 and 1.0')
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
@router.post("/analyze", response_model=CrossPlatformAttribution)
async def analyze_attribution(
    request: AttributionAnalysisRequest,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"]))
):
    """Analyze attribution for a single address across multiple sources"""
    try:
        attribution_engine = await get_cross_platform_engine()
        
        result = await attribution_engine.analyze_address(
            request.address,
            request.blockchain,
            request.sources,
            request.include_confidence_scores,
            request.include_source_details,
            request.time_range_days
        )
        
        logger.info(f"Analyzed attribution for address {request.address} on {request.blockchain} by user {current_user.id}")
        return CrossPlatformAttribution(**result.__dict__)
        
    except Exception as e:
        logger.error(f"Failed to analyze attribution for {request.address}: {e}")
        raise JackdawException(
            message="Failed to analyze attribution",
            details=str(e)
        )

@router.get("/{address}", response_model=CrossPlatformAttribution)
async def get_attribution(
    address: str,
    blockchain: str = Query(..., description="Blockchain network"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"]))
):
    """Get existing attribution data for an address"""
    try:
        if blockchain.lower() not in VALID_BLOCKCHAINS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid blockchain: {blockchain}"
            )
        
        attribution_engine = await get_cross_platform_engine()
        
        result = await attribution_engine.get_attribution(address, blockchain.lower())
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No attribution found for address {address} on {blockchain}"
            )
        
        return CrossPlatformAttribution(**result.__dict__)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get attribution for {address}: {e}")
        raise JackdawException(
            message="Failed to get attribution",
            details=str(e)
        )

@router.get("/sources/available", response_model=List[AttributionSource])
async def get_attribution_sources(
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"]))
):
    """Get list of available attribution sources with their status"""
    try:
        attribution_engine = await get_cross_platform_engine()
        
        sources = await attribution_engine.get_available_sources()
        
        return [AttributionSource(**source.__dict__) for source in sources]
        
    except Exception as e:
        logger.error(f"Failed to get attribution sources: {e}")
        raise JackdawException(
            message="Failed to get attribution sources",
            details=str(e)
        )

@router.post("/consolidate", response_model=ConsolidatedAttribution)
async def consolidate_attributions(
    request: AttributionConsolidationRequest,
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"]))
):
    """Consolidate attributions from multiple sources for multiple addresses"""
    try:
        attribution_engine = await get_cross_platform_engine()
        
        result = await attribution_engine.consolidate_attributions(
            request.addresses,
            request.blockchain,
            request.sources,
            request.consolidation_method,
            request.min_confidence_threshold
        )
        
        logger.info(f"Consolidated attributions for {len(request.addresses)} addresses on {request.blockchain} by user {current_user.id}")
        return ConsolidatedAttribution(**result.__dict__)
        
    except Exception as e:
        logger.error(f"Failed to consolidate attributions: {e}")
        raise JackdawException(
            message="Failed to consolidate attributions",
            details=str(e)
        )

@router.get("/confidence/metrics", response_model=ConfidenceMetrics)
async def get_confidence_metrics(
    blockchain: Optional[str] = Query(None, description="Filter by blockchain"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"]))
):
    """Get confidence scoring metrics and statistics"""
    try:
        if blockchain and blockchain.lower() not in VALID_BLOCKCHAINS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid blockchain: {blockchain}"
            )
        
        attribution_engine = await get_cross_platform_engine()
        
        metrics = await attribution_engine.get_confidence_metrics(
            blockchain.lower() if blockchain else None,
            days
        )
        
        return ConfidenceMetrics(**metrics)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get confidence metrics: {e}")
        raise JackdawException(
            message="Failed to get confidence metrics",
            details=str(e)
        )

@router.put("/verify/{attribution_id}", response_model=CrossPlatformAttribution)
async def verify_attribution(
    attribution_id: str,
    verification: AttributionVerification,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"]))
):
    """Verify or update attribution confidence"""
    try:
        attribution_engine = await get_cross_platform_engine()
        
        # Check if attribution exists
        existing_attribution = await attribution_engine.get_attribution_by_id(attribution_id)
        if not existing_attribution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Attribution {attribution_id} not found"
            )
        
        verification_data = verification.model_dump()
        verification_data["verified_by"] = current_user.id
        verification_data["verification_date"] = datetime.now(timezone.utc)
        
        updated_attribution = await attribution_engine.verify_attribution(
            attribution_id,
            verification_data
        )
        
        logger.info(f"Verified attribution {attribution_id} by user {current_user.id}")
        return CrossPlatformAttribution(**updated_attribution.__dict__)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify attribution {attribution_id}: {e}")
        raise JackdawException(
            message="Failed to verify attribution",
            details=str(e)
        )

@router.get("/search/entity", response_model=List[CrossPlatformAttribution])
async def search_by_entity(
    entity: str = Query(..., description="Entity name to search"),
    blockchain: Optional[str] = Query(None, description="Filter by blockchain"),
    confidence_level: Optional[str] = Query(None, description="Filter by confidence level"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"]))
):
    """Search attributions by entity name"""
    try:
        if blockchain and blockchain.lower() not in VALID_BLOCKCHAINS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid blockchain: {blockchain}"
            )
        
        if confidence_level and confidence_level not in VALID_CONFIDENCE_LEVELS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid confidence level: {confidence_level}"
            )
        
        attribution_engine = await get_cross_platform_engine()
        
        results = await attribution_engine.search_by_entity(
            entity,
            blockchain.lower() if blockchain else None,
            confidence_level,
            limit
        )
        
        return [CrossPlatformAttribution(**result.__dict__) for result in results]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search attributions by entity {entity}: {e}")
        raise JackdawException(
            message="Failed to search attributions by entity",
            details=str(e)
        )

@router.get("/batch/{addresses}", response_model=List[CrossPlatformAttribution])
async def get_batch_attributions(
    addresses: str,
    blockchain: str = Query(..., description="Blockchain network"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"]))
):
    """Get attributions for multiple addresses (comma-separated)"""
    try:
        if blockchain.lower() not in VALID_BLOCKCHAINS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid blockchain: {blockchain}"
            )
        
        # Parse addresses
        address_list = [addr.strip() for addr in addresses.split(",") if addr.strip()]
        if len(address_list) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 100 addresses allowed per batch request"
            )
        
        attribution_engine = await get_cross_platform_engine()
        
        results = await attribution_engine.get_batch_attributions(
            address_list,
            blockchain.lower()
        )
        
        return [CrossPlatformAttribution(**result.__dict__) for result in results]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get batch attributions: {e}")
        raise JackdawException(
            message="Failed to get batch attributions",
            details=str(e)
        )

@router.post("/refresh", response_model=Dict[str, str])
async def refresh_attributions(
    background_tasks: BackgroundTasks,
    sources: Optional[List[str]] = Query(None, description="Specific sources to refresh"),
    current_user: User = Depends(check_permissions(PERMISSIONS["write_intelligence"]))
):
    """Trigger refresh of attribution data from sources"""
    try:
        if sources:
            for source in sources:
                if source not in VALID_ATTRIBUTION_SOURCES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid attribution source: {source}"
                    )
        
        attribution_engine = await get_cross_platform_engine()
        
        # Trigger refresh in background
        background_tasks.add_task(attribution_engine.refresh_sources, sources)
        
        logger.info(f"Triggered attribution refresh for sources {sources or 'all'} by user {current_user.id}")
        
        return {"status": "refresh_triggered", "sources": sources or "all"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to refresh attributions: {e}")
        raise JackdawException(
            message="Failed to refresh attributions",
            details=str(e)
        )

@router.get("/statistics/overview", response_model=Dict[str, Any])
async def get_attribution_statistics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"]))
):
    """Get comprehensive attribution statistics"""
    try:
        attribution_engine = await get_cross_platform_engine()
        
        stats = await attribution_engine.get_statistics(days)
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get attribution statistics: {e}")
        raise JackdawException(
            message="Failed to get attribution statistics",
            details=str(e)
        )

@router.get("/conflicts", response_model=List[Dict[str, Any]])
async def get_attribution_conflicts(
    blockchain: Optional[str] = Query(None, description="Filter by blockchain"),
    min_confidence_gap: float = Query(0.3, ge=0.0, le=1.0, description="Minimum confidence gap to consider as conflict"),
    current_user: User = Depends(check_permissions(PERMISSIONS["read_intelligence"]))
):
    """Get attribution conflicts where sources disagree"""
    try:
        if blockchain and blockchain.lower() not in VALID_BLOCKCHAINS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid blockchain: {blockchain}"
            )
        
        attribution_engine = await get_cross_platform_engine()
        
        conflicts = await attribution_engine.get_conflicts(
            blockchain.lower() if blockchain else None,
            min_confidence_gap
        )
        
        return conflicts
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get attribution conflicts: {e}")
        raise JackdawException(
            message="Failed to get attribution conflicts",
            details=str(e)
        )
