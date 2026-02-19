"""
Unit tests for TronRpcClient
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.collectors.rpc.tron_rpc import TronRpcClient, SUN_PER_TRX


@pytest.fixture
def client():
    return TronRpcClient("https://api.trongrid.io", "tron")


class TestTronRpcClientInit:
    def test_init_sets_blockchain(self, client):
        assert client.blockchain == "tron"

    def test_sun_constant(self):
        assert SUN_PER_TRX == 1_000_000


class TestTronGetTransaction:
    @pytest.mark.asyncio
    async def test_returns_none_when_empty(self, client):
        with patch.object(client, '_rest_post', new_callable=AsyncMock, return_value={}):
            result = await client.get_transaction("faketxid")
        assert result is None

    @pytest.mark.asyncio
    async def test_parses_successful_transaction(self, client):
        mock_result = {
            "txID": "aaa111",
            "raw_data": {
                "contract": [{
                    "parameter": {
                        "value": {
                            "owner_address": "TFromAddress",
                            "to_address": "TToAddress",
                            "amount": 1_000_000,  # 1 TRX
                        }
                    }
                }],
                "timestamp": 1700000000000,
            },
            "ret": [{"contractRet": "SUCCESS"}],
            "fee": 500_000,
        }
        with patch.object(client, '_rest_post', new_callable=AsyncMock, return_value=mock_result):
            tx = await client.get_transaction("aaa111")

        assert tx is not None
        assert tx.hash == "aaa111"
        assert tx.blockchain == "tron"
        assert tx.from_address == "TFromAddress"
        assert tx.to_address == "TToAddress"
        assert abs(tx.value - 1.0) < 1e-6
        assert tx.status == "confirmed"

    @pytest.mark.asyncio
    async def test_failed_transaction(self, client):
        mock_result = {
            "txID": "fail999",
            "raw_data": {
                "contract": [{"parameter": {"value": {"owner_address": "A", "to_address": "B", "amount": 0}}}],
                "timestamp": 1700000000000,
            },
            "ret": [{"contractRet": "REVERT"}],
        }
        with patch.object(client, '_rest_post', new_callable=AsyncMock, return_value=mock_result):
            tx = await client.get_transaction("fail999")
        assert tx.status == "failed"

    @pytest.mark.asyncio
    async def test_fee_conversion(self, client):
        mock_result = {
            "txID": "fee123",
            "raw_data": {
                "contract": [{"parameter": {"value": {"owner_address": "A", "to_address": "B", "amount": 1_000_000}}}],
                "timestamp": 1700000000000,
            },
            "ret": [{"contractRet": "SUCCESS"}],
            "fee": 100_000,  # 0.1 TRX
        }
        with patch.object(client, '_rest_post', new_callable=AsyncMock, return_value=mock_result):
            tx = await client.get_transaction("fee123")
        assert abs(tx.fee - 0.1) < 1e-6


class TestTronGetAddressInfo:
    @pytest.mark.asyncio
    async def test_returns_none_on_none(self, client):
        with patch.object(client, '_rest_post', new_callable=AsyncMock, return_value=None):
            result = await client.get_address_info("fakeaddr")
        assert result is None

    @pytest.mark.asyncio
    async def test_parses_balance(self, client):
        with patch.object(client, '_rest_post', new_callable=AsyncMock, return_value={"balance": 5_000_000}):
            addr = await client.get_address_info("TMyAddress")

        assert addr is not None
        assert abs(addr.balance - 5.0) < 1e-6
        assert addr.blockchain == "tron"

    @pytest.mark.asyncio
    async def test_empty_response_returns_none(self, client):
        # Tron API returns {} for unknown addresses; implementation treats falsy as None
        with patch.object(client, '_rest_post', new_callable=AsyncMock, return_value={}):
            addr = await client.get_address_info("TEmpty")
        assert addr is None


class TestTronGetAddressTransactions:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, client):
        result = await client.get_address_transactions("TAddr")
        assert result == []


class TestTronGetBlock:
    @pytest.mark.asyncio
    async def test_returns_none_on_none(self, client):
        with patch.object(client, '_rest_post', new_callable=AsyncMock, return_value=None):
            result = await client.get_block(1000)
        assert result is None

    @pytest.mark.asyncio
    async def test_parses_block_fields(self, client):
        mock_result = {
            "blockID": "blockid000",
            "block_header": {
                "raw_data": {
                    "number": 50_000_000,
                    "timestamp": 1700000000000,
                    "parentHash": "parenthash000",
                }
            },
            "transactions": [{"id": "tx1"}, {"id": "tx2"}],
        }
        with patch.object(client, '_rest_post', new_callable=AsyncMock, return_value=mock_result):
            block = await client.get_block(50_000_000)

        assert block.number == 50_000_000
        assert block.hash == "blockid000"
        assert block.transaction_count == 2
        assert block.parent_hash == "parenthash000"


class TestTronGetLatestBlockNumber:
    @pytest.mark.asyncio
    async def test_returns_block_number(self, client):
        mock_result = {
            "block_header": {"raw_data": {"number": 60_000_000}}
        }
        with patch.object(client, '_rest_get', new_callable=AsyncMock, return_value=mock_result):
            num = await client.get_latest_block_number()
        assert num == 60_000_000
