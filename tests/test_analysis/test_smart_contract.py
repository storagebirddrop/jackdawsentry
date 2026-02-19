"""
Unit tests for src/analysis/smart_contract_analyzer.py (M16)
"""
import pytest
from src.analysis.smart_contract_analyzer import (
    decode_calldata,
    is_nft_interaction,
    classify_contract,
    analyze_nft_transfer,
    get_supported_standards,
)


# ---------------------------------------------------------------------------
# decode_calldata
# ---------------------------------------------------------------------------


class TestDecodeCalldata:
    def test_erc20_transfer_decoded(self):
        # selector a9059cbb = ERC-20 transfer
        calldata = "0xa9059cbb" + "0" * 64
        result = decode_calldata(calldata)
        assert result is not None
        assert result["standard"] == "ERC-20"
        assert result["name"] == "transfer"

    def test_erc721_owner_of_decoded(self):
        calldata = "0x6352211e" + "0" * 64
        result = decode_calldata(calldata)
        assert result["standard"] == "ERC-721"
        assert result["name"] == "ownerOf"

    def test_erc1155_safe_transfer_decoded(self):
        calldata = "0xf242432a" + "0" * 128
        result = decode_calldata(calldata)
        assert result["standard"] == "ERC-1155"

    def test_unknown_selector_returns_unknown(self):
        calldata = "0xdeadbeef" + "0" * 64
        result = decode_calldata(calldata)
        assert result is not None
        assert result["standard"] == "unknown"

    def test_empty_calldata_returns_none(self):
        assert decode_calldata("0x") is None
        assert decode_calldata("") is None

    def test_too_short_calldata_returns_none(self):
        assert decode_calldata("0xabc") is None

    def test_no_prefix_still_decoded(self):
        # Without 0x prefix
        calldata = "a9059cbb" + "0" * 64
        result = decode_calldata(calldata)
        assert result is not None
        assert result["standard"] == "ERC-20"

    def test_result_has_selector_key(self):
        calldata = "0xa9059cbb" + "0" * 64
        result = decode_calldata(calldata)
        assert result["selector"] == "a9059cbb"

    def test_uniswap_v3_decoded(self):
        calldata = "0x3593564c" + "0" * 128
        result = decode_calldata(calldata)
        assert result["standard"] == "Uniswap-V3"

    def test_weth_deposit_decoded(self):
        calldata = "0xd0e30db0"
        result = decode_calldata(calldata)
        assert result["standard"] == "WETH"
        assert result["name"] == "deposit"


# ---------------------------------------------------------------------------
# is_nft_interaction
# ---------------------------------------------------------------------------


class TestIsNftInteraction:
    def test_erc721_transfer_is_nft(self):
        calldata = "0x42842e0e" + "0" * 96
        assert is_nft_interaction(calldata) is True

    def test_erc1155_transfer_is_nft(self):
        calldata = "0xf242432a" + "0" * 128
        assert is_nft_interaction(calldata) is True

    def test_erc20_transfer_not_nft(self):
        calldata = "0xa9059cbb" + "0" * 64
        assert is_nft_interaction(calldata) is False

    def test_empty_calldata_not_nft(self):
        assert is_nft_interaction("0x") is False

    def test_uniswap_not_nft(self):
        calldata = "0x3593564c" + "0" * 128
        assert is_nft_interaction(calldata) is False


# ---------------------------------------------------------------------------
# classify_contract
# ---------------------------------------------------------------------------


class TestClassifyContract:
    def test_erc20_not_nft_not_defi(self):
        calldata = "0xa9059cbb" + "0" * 64
        result = classify_contract(calldata)
        assert result["is_nft"] is False
        assert result["standard"] == "ERC-20"

    def test_erc721_is_nft(self):
        calldata = "0x42842e0e" + "0" * 96
        result = classify_contract(calldata)
        assert result["is_nft"] is True

    def test_uniswap_is_defi(self):
        calldata = "0x3593564c" + "0" * 128
        result = classify_contract(calldata)
        assert result["is_defi"] is True
        assert result["is_nft"] is False

    def test_small_bytecode_unknown_is_risk_flagged(self):
        calldata = "0xdeadbeef" + "0" * 64
        result = classify_contract(calldata, bytecode_size=50)
        assert "minimal_bytecode" in result["risk_indicators"]

    def test_transfer_from_flagged_as_token_transfer(self):
        calldata = "0x23b872dd" + "0" * 96
        result = classify_contract(calldata)
        assert "token_transfer" in result["risk_indicators"]

    def test_result_has_required_keys(self):
        result = classify_contract("0xa9059cbb" + "0" * 64)
        for key in ("standard", "function", "is_nft", "is_defi", "risk_indicators", "decoded"):
            assert key in result

    def test_known_type_passed_through(self):
        result = classify_contract("0xa9059cbb" + "0" * 64, known_contract_type="stablecoin")
        assert result["known_type"] == "stablecoin"


# ---------------------------------------------------------------------------
# analyze_nft_transfer
# ---------------------------------------------------------------------------


class TestAnalyzeNftTransfer:
    def test_nft_calldata_detected(self):
        calldata = "0x42842e0e" + "0" * 96
        result = analyze_nft_transfer(calldata, "0xcontract", "ethereum")
        assert result["is_nft_transfer"] is True
        assert result["contract"] == "0xcontract"
        assert result["chain"] == "ethereum"

    def test_non_nft_calldata_not_detected(self):
        calldata = "0xa9059cbb" + "0" * 64
        result = analyze_nft_transfer(calldata, "0xcontract", "ethereum")
        assert result["is_nft_transfer"] is False

    def test_empty_calldata_not_nft(self):
        result = analyze_nft_transfer("0x", "0xcontract")
        assert result["is_nft_transfer"] is False

    def test_erc1155_batch_transfer_detected(self):
        calldata = "0x2eb2c2d6" + "0" * 128
        result = analyze_nft_transfer(calldata, "0xnft", "polygon")
        assert result["is_nft_transfer"] is True
        assert result["standard"] == "ERC-1155"


# ---------------------------------------------------------------------------
# get_supported_standards
# ---------------------------------------------------------------------------


class TestGetSupportedStandards:
    def test_returns_list(self):
        standards = get_supported_standards()
        assert isinstance(standards, list)
        assert len(standards) > 0

    def test_contains_erc20(self):
        assert "ERC-20" in get_supported_standards()

    def test_contains_erc721(self):
        assert "ERC-721" in get_supported_standards()

    def test_is_sorted(self):
        standards = get_supported_standards()
        assert standards == sorted(standards)
