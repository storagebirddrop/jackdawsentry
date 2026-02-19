"""
Jackdaw Sentry - Bulk Data API (M16)

Batch address screening, CSV export, and contract analysis endpoints.
Prefix: /api/v1/bulk
"""

import csv
import io
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from src.api.auth import User, get_current_user, check_permissions, PERMISSIONS

router = APIRouter()

_MAX_BULK = 500


class BulkScreenRequest(BaseModel):
    addresses: List[str]
    chain: str = "ethereum"
    include_sanctions: bool = True

    @field_validator("addresses")
    @classmethod
    def validate_addresses(cls, v: List[str]) -> List[str]:
        v = [a.strip() for a in v if a.strip()]
        if not v:
            raise ValueError("addresses list must not be empty")
        if len(v) > _MAX_BULK:
            raise ValueError(f"addresses list must not exceed {_MAX_BULK} items")
        return v


class ContractAnalyzeRequest(BaseModel):
    calldata: str
    contract_address: str
    chain: str = "ethereum"
    bytecode_size: Optional[int] = None


@router.post("/screen")
async def bulk_screen_addresses(
    request: BulkScreenRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_analysis"]])),
):
    """Screen up to 500 addresses for VASP matches in a single request."""
    from src.compliance.travel_rule import lookup_vasp

    results = []
    for addr in request.addresses:
        vasp = lookup_vasp(addr) if request.include_sanctions else None
        results.append({
            "address": addr,
            "chain": request.chain,
            "vasp_match": vasp,
            "screened": True,
        })

    return {
        "success": True,
        "chain": request.chain,
        "screened_count": len(results),
        "results": results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/screen/export")
async def export_bulk_screen_csv(
    request: BulkScreenRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_analysis"]])),
):
    """Screen addresses and stream results as a CSV download."""
    from src.compliance.travel_rule import lookup_vasp

    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=["address", "chain", "vasp_name", "vasp_jurisdiction", "screened"],
    )
    writer.writeheader()

    for addr in request.addresses:
        vasp = lookup_vasp(addr) if request.include_sanctions else None
        writer.writerow({
            "address": addr,
            "chain": request.chain,
            "vasp_name": vasp["name"] if vasp else "",
            "vasp_jurisdiction": vasp["jurisdiction"] if vasp else "",
            "screened": "true",
        })

    buffer.seek(0)
    filename = f"bulk_screen_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/analyze/contract")
async def analyze_contract(
    request: ContractAnalyzeRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_analysis"]])),
):
    """Decode and classify a smart contract interaction from calldata."""
    from src.analysis.smart_contract_analyzer import classify_contract, analyze_nft_transfer

    classification = classify_contract(
        request.calldata,
        bytecode_size=request.bytecode_size,
    )
    nft_details = analyze_nft_transfer(
        request.calldata,
        request.contract_address,
        request.chain,
    )
    return {
        "success": True,
        "contract": request.contract_address,
        "chain": request.chain,
        "classification": classification,
        "nft": nft_details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/stats")
async def bulk_api_stats(current_user: User = Depends(get_current_user)):
    """Return bulk API limits and available features."""
    return {
        "success": True,
        "max_addresses_per_request": _MAX_BULK,
        "supported_chains": [
            "ethereum", "bitcoin", "polygon", "solana", "tron", "xrpl",
            "arbitrum", "optimism", "bnb_chain", "avalanche",
        ],
        "features": ["screen", "export_csv", "contract_analysis"],
    }
