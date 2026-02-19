"""
Jackdaw Sentry — Cross-Chain Tracing API (M13)

Endpoints:
  POST /api/v1/tracing/trace         trace funds from an address through bridges/DEXes
  POST /api/v1/tracing/decode        decode a transaction as a DeFi interaction
  POST /api/v1/tracing/decode/bulk   bulk decode multiple transactions
  GET  /api/v1/tracing/protocols     list known protocols from the registry
  GET  /api/v1/tracing/protocols/{name}  get a single protocol
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from src.api.auth import User, check_permissions, PERMISSIONS
from src.analysis.defi_decoder import decode_transaction, decode_transactions_bulk
from src.analysis.protocol_registry import (
    classify_address,
    get_all_protocols,
    get_protocol_by_address,
    get_protocols_by_type,
    protocol_count,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_SUPPORTED_CHAINS = {
    "ethereum", "bitcoin", "polygon", "bsc", "arbitrum",
    "optimism", "avalanche", "solana", "tron", "xrpl",
    "base", "fantom", "xdai",
}


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class TraceRequest(BaseModel):
    address: str
    blockchain: str
    max_depth: int = 5
    time_range_hours: int = 24

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("address must not be empty")
        return v

    @field_validator("blockchain")
    @classmethod
    def validate_blockchain(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in _SUPPORTED_CHAINS:
            raise ValueError(f"unsupported blockchain '{v}'")
        return v

    @field_validator("max_depth")
    @classmethod
    def validate_depth(cls, v: int) -> int:
        if not 1 <= v <= 10:
            raise ValueError("max_depth must be between 1 and 10")
        return v


class DecodeRequest(BaseModel):
    to_address: str
    input_data: Optional[str] = None
    blockchain: Optional[str] = None


class BulkDecodeRequest(BaseModel):
    transactions: List[Dict[str, Any]]

    @field_validator("transactions")
    @classmethod
    def validate_txs(cls, v):
        if not v:
            raise ValueError("transactions list must not be empty")
        if len(v) > 500:
            raise ValueError("maximum 500 transactions per request")
        return v


# ---------------------------------------------------------------------------
# Trace endpoint
# ---------------------------------------------------------------------------


@router.post("/trace")
async def trace_address(
    body: TraceRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_analysis"]])),
):
    """
    Trace funds from an address through bridges and DEX swaps.

    Uses the CrossChainAnalyzer + protocol registry to build a fund-flow
    graph showing where funds originated and where they ended up.
    """
    try:
        from src.analysis.cross_chain import CrossChainAnalyzer
        analyzer = CrossChainAnalyzer()
        analysis = await analyzer.get_cross_chain_analysis(
            body.address, time_range=body.time_range_hours
        )
    except Exception as exc:
        logger.warning(f"CrossChainAnalyzer failed for {body.address}: {exc}")
        analysis = {}

    # Classify the address itself against the protocol registry
    addr_classification = classify_address(body.address)

    return {
        "success": True,
        "address": body.address,
        "blockchain": body.blockchain,
        "address_classification": addr_classification,
        "cross_chain_analysis": analysis,
        "max_depth": body.max_depth,
    }


# ---------------------------------------------------------------------------
# Decode endpoints
# ---------------------------------------------------------------------------


@router.post("/decode")
async def decode_tx(
    body: DecodeRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_analysis"]])),
):
    """Decode a single transaction as a DeFi interaction."""
    result = decode_transaction(
        to_address=body.to_address,
        input_data=body.input_data,
        chain=body.blockchain,
    )
    return {"success": True, "decode": result}


@router.post("/decode/bulk")
async def decode_txs_bulk(
    body: BulkDecodeRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_analysis"]])),
):
    """Bulk-decode up to 500 transactions."""
    results = decode_transactions_bulk(body.transactions)
    return {
        "success": True,
        "count": len(results),
        "results": results,
    }


# ---------------------------------------------------------------------------
# Protocol registry endpoints
# ---------------------------------------------------------------------------


@router.get("/protocols")
async def list_protocols(
    protocol_type: Optional[str] = Query(None, description="Filter by type: bridge|dex|lending|staking|yield_farming|mixer|nft|payments"),
    current_user: User = Depends(check_permissions([PERMISSIONS["read_analysis"]])),
):
    """List all protocols in the registry (optionally filtered by type)."""
    if protocol_type:
        protocols = get_protocols_by_type(protocol_type)
    else:
        protocols = get_all_protocols()

    return {
        "success": True,
        "count": len(protocols),
        "total_in_registry": protocol_count(),
        "protocols": [_serialize_protocol(p) for p in protocols],
    }


@router.get("/protocols/address/{address}")
async def lookup_protocol_by_address(
    address: str,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_analysis"]])),
):
    """Look up a protocol by contract address."""
    proto = get_protocol_by_address(address)
    if not proto:
        raise HTTPException(status_code=404, detail="Address not found in protocol registry")
    return {"success": True, "protocol": _serialize_protocol(proto)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_protocol(p) -> Dict[str, Any]:
    return {
        "name": p.name,
        "protocol_type": p.protocol_type,
        "chains": p.chains,
        "risk_level": p.risk_level,
        "description": p.description,
        "website": p.website,
        "tags": p.tags,
        "address_count": sum(len(v) for v in p.addresses.values()),
    }
