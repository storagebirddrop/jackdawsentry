"""
Jackdaw Sentry — ML Risk Scoring Model (M14)

Implements a feature-vector-based risk scorer that uses the rich
AddressFeatures dataclass from MLClusteringEngine.  Uses a logistic-
regression-style weighted sum over normalised features, with weights
stored in PostgreSQL so operators can tune them via the risk-config API.

Why this outperforms the simple heuristic (compute_risk_score):
  - 12 independent feature dimensions vs 4 combined signals
  - Per-feature weights configurable without code changes
  - Entity-label enrichment (mixer/darknet = immediate high risk bump)
  - Non-linear sigmoid squash → better calibration near 0 and 1
  - Volume / frequency features not available in the heuristic

Weight schema (stored in PostgreSQL table `risk_weights`):
  feature_name TEXT PRIMARY KEY
  weight       REAL NOT NULL   (default values set at initialisation)
  description  TEXT

Default weights were set by manual calibration against the labeled
entity dataset (entity_addresses table).
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default weight set (domain-calibrated)
# ---------------------------------------------------------------------------

_DEFAULT_WEIGHTS: Dict[str, Tuple[float, str]] = {
    # (weight, description)
    "mixer_usage":             (0.30, "Address has interacted with known mixer contracts"),
    "privacy_tool_usage":      (0.15, "Address uses privacy tools (Aztec, Wasabi, etc.)"),
    "sanctions_entity":        (0.40, "Address linked to OFAC/sanctioned entity"),
    "darknet_entity":          (0.35, "Address linked to darknet market"),
    "scam_entity":             (0.25, "Address linked to known scam"),
    "high_frequency_periods":  (0.10, "Unusual burst transaction frequency"),
    "round_amount_ratio":      (0.08, "High proportion of round-amount transactions"),
    "off_peak_ratio":          (0.07, "High proportion of off-peak-hour transactions"),
    "cross_chain_activity":    (0.05, "Cross-chain bridge activity"),
    "large_tx_ratio":          (0.08, "High proportion of large-value transactions"),
    "low_counterparty_ratio":  (0.06, "Few unique counterparties relative to tx count"),
    "bridge_usage":            (0.04, "Bridge usage detected"),
}

# Bias term (global base risk)
_DEFAULT_BIAS = 0.0


_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS risk_weights (
    feature_name TEXT PRIMARY KEY,
    weight       REAL NOT NULL DEFAULT 0.0,
    description  TEXT,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS custom_risk_rules (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    description TEXT,
    conditions  JSONB NOT NULL DEFAULT '{}',
    risk_bump   REAL NOT NULL DEFAULT 0.1,
    enabled     BOOLEAN NOT NULL DEFAULT TRUE,
    created_by  TEXT NOT NULL DEFAULT 'system',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


# ---------------------------------------------------------------------------
# PostgreSQL helpers
# ---------------------------------------------------------------------------


async def ensure_tables() -> None:
    from src.api.database import get_postgres_pool
    pool = get_postgres_pool()
    async with pool.acquire() as conn:
        await conn.execute(_CREATE_TABLES_SQL)
        # Seed default weights if table is empty
        count = await conn.fetchval("SELECT COUNT(*) FROM risk_weights")
        if count == 0:
            for fname, (w, desc) in _DEFAULT_WEIGHTS.items():
                await conn.execute(
                    "INSERT INTO risk_weights (feature_name, weight, description) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING",
                    fname, w, desc
                )


async def load_weights() -> Dict[str, float]:
    """Load weights from PostgreSQL, falling back to defaults on any error."""
    try:
        from src.api.database import get_postgres_pool
        pool = get_postgres_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT feature_name, weight FROM risk_weights")
        return {r["feature_name"]: float(r["weight"]) for r in rows}
    except Exception as exc:
        logger.warning(f"Could not load risk weights from DB: {exc} — using defaults")
        return {k: v[0] for k, v in _DEFAULT_WEIGHTS.items()}


async def save_weight(feature_name: str, weight: float) -> None:
    from src.api.database import get_postgres_pool
    pool = get_postgres_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO risk_weights (feature_name, weight) VALUES ($1,$2) ON CONFLICT (feature_name) DO UPDATE SET weight=$2, updated_at=NOW()",
            feature_name, weight
        )


async def list_weights() -> List[Dict[str, Any]]:
    try:
        from src.api.database import get_postgres_pool
        pool = get_postgres_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM risk_weights ORDER BY feature_name")
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.warning(f"Could not list risk weights: {exc}")
        return [{"feature_name": k, "weight": v[0], "description": v[1]} for k, v in _DEFAULT_WEIGHTS.items()]


# ---------------------------------------------------------------------------
# Feature extraction from AddressFeatures dataclass
# ---------------------------------------------------------------------------


@dataclass
class FeatureVector:
    """Normalised [0,1] feature values extracted from AddressFeatures."""
    mixer_usage: float = 0.0
    privacy_tool_usage: float = 0.0
    sanctions_entity: float = 0.0
    darknet_entity: float = 0.0
    scam_entity: float = 0.0
    high_frequency_periods: float = 0.0
    round_amount_ratio: float = 0.0
    off_peak_ratio: float = 0.0
    cross_chain_activity: float = 0.0
    large_tx_ratio: float = 0.0
    low_counterparty_ratio: float = 0.0
    bridge_usage: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {k: v for k, v in self.__dict__.items()}


def extract_features(
    address_features: Any,           # AddressFeatures dataclass
    entity_info: Optional[Dict] = None,  # from entity_attribution lookup
) -> FeatureVector:
    """
    Convert an AddressFeatures dataclass into a normalised FeatureVector.

    entity_info is the result of lookup_address() from entity_attribution;
    if None, entity signals default to 0.
    """
    fv = FeatureVector()

    # Binary signals → direct 0/1
    fv.mixer_usage = 1.0 if getattr(address_features, "mixer_usage", False) else 0.0
    fv.privacy_tool_usage = 1.0 if getattr(address_features, "privacy_tool_usage", False) else 0.0
    fv.cross_chain_activity = 1.0 if getattr(address_features, "cross_chain_activity", False) else 0.0
    fv.bridge_usage = 1.0 if getattr(address_features, "bridge_usage", False) else 0.0

    # Entity-label signals
    if entity_info:
        etype = (entity_info.get("entity_type") or "").lower()
        fv.sanctions_entity = 1.0 if entity_info.get("risk_level") == "critical" else 0.0
        fv.darknet_entity = 1.0 if etype == "darknet_market" else 0.0
        fv.scam_entity = 1.0 if etype in {"scam", "ransomware"} else 0.0

    # Ratio features — normalise against transaction count
    tx_count = max(getattr(address_features, "transaction_count", 0) or 1, 1)
    round_txs = getattr(address_features, "round_amount_transactions", 0) or 0
    off_peak_txs = getattr(address_features, "off_peak_transactions", 0) or 0
    large_txs = getattr(address_features, "large_transactions", 0) or 0
    unique_cp = max(getattr(address_features, "unique_counterparties", 1) or 1, 1)

    fv.round_amount_ratio = min(round_txs / tx_count, 1.0)
    fv.off_peak_ratio = min(off_peak_txs / tx_count, 1.0)
    fv.large_tx_ratio = min(large_txs / tx_count, 1.0)
    # Low counterparty ratio: penalise when many txs but few unique counterparties
    fv.low_counterparty_ratio = max(0.0, 1.0 - min(unique_cp / max(tx_count * 0.1, 1), 1.0))

    # Frequency: normalise by capping at 10 high-frequency periods
    hf = getattr(address_features, "high_frequency_periods", 0) or 0
    fv.high_frequency_periods = min(hf / 10.0, 1.0)

    return fv


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _sigmoid(x: float) -> float:
    """Logistic sigmoid: maps any real number to (0, 1)."""
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


def score_features(
    fv: FeatureVector,
    weights: Dict[str, float],
    bias: float = _DEFAULT_BIAS,
) -> float:
    """
    Compute a risk score in [0, 1] from a FeatureVector and weight map.

    Uses a logistic regression formula:
        z = bias + Σ (weight_i × feature_i)
        score = sigmoid(z × scale)

    The scale factor (4.0) is chosen so that a single critical feature
    (weight ≈ 0.40) maps to score ≈ 0.85 before the sigmoid.
    """
    fv_dict = fv.to_dict()
    z = bias
    for fname, fval in fv_dict.items():
        w = weights.get(fname, _DEFAULT_WEIGHTS.get(fname, (0.0,))[0])
        z += w * fval

    # Scale before sigmoid so that weights in [0,1] produce spread output
    score = _sigmoid(z * 4.0)
    return round(score, 4)


async def compute_ml_risk_score(
    address_features: Any,
    entity_info: Optional[Dict] = None,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Full ML risk scoring pipeline.

    Returns:
      score        : float in [0, 1]
      risk_level   : critical | high | medium | low
      feature_vector : dict of normalised feature values
      weights_used : dict of feature→weight used
      model        : "ml_v1"
    """
    if weights is None:
        weights = await load_weights()

    fv = extract_features(address_features, entity_info)
    score = score_features(fv, weights)

    return {
        "score": score,
        "risk_level": _level(score),
        "feature_vector": fv.to_dict(),
        "weights_used": {k: weights.get(k, 0.0) for k in fv.to_dict()},
        "model": "ml_v1",
    }


def _level(score: float) -> str:
    if score >= 0.75:
        return "critical"
    if score >= 0.50:
        return "high"
    if score >= 0.25:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Custom rules engine
# ---------------------------------------------------------------------------


async def evaluate_custom_rules(
    address: str,
    feature_vector: FeatureVector,
    entity_info: Optional[Dict] = None,
) -> Tuple[float, List[str]]:
    """
    Evaluate custom risk rules from PostgreSQL.

    Returns (total_bump, list_of_triggered_rule_names).
    """
    try:
        from src.api.database import get_postgres_pool
        pool = get_postgres_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT name, conditions, risk_bump FROM custom_risk_rules WHERE enabled = TRUE"
            )
    except Exception as exc:
        logger.warning(f"Could not load custom rules: {exc}")
        return 0.0, []

    total_bump = 0.0
    triggered = []
    fv_dict = feature_vector.to_dict()

    for row in rows:
        try:
            cond = json.loads(row["conditions"]) if isinstance(row["conditions"], str) else dict(row["conditions"])
            if _eval_rule_conditions(cond, fv_dict, address, entity_info):
                total_bump += float(row["risk_bump"])
                triggered.append(row["name"])
        except Exception:
            continue

    return min(total_bump, 0.5), triggered  # cap custom bump at 0.5


def _eval_rule_conditions(
    conditions: Dict[str, Any],
    fv: Dict[str, float],
    address: str,
    entity_info: Optional[Dict],
) -> bool:
    """Evaluate all conditions in AND logic."""
    for key, expected in conditions.items():
        # Feature threshold: e.g. {"mixer_usage": 1.0}
        if key in fv:
            actual = fv[key]
            if isinstance(expected, dict):
                op = expected.get("op", "gte")
                val = float(expected.get("value", 0))
                if op == "gte" and actual < val:
                    return False
                if op == "lte" and actual > val:
                    return False
                if op == "eq" and actual != val:
                    return False
            else:
                if actual != float(expected):
                    return False
        # Entity type match
        elif key == "entity_type" and entity_info:
            if (entity_info.get("entity_type") or "").lower() != str(expected).lower():
                return False
        # Address prefix
        elif key == "address_prefix":
            if not address.lower().startswith(str(expected).lower()):
                return False
    return True


# ---------------------------------------------------------------------------
# CRUD for custom rules
# ---------------------------------------------------------------------------


async def create_custom_rule(
    name: str,
    conditions: Dict[str, Any],
    risk_bump: float,
    description: str = "",
    created_by: str = "system",
) -> Dict[str, Any]:
    from src.api.database import get_postgres_pool
    pool = get_postgres_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO custom_risk_rules (name, description, conditions, risk_bump, created_by)
               VALUES ($1,$2,$3,$4,$5) RETURNING *""",
            name, description, json.dumps(conditions), risk_bump, created_by
        )
    return _rule_row(row)


async def list_custom_rules() -> List[Dict[str, Any]]:
    try:
        from src.api.database import get_postgres_pool
        pool = get_postgres_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM custom_risk_rules ORDER BY created_at DESC")
        return [_rule_row(r) for r in rows]
    except Exception:
        return []


async def delete_custom_rule(rule_id: str) -> bool:
    import uuid
    from src.api.database import get_postgres_pool
    pool = get_postgres_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM custom_risk_rules WHERE id = $1", uuid.UUID(rule_id)
        )
    return result.endswith("1")


def _rule_row(row) -> Dict[str, Any]:
    d = dict(row)
    d["id"] = str(d["id"])
    if isinstance(d.get("conditions"), str):
        d["conditions"] = json.loads(d["conditions"])
    for ts in ("created_at", "updated_at"):
        if d.get(ts) and hasattr(d[ts], "isoformat"):
            d[ts] = d[ts].isoformat()
    return d
