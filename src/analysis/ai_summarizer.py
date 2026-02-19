"""
Jackdaw Sentry — AI Risk Summarizer (M14)

Produces plain-language risk summaries for addresses and transactions.
Tries the Anthropic Claude API first; falls back to deterministic templates
so the service remains available even when the API key is absent or quota is
exceeded.

Summary types
─────────────
• address_risk   — 2–3 sentence narrative for a full address risk report
• transaction    — 1 sentence flag summary for a single transaction
• cluster        — brief description of a behavioural cluster

Configuration (all optional):
  ANTHROPIC_API_KEY  — if absent, template fallback is always used
  AI_SUMMARY_MODEL   — defaults to "claude-haiku-4-5-20251001" (fast/cheap)
  AI_SUMMARY_MAX_TOKENS — defaults to 256
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_MODEL = os.getenv("AI_SUMMARY_MODEL", "claude-haiku-4-5-20251001")
_MAX_TOKENS = int(os.getenv("AI_SUMMARY_MAX_TOKENS", "256"))
_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ---------------------------------------------------------------------------
# Template fallback (always available)
# ---------------------------------------------------------------------------

_RISK_LEVEL_PHRASES = {
    "critical": "presents critical-level risk",
    "high": "presents high risk",
    "medium": "presents medium risk",
    "low": "presents low risk",
}

_FEATURE_DESCRIPTIONS: Dict[str, str] = {
    "mixer_usage": "known mixer usage",
    "privacy_tool_usage": "privacy-tool activity",
    "sanctions_entity": "a link to a sanctioned entity",
    "darknet_entity": "association with a darknet marketplace",
    "scam_entity": "association with a known scam or ransomware operation",
    "high_frequency_periods": "abnormally high transaction frequency",
    "round_amount_ratio": "a high proportion of round-amount transactions",
    "off_peak_ratio": "an unusual volume of off-peak-hour activity",
    "cross_chain_activity": "cross-chain bridge activity",
    "large_tx_ratio": "a high proportion of large-value transfers",
    "low_counterparty_ratio": "an unusually low counterparty diversity",
    "bridge_usage": "bridge contract interactions",
}


def _template_address_summary(
    address: str,
    risk_level: str,
    score: float,
    feature_vector: Dict[str, float],
    entity_info: Optional[Dict] = None,
) -> str:
    """Deterministic template-based summary for an address risk report."""
    phrase = _RISK_LEVEL_PHRASES.get(risk_level, "presents unknown risk")

    # Collect triggered features (value > 0.1)
    flags: List[str] = [
        _FEATURE_DESCRIPTIONS[k]
        for k, v in feature_vector.items()
        if v > 0.1 and k in _FEATURE_DESCRIPTIONS
    ]

    entity_clause = ""
    if entity_info and entity_info.get("entity_name"):
        entity_clause = (
            f" The address is attributed to {entity_info['entity_name']}."
        )

    if flags:
        flag_list = ", ".join(flags[:3])  # cap at 3 for readability
        if len(flags) > 3:
            flag_list += f" and {len(flags) - 3} other signal(s)"
        flag_sentence = f" Key risk drivers include {flag_list}."
    else:
        flag_sentence = " No individual risk signals exceeded the threshold."

    return (
        f"Address {address[:10]}… {phrase} (score {score:.2f})."
        f"{entity_clause}{flag_sentence}"
        " Review the full feature breakdown before taking compliance action."
    )


def _template_transaction_summary(
    tx_hash: str,
    interaction_type: str,
    protocol_name: Optional[str],
    risk_level: str,
) -> str:
    """One-line template summary for a transaction."""
    proto = f" via {protocol_name}" if protocol_name else ""
    return (
        f"Transaction {tx_hash[:12]}… classified as {interaction_type}{proto},"
        f" risk level: {risk_level}."
    )


def _template_cluster_summary(
    cluster_id: str,
    cluster_type: str,
    address_count: int,
    dominant_feature: Optional[str],
) -> str:
    """Template summary for a behavioural cluster."""
    feat_note = ""
    if dominant_feature and dominant_feature in _FEATURE_DESCRIPTIONS:
        feat_note = f" The cluster is characterised by {_FEATURE_DESCRIPTIONS[dominant_feature]}."
    return (
        f"Cluster {cluster_id} ({cluster_type}) contains {address_count} address(es).{feat_note}"
    )


# ---------------------------------------------------------------------------
# Claude API path
# ---------------------------------------------------------------------------


def _build_address_prompt(
    address: str,
    risk_level: str,
    score: float,
    feature_vector: Dict[str, float],
    entity_info: Optional[Dict],
    patterns: Optional[List[str]],
) -> str:
    flags = [k for k, v in feature_vector.items() if v > 0.1]
    entity_note = ""
    if entity_info and entity_info.get("entity_name"):
        entity_note = f"\nEntity: {entity_info['entity_name']} ({entity_info.get('entity_type', 'unknown')})"
    pattern_note = ""
    if patterns:
        pattern_note = f"\nDetected patterns: {', '.join(patterns[:5])}"

    return (
        "You are a crypto compliance analyst. Write a concise 2–3 sentence risk summary "
        "for the following blockchain address. Be factual, specific, and professional. "
        "Do not speculate beyond the provided data.\n\n"
        f"Address: {address}\n"
        f"Risk level: {risk_level} (score: {score:.3f}){entity_note}{pattern_note}\n"
        f"Active risk signals: {', '.join(flags) if flags else 'none'}\n\n"
        "Summary:"
    )


def _build_transaction_prompt(
    tx_hash: str,
    interaction_type: str,
    protocol_name: Optional[str],
    risk_level: str,
    value_usd: Optional[float],
) -> str:
    proto = f" using {protocol_name}" if protocol_name else ""
    value_note = f" (≈${value_usd:,.0f})" if value_usd else ""
    return (
        "Write one sentence describing this blockchain transaction for a compliance log. "
        "Be factual and concise.\n\n"
        f"Transaction: {tx_hash}\n"
        f"Type: {interaction_type}{proto}{value_note}\n"
        f"Risk: {risk_level}\n\n"
        "Description:"
    )


async def _call_claude(prompt: str) -> Optional[str]:
    """Call the Anthropic Messages API. Returns None on any failure."""
    if not _API_KEY:
        return None
    try:
        import anthropic  # type: ignore

        client = anthropic.AsyncAnthropic(api_key=_API_KEY)
        msg = await client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text if msg.content else ""
        return text.strip() or None
    except Exception as exc:
        logger.warning(f"Claude API call failed: {exc} — using template fallback")
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def summarize_address_risk(
    address: str,
    risk_level: str,
    score: float,
    feature_vector: Dict[str, float],
    entity_info: Optional[Dict] = None,
    patterns: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generate a plain-language risk summary for an address.

    Returns:
      summary  : str — the narrative text
      source   : "claude_api" | "template"
      model    : str | None
    """
    ai_text: Optional[str] = None
    source = "template"
    model_used: Optional[str] = None

    if _API_KEY:
        prompt = _build_address_prompt(
            address, risk_level, score, feature_vector, entity_info, patterns
        )
        ai_text = await _call_claude(prompt)
        if ai_text:
            source = "claude_api"
            model_used = _MODEL

    summary = ai_text or _template_address_summary(
        address, risk_level, score, feature_vector, entity_info
    )

    return {"summary": summary, "source": source, "model": model_used}


async def summarize_transaction(
    tx_hash: str,
    interaction_type: str,
    protocol_name: Optional[str] = None,
    risk_level: str = "low",
    value_usd: Optional[float] = None,
) -> Dict[str, Any]:
    """Generate a one-line compliance description for a transaction."""
    ai_text: Optional[str] = None
    source = "template"
    model_used: Optional[str] = None

    if _API_KEY:
        prompt = _build_transaction_prompt(
            tx_hash, interaction_type, protocol_name, risk_level, value_usd
        )
        ai_text = await _call_claude(prompt)
        if ai_text:
            source = "claude_api"
            model_used = _MODEL

    summary = ai_text or _template_transaction_summary(
        tx_hash, interaction_type, protocol_name, risk_level
    )

    return {"summary": summary, "source": source, "model": model_used}


async def summarize_cluster(
    cluster_id: str,
    cluster_type: str,
    address_count: int,
    dominant_feature: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a short description of a behavioural cluster."""
    summary = _template_cluster_summary(
        cluster_id, cluster_type, address_count, dominant_feature
    )
    return {"summary": summary, "source": "template", "model": None}
