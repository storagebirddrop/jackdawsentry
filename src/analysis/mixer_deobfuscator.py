"""
Jackdaw Sentry — Mixer De-obfuscation Engine (M14)

Attempts to correlate deposits into and withdrawals from mixing services by
analysing timing patterns and transaction amounts.  The engine does NOT
produce definitive links (mixers are designed to be opaque) but returns a
list of *candidate pairs* with a confidence score so investigators can
prioritise manual review.

Algorithm
─────────
1. Split a set of transactions into *deposits* (into mixer) and
   *withdrawals* (from mixer) using the interaction_type field or the
   presence of a known mixer address.
2. For each (deposit, withdrawal) pair:
   a. Amount similarity   — absolute relative difference in value
   b. Timing window match — withdrawal occurs within `max_delay_hours` after
      the deposit, with higher confidence for shorter gaps
   c. Chain continuity    — same-chain pairs score higher
3. Pairs with combined confidence ≥ `min_confidence` (default 0.40) are
   returned, sorted descending by confidence.

Limitations and caveats
───────────────────────
• CoinJoin-style mixers (Bitcoin Wasabi) cannot be trivially linked by
  amount alone — this engine is most effective against fee-transparent
  mixers like Tornado Cash where the denomination is fixed.
• Equal-amount Tornado Cash pools (0.1 / 1 / 10 / 100 ETH) make amount
  matching trivial but timing matching carries the signal.
• Results are probabilistic, NOT evidentiary.  Always note this in reports.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class MixerTransaction:
    """Normalised representation of a single transaction for de-obfuscation."""

    tx_hash: str
    address: str  # the user-controlled address (not the mixer contract)
    direction: str  # "deposit" | "withdrawal"
    amount: float  # in native token units (e.g. ETH)
    timestamp: float  # Unix epoch seconds
    chain: str = "unknown"
    mixer_name: Optional[str] = None


@dataclass
class CandidatePair:
    """A (deposit, withdrawal) pair that may represent the same user."""

    deposit_tx: str
    withdrawal_tx: str
    deposit_address: str
    withdrawal_address: str
    deposit_amount: float
    withdrawal_amount: float
    deposit_time: float
    withdrawal_time: float
    delay_hours: float
    amount_similarity: float  # 1.0 = identical amounts
    timing_score: float  # higher for faster withdrawals
    confidence: float  # weighted combination [0, 1]
    same_chain: bool
    notes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

_MAX_DELAY_HOURS_DEFAULT = 72.0
_MIN_CONFIDENCE_DEFAULT = 0.40

# Weights for the three sub-signals
_W_AMOUNT = 0.55
_W_TIMING = 0.35
_W_CHAIN = 0.10


def _amount_similarity(a: float, b: float) -> float:
    """
    Return a score in [0, 1] reflecting how close two amounts are.
    Uses relative difference; identical amounts → 1.0.
    Tornado Cash fixed denominations: 0.1/1/10/100 ETH → deposits and
    withdrawals are the *same* amount (minus fee), so this will be near 1.
    """
    if a <= 0 and b <= 0:
        return 1.0
    denom = max(abs(a), abs(b), 1e-18)
    diff = abs(a - b) / denom
    # Exponential decay: diff=0 → 1.0, diff=0.05 → ~0.95, diff=0.5 → ~0.37
    return math.exp(-diff * 2.0)


def _timing_score(delay_seconds: float, max_delay_hours: float) -> float:
    """
    Return a score in [0, 1].  Shorter delays score higher.
    Delay beyond max_delay_hours → 0.
    """
    if delay_seconds < 0:
        return 0.0  # withdrawal before deposit — impossible
    max_seconds = max_delay_hours * 3600.0
    if delay_seconds > max_seconds:
        return 0.0
    # Linear decay from 1.0 → 0.0 over the allowed window
    return 1.0 - (delay_seconds / max_seconds)


def _combined_confidence(
    amount_sim: float,
    timing: float,
    same_chain: bool,
) -> float:
    chain_score = 1.0 if same_chain else 0.5
    raw = _W_AMOUNT * amount_sim + _W_TIMING * timing + _W_CHAIN * chain_score
    return round(min(raw, 1.0), 4)


# ---------------------------------------------------------------------------
# Core de-obfuscation logic
# ---------------------------------------------------------------------------


def find_candidate_pairs(
    transactions: List[MixerTransaction],
    max_delay_hours: float = _MAX_DELAY_HOURS_DEFAULT,
    min_confidence: float = _MIN_CONFIDENCE_DEFAULT,
) -> List[CandidatePair]:
    """
    Given a list of MixerTransaction objects, return candidate deposit↔withdrawal
    pairs sorted by descending confidence.

    Parameters
    ----------
    transactions     : normalised transactions (direction must be set)
    max_delay_hours  : discard pairs where withdrawal > deposit + this window
    min_confidence   : only include pairs with confidence ≥ this threshold

    Returns
    -------
    List[CandidatePair] sorted by confidence descending.
    """
    deposits = [t for t in transactions if t.direction == "deposit"]
    withdrawals = [t for t in transactions if t.direction == "withdrawal"]

    pairs: List[CandidatePair] = []

    for dep in deposits:
        for wit in withdrawals:
            delay_s = wit.timestamp - dep.timestamp
            if delay_s < 0 or delay_s > max_delay_hours * 3600:
                continue

            amt_sim = _amount_similarity(dep.amount, wit.amount)
            timing = _timing_score(delay_s, max_delay_hours)
            same_chain = dep.chain.lower() == wit.chain.lower()
            conf = _combined_confidence(amt_sim, timing, same_chain)

            if conf < min_confidence:
                continue

            notes: List[str] = []
            if amt_sim >= 0.99:
                notes.append("exact amount match")
            if delay_s < 3600:
                notes.append("withdrawn within 1 hour")
            elif delay_s < 86400:
                notes.append("withdrawn same day")
            if not same_chain:
                notes.append("cross-chain pair")

            pairs.append(
                CandidatePair(
                    deposit_tx=dep.tx_hash,
                    withdrawal_tx=wit.tx_hash,
                    deposit_address=dep.address,
                    withdrawal_address=wit.address,
                    deposit_amount=dep.amount,
                    withdrawal_amount=wit.amount,
                    deposit_time=dep.timestamp,
                    withdrawal_time=wit.timestamp,
                    delay_hours=round(delay_s / 3600.0, 3),
                    amount_similarity=round(amt_sim, 4),
                    timing_score=round(timing, 4),
                    confidence=conf,
                    same_chain=same_chain,
                    notes=notes,
                )
            )

    pairs.sort(key=lambda p: p.confidence, reverse=True)
    return pairs


def build_mixer_transactions(
    raw_txs: List[Dict[str, Any]],
    mixer_addresses: Optional[set] = None,
) -> List[MixerTransaction]:
    """
    Convert raw transaction dicts (as returned by RPC clients or the DeFi
    decoder) into MixerTransaction objects.

    Expected keys in each dict (all optional with defaults):
      tx_hash, from_address, to_address, value, timestamp, chain,
      interaction_type, protocol_name
    """
    if mixer_addresses is None:
        try:
            from src.analysis.protocol_registry import get_known_mixer_addresses

            mixer_addresses = get_known_mixer_addresses()
        except Exception:
            mixer_addresses = set()

    result: List[MixerTransaction] = []
    for tx in raw_txs:
        tx_hash = tx.get("tx_hash") or tx.get("hash") or ""
        from_addr = (tx.get("from_address") or tx.get("from") or "").lower()
        to_addr = (tx.get("to_address") or tx.get("to") or "").lower()
        value = float(tx.get("value") or tx.get("amount") or 0)
        ts = float(tx.get("timestamp") or tx.get("block_time") or 0)
        chain = tx.get("chain") or tx.get("blockchain") or "unknown"
        interaction = (tx.get("interaction_type") or "").lower()
        protocol = tx.get("protocol_name") or ""

        # Determine direction
        is_mixer_deposit = "mixer_deposit" in interaction or to_addr in mixer_addresses
        is_mixer_withdrawal = (
            "mixer_withdraw" in interaction or from_addr in mixer_addresses
        )

        if is_mixer_deposit:
            direction = "deposit"
            user_address = from_addr
        elif is_mixer_withdrawal:
            direction = "withdrawal"
            user_address = to_addr
        else:
            continue  # not a mixer tx, skip

        result.append(
            MixerTransaction(
                tx_hash=tx_hash,
                address=user_address,
                direction=direction,
                amount=value,
                timestamp=ts,
                chain=chain,
                mixer_name=protocol or None,
            )
        )

    return result


def summarize_deobfuscation(
    pairs: List[CandidatePair],
) -> Dict[str, Any]:
    """
    Return a summary dict suitable for API responses.
    """
    if not pairs:
        return {
            "candidate_pairs": [],
            "total_pairs": 0,
            "high_confidence_pairs": 0,
            "note": "No correlated deposit-withdrawal pairs found.",
        }

    high_conf = [p for p in pairs if p.confidence >= 0.70]

    return {
        "candidate_pairs": [
            {
                "deposit_tx": p.deposit_tx,
                "withdrawal_tx": p.withdrawal_tx,
                "deposit_address": p.deposit_address,
                "withdrawal_address": p.withdrawal_address,
                "deposit_amount": p.deposit_amount,
                "withdrawal_amount": p.withdrawal_amount,
                "delay_hours": p.delay_hours,
                "amount_similarity": p.amount_similarity,
                "timing_score": p.timing_score,
                "confidence": p.confidence,
                "same_chain": p.same_chain,
                "notes": p.notes,
            }
            for p in pairs
        ],
        "total_pairs": len(pairs),
        "high_confidence_pairs": len(high_conf),
        "note": (
            "Results are probabilistic estimates. "
            "Treat as investigative leads, not evidence."
        ),
    }
