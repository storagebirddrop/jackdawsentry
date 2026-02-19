"""
Unit tests for the RPC client factory (get_rpc_client).
"""

import pytest
from unittest.mock import patch, MagicMock

from src.collectors.rpc.factory import get_rpc_client
from src.collectors.rpc.solana_rpc import SolanaRpcClient
from src.collectors.rpc.tron_rpc import TronRpcClient
from src.collectors.rpc.xrpl_rpc import XrplRpcClient
from src.collectors.rpc.evm_rpc import EvmRpcClient
from src.collectors.rpc.bitcoin_rpc import BitcoinRpcClient


def _make_config(family: str, rpc_url: str = "https://node.example.com") -> dict:
    return {"family": family, "rpc_url": rpc_url}


class TestFactorySolana:
    def test_returns_solana_client(self):
        with patch("src.collectors.rpc.factory._clients", {}), \
             patch("src.collectors.rpc.factory.get_blockchain_config",
                   return_value=_make_config("solana")):
            client = get_rpc_client("solana")
        assert isinstance(client, SolanaRpcClient)

    def test_solana_client_blockchain_attribute(self):
        with patch("src.collectors.rpc.factory._clients", {}), \
             patch("src.collectors.rpc.factory.get_blockchain_config",
                   return_value=_make_config("solana")):
            client = get_rpc_client("solana-mainnet")
        assert client.blockchain == "solana-mainnet"


class TestFactoryTron:
    def test_returns_tron_client(self):
        with patch("src.collectors.rpc.factory._clients", {}), \
             patch("src.collectors.rpc.factory.get_blockchain_config",
                   return_value=_make_config("tron")):
            client = get_rpc_client("tron")
        assert isinstance(client, TronRpcClient)


class TestFactoryXrpl:
    def test_returns_xrpl_client(self):
        with patch("src.collectors.rpc.factory._clients", {}), \
             patch("src.collectors.rpc.factory.get_blockchain_config",
                   return_value=_make_config("xrpl")):
            client = get_rpc_client("xrpl")
        assert isinstance(client, XrplRpcClient)


class TestFactoryEvm:
    def test_returns_evm_client(self):
        with patch("src.collectors.rpc.factory._clients", {}), \
             patch("src.collectors.rpc.factory.get_blockchain_config",
                   return_value=_make_config("evm")):
            client = get_rpc_client("ethereum")
        assert isinstance(client, EvmRpcClient)


class TestFactoryUnknown:
    def test_returns_none_for_unknown_family(self):
        with patch("src.collectors.rpc.factory._clients", {}), \
             patch("src.collectors.rpc.factory.get_blockchain_config",
                   return_value={"family": "unknown", "rpc_url": "http://x"}):
            client = get_rpc_client("unknown-chain")
        assert client is None

    def test_returns_none_when_no_config(self):
        with patch("src.collectors.rpc.factory._clients", {}), \
             patch("src.collectors.rpc.factory.get_blockchain_config", return_value=None):
            client = get_rpc_client("notachain")
        assert client is None

    def test_returns_none_when_no_rpc_url(self):
        with patch("src.collectors.rpc.factory._clients", {}), \
             patch("src.collectors.rpc.factory.get_blockchain_config",
                   return_value={"family": "evm", "rpc_url": ""}):
            client = get_rpc_client("ethereum")
        assert client is None


class TestFactoryCaching:
    def test_returns_same_instance_second_call(self):
        cache = {}
        with patch("src.collectors.rpc.factory._clients", cache), \
             patch("src.collectors.rpc.factory.get_blockchain_config",
                   return_value=_make_config("solana")) as mock_cfg:
            c1 = get_rpc_client("solana")
            c2 = get_rpc_client("solana")
        assert c1 is c2
        # get_blockchain_config only called once (cached on second call)
        assert mock_cfg.call_count == 1
