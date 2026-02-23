"""
Jackdaw Sentry - Pattern Detection API Router
REST endpoints for advanced pattern detection and analysis
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

from src.api.auth import PERMISSIONS
from src.api.auth import User
from src.api.auth import check_permissions
from src.api.auth import get_current_user
from src.api.database import get_postgres_connection
from src.patterns import BatchPatternRequest
from src.patterns import BatchPatternResponse
from src.patterns import PatternAnalysisResult
from src.patterns import PatternConfig
from src.patterns import PatternRequest
from src.patterns import PatternResponse
from src.patterns import PatternSeverity
from src.patterns import PatternSignature
from src.patterns import PatternStatistics
from src.patterns import PatternType
from src.patterns import get_pattern_detector
from src.patterns import get_pattern_library

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize engines
pattern_detector = get_pattern_detector()
pattern_library = get_pattern_library()


# Pydantic models for API requests/responses
class PatternSearchRequest(BaseModel):
    pattern_types: Optional[List[PatternType]] = None
    min_severity: Optional[PatternSeverity] = None
    enabled_only: bool = True


class PatternAlertRequest(BaseModel):
    address: str
    blockchain: str
    pattern_id: str
    severity: PatternSeverity
    notes: Optional[str] = None


class PatternConfigUpdateRequest(BaseModel):
    enabled_patterns: Optional[List[str]] = None
    confidence_thresholds: Optional[Dict[str, float]] = None
    severity_overrides: Optional[Dict[str, PatternSeverity]] = None


# API Endpoints


@router.post("/analyze", response_model=PatternAnalysisResult)
async def analyze_address_patterns(
    request: PatternRequest, current_user: User = Depends(get_current_user)
):
    """
    Analyze patterns for a single address

    - **addresses**: List of addresses to analyze (single address expected)
    - **blockchain**: Blockchain name (bitcoin, ethereum, etc.)
    - **pattern_types**: Filter by pattern types
    - **min_severity**: Filter by minimum severity level
    - **time_range_hours**: Time window for analysis (1-8760 hours)
    - **include_evidence**: Include supporting evidence in response
    - **min_confidence**: Minimum confidence threshold (0.0-1.0)
    """

    if len(request.addresses) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint accepts only one address. Use /batch-analyze for multiple addresses.",
        )

    try:
        # Ensure pattern detector is initialized
        await pattern_detector.initialize()

        # Analyze patterns
        result = await pattern_detector.analyze_address_patterns(
            address=request.addresses[0],
            blockchain=request.blockchain,
            pattern_types=request.pattern_types,
            min_severity=request.min_severity,
            time_range_hours=request.time_range_hours,
            include_evidence=request.include_evidence,
            min_confidence=request.min_confidence,
        )

        return result

    except Exception as e:
        logger.error(f"Error analyzing patterns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze patterns",
        )


@router.post("/batch-analyze", response_model=BatchPatternResponse)
async def batch_analyze_patterns(
    request: BatchPatternRequest,
    current_user: User = Depends(check_permissions(PERMISSIONS["bulk_screening"])),
):
    """
    Analyze patterns for multiple addresses in batch

    - **addresses**: List of addresses to analyze (max 1000)
    - **blockchain**: Blockchain name (bitcoin, ethereum, etc.)
    - **pattern_types**: Filter by pattern types
    - **min_severity**: Filter by minimum severity level
    - **time_range_hours**: Time window for analysis (1-8760 hours)
    - **include_evidence**: Include supporting evidence (disabled for batch performance)
    - **min_confidence**: Minimum confidence threshold (0.0-1.0)
    - **parallel_processing**: Enable parallel processing
    - **max_concurrent**: Maximum concurrent analyses

    *Requires bulk screening permission*
    """

    if len(request.addresses) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 1000 addresses allowed per batch",
        )

    try:
        # Ensure pattern detector is initialized
        await pattern_detector.initialize()

        start_time = datetime.now(timezone.utc)

        # Convert to single address request for batch processing
        single_request = PatternRequest(
            addresses=request.addresses,
            blockchain=request.blockchain,
            pattern_types=request.pattern_types,
            min_severity=request.min_severity,
            time_range_hours=request.time_range_hours,
            include_evidence=request.include_evidence,
            min_confidence=request.min_confidence,
        )

        # Process batch analysis
        results = await pattern_detector.batch_analyze_patterns(single_request)

        # Calculate statistics
        successful_count = len(results)
        failed_addresses = [addr for addr in request.addresses if addr not in results]
        processing_time = (
            datetime.now(timezone.utc) - start_time
        ).total_seconds() * 1000

        # Count patterns detected
        total_patterns = sum(
            len(result.patterns) for result in results.values() if result
        )
        high_risk_findings = sum(
            1
            for result in results.values()
            if result and result.overall_risk_score >= 0.7
        )

        return BatchPatternResponse(
            results=results,
            total_addresses=len(request.addresses),
            successful_analyses=successful_count,
            failed_addresses=failed_addresses,
            processing_time_ms=processing_time,
            patterns_detected=total_patterns,
            high_risk_findings=high_risk_findings,
        )

    except Exception as e:
        logger.error(f"Error in batch pattern analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process batch pattern analysis",
        )


@router.get("/patterns", response_model=List[PatternSignature])
async def list_patterns(
    pattern_types: Optional[List[PatternType]] = Query(
        None, description="Filter by pattern types"
    ),
    min_severity: Optional[PatternSeverity] = Query(
        None, description="Filter by minimum severity"
    ),
    enabled_only: bool = Query(True, description="Show only enabled patterns"),
    current_user: User = Depends(get_current_user),
):
    """
    Get all available pattern signatures

    - **pattern_types**: Filter by pattern types
    - **min_severity**: Filter by minimum severity level
    - **enabled_only**: Show only enabled patterns
    """

    try:
        patterns = pattern_library.get_all_patterns()

        # Apply filters
        filtered_patterns = []

        for pattern in patterns.values():
            # Filter by pattern type
            if pattern_types and pattern.pattern_type not in pattern_types:
                continue

            # Filter by severity
            if min_severity and pattern.severity.value < min_severity.value:
                continue

            # Filter by enabled status
            if enabled_only and not pattern.enabled:
                continue

            filtered_patterns.append(pattern)

        # Sort by severity and name
        severity_order = {
            PatternSeverity.SEVERE: 5,
            PatternSeverity.CRITICAL: 4,
            PatternSeverity.HIGH: 3,
            PatternSeverity.MEDIUM: 2,
            PatternSeverity.LOW: 1,
        }

        filtered_patterns.sort(
            key=lambda p: (severity_order.get(p.severity, 0), p.name)
        )

        return filtered_patterns

    except Exception as e:
        logger.error(f"Error listing patterns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list patterns",
        )


@router.get("/patterns/{pattern_id}", response_model=PatternSignature)
async def get_pattern_details(
    pattern_id: str, current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific pattern

    - **pattern_id**: Pattern identifier
    """

    try:
        pattern = pattern_library.get_pattern(pattern_id)
        if not pattern:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pattern with ID {pattern_id} not found",
            )

        return pattern

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pattern details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get pattern details",
        )


@router.put("/patterns/{pattern_id}/enable")
async def enable_pattern(
    pattern_id: str,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_analysis"])),
):
    """
    Enable a pattern for detection

    - **pattern_id**: Pattern identifier

    *Requires write analysis permission*
    """

    try:
        success = pattern_library.enable_pattern(pattern_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pattern with ID {pattern_id} not found",
            )

        return {"message": f"Pattern {pattern_id} enabled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling pattern: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enable pattern",
        )


@router.put("/patterns/{pattern_id}/disable")
async def disable_pattern(
    pattern_id: str,
    current_user: User = Depends(check_permissions(PERMISSIONS["write_analysis"])),
):
    """
    Disable a pattern for detection

    - **pattern_id**: Pattern identifier

    *Requires write analysis permission*
    """

    try:
        success = pattern_library.disable_pattern(pattern_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pattern with ID {pattern_id} not found",
            )

        return {"message": f"Pattern {pattern_id} disabled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling pattern: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable pattern",
        )


@router.get("/statistics", response_model=PatternStatistics)
async def get_pattern_statistics(
    current_user: User = Depends(check_permissions(PERMISSIONS["view_analytics"])),
):
    """
    Get pattern detection system statistics

    Returns statistics about pattern detection performance and metrics

    *Requires analytics permission*
    """

    try:
        # Get detector metrics
        detector_metrics = pattern_detector.get_metrics()

        # Get library statistics
        library_stats = pattern_library.get_pattern_statistics()

        # Get database statistics
        db_stats = await _get_database_statistics()

        return PatternStatistics(
            total_patterns=library_stats["total_patterns"],
            enabled_patterns=library_stats["enabled_patterns"],
            total_detections_24h=db_stats.get("total_detections_24h", 0),
            total_detections_7d=db_stats.get("total_detections_7d", 0),
            high_risk_detections_24h=db_stats.get("high_risk_detections_24h", 0),
            avg_confidence_24h=db_stats.get("avg_confidence_24h", 0.0),
            most_detected_pattern=db_stats.get("most_detected_pattern"),
            pattern_accuracy=db_stats.get("pattern_accuracy", {}),
            processing_performance=detector_metrics,
            generated_at=datetime.now(timezone.utc),
        )

    except Exception as e:
        logger.error(f"Error getting pattern statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get pattern statistics",
        )


@router.post("/clear-cache")
async def clear_pattern_cache(
    current_user: User = Depends(check_permissions(PERMISSIONS["admin_full"])),
):
    """
    Clear the pattern detection cache

    *Requires admin system permission*
    """

    try:
        pattern_detector.clear_cache()
        return {"message": "Pattern detection cache cleared successfully"}

    except Exception as e:
        logger.error(f"Error clearing pattern cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear pattern cache",
        )


@router.get("/metrics")
async def get_pattern_metrics(
    current_user: User = Depends(check_permissions(PERMISSIONS["view_analytics"])),
):
    """
    Get detailed pattern detection metrics

    *Requires analytics permission*
    """

    try:
        metrics = pattern_detector.get_metrics()
        return metrics

    except Exception as e:
        logger.error(f"Error getting pattern metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get pattern metrics",
        )


# Helper functions


async def _get_database_statistics() -> Dict[str, Any]:
    """Get pattern detection statistics from database"""

    queries = {
        "total_detections_24h": """
            SELECT COUNT(*) FROM pattern_detections 
            WHERE analysis_timestamp > NOW() - INTERVAL '24 hours'
        """,
        "total_detections_7d": """
            SELECT COUNT(*) FROM pattern_detections 
            WHERE analysis_timestamp > NOW() - INTERVAL '7 days'
        """,
        "high_risk_detections_24h": """
            SELECT COUNT(*) FROM pattern_detections 
            WHERE analysis_timestamp > NOW() - INTERVAL '24 hours'
            AND confidence_score >= 0.7
        """,
        "avg_confidence_24h": """
            SELECT AVG(confidence_score) FROM pattern_detections 
            WHERE analysis_timestamp > NOW() - INTERVAL '24 hours'
            AND detected = TRUE
        """,
        "most_detected_pattern": """
            SELECT pattern_id, COUNT(*) as count
            FROM pattern_detections 
            WHERE analysis_timestamp > NOW() - INTERVAL '24 hours'
            AND detected = TRUE
            GROUP BY pattern_id
            ORDER BY count DESC
            LIMIT 1
        """,
    }

    conn = await get_postgres_connection()
    try:
        stats = {}

        # Total detections (24h)
        stats["total_detections_24h"] = await conn.fetchval(
            queries["total_detections_24h"]
        )

        # Total detections (7d)
        stats["total_detections_7d"] = await conn.fetchval(
            queries["total_detections_7d"]
        )

        # High risk detections (24h)
        stats["high_risk_detections_24h"] = await conn.fetchval(
            queries["high_risk_detections_24h"]
        )

        # Average confidence (24h)
        avg_confidence = await conn.fetchval(queries["avg_confidence_24h"])
        stats["avg_confidence_24h"] = float(avg_confidence) if avg_confidence else 0.0

        # Most detected pattern
        most_detected = await conn.fetchrow(queries["most_detected_pattern"])
        stats["most_detected_pattern"] = (
            most_detected["pattern_id"] if most_detected else None
        )

        # Pattern accuracy (placeholder - would come from metrics table)
        stats["pattern_accuracy"] = {}

        return stats

    except Exception as e:
        logger.error(f"Error getting database statistics: {e}")
        return {}
    finally:
        await conn.close()
