"""
Unit tests for XrplRpcClient
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from src.collectors.rpc.xrpl_rpc import XrplRpcClient, DROPS_PER_XRP, XRPL_EPOCH_OFFSET, _xrpl_ts_to_datetime


@pytest.fixture
def client():
    return XrplRpcClient("https://xrplcluster.com", "xrpl")


class TestXrplRpcClientInit:
    def test_init_sets_blockchain(self, client):
        assert client.blockchain == "xrpl"

    def test_drops_constant(self):
        assert DROPS_PER_XRP == 1_000_000

    def test_epoch_offset(self):
        assert XRPL_EPOCH_OFFSET == 946684800


class TestXrplTimestampConversion:
    def test_none_returns_now(self):
        dt = _xrpl_ts_to_datetime(None)
        assert isinstance(dt, datetime)
        assert dt.tzinfo is not None

    def test_converts_correctly(self):
        dt = _xrpl_ts_to_datetime(0)
        assert dt.year == 2000
        assert dt.month == 1
        assert dt.day == 1


class TestXrplGetTransaction:
    @pytest.mark.asyncio
    async def test_returns_none_on_error_status(self, client):
        mock_result = {"status": "error", "error": "txnNotFound"}
        with patch.object(client, '_xrpl_rpc', new_callable=AsyncMock, return_value=mock_result):
            result = await client.get_transaction("FAKETXHASH")
        assert result is None

    @pytest.mark.asyncio
    async def test_parses_payment_transaction(self, client):
        mock_result = {
            "hash": "ABC123",
            "Account": "rSender",
            "Destination": "rReceiver",
            "Amount": "5000000",  # 5 XRP in drops
            "Fee": "12",
            "date": 0,
            "validated": True,
            "ledger_index": 80_000_000,
            "meta": {"TransactionResult": "tesSUCCESS"},
        }
        with patch.object(client, '_xrpl_rpc', new_callable=AsyncMock, return_value=mock_result):
            tx = await client.get_transaction("ABC123")

        assert tx is not None
        assert tx.hash == "ABC123"
        assert tx.from_address == "rSender"
        assert tx.to_address == "rReceiver"
        assert abs(tx.value - 5.0) < 1e-6
        assert tx.status == "confirmed"
        assert tx.block_number == 80_000_000

    @pytest.mark.asyncio
    async def test_iou_amount_parsed_as_float(self, client):
        mock_result = {
            "hash": "IOU123",
            "Account": "rSender",
            "Destination": "rReceiver",
            "Amount": {"value": "100.5", "currency": "USD", "issuer": "rIssuer"},
            "Fee": "12",
            "date": 0,
            "validated": True,
            "meta": {"TransactionResult": "tesSUCCESS"},
        }
        with patch.object(client, '_xrpl_rpc', new_callable=AsyncMock, return_value=mock_result):
            tx = await client.get_transaction("IOU123")
        assert abs(tx.value - 100.5) < 1e-6

    @pytest.mark.asyncio
    async def test_failed_tx_status(self, client):
        mock_result = {
            "hash": "FAIL",
            "Account": "a",
            "Destination": "b",
            "Amount": "1000",
            "Fee": "12",
            "date": 0,
            "validated": True,
            "meta": {"TransactionResult": "tecUNFUNDED_PAYMENT"},
        }
        with patch.object(client, '_xrpl_rpc', new_callable=AsyncMock, return_value=mock_result):
            tx = await client.get_transaction("FAIL")
        assert tx.status == "failed"

    @pytest.mark.asyncio
    async def test_fee_conversion(self, client):
        mock_result = {
            "hash": "FEE",
            "Account": "a",
            "Destination": "b",
            "Amount": "1000000",
            "Fee": "1000000",  # 1 XRP fee
            "date": 0,
            "validated": True,
            "meta": {"TransactionResult": "tesSUCCESS"},
        }
        with patch.object(client, '_xrpl_rpc', new_callable=AsyncMock, return_value=mock_result):
            tx = await client.get_transaction("FEE")
        assert abs(tx.fee - 1.0) < 1e-6


class TestXrplGetAddressInfo:
    @pytest.mark.asyncio
    async def test_returns_none_on_none(self, client):
        with patch.object(client, '_xrpl_rpc', new_callable=AsyncMock, return_value=None):
            result = await client.get_address_info("rFake")
        assert result is None

    @pytest.mark.asyncio
    async def test_parses_balance(self, client):
        mock_result = {
            "account_data": {
                "Account": "rMyAddress",
                "Balance": "10000000",  # 10 XRP
                "Sequence": 42,
            }
        }
        with patch.object(client, '_xrpl_rpc', new_callable=AsyncMock, return_value=mock_result):
            addr = await client.get_address_info("rMyAddress")

        assert addr is not None
        assert abs(addr.balance - 10.0) < 1e-6
        assert addr.transaction_count == 42
        assert addr.blockchain == "xrpl"


class TestXrplGetAddressTransactions:
    @pytest.mark.asyncio
    async def test_returns_empty_on_none(self, client):
        with patch.object(client, '_xrpl_rpc', new_callable=AsyncMock, return_value=None):
            result = await client.get_address_transactions("rAddr")
        assert result == []

    @pytest.mark.asyncio
    async def test_parses_multiple_transactions(self, client):
        mock_result = {
            "transactions": [
                {
                    "tx": {"hash": "H1", "Account": "rA", "Destination": "rB", "Amount": "1000000", "Fee": "12", "date": 0},
                    "meta": {"TransactionResult": "tesSUCCESS"},
                },
                {
                    "tx": {"hash": "H2", "Account": "rC", "Destination": "rD", "Amount": "2000000", "Fee": "12", "date": 0},
                    "meta": {"TransactionResult": "tesSUCCESS"},
                },
            ]
        }
        with patch.object(client, '_xrpl_rpc', new_callable=AsyncMock, return_value=mock_result):
            txs = await client.get_address_transactions("rAddr")

        assert len(txs) == 2
        assert txs[0].hash == "H1"
        assert txs[1].hash == "H2"


class TestXrplGetBlock:
    @pytest.mark.asyncio
    async def test_returns_none_on_none(self, client):
        with patch.object(client, '_xrpl_rpc', new_callable=AsyncMock, return_value=None):
            result = await client.get_block(100)
        assert result is None

    @pytest.mark.asyncio
    async def test_parses_ledger(self, client):
        mock_result = {
            "ledger": {
                "ledger_index": "80000000",
                "ledger_hash": "LEDGERHASH",
                "parent_hash": "PARENTHASH",
                "close_time": 0,
                "transaction_count": 250,
            }
        }
        with patch.object(client, '_xrpl_rpc', new_callable=AsyncMock, return_value=mock_result):
            block = await client.get_block(80_000_000)

        assert block.number == 80_000_000
        assert block.hash == "LEDGERHASH"
        assert block.parent_hash == "PARENTHASH"
        assert block.transaction_count == 250


class TestXrplGetLatestBlockNumber:
    @pytest.mark.asyncio
    async def test_returns_ledger_index(self, client):
        mock_result = {"ledger": {"ledger_index": "90000000"}}
        with patch.object(client, '_xrpl_rpc', new_callable=AsyncMock, return_value=mock_result):
            num = await client.get_latest_block_number()
        assert num == 90_000_000
