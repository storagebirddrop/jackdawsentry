"""
Jackdaw Sentry — DeFi Interaction Decoder (M13)

Classifies a transaction as a specific DeFi interaction type by matching:
  1. The recipient contract address against the protocol registry
  2. The transaction input data's 4-byte function selector against known
     function signature tables for each protocol type

Interaction types returned:
  bridge_deposit   — deposit into a cross-chain bridge
  bridge_withdraw  — claim / receive from a bridge
  dex_swap         — token swap on a DEX/AMM
  dex_add_liquidity
  dex_remove_liquidity
  lending_deposit  — deposit/supply to a lending pool
  lending_borrow
  lending_repay
  lending_withdraw
  staking_stake
  staking_unstake
  yield_deposit    — deposit into a yield vault/farm
  yield_withdraw
  mixer_deposit    — deposit into a mixer (HIGH RISK)
  mixer_withdraw   — withdraw from a mixer (HIGH RISK)
  nft_buy
  nft_sell
  transfer         — plain ERC-20 or native transfer
  unknown          — could not classify
"""

from __future__ import annotations

from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from src.analysis.protocol_registry import classify_address
from src.analysis.protocol_registry import get_protocol_by_address

# ---------------------------------------------------------------------------
# Function selector tables  (4-byte hex prefix of keccak256(signature))
# These are the canonical selectors for the most common DeFi functions.
# ---------------------------------------------------------------------------

# Bridge selectors
_BRIDGE_DEPOSIT_SELECTORS = {
    "0x1114cd2a",  # Stargate: swap(...)
    "0xc4270900",  # Wormhole: transferTokens(...)
    "0xc7cd97480",  # LayerZero: send(...)
    "0xd77d6ec0",  # Hop: sendToL2(...)
    "0x30c35702",  # Across: deposit(...)
    "0x44bc937b",  # Celer: send(...)
    "0x625f7e8a",  # Multichain: anySwapOut(...)
}

_BRIDGE_WITHDRAW_SELECTORS = {
    "0x3d12a85a",  # Wormhole: completeTransfer(...)
    "0xf953cec7",  # LayerZero: lzReceive(...)
    "0xab9c4b5d",  # Hop: bondWithdrawal(...)
    "0xef05d7d2",  # Across: fillRelay(...)
}

# DEX swap selectors
_DEX_SWAP_SELECTORS = {
    "0x38ed1739",  # Uniswap V2: swapExactTokensForTokens(...)
    "0x7ff36ab5",  # Uniswap V2: swapExactETHForTokens(...)
    "0x18cbafe5",  # Uniswap V2: swapExactTokensForETH(...)
    "0x414bf389",  # Uniswap V3: exactInputSingle(...)
    "0xb858183f",  # Uniswap V3: exactInput(...)
    "0x04e45aaf",  # Uniswap V3 (new router): exactInputSingle(...)
    "0xe449022e",  # 1inch V5: swap(...)
    "0x12aa3caf",  # 1inch V4: swap(...)
    "0x0502b1c5",  # 1inch V3: swap(...)
    "0xa6417ed6",  # Curve: exchange(...)
    "0x3df02124",  # Curve: exchange(int128,int128,uint256,uint256)
    "0x9169558b",  # dYdX: trade(...)
}

_DEX_ADD_LIQ_SELECTORS = {
    "0xe8e33700",  # Uniswap V2: addLiquidity(...)
    "0xf305d719",  # Uniswap V2: addLiquidityETH(...)
    "0x883164560",  # Uniswap V3: mint(...)
    "0x4515cef3",  # Curve: add_liquidity(uint256[3],uint256)
}

_DEX_REMOVE_LIQ_SELECTORS = {
    "0xbaa2abde",  # Uniswap V2: removeLiquidity(...)
    "0x02751cec",  # Uniswap V2: removeLiquidityETH(...)
    "0xa34123a7",  # Uniswap V3: burn(...)
    "0x1a4d01d2",  # Curve: remove_liquidity_one_coin(...)
}

# Lending selectors
_LENDING_DEPOSIT_SELECTORS = {
    "0xe8eda9df",  # Aave V2: deposit(address,uint256,address,uint16)
    "0x617ba037",  # Aave V3: supply(address,uint256,address,uint16)
    "0xa0712d68",  # Compound: mint(uint256)
    "0x1249c58b",  # Compound: mint()
    "0xd5ed3933",  # MakerDAO: frob(...)
}

_LENDING_BORROW_SELECTORS = {
    "0xc858f5f9",  # Aave V2: borrow(address,uint256,uint256,uint16,address)
    "0xa415bcad",  # Aave V3: borrow(address,uint256,uint256,uint16,address)
    "0xc5ebeaec",  # Compound: borrow(uint256)
}

_LENDING_REPAY_SELECTORS = {
    "0x573ade81",  # Aave V2: repay(address,uint256,uint256,address)
    "0x563dd613",  # Aave V3: repay(address,uint256,uint256,address)
    "0x0e752702",  # Compound: repayBorrow(uint256)
    "0x4e4d9fea",  # Compound: repayBorrowBehalf(address,uint256) (first 4 bytes)
}

_LENDING_WITHDRAW_SELECTORS = {
    "0x69328dec",  # Aave V2: withdraw(address,uint256,address)
    "0x69328dec",  # Aave V3: withdraw (same selector)
    "0xdb006a75",  # Compound: redeem(uint256)
}

# Staking selectors
_STAKING_STAKE_SELECTORS = {
    "0xa694fc3a",  # Lido: submit(address)
    "0xd0e30db0",  # Generic: deposit() (e.g. wETH wrap, staking)
    "0x8dbdbe6d",  # Convex: deposit(uint256,uint256,bool)
    "0xd5575982",  # Stader: deposit(...)
}

_STAKING_UNSTAKE_SELECTORS = {
    "0x2e1a7d4d",  # Generic: withdraw(uint256)
    "0x38d07436",  # Lido: requestWithdrawals(...)
    "0x441a3e70",  # Convex: withdraw(uint256,uint256)
}

# Yield selectors
_YIELD_DEPOSIT_SELECTORS = {
    "0xb6b55f25",  # Yearn: deposit(uint256)
    "0x6e553f65",  # ERC-4626: deposit(uint256,address)
    "0xd0e30db0",  # Generic deposit()
    "0xe2bbb158",  # SushiSwap MasterChef: deposit(uint256,uint256)
    "0xe8e33700",  # Beefy / generic LP deposit
}

_YIELD_WITHDRAW_SELECTORS = {
    "0x2e1a7d4d",  # Yearn / ERC-4626: withdraw(uint256)
    "0x228951182",  # ERC-4626: withdraw(uint256,address,address)
    "0x441a3e70",  # MasterChef: withdraw(uint256,uint256)
}

# Mixer selectors
_MIXER_DEPOSIT_SELECTORS = {
    "0xb214faa5",  # Tornado Cash: deposit(bytes32)
    "0x0f94b2a2",  # Railgun: generateDeposit(...)
}

_MIXER_WITHDRAW_SELECTORS = {
    "0x21a0adb6",  # Tornado Cash: withdraw(bytes,bytes32,address,address,uint256,uint256)
    "0xbc36a11f",  # Railgun: withdraw(...)
}

# NFT selectors
_NFT_BUY_SELECTORS = {
    "0xfb0f3ee1",  # OpenSea Seaport: fulfillBasicOrder(...)
    "0x00000000",  # Seaport: various
    "0x87201b41",  # Blur: execute(...)
}

_NFT_SELL_SELECTORS = {
    "0xed98a574",  # OpenSea: matchOrders(...)
    "0xf16b1d84",  # Blur: bulkExecute(...)
}

# Flat lookup: selector → interaction type (more specific types first)
_SELECTOR_MAP: Dict[str, str] = {}
for _sel in _MIXER_DEPOSIT_SELECTORS:
    _SELECTOR_MAP[_sel] = "mixer_deposit"
for _sel in _MIXER_WITHDRAW_SELECTORS:
    _SELECTOR_MAP[_sel] = "mixer_withdraw"
for _sel in _BRIDGE_DEPOSIT_SELECTORS:
    _SELECTOR_MAP.setdefault(_sel, "bridge_deposit")
for _sel in _BRIDGE_WITHDRAW_SELECTORS:
    _SELECTOR_MAP.setdefault(_sel, "bridge_withdraw")
for _sel in _LENDING_DEPOSIT_SELECTORS:
    _SELECTOR_MAP.setdefault(_sel, "lending_deposit")
for _sel in _LENDING_BORROW_SELECTORS:
    _SELECTOR_MAP.setdefault(_sel, "lending_borrow")
for _sel in _LENDING_REPAY_SELECTORS:
    _SELECTOR_MAP.setdefault(_sel, "lending_repay")
for _sel in _LENDING_WITHDRAW_SELECTORS:
    _SELECTOR_MAP.setdefault(_sel, "lending_withdraw")
for _sel in _STAKING_STAKE_SELECTORS:
    _SELECTOR_MAP.setdefault(_sel, "staking_stake")
for _sel in _STAKING_UNSTAKE_SELECTORS:
    _SELECTOR_MAP.setdefault(_sel, "staking_unstake")
for _sel in _YIELD_DEPOSIT_SELECTORS:
    _SELECTOR_MAP.setdefault(_sel, "yield_deposit")
for _sel in _YIELD_WITHDRAW_SELECTORS:
    _SELECTOR_MAP.setdefault(_sel, "yield_withdraw")
for _sel in _DEX_SWAP_SELECTORS:
    _SELECTOR_MAP.setdefault(_sel, "dex_swap")
for _sel in _DEX_ADD_LIQ_SELECTORS:
    _SELECTOR_MAP.setdefault(_sel, "dex_add_liquidity")
for _sel in _DEX_REMOVE_LIQ_SELECTORS:
    _SELECTOR_MAP.setdefault(_sel, "dex_remove_liquidity")
for _sel in _NFT_BUY_SELECTORS:
    _SELECTOR_MAP.setdefault(_sel, "nft_buy")
for _sel in _NFT_SELL_SELECTORS:
    _SELECTOR_MAP.setdefault(_sel, "nft_sell")


# ---------------------------------------------------------------------------
# Public decode API
# ---------------------------------------------------------------------------


def decode_transaction(
    to_address: str,
    input_data: Optional[str] = None,
    chain: str = None,
) -> Dict[str, Any]:
    """
    Classify a transaction into a DeFi interaction type.

    Parameters
    ----------
    to_address  : recipient contract address (hex string)
    input_data  : hex-encoded transaction input (0x...)
    chain       : blockchain name (optional, used for protocol lookup)

    Returns
    -------
    dict with keys:
      interaction_type  : one of the interaction type strings above
      protocol_name     : matched protocol name or None
      protocol_type     : bridge | dex | lending | etc., or None
      risk_level        : low | medium | high | critical | None
      function_selector : 4-byte selector extracted from input_data, or None
      confidence        : 0.0–1.0
    """
    result: Dict[str, Any] = {
        "interaction_type": "unknown",
        "protocol_name": None,
        "protocol_type": None,
        "risk_level": None,
        "function_selector": None,
        "confidence": 0.0,
    }

    # Extract 4-byte function selector
    selector = _extract_selector(input_data)
    result["function_selector"] = selector

    # Protocol lookup by address
    proto = get_protocol_by_address(to_address) if to_address else None
    if proto:
        result["protocol_name"] = proto.name
        result["protocol_type"] = proto.protocol_type
        result["risk_level"] = proto.risk_level

    # Selector-based interaction type (most specific)
    if selector and selector in _SELECTOR_MAP:
        result["interaction_type"] = _SELECTOR_MAP[selector]
        result["confidence"] = 0.9
        return result

    # Fallback: infer from protocol type if address matched
    if proto:
        result["interaction_type"] = _default_for_type(proto.protocol_type)
        result["confidence"] = 0.6
        return result

    # Plain transfer heuristic: no input data or just a value transfer
    if not input_data or input_data in ("0x", ""):
        result["interaction_type"] = "transfer"
        result["confidence"] = 0.8
        return result

    result["confidence"] = 0.1
    return result


def decode_transactions_bulk(txs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Decode a list of transactions.

    Each element in *txs* should have at minimum a ``to`` key.
    Optional keys: ``input``, ``blockchain``.
    Returns a list of decode results in the same order.
    """
    return [
        decode_transaction(
            to_address=tx.get("to") or tx.get("to_address", ""),
            input_data=tx.get("input") or tx.get("input_data"),
            chain=tx.get("blockchain") or tx.get("chain"),
        )
        for tx in txs
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_selector(input_data: Optional[str]) -> Optional[str]:
    """Extract the 4-byte function selector from hex input data."""
    if not input_data:
        return None
    data = input_data.lstrip("0x").lstrip("0X")
    if len(data) < 8:
        return None
    return "0x" + data[:8].lower()


def _default_for_type(protocol_type: str) -> str:
    """Return a generic interaction type for a protocol type when selector is unknown."""
    mapping = {
        "bridge": "bridge_deposit",
        "dex": "dex_swap",
        "lending": "lending_deposit",
        "staking": "staking_stake",
        "yield_farming": "yield_deposit",
        "mixer": "mixer_deposit",
        "nft": "nft_buy",
        "payments": "transfer",
    }
    return mapping.get(protocol_type, "unknown")
