"""
Jackdaw Sentry - Smart Contract Analyzer (M16)

Decodes EVM calldata and categorizes contract interactions.
Supports ERC-20, ERC-721 (NFT), and ERC-1155 (multi-token) standards,
plus common DeFi protocol function signatures.
"""

from typing import Any, Dict, List, Optional

# 4-byte function selector → metadata
_FUNCTION_SELECTORS: Dict[str, Dict[str, Any]] = {
    # ERC-20
    "a9059cbb": {"standard": "ERC-20", "name": "transfer", "params": ["address", "uint256"]},
    "23b872dd": {"standard": "ERC-20", "name": "transferFrom", "params": ["address", "address", "uint256"]},
    "095ea7b3": {"standard": "ERC-20", "name": "approve", "params": ["address", "uint256"]},
    "70a08231": {"standard": "ERC-20", "name": "balanceOf", "params": ["address"]},
    "dd62ed3e": {"standard": "ERC-20", "name": "allowance", "params": ["address", "address"]},
    "18160ddd": {"standard": "ERC-20", "name": "totalSupply", "params": []},
    # ERC-721
    "42842e0e": {"standard": "ERC-721", "name": "safeTransferFrom", "params": ["address", "address", "uint256"]},
    "6352211e": {"standard": "ERC-721", "name": "ownerOf", "params": ["uint256"]},
    "081812fc": {"standard": "ERC-721", "name": "getApproved", "params": ["uint256"]},
    "e985e9c5": {"standard": "ERC-721", "name": "isApprovedForAll", "params": ["address", "address"]},
    "b88d4fde": {"standard": "ERC-721", "name": "safeTransferFrom(data)", "params": ["address", "address", "uint256", "bytes"]},
    # ERC-1155
    "f242432a": {"standard": "ERC-1155", "name": "safeTransferFrom", "params": ["address", "address", "uint256", "uint256", "bytes"]},
    "2eb2c2d6": {"standard": "ERC-1155", "name": "safeBatchTransferFrom", "params": ["address", "address", "uint256[]", "uint256[]", "bytes"]},
    "00fdd58e": {"standard": "ERC-1155", "name": "balanceOf", "params": ["address", "uint256"]},
    "4e1273f4": {"standard": "ERC-1155", "name": "balanceOfBatch", "params": ["address[]", "uint256[]"]},
    # WETH
    "d0e30db0": {"standard": "WETH", "name": "deposit", "params": []},
    "2e1a7d4d": {"standard": "WETH", "name": "withdraw", "params": ["uint256"]},
    # Uniswap
    "3593564c": {"standard": "Uniswap-V3", "name": "execute", "params": ["bytes", "bytes[]", "uint256"]},
    "7ff36ab5": {"standard": "Uniswap-V2", "name": "swapExactETHForTokens", "params": ["uint256", "address[]", "address", "uint256"]},
    "38ed1739": {"standard": "Uniswap-V2", "name": "swapExactTokensForTokens", "params": ["uint256", "uint256", "address[]", "address", "uint256"]},
}

_NFT_STANDARDS = frozenset({"ERC-721", "ERC-1155"})
_DEFI_STANDARDS = frozenset({"Uniswap-V2", "Uniswap-V3", "WETH"})


# ---------------------------------------------------------------------------
# Core decoding
# ---------------------------------------------------------------------------


def decode_calldata(calldata: str) -> Optional[Dict[str, Any]]:
    """Decode a hex calldata string and return the function metadata, or None for empty input.

    Returns a dict with keys: selector, standard, name, params.
    If the selector is not recognised, standard and name are "unknown".
    """
    if not calldata or calldata in ("0x", ""):
        return None
    clean = calldata.removeprefix("0x").lower()
    if len(clean) < 8:
        return None
    selector = clean[:8]
    match = _FUNCTION_SELECTORS.get(selector)
    if not match:
        return {"selector": selector, "standard": "unknown", "name": "unknown", "params": []}
    return {"selector": selector, **match}


def is_nft_interaction(calldata: str) -> bool:
    """Return True if the calldata matches an ERC-721 or ERC-1155 function."""
    decoded = decode_calldata(calldata)
    if not decoded:
        return False
    return decoded.get("standard") in _NFT_STANDARDS


def classify_contract(
    calldata: str,
    bytecode_size: Optional[int] = None,
    known_contract_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a classification dict for a contract interaction."""
    decoded = decode_calldata(calldata)
    standard = decoded.get("standard", "unknown") if decoded else "unknown"
    function_name = decoded.get("name", "unknown") if decoded else "unknown"

    risk_indicators: List[str] = []
    if standard == "unknown" and bytecode_size is not None and bytecode_size < 100:
        risk_indicators.append("minimal_bytecode")
    if function_name in ("transferFrom", "safeTransferFrom"):
        risk_indicators.append("token_transfer")

    return {
        "standard": standard,
        "function": function_name,
        "is_nft": standard in _NFT_STANDARDS,
        "is_defi": standard in _DEFI_STANDARDS,
        "risk_indicators": risk_indicators,
        "decoded": decoded,
        "known_type": known_contract_type,
    }


def analyze_nft_transfer(
    calldata: str,
    contract_address: str,
    chain: str = "ethereum",
) -> Dict[str, Any]:
    """Extract NFT transfer details from calldata."""
    decoded = decode_calldata(calldata)
    if not decoded or decoded.get("standard") not in _NFT_STANDARDS:
        return {
            "is_nft_transfer": False,
            "contract": contract_address,
            "chain": chain,
        }
    return {
        "is_nft_transfer": True,
        "contract": contract_address,
        "chain": chain,
        "standard": decoded["standard"],
        "function": decoded["name"],
        "selector": decoded["selector"],
    }


def get_supported_standards() -> List[str]:
    """Return a sorted list of recognised contract standards."""
    return sorted({v["standard"] for v in _FUNCTION_SELECTORS.values()})
