"""
Jackdaw Sentry - Travel Rule Router (M16)

FATF Recommendation 16 / MiCA Article 83 compliance endpoints.
Prefix: /api/v1/travel-rule
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.api.auth import User, get_current_user, check_permissions, PERMISSIONS

router = APIRouter()


class TravelRuleCheckRequest(BaseModel):
    tx_hash: str
    originator_address: str
    beneficiary_address: str
    amount_usd: float
    originator_name: Optional[str] = None
    beneficiary_name: Optional[str] = None


class VaspValidateRequest(BaseModel):
    name: str = ""
    jurisdiction: str = ""
    lei: str = ""


@router.post("/check")
async def check_travel_rule(
    request: TravelRuleCheckRequest,
    current_user: User = Depends(check_permissions([PERMISSIONS["read_compliance"]])),
):
    """Check whether a transaction triggers the Travel Rule and assess compliance."""
    from src.compliance.travel_rule import build_travel_rule_record
    record = build_travel_rule_record(
        tx_hash=request.tx_hash,
        originator_address=request.originator_address,
        beneficiary_address=request.beneficiary_address,
        amount_usd=request.amount_usd,
        originator_name=request.originator_name,
        beneficiary_name=request.beneficiary_name,
    )
    return {"success": True, **record}


@router.get("/vasp/{address}")
async def lookup_vasp(
    address: str,
    current_user: User = Depends(get_current_user),
):
    """Look up known VASP information for an address."""
    from src.compliance.travel_rule import lookup_vasp as _lookup
    vasp = _lookup(address)
    if not vasp:
        raise HTTPException(status_code=404, detail="No known VASP for this address")
    return {"success": True, "address": address, "vasp": vasp}


@router.post("/vasp/validate")
async def validate_vasp(
    request: VaspValidateRequest,
    current_user: User = Depends(get_current_user),
):
    """Validate completeness of VASP information fields."""
    from src.compliance.travel_rule import validate_vasp_info
    errors = validate_vasp_info(request.model_dump())
    return {
        "success": True,
        "valid": len(errors) == 0,
        "errors": errors,
    }


@router.get("/threshold")
async def get_threshold(current_user: User = Depends(get_current_user)):
    """Return the current Travel Rule monetary threshold."""
    from src.compliance.travel_rule import _THRESHOLD_USD
    return {
        "success": True,
        "threshold_usd": _THRESHOLD_USD,
        "regulatory_basis": ["FATF Recommendation 16", "MiCA Article 83"],
    }
