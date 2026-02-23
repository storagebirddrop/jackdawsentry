"""
Jackdaw Sentry — DeFi Protocol Registry (M13)

Canonical registry of 50+ known DeFi protocols with:
  - contract addresses per chain
  - protocol type classification
  - risk metadata

Protocol types:
  bridge        — cross-chain token bridges
  dex           — decentralised exchanges / AMMs
  lending       — lending/borrowing protocols
  staking       — liquid staking / validator staking
  yield_farming — yield aggregators / vaults
  mixer         — privacy / tumbling protocols
  nft           — NFT marketplaces
  payments      — payment processors
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Dict
from typing import List
from typing import Optional
from typing import Set

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Protocol:
    name: str
    protocol_type: (
        str  # bridge | dex | lending | staking | yield_farming | mixer | nft | payments
    )
    chains: List[str]
    addresses: Dict[str, List[str]]  # chain → list of known contract addresses
    risk_level: str = "low"  # low | medium | high | critical
    description: str = ""
    website: str = ""
    tags: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Registry — 50+ protocols
# ---------------------------------------------------------------------------

_PROTOCOLS: List[Protocol] = [
    # ── Bridges ──────────────────────────────────────────────────────────────
    Protocol(
        name="Wormhole",
        protocol_type="bridge",
        chains=["ethereum", "solana", "polygon", "bsc", "avalanche", "arbitrum"],
        addresses={
            "ethereum": ["0x98f3c9e6e3face36baad05fe09d375ef1464288b"],
            "solana": ["worm2ZoG2kUd4vFXhvjh93UUH596ayRfgQ2MgjNMTth"],
            "polygon": ["0x7A4B5464EC2aA65fEFF3a5AaCb3E7a98AfAAe6C7"],
            "bsc": ["0x98f3c9e6e3face36baad05fe09d375ef1464288b"],
        },
        risk_level="medium",
        description="Cross-chain messaging and token bridge",
        website="https://wormhole.com",
        tags=["bridge", "cross-chain"],
    ),
    Protocol(
        name="LayerZero",
        protocol_type="bridge",
        chains=["ethereum", "polygon", "bsc", "arbitrum", "optimism", "avalanche"],
        addresses={
            "ethereum": ["0x66a71dcef29a0ffbdbe3c6a460a3b5bc225cd675"],
            "polygon": ["0x3c2269811836af69497e5f486a85d7316753cf62"],
            "bsc": ["0x3c2269811836af69497e5f486a85d7316753cf62"],
            "arbitrum": ["0x3c2269811836af69497e5f486a85d7316753cf62"],
            "optimism": ["0x3c2269811836af69497e5f486a85d7316753cf62"],
            "avalanche": ["0x3c2269811836af69497e5f486a85d7316753cf62"],
        },
        risk_level="low",
        description="Omnichain interoperability protocol",
        website="https://layerzero.network",
        tags=["bridge", "omnichain"],
    ),
    Protocol(
        name="Stargate Finance",
        protocol_type="bridge",
        chains=["ethereum", "polygon", "bsc", "arbitrum", "optimism", "avalanche"],
        addresses={
            "ethereum": ["0x8731d54e9d02c286767d56ac03e8037c07e01e98"],
            "polygon": ["0x45a01e4e04f14f7a4a6702c74187c5f6222033cd"],
            "arbitrum": ["0x53bf833a5d6c4dda888f69c22c88c9f356a41614"],
            "optimism": ["0xb0d502e938ed5f4df2e681fe6e419ff29631d62b"],
        },
        risk_level="low",
        description="Composable liquidity bridge built on LayerZero",
        website="https://stargate.finance",
        tags=["bridge", "liquidity"],
    ),
    Protocol(
        name="Across Protocol",
        protocol_type="bridge",
        chains=["ethereum", "polygon", "arbitrum", "optimism", "bsc"],
        addresses={
            "ethereum": ["0x4d9079bb4165aeb4084c526a32695dcfd2f77381"],
            "arbitrum": ["0xe35e9842fceaCA96570B734083f4a58e8F7C5f2A"],
            "optimism": ["0x6f26bf09b1c792e3228e5467807a900a503c0281"],
        },
        risk_level="low",
        description="Fast, capital-efficient bridge using UMA's optimistic oracle",
        website="https://across.to",
        tags=["bridge"],
    ),
    Protocol(
        name="Multichain (AnySwap)",
        protocol_type="bridge",
        chains=["ethereum", "bsc", "polygon", "avalanche", "fantom"],
        addresses={
            "ethereum": ["0x765277eebeca2e31912c9946eae1021199b39c61"],
            "bsc": ["0xd1c5966f9f5ee6881ff6b261bbeda45972b1b5f3"],
        },
        risk_level="high",
        description="Cross-chain router protocol (hacked 2023 — monitor carefully)",
        website="https://multichain.org",
        tags=["bridge", "hacked"],
    ),
    Protocol(
        name="Hop Protocol",
        protocol_type="bridge",
        chains=["ethereum", "polygon", "arbitrum", "optimism", "xdai"],
        addresses={
            "ethereum": ["0x3666f603cc164936c1b87e207f36beba4ac5f18a"],
            "polygon": ["0x553bc791d746767166fA3888432038193cEED5E2"],
        },
        risk_level="low",
        description="Scalable rollup-to-rollup token bridge",
        website="https://hop.exchange",
        tags=["bridge", "l2"],
    ),
    Protocol(
        name="Celer cBridge",
        protocol_type="bridge",
        chains=["ethereum", "bsc", "polygon", "arbitrum", "optimism", "avalanche"],
        addresses={
            "ethereum": ["0x5427fefa711eff984124bfbb1ab6fbf5e3da1820"],
            "bsc": ["0xdd90e5e87a2081dcf0391920868ebc2ffb81a1af"],
        },
        risk_level="low",
        description="Multi-chain liquidity network",
        website="https://cbridge.celer.network",
        tags=["bridge"],
    ),
    # ── DEXes ─────────────────────────────────────────────────────────────────
    Protocol(
        name="Uniswap V2",
        protocol_type="dex",
        chains=["ethereum", "polygon", "bsc"],
        addresses={
            "ethereum": ["0x7a250d5630b4cf539739df2c5dacb4c659f2488d"],
            "polygon": ["0xa5e0829caced155ff79577b4a2d8a2362770bf5c"],
        },
        risk_level="low",
        description="Automated market maker — constant product formula",
        website="https://uniswap.org",
        tags=["dex", "amm"],
    ),
    Protocol(
        name="Uniswap V3",
        protocol_type="dex",
        chains=["ethereum", "polygon", "arbitrum", "optimism", "bsc"],
        addresses={
            "ethereum": [
                "0xe592427a0aece92de3edee1f18e0157c05861564",
                "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45",
            ],
            "polygon": ["0xe592427a0aece92de3edee1f18e0157c05861564"],
            "arbitrum": ["0xe592427a0aece92de3edee1f18e0157c05861564"],
        },
        risk_level="low",
        description="Concentrated liquidity AMM",
        website="https://uniswap.org",
        tags=["dex", "amm", "concentrated-liquidity"],
    ),
    Protocol(
        name="Curve Finance",
        protocol_type="dex",
        chains=["ethereum", "polygon", "arbitrum", "avalanche"],
        addresses={
            "ethereum": [
                "0x99e921ad2c4dbf743735b9bea3682db22f7a7a3f",
                "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",
            ],
        },
        risk_level="low",
        description="AMM optimised for stablecoin and pegged asset swaps",
        website="https://curve.fi",
        tags=["dex", "stablecoin"],
    ),
    Protocol(
        name="SushiSwap",
        protocol_type="dex",
        chains=["ethereum", "polygon", "arbitrum", "avalanche", "bsc"],
        addresses={
            "ethereum": ["0xc0aee478e3658e2610c5f7a4a2e1777ce9e4f2ac"],
            "polygon": ["0xc35dadb65012ec5796536bd9864ed8773abc74c4"],
        },
        risk_level="low",
        description="Multi-chain AMM and DeFi hub",
        website="https://sushi.com",
        tags=["dex", "amm"],
    ),
    Protocol(
        name="PancakeSwap",
        protocol_type="dex",
        chains=["bsc", "ethereum"],
        addresses={
            "bsc": [
                "0x10ed43c718714eb63d5aa57b78b54704e256024e",
                "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73",
            ],
        },
        risk_level="low",
        description="Leading DEX on BNB Chain",
        website="https://pancakeswap.finance",
        tags=["dex", "amm"],
    ),
    Protocol(
        name="1inch",
        protocol_type="dex",
        chains=["ethereum", "polygon", "bsc", "arbitrum", "optimism", "avalanche"],
        addresses={
            "ethereum": [
                "0x1111111254fb6c44bac0bed2854e76f90643097d",
                "0x1111111254eeb25477b68fb85ed929f73a960582",
            ],
            "polygon": ["0x1111111254fb6c44bac0bed2854e76f90643097d"],
        },
        risk_level="low",
        description="DEX aggregator routing trades across multiple AMMs",
        website="https://1inch.io",
        tags=["dex", "aggregator"],
    ),
    Protocol(
        name="Jupiter",
        protocol_type="dex",
        chains=["solana"],
        addresses={
            "solana": ["JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"],
        },
        risk_level="low",
        description="Leading DEX aggregator on Solana",
        website="https://jup.ag",
        tags=["dex", "aggregator", "solana"],
    ),
    Protocol(
        name="dYdX",
        protocol_type="dex",
        chains=["ethereum", "starkex"],
        addresses={
            "ethereum": ["0xd54f502e184b6b739d7d27a6410a67dc462d69c8"],
        },
        risk_level="low",
        description="Decentralised perpetuals and margin trading",
        website="https://dydx.exchange",
        tags=["dex", "derivatives", "perps"],
    ),
    # ── Lending ───────────────────────────────────────────────────────────────
    Protocol(
        name="Aave V2",
        protocol_type="lending",
        chains=["ethereum", "polygon", "avalanche"],
        addresses={
            "ethereum": ["0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9"],
            "polygon": ["0x8dff5e27ea6b7ac08ebfdf9eb090f32ee9a30fcf"],
        },
        risk_level="low",
        description="Decentralised lending and borrowing protocol",
        website="https://aave.com",
        tags=["lending", "borrowing"],
    ),
    Protocol(
        name="Aave V3",
        protocol_type="lending",
        chains=["ethereum", "polygon", "arbitrum", "optimism", "avalanche"],
        addresses={
            "ethereum": ["0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2"],
            "polygon": ["0x794a61358d6845594f94dc1db02a252b5b4814ad"],
            "arbitrum": ["0x794a61358d6845594f94dc1db02a252b5b4814ad"],
        },
        risk_level="low",
        description="Aave V3 with isolation mode and efficiency mode",
        website="https://aave.com",
        tags=["lending", "borrowing"],
    ),
    Protocol(
        name="Compound V2",
        protocol_type="lending",
        chains=["ethereum"],
        addresses={
            "ethereum": ["0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b"],
        },
        risk_level="low",
        description="Algorithmic money market protocol on Ethereum",
        website="https://compound.finance",
        tags=["lending", "borrowing"],
    ),
    Protocol(
        name="Compound V3",
        protocol_type="lending",
        chains=["ethereum", "polygon", "arbitrum"],
        addresses={
            "ethereum": ["0xc3d688b66703497daa19211eedff47f25384cdc3"],
        },
        risk_level="low",
        description="Compound V3 (Comet) — single-asset collateral model",
        website="https://compound.finance",
        tags=["lending", "borrowing"],
    ),
    Protocol(
        name="MakerDAO",
        protocol_type="lending",
        chains=["ethereum"],
        addresses={
            "ethereum": [
                "0x9759a6ac90977b93b58547b4a71c78317f391a28",
                "0x35d1b3f3d7966a1dfe207aa4514c12a259a0492b",
            ],
        },
        risk_level="low",
        description="DAI stablecoin and CDP lending protocol",
        website="https://makerdao.com",
        tags=["lending", "stablecoin", "cdp"],
    ),
    Protocol(
        name="Euler Finance",
        protocol_type="lending",
        chains=["ethereum"],
        addresses={
            "ethereum": ["0x27182842e098f60e3d576794a5bffb0777e025d3"],
        },
        risk_level="high",
        description="Permissionless lending protocol (exploited 2023)",
        website="https://euler.finance",
        tags=["lending", "hacked"],
    ),
    Protocol(
        name="Morpho",
        protocol_type="lending",
        chains=["ethereum", "base"],
        addresses={
            "ethereum": [
                "0x8888882f8f843896699869179fb6035b5ab7bb1b",
                "0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb",
            ],
        },
        risk_level="low",
        description="Peer-to-peer lending optimizer on top of Aave/Compound",
        website="https://morpho.xyz",
        tags=["lending", "optimizer"],
    ),
    Protocol(
        name="Radiant Capital",
        protocol_type="lending",
        chains=["arbitrum", "bsc"],
        addresses={
            "arbitrum": ["0xf4b1486dd74d07706052a33d31d7c0aafd0659e1"],
            "bsc": ["0xd50cf00b6e600dd036ba8ef475677d816d6c4281"],
        },
        risk_level="medium",
        description="Omnichain money market (exploited 2024)",
        website="https://radiant.capital",
        tags=["lending", "omnichain"],
    ),
    # ── Staking ───────────────────────────────────────────────────────────────
    Protocol(
        name="Lido Finance",
        protocol_type="staking",
        chains=["ethereum", "solana", "polygon"],
        addresses={
            "ethereum": [
                "0xae7ab96520de3a18e5e111b5eaab095312d7fe84",
                "0xdc24316b9ae028f1497c275eb9192a3ea0f67022",
            ],
            "solana": ["CrpYkTSz4hkdENNfEXeB61ipTiHzmKjRSZxVaLMez5tA"],
        },
        risk_level="low",
        description="Liquid staking for ETH (stETH) and SOL (stSOL)",
        website="https://lido.fi",
        tags=["staking", "liquid-staking"],
    ),
    Protocol(
        name="Rocket Pool",
        protocol_type="staking",
        chains=["ethereum"],
        addresses={
            "ethereum": [
                "0xdd3f50f8a6cafbe9b31a427582963f465e745af8",
                "0xae78736cd615f374d3085123a210448e74fc6393",
            ],
        },
        risk_level="low",
        description="Decentralised Ethereum staking protocol (rETH)",
        website="https://rocketpool.net",
        tags=["staking", "liquid-staking"],
    ),
    Protocol(
        name="Frax Ether",
        protocol_type="staking",
        chains=["ethereum"],
        addresses={
            "ethereum": ["0xbafa44efe7901e04e39dad13167d089c559c1138"],
        },
        risk_level="low",
        description="Liquid ETH staking from the Frax ecosystem (frxETH)",
        website="https://frax.finance",
        tags=["staking", "liquid-staking"],
    ),
    Protocol(
        name="Stader Labs",
        protocol_type="staking",
        chains=["ethereum", "polygon", "bsc", "avalanche"],
        addresses={
            "ethereum": ["0xcf5ea1b38380f6af39068375516daf40ed70d299"],
            "polygon": ["0xfd225c9e6601c9d38d8f98d8731bf59efcf8c0e3"],
        },
        risk_level="low",
        description="Multi-chain liquid staking protocol",
        website="https://staderlabs.com",
        tags=["staking", "liquid-staking"],
    ),
    # ── Yield Farming / Aggregators ───────────────────────────────────────────
    Protocol(
        name="Yearn Finance",
        protocol_type="yield_farming",
        chains=["ethereum", "polygon", "arbitrum", "avalanche"],
        addresses={
            "ethereum": [
                "0x50c1a2ea0a861a967d9d0ffe2ae4012c2e053804",
                "0x52f04c806eb82930f40d410259b8aa71c0abe1e0",
            ],
        },
        risk_level="low",
        description="Automated yield optimisation vaults",
        website="https://yearn.fi",
        tags=["yield", "vaults", "aggregator"],
    ),
    Protocol(
        name="Convex Finance",
        protocol_type="yield_farming",
        chains=["ethereum"],
        addresses={
            "ethereum": ["0xf403c135812408bfbe8713b5a23a04b3d48aae31"],
        },
        risk_level="low",
        description="Yield booster for Curve LP tokens",
        website="https://convexfinance.com",
        tags=["yield", "curve"],
    ),
    Protocol(
        name="Beefy Finance",
        protocol_type="yield_farming",
        chains=["bsc", "polygon", "avalanche", "arbitrum", "optimism"],
        addresses={
            "bsc": ["0x453d4ba9a2d594314df88564248497f7d74d6b2c"],
            "polygon": ["0x7845e92f2f6a9daa05a1ebe5e1e8ba6f1f8c0f5a"],
        },
        risk_level="low",
        description="Multi-chain auto-compounding yield optimiser",
        website="https://beefy.finance",
        tags=["yield", "autocompound"],
    ),
    Protocol(
        name="Harvest Finance",
        protocol_type="yield_farming",
        chains=["ethereum", "bsc", "polygon"],
        addresses={
            "ethereum": ["0xc95628b4b73b6b40e0c64a793ab7b75ded7e2882"],
        },
        risk_level="medium",
        description="Yield farming aggregator (flash loan attack history)",
        website="https://harvest.finance",
        tags=["yield", "aggregator"],
    ),
    Protocol(
        name="Pendle Finance",
        protocol_type="yield_farming",
        chains=["ethereum", "arbitrum", "bsc"],
        addresses={
            "ethereum": ["0x888888888889758F76e7103c6CbF23ABbF58F946"],
            "arbitrum": ["0x888888888889758F76e7103c6CbF23ABbF58F946"],
        },
        risk_level="low",
        description="Yield tokenisation and trading protocol",
        website="https://pendle.finance",
        tags=["yield", "tokenisation"],
    ),
    # ── Mixers / Privacy ──────────────────────────────────────────────────────
    Protocol(
        name="Tornado Cash",
        protocol_type="mixer",
        chains=["ethereum", "bsc", "polygon", "avalanche"],
        addresses={
            "ethereum": [
                "0x12d66f87a04a9e220c9d6d34deef7eb5dbbf4b22",
                "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936",
                "0x910cbd523d972eb0a6f4cae4618ad62622b39dbf",
                "0xa160cdab225685da1d56aa342ad8841c3b53f291",
            ],
            "bsc": ["0x1e34a77868e19a6647b1f2f47b51ed72dede95dd"],
        },
        risk_level="critical",
        description="OFAC-sanctioned Ethereum mixer — all interactions flagged",
        website="https://tornado.cash",
        tags=["mixer", "sanctioned", "ofac"],
    ),
    Protocol(
        name="Railgun",
        protocol_type="mixer",
        chains=["ethereum", "bsc", "polygon"],
        addresses={
            "ethereum": ["0xfa7093cdd9ee6932b4eb2c9e1cde7ce00b1fa4b9"],
            "polygon": ["0x19b620929f97b7b990801496c3b361ca5def8c71"],
        },
        risk_level="high",
        description="On-chain privacy system using zkSNARKs",
        website="https://railgun.org",
        tags=["mixer", "privacy", "zk"],
    ),
    # ── NFT Marketplaces ──────────────────────────────────────────────────────
    Protocol(
        name="OpenSea",
        protocol_type="nft",
        chains=["ethereum", "polygon"],
        addresses={
            "ethereum": ["0x00000000006c3852cbef3e08e8df289169ede581"],
        },
        risk_level="low",
        description="Leading NFT marketplace",
        website="https://opensea.io",
        tags=["nft", "marketplace"],
    ),
    Protocol(
        name="Blur",
        protocol_type="nft",
        chains=["ethereum"],
        addresses={
            "ethereum": ["0x000000000000ad05ccc4f10045630fb830b95127"],
        },
        risk_level="low",
        description="NFT marketplace and aggregator for pro traders",
        website="https://blur.io",
        tags=["nft", "marketplace"],
    ),
    # ── Payment Processors ─────────────────────────────────────────────────────
    Protocol(
        name="Tornado Cash Nova",
        protocol_type="mixer",
        chains=["ethereum"],
        addresses={
            "ethereum": ["0x84443cfd09a6fa2c4de6d5f8e3b8e0a3c5b3e82c"],
        },
        risk_level="critical",
        description="OFAC-sanctioned shielded pool on Gnosis Chain",
        website="https://tornado.cash",
        tags=["mixer", "sanctioned"],
    ),
    Protocol(
        name="Request Network",
        protocol_type="payments",
        chains=["ethereum", "polygon"],
        addresses={
            "ethereum": ["0x9adcb6f1b535e3f50e19186e24e0c6bd44e5fe5f"],
        },
        risk_level="low",
        description="Decentralised payment request protocol",
        website="https://request.network",
        tags=["payments"],
    ),
    Protocol(
        name="Sablier",
        protocol_type="payments",
        chains=["ethereum", "polygon", "arbitrum"],
        addresses={
            "ethereum": ["0xb10daee1fcf62243ae27776d7a92d39dc8740f95"],
        },
        risk_level="low",
        description="Token streaming protocol for continuous payments",
        website="https://sablier.com",
        tags=["payments", "streaming"],
    ),
    # ── Additional DEXes ─────────────────────────────────────────────────────
    Protocol(
        name="Balancer",
        protocol_type="dex",
        chains=["ethereum", "polygon", "arbitrum"],
        addresses={
            "ethereum": ["0xba12222222228d8ba445958a75a0704d566bf2c8"],
            "polygon": ["0xba12222222228d8ba445958a75a0704d566bf2c8"],
        },
        risk_level="low",
        description="Automated portfolio manager and DEX",
        website="https://balancer.fi",
        tags=["dex", "amm"],
    ),
    Protocol(
        name="Velodrome",
        protocol_type="dex",
        chains=["optimism"],
        addresses={
            "optimism": ["0xa132dab612db5cb9fc9ac426a0cc215a3423f9c9"],
        },
        risk_level="low",
        description="AMM on Optimism based on ve(3,3) tokenomics",
        website="https://velodrome.finance",
        tags=["dex", "amm", "l2"],
    ),
    Protocol(
        name="Aerodrome",
        protocol_type="dex",
        chains=["base"],
        addresses={
            "base": ["0x420dd381b31aef6683db6b902084cb0ffece40da"],
        },
        risk_level="low",
        description="AMM on Base, fork of Velodrome",
        website="https://aerodrome.finance",
        tags=["dex", "amm", "l2"],
    ),
    # ── Additional Lending ────────────────────────────────────────────────────
    Protocol(
        name="Spark Protocol",
        protocol_type="lending",
        chains=["ethereum"],
        addresses={
            "ethereum": ["0xc13e21b648a5ee794902342038ff3adab66be987"],
        },
        risk_level="low",
        description="MakerDAO-backed lending protocol (DAI/sDAI focused)",
        website="https://spark.fi",
        tags=["lending", "makerdao"],
    ),
    Protocol(
        name="Venus Protocol",
        protocol_type="lending",
        chains=["bsc"],
        addresses={
            "bsc": ["0xfd36e2c2a6789db23113685031d7f16329158384"],
        },
        risk_level="medium",
        description="Decentralised money market on BNB Chain",
        website="https://venus.io",
        tags=["lending", "bsc"],
    ),
    # ── Additional Staking ────────────────────────────────────────────────────
    Protocol(
        name="EtherFi",
        protocol_type="staking",
        chains=["ethereum"],
        addresses={
            "ethereum": ["0x308861a430be4cce5502d0a12724771fc6dcf23b"],
        },
        risk_level="low",
        description="Liquid restaking protocol (eETH / weETH)",
        website="https://ether.fi",
        tags=["staking", "restaking", "eigenlayer"],
    ),
    Protocol(
        name="Kelp DAO",
        protocol_type="staking",
        chains=["ethereum"],
        addresses={
            "ethereum": ["0x13e46b2a3f8512ed4682a8fb8b560589fe3c2172"],
        },
        risk_level="low",
        description="Liquid restaking on EigenLayer (rsETH)",
        website="https://kelpdao.xyz",
        tags=["staking", "restaking"],
    ),
    # ── Additional Yield ──────────────────────────────────────────────────────
    Protocol(
        name="Ethena",
        protocol_type="yield_farming",
        chains=["ethereum"],
        addresses={
            "ethereum": ["0x9d39a5de30e57443bff2a8307a4256c8797a3497"],
        },
        risk_level="medium",
        description="Synthetic dollar protocol (USDe) with delta-neutral yield",
        website="https://ethena.fi",
        tags=["yield", "stablecoin", "synthetic"],
    ),
    Protocol(
        name="Origin Protocol",
        protocol_type="yield_farming",
        chains=["ethereum"],
        addresses={
            "ethereum": ["0x2a8e1e676ec238d8a992307b495b45b3feaa5e86"],
        },
        risk_level="low",
        description="Yield-bearing stablecoin (OUSD) and ETH (OETH)",
        website="https://originprotocol.com",
        tags=["yield", "stablecoin"],
    ),
    # ── Additional Bridge ─────────────────────────────────────────────────────
    Protocol(
        name="Synapse Protocol",
        protocol_type="bridge",
        chains=["ethereum", "arbitrum", "optimism", "polygon", "bsc", "avalanche"],
        addresses={
            "ethereum": ["0x2796317b0ff8538f253012862c06787adfb8ceb6"],
            "arbitrum": ["0x6f4e8eba4d337f874ab57478acc2cb5bacdc19c9"],
        },
        risk_level="low",
        description="Cross-chain bridge and interoperability network",
        website="https://synapseprotocol.com",
        tags=["bridge"],
    ),
    Protocol(
        name="deBridge",
        protocol_type="bridge",
        chains=["ethereum", "polygon", "bsc", "arbitrum", "avalanche", "solana"],
        addresses={
            "ethereum": ["0x43de2d77bf8027e25dbd179b491e8d64f38398aa"],
            "polygon": ["0xde1e598b81620773454588b85d6b5d4eec32573e"],
        },
        risk_level="low",
        description="Cross-chain interoperability and liquidity transfer protocol",
        website="https://debridge.finance",
        tags=["bridge"],
    ),
]

# Build lookup indexes at import time
_BY_NAME: Dict[str, Protocol] = {p.name.lower(): p for p in _PROTOCOLS}
_BY_ADDRESS: Dict[str, Protocol] = {}
for _p in _PROTOCOLS:
    for _chain, _addrs in _p.addresses.items():
        for _addr in _addrs:
            _BY_ADDRESS[_addr.lower()] = _p


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_all_protocols() -> List[Protocol]:
    """Return all registered protocols."""
    return list(_PROTOCOLS)


def get_protocol_by_address(address: str, chain: str = None) -> Optional[Protocol]:
    """Look up a protocol by contract address (case-insensitive)."""
    return _BY_ADDRESS.get(address.lower())


def get_protocols_by_type(protocol_type: str) -> List[Protocol]:
    """Return all protocols of a given type."""
    return [p for p in _PROTOCOLS if p.protocol_type == protocol_type]


def get_known_bridge_addresses() -> Set[str]:
    """Return all known bridge contract addresses (lowercase)."""
    return {
        addr.lower()
        for p in _PROTOCOLS
        if p.protocol_type == "bridge"
        for addrs in p.addresses.values()
        for addr in addrs
    }


def get_known_dex_addresses() -> Set[str]:
    """Return all known DEX contract addresses (lowercase)."""
    return {
        addr.lower()
        for p in _PROTOCOLS
        if p.protocol_type == "dex"
        for addrs in p.addresses.values()
        for addr in addrs
    }


def get_known_mixer_addresses() -> Set[str]:
    """Return all known mixer contract addresses (lowercase)."""
    return {
        addr.lower()
        for p in _PROTOCOLS
        if p.protocol_type == "mixer"
        for addrs in p.addresses.values()
        for addr in addrs
    }


def get_high_risk_addresses() -> Set[str]:
    """Return addresses belonging to high/critical risk protocols."""
    return {
        addr.lower()
        for p in _PROTOCOLS
        if p.risk_level in {"high", "critical"}
        for addrs in p.addresses.values()
        for addr in addrs
    }


def classify_address(address: str) -> Optional[Dict]:
    """
    Classify a contract address against the registry.

    Returns a dict with protocol metadata or None if unknown.
    """
    proto = get_protocol_by_address(address)
    if not proto:
        return None
    return {
        "protocol_name": proto.name,
        "protocol_type": proto.protocol_type,
        "risk_level": proto.risk_level,
        "chains": proto.chains,
        "tags": proto.tags,
        "description": proto.description,
    }


def protocol_count() -> int:
    """Return total number of registered protocols."""
    return len(_PROTOCOLS)
