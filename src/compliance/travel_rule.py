"""
Jackdaw Sentry - Travel Rule Compliance Engine (M16)

Implements FATF Recommendation 16 and MiCA Article 83 requirements.
Checks whether a transaction requires VASP-to-VASP information transfer
and validates originator/beneficiary information completeness.
"""

from typing import Any
from typing import Dict
from typing import List
from typing import Optional

# FATF / MiCA threshold (USD equivalent)
_THRESHOLD_USD: float = 1000.0

# Simplified VASP registry: address prefix → VASP metadata
_VASP_REGISTRY: Dict[str, Dict[str, str]] = {
    "0x1111": {"name": "Coinbase", "jurisdiction": "US", "lei": "KGCEPHLVVKVRZYO1"},
    "0x2222": {"name": "Kraken", "jurisdiction": "US", "lei": "549300YFCPHG28AHLO95"},
    "0x3333": {"name": "Binance", "jurisdiction": "KY", "lei": "254900GS6WFIAX5GF683"},
    "0x4444": {"name": "Bitstamp", "jurisdiction": "GB", "lei": "8356007750DTD1WGHJ65"},
    "0x5555": {
        "name": "Kraken EU",
        "jurisdiction": "EU",
        "lei": "529900WGBVWHEP5IOP06",
    },
}


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def lookup_vasp(address: str) -> Optional[Dict[str, str]]:
    """Return VASP info for an address by prefix match, or None if unknown."""
    for prefix, info in _VASP_REGISTRY.items():
        if address.lower().startswith(prefix.lower()):
            return info
    return None


def requires_travel_rule(amount_usd: float) -> bool:
    """Return True if the amount meets or exceeds the Travel Rule threshold."""
    return amount_usd >= _THRESHOLD_USD


def _assess_compliance(
    triggered: bool,
    originator_vasp: Optional[Dict],
    beneficiary_vasp: Optional[Dict],
) -> str:
    if not triggered:
        return "not_required"
    if originator_vasp and beneficiary_vasp:
        return "compliant"
    if originator_vasp or beneficiary_vasp:
        return "partial"
    return "non_compliant"


def _missing_fields(
    triggered: bool,
    originator_name: Optional[str],
    beneficiary_name: Optional[str],
    originator_vasp: Optional[Dict],
    beneficiary_vasp: Optional[Dict],
) -> List[str]:
    if not triggered:
        return []
    missing: List[str] = []
    if not originator_name:
        missing.append("originator_name")
    if not originator_vasp:
        missing.append("originator_vasp")
    if not beneficiary_name:
        missing.append("beneficiary_name")
    if not beneficiary_vasp:
        missing.append("beneficiary_vasp")
    return missing


def build_travel_rule_record(
    tx_hash: str,
    originator_address: str,
    beneficiary_address: str,
    amount_usd: float,
    originator_name: Optional[str] = None,
    beneficiary_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a complete Travel Rule compliance record for a transaction."""
    originator_vasp = lookup_vasp(originator_address)
    beneficiary_vasp = lookup_vasp(beneficiary_address)
    triggered = requires_travel_rule(amount_usd)

    return {
        "tx_hash": tx_hash,
        "amount_usd": amount_usd,
        "threshold_usd": _THRESHOLD_USD,
        "travel_rule_required": triggered,
        "originator": {
            "address": originator_address,
            "name": originator_name,
            "vasp": originator_vasp,
        },
        "beneficiary": {
            "address": beneficiary_address,
            "name": beneficiary_name,
            "vasp": beneficiary_vasp,
        },
        "compliance_status": _assess_compliance(
            triggered, originator_vasp, beneficiary_vasp
        ),
        "missing_fields": _missing_fields(
            triggered,
            originator_name,
            beneficiary_name,
            originator_vasp,
            beneficiary_vasp,
        ),
    }


def validate_vasp_info(vasp_info: Dict[str, Any]) -> List[str]:
    """Validate VASP record completeness. Returns list of error strings."""
    errors: List[str] = []
    for field in ("name", "jurisdiction", "lei"):
        if not vasp_info.get(field, "").strip():
            errors.append(f"Missing required field: {field}")
    jurisdiction = vasp_info.get("jurisdiction", "")
    if jurisdiction and len(jurisdiction) > 3:
        errors.append("jurisdiction should be an ISO 3166-1 alpha-2/alpha-3 code")
    return errors
