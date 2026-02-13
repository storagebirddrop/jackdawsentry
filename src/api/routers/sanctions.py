"""
Jackdaw Sentry - Sanctions Screening Router (M9.4)
Screen addresses against OFAC SDN + EU Consolidated sanctions lists.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, validator
import logging

from src.api.auth import User, check_permissions, require_admin, PERMISSIONS
from src.services.sanctions import (
    screen_address,
    screen_addresses_bulk,
    log_screening,
    sync_all,
    get_sync_status,
    get_sanctioned_count,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request / Response models
# =============================================================================


class ScreenRequest(BaseModel):
    address: str
    blockchain: Optional[str] = None

    @validator("address")
    def validate_address(cls, v):
        if not v or not v.strip():
            raise ValueError("Address cannot be empty")
        return v.strip()

    @validator("blockchain", pre=True, always=True)
    def validate_blockchain(cls, v):
        return v.lower() if v else None


class BulkScreenRequest(BaseModel):
    addresses: List[str]
    blockchain: Optional[str] = None

    @validator("addresses")
    def validate_addresses(cls, v):
        cleaned = [a.strip() for a in (v or []) if a.strip()]
        if not cleaned:
            raise ValueError("At least one address required")
        if len(cleaned) > 100:
            raise ValueError("Maximum 100 addresses per bulk screen")
        return cleaned

    @validator("blockchain", pre=True, always=True)
    def validate_blockchain(cls, v):
        return v.lower() if v else None


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/screen")
async def screen_single(
    request: ScreenRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_blockchain"]])),
):
    """Screen a single address against all active sanctions lists."""
    try:
        result = await screen_address(request.address, request.blockchain)

        # Log the screening
        match_source = None
        match_entity = None
        if result["matched"] and result["matches"]:
            match_source = result["matches"][0].get("source")
            match_entity = result["matches"][0].get("entity_name")

        await log_screening(
            address=request.address,
            blockchain=request.blockchain,
            matched=result["matched"],
            match_source=match_source,
            match_entity=match_entity,
            user_id=getattr(current_user, 'id', None),
        )

        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now(timezone.utc),
        }
    except Exception as exc:
        logger.error(f"Sanctions screening failed: {exc}")
        raise HTTPException(status_code=500, detail="Screening failed")


@router.post("/screen/bulk")
async def screen_bulk(
    request: BulkScreenRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_blockchain"]])),
):
    """Screen multiple addresses in one request (max 100)."""
    try:
        results = await screen_addresses_bulk(
            request.addresses, request.blockchain
        )

        # Log each screening
        for r in results:
            match_source = None
            match_entity = None
            if r["matched"] and r["matches"]:
                match_source = r["matches"][0].get("source")
                match_entity = r["matches"][0].get("entity_name")
            await log_screening(
                address=r["address"],
                blockchain=request.blockchain,
                matched=r["matched"],
                match_source=match_source,
                match_entity=match_entity,
                user_id=getattr(current_user, 'id', None),
            )

        matched_count = sum(1 for r in results if r["matched"])
        return {
            "success": True,
            "total_screened": len(results),
            "total_matched": matched_count,
            "results": results,
            "timestamp": datetime.now(timezone.utc),
        }
    except Exception as exc:
        logger.error(f"Bulk sanctions screening failed: {exc}")
        raise HTTPException(status_code=500, detail="Bulk screening failed")


@router.get("/lookup/{address}")
async def lookup_address(
    address: str,
    blockchain: Optional[str] = None,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_blockchain"]])),
):
    """Look up a specific address in the sanctions database (no audit log)."""
    try:
        blockchain = blockchain.lower() if blockchain else None
        result = await screen_address(address.strip(), blockchain)
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now(timezone.utc),
        }
    except Exception as exc:
        logger.error(f"Sanctions lookup failed: {exc}")
        raise HTTPException(status_code=500, detail="Lookup failed")


@router.post("/sync")
async def trigger_sync(
    current_user: User = Depends(require_admin),
):
    """Trigger a manual sanctions sync (admin only).

    Downloads and parses OFAC SDN + EU Consolidated lists.
    """
    try:
        results = await sync_all(requested_by=current_user.username)
        return {
            "success": True,
            "sync_results": results,
            "timestamp": datetime.now(timezone.utc),
        }
    except Exception as exc:
        logger.error(f"Sanctions sync failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(exc)}")


@router.get("/status")
async def sanctions_status(
    current_user: User = Depends(check_permissions([PERMISSIONS["read_blockchain"]])),
):
    """Get sanctions database status: sync times, record counts."""
    try:
        sync_status = await get_sync_status()
        counts = await get_sanctioned_count()
        total = sum(counts.values())

        return {
            "success": True,
            "total_sanctioned_addresses": total,
            "counts_by_source": counts,
            "sync_status": sync_status,
            "timestamp": datetime.now(timezone.utc),
        }
    except Exception as exc:
        logger.error(f"Sanctions status failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(exc)}")


@router.get("/statistics")
async def sanctions_statistics(
    current_user: User = Depends(check_permissions([PERMISSIONS["read_blockchain"]])),
):
    """Summary statistics for the sanctions system."""
    try:
        counts = await get_sanctioned_count()
        sync_status = await get_sync_status()

        return {
            "success": True,
            "statistics": {
                "total_sanctioned": sum(counts.values()),
                "by_source": counts,
                "last_sync": {
                    s["source"]: {
                        "at": s.get("last_sync_at"),
                        "records": s.get("records_synced", 0),
                        "status": s.get("status", "unknown"),
                    }
                    for s in sync_status
                },
            },
            "timestamp": datetime.now(timezone.utc),
        }
    except Exception as exc:
        logger.error(f"Sanctions statistics failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Statistics failed: {str(exc)}")
