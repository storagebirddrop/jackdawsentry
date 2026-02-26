"""
Jackdaw Sentry - Advanced Analytics API Router
REST endpoints for multi-route pathfinding, seed analysis, and transaction fingerprinting
"""

import logging
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status
from pydantic import BaseModel
from pydantic import field_validator

from src.analytics import BatchAnalyticsRequest
from src.analytics import BatchAnalyticsResponse
from src.analytics import DerivationType
from src.analytics import FingerprintingRequest
from src.analytics import FingerprintingResponse
from src.analytics import FingerprintResult
from src.analytics import FingerprintType
from src.analytics import PathfindingAlgorithm
from src.analytics import PathfindingRequest
from src.analytics import PathfindingResponse
from src.analytics import PathfindingResult
from src.analytics import SeedAnalysisRequest
from src.analytics import SeedAnalysisResponse
from src.analytics import SeedAnalysisResult
from src.analytics import get_analytics_engine
from src.api.auth import PERMISSIONS
from src.api.auth import User
from src.api.auth import check_permissions
from src.api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize analytics engine
analytics_engine = get_analytics_engine()


# Pydantic models for API requests/responses
class MultiRoutePathfindingRequest(BaseModel):
    source_address: str
    target_address: str
    blockchain: str
    algorithm: PathfindingAlgorithm = PathfindingAlgorithm.ALL_PATHS
    max_paths: int = 100
    max_hops: int = 10
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    time_window_hours: int = 168
    include_intermediate: bool = True
    confidence_threshold: float = 0.5

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


class SeedPhraseAnalysisRequest(BaseModel):
    seed_phrase: str
    derivation_types: List[DerivationType] = [DerivationType.BIP44]
    blockchains: List[str] = ["bitcoin", "ethereum"]
    max_derivations: int = 100
    check_balances: bool = True
    include_inactive: bool = True

    @field_validator("seed_phrase")
    @classmethod
    def validate_seed_phrase(cls, v):
        if not v or not v.strip():
            raise ValueError("Seed phrase cannot be empty")

        words = v.strip().split()
        if len(words) not in [12, 24]:
            raise ValueError("Seed phrase must be 12 or 24 words")

        return v.strip().lower()


class TransactionFingerprintingRequest(BaseModel):
    query_type: FingerprintType
    parameters: Dict[str, Any] = {}
    blockchain: Optional[str] = None
    time_window_hours: int = 168
    min_confidence: float = 0.5
    max_results: int = 100


# API Endpoints


@router.post("/pathfinding", response_model=PathfindingResponse)
async def find_transaction_paths(
    request: MultiRoutePathfindingRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Find transaction paths between two addresses

    - **source_address**: Source address to start pathfinding from
    - **target_address**: Target address to find paths to
    - **blockchain**: Blockchain name (bitcoin, ethereum, etc.)
    - **algorithm**: Pathfinding algorithm (shortest_path, all_paths, disconnected_paths, funnel_analysis, circular_paths)
    - **max_paths**: Maximum number of paths to return (1-1000)
    - **max_hops**: Maximum number of hops in path (1-50)
    - **min_amount**: Minimum amount filter (optional)
    - **max_amount**: Maximum amount filter (optional)
    - **time_window_hours**: Time window for transaction analysis (1-8760 hours)
    - **include_intermediate**: Include intermediate nodes in analysis
    - **confidence_threshold**: Minimum confidence threshold (0.0-1.0)
    """

    try:
        # Ensure analytics engine is initialized
        await analytics_engine.initialize()

        # Create pathfinding request
        pathfinding_request = PathfindingRequest(
            source_address=request.source_address,
            target_address=request.target_address,
            blockchain=request.blockchain,
            algorithm=request.algorithm,
            max_paths=request.max_paths,
            max_hops=request.max_hops,
            min_amount=request.min_amount,
            max_amount=request.max_amount,
            time_window_hours=request.time_window_hours,
            include_intermediate=request.include_intermediate,
            confidence_threshold=request.confidence_threshold,
        )

        # Process pathfinding
        result = await analytics_engine.pathfinder.find_paths(pathfinding_request)

        return PathfindingResponse(
            success=True, result=result, processing_time_ms=result.processing_time_ms
        )

    except Exception as e:
        logger.error(f"Error in pathfinding: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find transaction paths",
        )


@router.post("/seed-analysis", response_model=SeedAnalysisResponse)
async def analyze_seed_phrase(
    request: SeedPhraseAnalysisRequest,
    current_user: User = Depends(check_permissions(PERMISSIONS.WRITE_ANALYSIS)),
):
    """
    Analyze seed phrase and derive wallet addresses

    - **seed_phrase**: 12 or 24 word seed phrase (will be hashed for privacy)
    - **derivation_types**: List of derivation types (bip44, bip49, bip84, bip32, custom)
    - **blockchains**: List of blockchains to derive for
    - **max_derivations**: Maximum number of derivations per type (1-1000)
    - **check_balances**: Check wallet balances and activity
    - **include_inactive**: Include wallets with no activity

    *Requires write analysis permission*
    """

    try:
        # Ensure analytics engine is initialized
        await analytics_engine.initialize()

        # Create seed analysis request
        seed_request = SeedAnalysisRequest(
            seed_phrase=request.seed_phrase,
            derivation_types=request.derivation_types,
            blockchains=request.blockchains,
            max_derivations=request.max_derivations,
            check_balances=request.check_balances,
            include_inactive=request.include_inactive,
        )

        # Process seed analysis
        result = await analytics_engine.seed_analyzer.analyze_seed_phrase(seed_request)

        return SeedAnalysisResponse(
            success=True, result=result, processing_time_ms=result.processing_time_ms
        )

    except Exception as e:
        logger.error(f"Error in seed analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze seed phrase",
        )


@router.post("/fingerprinting", response_model=FingerprintingResponse)
async def fingerprint_transactions(
    request: TransactionFingerprintingRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Fingerprint transactions based on patterns

    - **query_type**: Type of fingerprinting query (amount_pattern, timing_pattern, address_pattern, sequence_pattern, behavioral_pattern, network_pattern)
    - **parameters**: Query parameters specific to the query type
    - **blockchain**: Blockchain to search (optional)
    - **time_window_hours**: Time window for analysis (1-8760 hours)
    - **min_confidence**: Minimum confidence threshold (0.0-1.0)
    - **max_results**: Maximum number of results to return (1-1000)
    """

    try:
        # Ensure analytics engine is initialized
        await analytics_engine.initialize()

        # Create fingerprinting request
        fingerprint_request = FingerprintingRequest(
            query_type=request.query_type,
            parameters=request.parameters,
            blockchain=request.blockchain,
            time_window_hours=request.time_window_hours,
            min_confidence=request.min_confidence,
            max_results=request.max_results,
        )

        # Process fingerprinting
        result = await analytics_engine.fingerprinter.fingerprint_transactions(
            fingerprint_request
        )

        return FingerprintingResponse(
            success=True, result=result, processing_time_ms=result.processing_time_ms
        )

    except Exception as e:
        logger.error(f"Error in transaction fingerprinting: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fingerprint transactions",
        )


@router.post("/batch", response_model=BatchAnalyticsResponse)
async def batch_analytics(
    request: BatchAnalyticsRequest,
    current_user: User = Depends(check_permissions(PERMISSIONS.BULK_SCREENING)),
):
    """
    Process multiple analytics requests in batch

    - **requests**: List of analytics requests to process
    - **parallel_processing**: Enable parallel processing
    - **max_concurrent**: Maximum concurrent requests (1-20)

    *Requires bulk screening permission*
    """

    try:
        # Ensure analytics engine is initialized
        await analytics_engine.initialize()

        # Process batch request
        result = await analytics_engine.process_batch_requests(request)

        return result

    except Exception as e:
        logger.error(f"Error in batch analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process batch analytics",
        )


@router.get("/algorithms")
async def list_pathfinding_algorithms(current_user: User = Depends(get_current_user)):
    """
    Get available pathfinding algorithms

    Returns a list of supported pathfinding algorithms with descriptions
    """

    algorithms = {
        "shortest_path": {
            "name": "Shortest Path",
            "description": "Find the shortest path by amount between two addresses",
            "use_case": "Quick analysis of most direct fund flow",
        },
        "all_paths": {
            "name": "All Paths",
            "description": "Find all possible paths between two addresses",
            "use_case": "Comprehensive analysis of all possible routes",
        },
        "disconnected_paths": {
            "name": "Disconnected Paths",
            "description": "Find disconnected path segments when no direct path exists",
            "use_case": "Analysis of separate transaction clusters",
        },
        "funnel_analysis": {
            "name": "Funnel Analysis",
            "description": "Analyze convergence patterns where multiple sources funnel to targets",
            "use_case": "Identify aggregation points and mixing patterns",
        },
        "circular_paths": {
            "name": "Circular Paths",
            "description": "Find circular transaction paths and cycles",
            "use_case": "Detect circular trading and round-tripping",
        },
    }

    return algorithms


@router.get("/fingerprint-patterns")
async def list_fingerprint_patterns(
    pattern_type: Optional[FingerprintType] = Query(
        None, description="Filter by pattern type"
    ),
    current_user: User = Depends(get_current_user),
):
    """
    Get available fingerprint patterns

    - **pattern_type**: Filter patterns by type (optional)

    Returns a list of available fingerprint patterns with descriptions
    """

    try:
        # Ensure analytics engine is initialized
        await analytics_engine.initialize()

        patterns = analytics_engine.fingerprinter.get_patterns(pattern_type)

        return [
            {
                "pattern_type": pattern.pattern_type.value,
                "name": pattern.name,
                "description": pattern.description,
                "confidence_score": pattern.confidence_score,
                "pattern_data": pattern.pattern_data,
            }
            for pattern in patterns
        ]

    except Exception as e:
        logger.error(f"Error listing fingerprint patterns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list fingerprint patterns",
        )


@router.get("/statistics")
async def get_analytics_statistics(
    current_user: User = Depends(check_permissions(PERMISSIONS.VIEW_ANALYTICS)),
):
    """
    Get advanced analytics statistics

    Returns statistics about pathfinding, seed analysis, and fingerprinting performance

    *Requires analytics permission*
    """

    try:
        # Ensure analytics engine is initialized
        await analytics_engine.initialize()

        stats = await analytics_engine.get_analytics_statistics()

        return stats

    except Exception as e:
        logger.error(f"Error getting analytics statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analytics statistics",
        )


@router.post("/clear-cache")
async def clear_analytics_cache(
    current_user: User = Depends(check_permissions(PERMISSIONS.ADMIN_SYSTEM)),
):
    """
    Clear all analytics caches

    *Requires admin system permission*
    """

    try:
        await analytics_engine.clear_all_caches()
        return {"message": "All analytics caches cleared successfully"}

    except Exception as e:
        logger.error(f"Error clearing analytics cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear analytics cache",
        )


@router.get("/health")
async def analytics_health_check():
    """
    Health check for advanced analytics engine

    Returns the status of all analytics components
    """

    try:
        # Check if engine is initialized
        is_initialized = analytics_engine._initialized

        # Check component health
        components = {
            "pathfinder": (
                analytics_engine.pathfinder._initialized
                if hasattr(analytics_engine.pathfinder, "_initialized")
                else False
            ),
            "seed_analyzer": (
                analytics_engine.seed_analyzer._initialized
                if hasattr(analytics_engine.seed_analyzer, "_initialized")
                else False
            ),
            "fingerprinter": (
                analytics_engine.fingerprinter._initialized
                if hasattr(analytics_engine.fingerprinter, "_initialized")
                else False
            ),
        }

        all_healthy = is_initialized and all(components.values())

        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "initialized": is_initialized,
            "components": components,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in analytics health check: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
