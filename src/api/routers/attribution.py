"""
Jackdaw Sentry - Attribution API Router
REST endpoints for entity attribution and VASP screening
"""

import logging
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import APIRouter
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
from src.attribution import VASP
from src.attribution import AttributionRequest
from src.attribution import AttributionResult
from src.attribution import AttributionSearchFilters
from src.attribution import EntityType
from src.attribution import RiskLevel
from src.attribution import VASPResult
from src.attribution import get_attribution_engine
from src.attribution import get_vasp_registry

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize engines
attribution_engine = get_attribution_engine()
vasp_registry = get_vasp_registry()


# Pydantic models for API requests/responses
class VASPSearchRequest(BaseModel):
    query: Optional[str] = None
    entity_types: Optional[List[EntityType]] = None
    risk_levels: Optional[List[RiskLevel]] = None
    jurisdictions: Optional[List[str]] = None
    min_reliability: float = 0.0
    supported_blockchains: Optional[List[str]] = None

    @field_validator("min_reliability")
    @classmethod
    def validate_min_reliability(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("min_reliability must be between 0.0 and 1.0")
        return v


class AddressAttributionRequest(BaseModel):
    addresses: List[str]
    blockchain: str
    include_evidence: bool = True
    include_sources: bool = True
    min_confidence: float = 0.5

    @field_validator("addresses")
    @classmethod
    def validate_addresses(cls, v):
        # Filter first, then validate
        cleaned = [addr.strip().lower() for addr in v if addr.strip()]
        if not cleaned:
            raise ValueError("At least one address must be provided")
        return cleaned

    @field_validator("blockchain")
    @classmethod
    def validate_blockchain(cls, v):
        if not v or not v.strip():
            raise ValueError("Blockchain cannot be empty")
        return v.strip().lower()

    @field_validator("min_confidence")
    @classmethod
    def validate_min_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("min_confidence must be between 0.0 and 1.0")
        return v


class BatchAttributionResponse(BaseModel):
    results: Dict[str, AttributionResult]
    total_addresses: int
    successful_attributions: int
    failed_addresses: List[str]
    processing_time_ms: float


# API Endpoints


@router.get("/vasp-search", response_model=List[VASPResult])
async def search_vasps(
    query: Optional[str] = Query(
        None, description="Search query for VASP name or description"
    ),
    entity_types: Optional[List[EntityType]] = Query(
        None, description="Filter by entity types"
    ),
    risk_levels: Optional[List[RiskLevel]] = Query(
        None, description="Filter by risk levels"
    ),
    jurisdictions: Optional[List[str]] = Query(
        None, description="Filter by jurisdictions"
    ),
    min_reliability: float = Query(
        0.0, ge=0.0, le=1.0, description="Minimum reliability score"
    ),
    supported_blockchains: Optional[List[str]] = Query(
        None, description="Filter by supported blockchains"
    ),
    current_user: User = Depends(get_current_user),
):
    """
    Search VASP registry with filters

    - **query**: Search term for VASP name or description
    - **entity_types**: Filter by entity types (exchange, mixer, defi, etc.)
    - **risk_levels**: Filter by risk levels (low, medium, high, critical)
    - **jurisdictions**: Filter by jurisdictions
    - **min_reliability**: Minimum reliability score (0.0-1.0)
    - **supported_blockchains**: Filter by supported blockchains
    """

    try:
        # Build search filters
        filters = AttributionSearchFilters(
            entity_types=entity_types,
            risk_levels=risk_levels,
            jurisdictions=jurisdictions,
            min_reliability=min_reliability,
            supported_blockchains=supported_blockchains,
        )

        # Search VASPs
        vasps = await vasp_registry.search_vasps(query=query, filters=filters)

        # Get attribution counts in batch to avoid N+1 queries
        if vasps:
            vasp_ids = [vasp.id for vasp in vasps]
            attribution_counts = await _get_vasp_attribution_counts_batch(vasp_ids)
        else:
            attribution_counts = {}

        # Convert to VASPResult format
        results = []
        for vasp in vasps:
            attribution_count = attribution_counts.get(vasp.id, 0)

            vasp_result = VASPResult(
                vasp=vasp,
                attribution_count=attribution_count,
                risk_factors=_get_vasp_risk_factors(vasp),
            )
            results.append(vasp_result)

        return results

    except Exception as e:
        logger.error(f"Error searching VASPs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search VASP registry",
        )


@router.get("/vasp/{vasp_id}", response_model=VASP)
async def get_vasp_details(
    vasp_id: int, current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific VASP

    - **vasp_id**: VASP database ID
    """

    try:
        vasp = await vasp_registry.get_vasp_by_id(vasp_id)
        if not vasp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"VASP with ID {vasp_id} not found",
            )

        return vasp

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting VASP details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get VASP details",
        )


@router.post("/attribute-address", response_model=AttributionResult)
async def attribute_address(
    request: AddressAttributionRequest, current_user: User = Depends(get_current_user)
):
    """
    Attribute a single address with confidence scoring

    - **addresses**: List of addresses to attribute (single address expected)
    - **blockchain**: Blockchain name (bitcoin, ethereum, etc.)
    - **include_evidence**: Include supporting evidence in response
    - **include_sources**: Include attribution sources in response
    - **min_confidence**: Minimum confidence threshold (0.0-1.0)
    """

    if len(request.addresses) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint accepts only one address. Use /attribute-batch for multiple addresses.",
        )

    try:
        # Ensure attribution engine is initialized
        await attribution_engine.initialize()

        # Attribute the address
        result = await attribution_engine.attribute_address(
            address=request.addresses[0],
            blockchain=request.blockchain,
            include_evidence=request.include_evidence,
            min_confidence=request.min_confidence,
        )

        # Filter sources if not requested
        if not request.include_sources:
            result = result.model_copy(deep=True)
            result.sources = []

        return result

    except Exception as e:
        logger.error(f"Error attributing address: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to attribute address",
        )


@router.post("/attribute-batch", response_model=BatchAttributionResponse)
async def batch_attribute_addresses(
    request: AddressAttributionRequest,
    current_user: User = Depends(check_permissions(PERMISSIONS["bulk_screening"])),
):
    """
    Attribute multiple addresses in batch

    - **addresses**: List of addresses to attribute (max 1000)
    - **blockchain**: Blockchain name (bitcoin, ethereum, etc.)
    - **include_evidence**: Include supporting evidence in response
    - **include_sources**: Include attribution sources in response
    - **min_confidence**: Minimum confidence threshold (0.0-1.0)

    *Requires bulk screening permission*
    """

    if len(request.addresses) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 1000 addresses allowed per batch",
        )

    try:
        # Ensure attribution engine is initialized
        await attribution_engine.initialize()

        start_time = datetime.now(timezone.utc)

        # Process batch attribution
        results = await attribution_engine.batch_attribute_addresses(request)

        # Calculate statistics
        successful_count = len(results)
        failed_addresses = [addr for addr in request.addresses if addr not in results]
        processing_time = (
            datetime.now(timezone.utc) - start_time
        ).total_seconds() * 1000

        # Filter sources if not requested
        if not request.include_sources:
            for address, result in results.items():
                results[address] = result.model_copy(deep=True)
                results[address].sources = []

        return BatchAttributionResponse(
            results=results,
            total_addresses=len(request.addresses),
            successful_attributions=successful_count,
            failed_addresses=failed_addresses,
            processing_time_ms=processing_time,
        )

    except Exception as e:
        logger.error(f"Error in batch attribution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process batch attribution",
        )


@router.get("/attribution-sources")
async def get_attribution_sources(current_user: User = Depends(get_current_user)):
    """
    Get all attribution sources with reliability scores

    Returns list of attribution sources used for address classification
    """

    try:
        sources = await vasp_registry.get_attribution_sources()
        return sources

    except Exception as e:
        logger.error(f"Error getting attribution sources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get attribution sources",
        )


@router.get("/statistics")
async def get_attribution_statistics(
    current_user: User = Depends(check_permissions(PERMISSIONS["view_analytics"])),
):
    """
    Get attribution system statistics

    Returns statistics about the attribution system including:
    - Total VASPs in registry
    - Total attributions
    - Attribution accuracy metrics
    - Source reliability statistics

    *Requires analytics permission*
    """

    try:
        # Get VASP statistics
        vasp_stats = await _get_vasp_statistics()

        # Get attribution statistics
        attribution_stats = await _get_attribution_statistics()

        # Get source statistics
        source_stats = await _get_source_statistics()

        return {
            "vasp_registry": vasp_stats,
            "attributions": attribution_stats,
            "sources": source_stats,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting attribution statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get attribution statistics",
        )


# Helper functions


async def _get_vasp_attribution_counts_batch(vasp_ids: List[int]) -> Dict[int, int]:
    """Get attribution counts for multiple VASPs in a single batch query"""
    if not vasp_ids:
        return {}

    # Create IN clause placeholders
    placeholders = ", ".join([f"${i+1}" for i in range(len(vasp_ids))])

    query = f"""
    SELECT vasp_id, COUNT(*) as attribution_count
    FROM address_attributions
    WHERE vasp_id IN ({placeholders})
    GROUP BY vasp_id
    """

    conn = await get_postgres_connection()
    try:
        rows = await conn.fetch(query, *vasp_ids)
        return {row["vasp_id"]: row["attribution_count"] for row in rows}
    except Exception as e:
        logger.error(f"Error getting batch VASP attribution counts: {e}")
        return {}
    finally:
        await conn.close()


async def _get_vasp_attribution_count(vasp_id: int) -> int:
    """Get number of attributions for a VASP"""

    query = "SELECT COUNT(*) FROM address_attributions WHERE vasp_id = $1"
    conn = await get_postgres_connection()

    try:
        count = await conn.fetchval(query, vasp_id)
        return count or 0
    except Exception as e:
        logger.error(f"Error getting VASP attribution count: {e}")
        return 0
    finally:
        await conn.close()


def _get_vasp_risk_factors(vasp: VASP) -> List[str]:
    """Get risk factors for a VASP"""

    risk_factors = []

    # Entity type risk factors
    if vasp.entity_type == EntityType.MIXER:
        risk_factors.append("Privacy mixer - high money laundering risk")
    elif vasp.entity_type == EntityType.DEFI:
        risk_factors.append("DeFi protocol - limited KYC/AML")
    elif vasp.entity_type == EntityType.GAMBLING:
        risk_factors.append("Gambling platform - high-risk jurisdiction")

    # Risk level factors
    if vasp.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.SEVERE]:
        risk_factors.append(f"High risk classification: {vasp.risk_level.value}")

    # Compliance factors
    if not vasp.compliance_program:
        risk_factors.append("No known compliance program")

    if not vasp.regulatory_licenses:
        risk_factors.append("No regulatory licenses identified")

    # Jurisdiction factors
    high_risk_jurisdictions = ["unknown", "offshore"]
    if any(jur.lower() in high_risk_jurisdictions for jur in vasp.jurisdictions):
        risk_factors.append("High-risk jurisdiction")

    return risk_factors


async def _get_vasp_statistics() -> Dict[str, Any]:
    """Get VASP registry statistics"""

    queries = {
        "total_vasps": "SELECT COUNT(*) FROM vasp_registry",
        "by_entity_type": "SELECT entity_type, COUNT(*) FROM vasp_registry GROUP BY entity_type",
        "by_risk_level": "SELECT risk_level, COUNT(*) FROM vasp_registry GROUP BY risk_level",
        "by_jurisdiction": "SELECT jsonb_array_elements_text(jurisdictions) as jur, COUNT(*) FROM vasp_registry GROUP BY jur",
    }

    conn = await get_postgres_connection()
    try:
        stats = {}

        # Total VASPs
        stats["total"] = await conn.fetchval(queries["total_vasps"])

        # By entity type
        entity_rows = await conn.fetch(queries["by_entity_type"])
        stats["by_entity_type"] = {
            row["entity_type"]: row["count"] for row in entity_rows
        }

        # By risk level
        risk_rows = await conn.fetch(queries["by_risk_level"])
        stats["by_risk_level"] = {row["risk_level"]: row["count"] for row in risk_rows}

        # By jurisdiction
        jur_rows = await conn.fetch(queries["by_jurisdiction"])
        stats["by_jurisdiction"] = {row["jur"]: row["count"] for row in jur_rows}

        return stats

    except Exception as e:
        logger.error(f"Error getting VASP statistics: {e}")
        return {}
    finally:
        await conn.close()


async def _get_attribution_statistics() -> Dict[str, Any]:
    """Get attribution statistics"""

    queries = {
        "total_attributions": "SELECT COUNT(*) FROM address_attributions",
        "by_blockchain": "SELECT blockchain, COUNT(*) FROM address_attributions GROUP BY blockchain",
        "by_confidence": "SELECT AVG(confidence_score), MIN(confidence_score), MAX(confidence_score) FROM address_attributions",
        "by_status": "SELECT verification_status, COUNT(*) FROM address_attributions GROUP BY verification_status",
        "recent_attributions": "SELECT COUNT(*) FROM address_attributions WHERE created_at > NOW() - INTERVAL '30 days'",
    }

    conn = await get_postgres_connection()
    try:
        stats = {}

        # Total attributions
        stats["total"] = await conn.fetchval(queries["total_attributions"])

        # By blockchain
        blockchain_rows = await conn.fetch(queries["by_blockchain"])
        stats["by_blockchain"] = {
            row["blockchain"]: row["count"] for row in blockchain_rows
        }

        # Confidence statistics
        confidence_row = await conn.fetchrow(queries["by_confidence"])
        stats["confidence"] = {
            "average": float(confidence_row["avg"]) if confidence_row["avg"] else 0.0,
            "minimum": float(confidence_row["min"]) if confidence_row["min"] else 0.0,
            "maximum": float(confidence_row["max"]) if confidence_row["max"] else 0.0,
        }

        # By verification status
        status_rows = await conn.fetch(queries["by_status"])
        stats["by_status"] = {
            row["verification_status"]: row["count"] for row in status_rows
        }

        # Recent attributions
        stats["recent_30_days"] = await conn.fetchval(queries["recent_attributions"])

        return stats

    except Exception as e:
        logger.error(f"Error getting attribution statistics: {e}")
        return {}
    finally:
        await conn.close()


async def _get_source_statistics() -> Dict[str, Any]:
    """Get attribution source statistics"""

    query = """
    SELECT source_type, COUNT(*) as count, AVG(reliability_score) as avg_reliability
    FROM attribution_sources
    GROUP BY source_type
    ORDER BY count DESC
    """

    conn = await get_postgres_connection()
    try:
        rows = await conn.fetch(query)
        return {
            row["source_type"]: {
                "count": row["count"],
                "average_reliability": (
                    float(row["avg_reliability"]) if row["avg_reliability"] else 0.0
                ),
            }
            for row in rows
        }
    except Exception as e:
        logger.error(f"Error getting source statistics: {e}")
        return {}
    finally:
        await conn.close()
