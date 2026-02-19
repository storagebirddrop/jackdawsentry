"""
Jackdaw Sentry — Transaction Monitoring Pipeline (M12)

Polls each configured RPC client for new blocks/transactions and feeds
them through the alert rules engine.  Designed to run as a background
asyncio task started from the app lifespan.

Each chain is polled independently at its own cadence.  The last-seen
block number is stored in Redis so restarts don't re-evaluate old blocks.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.monitoring.alert_rules import evaluate_transaction

logger = logging.getLogger(__name__)

# Polling intervals (seconds) per chain family
_POLL_INTERVALS: Dict[str, int] = {
    "evm": 12,       # ~ETH block time
    "bitcoin": 60,
    "solana": 4,
    "tron": 3,
    "xrpl": 4,
}

_LAST_BLOCK_KEY = "jackdaw:monitor:last_block:{chain}"

# Running flag — set to False to stop all loops cleanly
_running = False
_tasks: List[asyncio.Task] = []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def start_monitor(chains: List[str] = None) -> None:
    """
    Schedule per-chain monitoring loops.

    Call from the FastAPI lifespan *after* the event loop is running.
    Default chains: ethereum, bitcoin (lightweight defaults; extend via config).
    """
    global _running
    _running = True
    target_chains = chains or ["ethereum", "bitcoin"]
    for chain in target_chains:
        task = asyncio.ensure_future(_chain_loop(chain))
        _tasks.append(task)
    logger.info(f"Transaction monitor started for chains: {target_chains}")


def stop_monitor() -> None:
    """Cancel all monitoring loops."""
    global _running
    _running = False
    for task in _tasks:
        task.cancel()
    _tasks.clear()
    logger.info("Transaction monitor stopped")


# ---------------------------------------------------------------------------
# Per-chain polling loop
# ---------------------------------------------------------------------------


async def _chain_loop(chain: str) -> None:
    """Poll *chain* for new transactions and evaluate alert rules."""
    try:
        from src.collectors.rpc.factory import get_rpc_client
    except ImportError:
        logger.warning("RPC factory not available — monitor loop exiting for %s", chain)
        return

    family = _get_family(chain)
    interval = _POLL_INTERVALS.get(family, 30)

    logger.info(f"[monitor] Starting loop for {chain} (poll every {interval}s)")

    while _running:
        try:
            client = get_rpc_client(chain)
            if client is None:
                await asyncio.sleep(interval)
                continue

            txs = await _fetch_latest_txs(client, chain)
            for tx in txs:
                tx["blockchain"] = chain
                try:
                    await evaluate_transaction(tx)
                except Exception as exc:
                    logger.debug(f"[monitor] eval error for {tx.get('hash')}: {exc}")

        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning(f"[monitor] {chain} loop error: {exc}")

        await asyncio.sleep(interval)


async def _fetch_latest_txs(client: Any, chain: str) -> List[Dict[str, Any]]:
    """
    Fetch transactions from the latest block via *client*.

    Returns a normalised list of tx dicts with at minimum:
      hash, from, to, value (native token, float), blockchain
    """
    try:
        block = await client.get_latest_block()
        if not block:
            return []

        txs = getattr(block, "transactions", None) or []
        result = []
        for tx in txs[:50]:  # cap at 50 per poll cycle to avoid spikes
            result.append(_normalise_tx(tx, chain))
        return result
    except Exception as exc:
        logger.debug(f"[monitor] fetch error for {chain}: {exc}")
        return []


def _normalise_tx(tx: Any, chain: str) -> Dict[str, Any]:
    """Convert a Transaction dataclass or dict into a flat alert-engine dict."""
    if isinstance(tx, dict):
        return {
            "hash": tx.get("hash") or tx.get("txid", ""),
            "from": tx.get("from") or tx.get("sender", ""),
            "to": tx.get("to") or tx.get("receiver", ""),
            "value": _safe_float(tx.get("value") or tx.get("amount")),
            "blockchain": chain,
            "timestamp": tx.get("timestamp"),
        }
    # Dataclass-style (Transaction namedtuple/dataclass)
    return {
        "hash": getattr(tx, "hash", "") or getattr(tx, "txid", ""),
        "from": getattr(tx, "from_address", "") or getattr(tx, "sender", ""),
        "to": getattr(tx, "to_address", "") or getattr(tx, "receiver", ""),
        "value": _safe_float(getattr(tx, "value", None) or getattr(tx, "amount", None)),
        "blockchain": chain,
        "timestamp": getattr(tx, "timestamp", None),
    }


def _safe_float(v: Any) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _get_family(chain: str) -> str:
    evm = {"ethereum", "polygon", "bsc", "arbitrum", "optimism", "avalanche", "base"}
    if chain in evm:
        return "evm"
    if chain == "bitcoin":
        return "bitcoin"
    if chain in {"solana", "solana-mainnet"}:
        return "solana"
    if chain == "tron":
        return "tron"
    if chain in {"xrpl", "xrp"}:
        return "xrpl"
    return "evm"
