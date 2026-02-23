"""
Jackdaw Sentry - Entity Attribution Router (M11)
Endpoints for entity lookup, search, and label sync management.
"""

import logging
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from pydantic import BaseModel

from src.api.auth import PERMISSIONS
from src.api.auth import User
from src.api.auth import check_permissions
from src.api.auth import require_admin
from src.services.entity_attribution import get_entity_counts
from src.services.entity_attribution import get_entity_details
from src.services.entity_attribution import get_sync_status
from src.services.entity_attribution import lookup_address
from src.services.entity_attribution import lookup_addresses_bulk
from src.services.entity_attribution import search_entities
from src.services.entity_attribution import sync_all_labels

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------


class BulkLookupRequest(BaseModel):
    addresses: List[str]
    blockchain: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/lookup")
async def entity_lookup(
    address: str = Query(..., description="Blockchain address to look up"),
    blockchain: Optional[str] = Query(None, description="Blockchain filter"),
    current_user: User = Depends(check_permissions([PERMISSIONS["read_analysis"]])),
):
    """Look up entity attribution for a single address."""
    result = await lookup_address(address, blockchain)
    return {
        "success": True,
        "address": address,
        "blockchain": blockchain,
        "entity": result,
        "found": result is not None,
    }


@router.post("/lookup")
async def entity_bulk_lookup(
    request: BulkLookupRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_analysis"]])),
):
    """Bulk entity lookup for multiple addresses."""
    if len(request.addresses) > 500:
        raise HTTPException(status_code=400, detail="Maximum 500 addresses per request")

    results = await lookup_addresses_bulk(request.addresses, request.blockchain)
    return {
        "success": True,
        "results": results,
        "found_count": len(results),
        "total_queried": len(request.addresses),
    }


@router.get("/search")
async def entity_search(
    q: str = Query(..., min_length=1, description="Search query"),
    type: Optional[str] = Query(None, description="Filter by entity type"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(check_permissions([PERMISSIONS["read_analysis"]])),
):
    """Search entities by name or address."""
    results = await search_entities(q, entity_type=type, limit=limit)
    return {
        "success": True,
        "results": results,
        "count": len(results),
        "query": q,
    }


@router.get("/{entity_id}")
async def get_entity(
    entity_id: str,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_analysis"]])),
):
    """Get full entity details with all associated addresses."""
    result = await get_entity_details(entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Entity not found")
    return {"success": True, "entity": result}


@router.post("/sync")
async def trigger_sync(
    current_user: User = Depends(require_admin),
):
    """Trigger a manual entity label sync. Admin only."""
    results = await sync_all_labels(requested_by=current_user.username)
    return {
        "success": True,
        "results": results,
    }


@router.get("/sync/status")
async def sync_status(
    current_user: User = Depends(check_permissions([PERMISSIONS["read_analysis"]])),
):
    """Get label source sync status."""
    status = await get_sync_status()
    counts = await get_entity_counts()
    return {
        "success": True,
        "sources": status,
        "address_counts": counts,
    }
