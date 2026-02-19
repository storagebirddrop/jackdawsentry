"""
Jackdaw Sentry - Investigation Narrative Generator (M15)

Produces plain-language investigation summaries from structured data.
Uses Claude API when ANTHROPIC_API_KEY is set; falls back to template generation.
"""

import os
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
_MODEL: str = os.getenv("AI_SUMMARY_MODEL", "claude-haiku-4-5-20251001")
_MAX_TOKENS: int = 512

_RISK_LEVEL_PHRASES: Dict[str, str] = {
    "critical": "represents a critical compliance risk requiring immediate escalation",
    "high": "presents high-risk indicators warranting urgent investigative action",
    "medium": "shows moderate risk signals that merit further review",
    "low": "displays low-risk characteristics with no immediate concern",
}

_PRIORITY_PHRASES: Dict[str, str] = {
    "critical": "classified as critical priority",
    "high": "flagged as high priority",
    "medium": "assessed at medium priority",
    "low": "assigned low priority",
}

_EVIDENCE_TYPE_LABELS: Dict[str, str] = {
    "transaction": "linked transaction",
    "address": "associated address",
    "pattern": "detected behavioural pattern",
    "external": "external intelligence item",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _risk_level_from_score(score: float) -> str:
    if score >= 0.75:
        return "critical"
    if score >= 0.55:
        return "high"
    if score >= 0.35:
        return "medium"
    return "low"


def _format_evidence_chain(evidence: List[Dict[str, Any]]) -> str:
    """Render a numbered evidence list (capped at 10 items)."""
    if not evidence:
        return "No evidence items have been attached to this investigation."
    lines = []
    for i, ev in enumerate(evidence[:10], 1):
        label = _EVIDENCE_TYPE_LABELS.get(ev.get("evidence_type", ""), "item")
        conf = float(ev.get("confidence", 0.5))
        desc = str(ev.get("description", ""))[:120]
        lines.append(f"  {i}. {label.capitalize()} — {desc} (confidence: {conf:.0%})")
    if len(evidence) > 10:
        lines.append(f"  … and {len(evidence) - 10} additional item(s).")
    return "\n".join(lines)


def extract_key_findings(
    investigation: Dict[str, Any],
    evidence: List[Dict[str, Any]],
) -> List[str]:
    """Derive a list of factual finding bullets from investigation data."""
    findings: List[str] = []

    addresses = investigation.get("addresses", [])
    if addresses:
        sample = ", ".join(str(a) for a in addresses[:3])
        suffix = "…" if len(addresses) > 3 else ""
        findings.append(f"{len(addresses)} address(es) under scrutiny: {sample}{suffix}.")

    risk_score = float(investigation.get("risk_score", 0.0))
    if risk_score > 0.0:
        findings.append(f"Composite risk score: {risk_score:.2f}.")

    if evidence:
        high_conf = [e for e in evidence if float(e.get("confidence", 0.0)) >= 0.80]
        if high_conf:
            findings.append(f"{len(high_conf)} high-confidence evidence item(s) recorded.")
        ev_types = sorted({e.get("evidence_type", "other") for e in evidence})
        findings.append(
            f"Evidence spans {len(ev_types)} category type(s): {', '.join(ev_types)}."
        )

    blockchain = investigation.get("blockchain", "")
    if blockchain:
        findings.append(f"Investigation scope: {blockchain} network.")

    return findings or ["No significant findings extracted from available data."]


def _template_narrative(
    investigation: Dict[str, Any],
    evidence: List[Dict[str, Any]],
    risk_score: Optional[float] = None,
) -> str:
    """Build a deterministic template-based investigation narrative."""
    inv_id = investigation.get("investigation_id", "N/A")
    title = investigation.get("title", "Untitled")
    status = investigation.get("status", "open")
    priority = investigation.get("priority", "medium")
    blockchain = investigation.get("blockchain", "")
    created_by = investigation.get("created_by", "unknown")
    addresses = investigation.get("addresses", [])
    description = str(investigation.get("description", ""))

    effective_score = (
        risk_score if risk_score is not None
        else float(investigation.get("risk_score", 0.0))
    )
    risk_level = _risk_level_from_score(effective_score)
    risk_phrase = _RISK_LEVEL_PHRASES.get(risk_level, "requires further analysis")
    priority_phrase = _PRIORITY_PHRASES.get(priority, f"assessed at {priority} priority")

    addr_summary = (
        f"{len(addresses)} blockchain address(es)" if addresses
        else "an unspecified set of addresses"
    )
    chain_phrase = f" on the {blockchain} network" if blockchain else ""

    narrative = (
        f"Investigation {inv_id} — '{title}'\n\n"
        f"This investigation, opened by {created_by} and {priority_phrase}, examines "
        f"{addr_summary}{chain_phrase}. "
        f"Based on the available data, this case {risk_phrase}.\n"
    )

    if description:
        narrative += f"\nBackground: {description}\n"

    narrative += f"\nCurrent status: {status.replace('_', ' ')}.\n"

    narrative += f"\nEvidence chain ({len(evidence)} item(s)):\n"
    narrative += _format_evidence_chain(evidence)
    narrative += "\n"

    narrative += (
        "\nNote: This narrative is auto-generated from structured investigation data "
        "and should be reviewed by the responsible analyst before use in formal proceedings."
    )

    return narrative.strip()


# ---------------------------------------------------------------------------
# Claude API call
# ---------------------------------------------------------------------------


async def _call_claude_narrative(prompt: str) -> Optional[str]:
    if not _API_KEY:
        return None
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=_API_KEY)
        msg = await client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as exc:
        logger.warning("Claude API call failed for investigation narrative: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_investigation_narrative(
    investigation: Dict[str, Any],
    evidence: List[Dict[str, Any]],
    risk_score: Optional[float] = None,
) -> Dict[str, Any]:
    """Generate a plain-language narrative for an investigation.

    Returns a dict with keys:
        narrative       — full text narrative
        key_findings    — list of factual bullet strings
        risk_assessment — one-line risk summary
        source          — "claude_api" or "template"
        model           — model name if Claude was used, else None
    """
    key_findings = extract_key_findings(investigation, evidence)

    effective_score = (
        risk_score if risk_score is not None
        else float(investigation.get("risk_score", 0.0))
    )
    risk_level = _risk_level_from_score(effective_score)
    risk_assessment = _RISK_LEVEL_PHRASES.get(risk_level, "requires further review")

    template_text = _template_narrative(investigation, evidence, risk_score)

    if _API_KEY:
        prompt = (
            "You are a compliance analyst writing a concise investigation narrative "
            "for a court-ready report.\n"
            f"Investigation summary:\n{template_text}\n\n"
            "Write a professional 2-3 paragraph narrative suitable for a legal proceeding. "
            "Use precise, factual language. Do not introduce facts not in the summary."
        )
        api_result = await _call_claude_narrative(prompt)
        if api_result:
            return {
                "narrative": api_result,
                "key_findings": key_findings,
                "risk_assessment": risk_assessment,
                "source": "claude_api",
                "model": _MODEL,
            }

    return {
        "narrative": template_text,
        "key_findings": key_findings,
        "risk_assessment": risk_assessment,
        "source": "template",
        "model": None,
    }
