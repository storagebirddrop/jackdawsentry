"""
Jackdaw Sentry — Risk Configuration API (M14)

CRUD endpoints for ML risk model weights and custom alert rules.

Endpoints
─────────
GET    /risk-config/weights              list all feature weights
PATCH  /risk-config/weights/{feature}   update a single weight
POST   /risk-config/weights/reset        reset all weights to defaults

GET    /risk-config/rules               list custom rules
POST   /risk-config/rules               create a custom rule
DELETE /risk-config/rules/{id}          delete a custom rule

POST   /risk-config/score               score an address with current weights
POST   /risk-config/deobfuscate         run mixer de-obfuscation on a tx list
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from src.api.auth import get_current_user, require_admin, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/risk-config", tags=["risk-config"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class WeightUpdate(BaseModel):
    weight: float

    @field_validator("weight")
    @classmethod
    def weight_in_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("weight must be between 0.0 and 1.0")
        return round(v, 6)


class CustomRuleCreate(BaseModel):
    name: str
    conditions: Dict[str, Any]
    risk_bump: float
    description: str = ""

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be empty")
        return v.strip()

    @field_validator("risk_bump")
    @classmethod
    def bump_in_range(cls, v: float) -> float:
        if not (0.0 < v <= 0.5):
            raise ValueError("risk_bump must be between 0.0 (exclusive) and 0.5")
        return round(v, 4)


class ScoreRequest(BaseModel):
    """Minimal address feature dict for on-demand scoring."""
    # Binary flags
    mixer_usage: bool = False
    privacy_tool_usage: bool = False
    cross_chain_activity: bool = False
    bridge_usage: bool = False
    # Count-based
    transaction_count: int = 0
    round_amount_transactions: int = 0
    off_peak_transactions: int = 0
    large_transactions: int = 0
    unique_counterparties: int = 0
    high_frequency_periods: int = 0
    # Optional entity context
    entity_type: Optional[str] = None
    risk_level: Optional[str] = None
    entity_name: Optional[str] = None


class DeobfuscateRequest(BaseModel):
    transactions: List[Dict[str, Any]]
    max_delay_hours: float = 72.0
    min_confidence: float = 0.40

    @field_validator("transactions")
    @classmethod
    def txs_not_empty(cls, v: List) -> List:
        if not v:
            raise ValueError("transactions list must not be empty")
        if len(v) > 1000:
            raise ValueError("maximum 1000 transactions per request")
        return v

    @field_validator("max_delay_hours")
    @classmethod
    def delay_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("max_delay_hours must be positive")
        return v

    @field_validator("min_confidence")
    @classmethod
    def conf_in_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("min_confidence must be in [0, 1]")
        return v


# ---------------------------------------------------------------------------
# Weight endpoints
# ---------------------------------------------------------------------------


@router.get("/weights", summary="List all ML risk feature weights")
async def list_weights(
    _: User = Depends(get_current_user),
) -> Dict[str, Any]:
    from src.analysis.ml_risk_model import list_weights as _list
    rows = await _list()
    return {"weights": rows, "count": len(rows)}


@router.patch("/weights/{feature_name}", summary="Update a single feature weight")
async def update_weight(
    feature_name: str,
    body: WeightUpdate,
    _: User = Depends(require_admin),
) -> Dict[str, Any]:
    from src.analysis.ml_risk_model import _DEFAULT_WEIGHTS, save_weight
    if feature_name not in _DEFAULT_WEIGHTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown feature '{feature_name}'. Valid features: {list(_DEFAULT_WEIGHTS)}",
        )
    await save_weight(feature_name, body.weight)
    return {"feature_name": feature_name, "weight": body.weight, "updated": True}


@router.post("/weights/reset", summary="Reset all feature weights to defaults")
async def reset_weights(
    _: User = Depends(require_admin),
) -> Dict[str, Any]:
    from src.analysis.ml_risk_model import _DEFAULT_WEIGHTS, save_weight
    for fname, (w, _desc) in _DEFAULT_WEIGHTS.items():
        await save_weight(fname, w)
    return {"reset": True, "features_reset": len(_DEFAULT_WEIGHTS)}


# ---------------------------------------------------------------------------
# Custom rule endpoints
# ---------------------------------------------------------------------------


@router.get("/rules", summary="List custom risk rules")
async def list_rules(
    _: User = Depends(get_current_user),
) -> Dict[str, Any]:
    from src.analysis.ml_risk_model import list_custom_rules
    rules = await list_custom_rules()
    return {"rules": rules, "count": len(rules)}


@router.post("/rules", status_code=status.HTTP_201_CREATED, summary="Create a custom risk rule")
async def create_rule(
    body: CustomRuleCreate,
    user: User = Depends(require_admin),
) -> Dict[str, Any]:
    from src.analysis.ml_risk_model import create_custom_rule
    rule = await create_custom_rule(
        name=body.name,
        conditions=body.conditions,
        risk_bump=body.risk_bump,
        description=body.description,
        created_by=user.username,
    )
    return rule


@router.delete("/rules/{rule_id}", summary="Delete a custom risk rule")
async def delete_rule(
    rule_id: str,
    _: User = Depends(require_admin),
) -> Dict[str, Any]:
    from src.analysis.ml_risk_model import delete_custom_rule
    try:
        deleted = await delete_custom_rule(rule_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid rule ID or delete failed: {exc}",
        )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found",
        )
    return {"deleted": True, "rule_id": rule_id}


# ---------------------------------------------------------------------------
# On-demand scoring
# ---------------------------------------------------------------------------


@router.post("/score", summary="Score an address feature vector with current weights")
async def score_address(
    body: ScoreRequest,
    _: User = Depends(get_current_user),
) -> Dict[str, Any]:
    from src.analysis.ml_risk_model import compute_ml_risk_score

    # Build entity_info if any entity fields are set
    entity_info: Optional[Dict[str, Any]] = None
    if body.entity_type or body.risk_level:
        entity_info = {
            "entity_type": body.entity_type,
            "risk_level": body.risk_level,
            "entity_name": body.entity_name,
        }

    result = await compute_ml_risk_score(
        address_features=body,
        entity_info=entity_info,
    )
    return result


# ---------------------------------------------------------------------------
# Mixer de-obfuscation
# ---------------------------------------------------------------------------


@router.post("/deobfuscate", summary="Run mixer de-obfuscation on a transaction list")
async def deobfuscate_transactions(
    body: DeobfuscateRequest,
    _: User = Depends(get_current_user),
) -> Dict[str, Any]:
    from src.analysis.mixer_deobfuscator import (
        build_mixer_transactions,
        find_candidate_pairs,
        summarize_deobfuscation,
    )

    mixer_txs = build_mixer_transactions(body.transactions)
    if not mixer_txs:
        return {
            "candidate_pairs": [],
            "total_pairs": 0,
            "high_confidence_pairs": 0,
            "note": "No mixer deposits or withdrawals identified in the provided transactions.",
        }

    pairs = find_candidate_pairs(
        mixer_txs,
        max_delay_hours=body.max_delay_hours,
        min_confidence=body.min_confidence,
    )
    return summarize_deobfuscation(pairs)
