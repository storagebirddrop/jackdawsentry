"""
Unit tests for SolanaRpcClient
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.collectors.rpc.solana_rpc import SolanaRpcClient, LAMPORTS_PER_SOL


@pytest.fixture
def client():
    return SolanaRpcClient("https://api.mainnet-beta.solana.com", "solana")


class TestSolanaRpcClientInit:
    def test_init_sets_blockchain(self, client):
        assert client.blockchain == "solana"

    def test_init_sets_rpc_url(self, client):
        assert "mainnet-beta" in client.rpc_url

    def test_lamports_constant(self):
        assert LAMPORTS_PER_SOL == 1_000_000_000


class TestSolanaGetTransaction:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, client):
        with patch.object(client, '_json_rpc', new_callable=AsyncMock, return_value=None):
            result = await client.get_transaction("fakesig")
        assert result is None

    @pytest.mark.asyncio
    async def test_parses_transaction_fields(self, client):
        mock_result = {
            "slot": 300_000_000,
            "blockTime": 1700000000,
            "meta": {
                "fee": 5000,
                "err": None,
                "preBalances": [2_000_000_000, 500_000_000],
                "postBalances": [1_500_000_000, 1_000_000_000],
            },
            "transaction": {
                "message": {
                    "accountKeys": ["sender111", "recipient222"],
                }
            },
        }
        with patch.object(client, '_json_rpc', new_callable=AsyncMock, return_value=mock_result):
            tx = await client.get_transaction("testsig123")

        assert tx is not None
        assert tx.blockchain == "solana"
        assert tx.from_address == "sender111"
        assert tx.to_address == "recipient222"
        assert tx.block_number == 300_000_000
        assert tx.status == "confirmed"

    @pytest.mark.asyncio
    async def test_failed_tx_status(self, client):
        mock_result = {
            "slot": 100,
            "blockTime": 1700000000,
            "meta": {"fee": 5000, "err": {"InstructionError": [0, "Custom"]}, "preBalances": [], "postBalances": []},
            "transaction": {"message": {"accountKeys": ["a", "b"]}},
        }
        with patch.object(client, '_json_rpc', new_callable=AsyncMock, return_value=mock_result):
            tx = await client.get_transaction("failsig")
        assert tx.status == "failed"

    @pytest.mark.asyncio
    async def test_value_converted_from_lamports(self, client):
        mock_result = {
            "slot": 1,
            "blockTime": 1700000000,
            "meta": {
                "fee": 5000,
                "err": None,
                "preBalances": [3_000_000_000, 0],
                "postBalances": [2_000_000_000, 1_000_000_000],
            },
            "transaction": {"message": {"accountKeys": ["a", "b"]}},
        }
        with patch.object(client, '_json_rpc', new_callable=AsyncMock, return_value=mock_result):
            tx = await client.get_transaction("testsig")
        # value should be 1 SOL
        assert abs(tx.value - 1.0) < 1e-6

    @pytest.mark.asyncio
    async def test_fee_converted_from_lamports(self, client):
        mock_result = {
            "slot": 1,
            "blockTime": 1700000000,
            "meta": {"fee": 5000, "err": None, "preBalances": [1_000_000_000], "postBalances": [995_000_000]},
            "transaction": {"message": {"accountKeys": ["a"]}},
        }
        with patch.object(client, '_json_rpc', new_callable=AsyncMock, return_value=mock_result):
            tx = await client.get_transaction("feesig")
        assert abs(tx.fee - 5000 / LAMPORTS_PER_SOL) < 1e-12


class TestSolanaGetAddressInfo:
    @pytest.mark.asyncio
    async def test_returns_none_on_none(self, client):
        with patch.object(client, '_json_rpc', new_callable=AsyncMock, return_value=None):
            result = await client.get_address_info("fakeaddress")
        assert result is None

    @pytest.mark.asyncio
    async def test_parses_balance(self, client):
        async def mock_json_rpc(method, params=None, **kwargs):
            if method == "getBalance":
                return {"value": 2_000_000_000}
            if method == "getSignaturesForAddress":
                return [{"signature": "sig1"}, {"signature": "sig2"}]
            return None

        with patch.object(client, '_json_rpc', side_effect=mock_json_rpc):
            addr = await client.get_address_info("myaddress")

        assert addr is not None
        assert abs(addr.balance - 2.0) < 1e-6
        assert addr.transaction_count == 2

    @pytest.mark.asyncio
    async def test_address_type_is_account(self, client):
        async def mock_json_rpc(method, params=None, **kwargs):
            if method == "getBalance":
                return {"value": 0}
            return []

        with patch.object(client, '_json_rpc', side_effect=mock_json_rpc):
            addr = await client.get_address_info("empty")

        assert addr.type == "account"


class TestSolanaGetBlock:
    @pytest.mark.asyncio
    async def test_returns_none_on_none(self, client):
        with patch.object(client, '_json_rpc', new_callable=AsyncMock, return_value=None):
            result = await client.get_block(100)
        assert result is None

    @pytest.mark.asyncio
    async def test_parses_block_fields(self, client):
        mock_result = {
            "blockhash": "bh123",
            "previousBlockhash": "bh000",
            "blockTime": 1700000000,
            "signatures": ["s1", "s2", "s3"],
        }
        with patch.object(client, '_json_rpc', new_callable=AsyncMock, return_value=mock_result):
            block = await client.get_block(42)

        assert block.number == 42
        assert block.hash == "bh123"
        assert block.blockchain == "solana"
        assert block.transaction_count == 3
        assert block.parent_hash == "bh000"


class TestSolanaGetLatestBlockNumber:
    @pytest.mark.asyncio
    async def test_returns_slot(self, client):
        with patch.object(client, '_json_rpc', new_callable=AsyncMock, return_value=12345678):
            slot = await client.get_latest_block_number()
        assert slot == 12345678

    @pytest.mark.asyncio
    async def test_returns_zero_on_none(self, client):
        with patch.object(client, '_json_rpc', new_callable=AsyncMock, return_value=None):
            slot = await client.get_latest_block_number()
        assert slot == 0
