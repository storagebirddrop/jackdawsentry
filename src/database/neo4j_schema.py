"""
Jackdaw Sentry - Neo4j Graph Database Schema
Cross-chain stablecoin tracking and transaction flow analysis
"""

import logging
from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional

from neo4j import AsyncGraphDatabase

logger = logging.getLogger(__name__)


class Neo4jSchema:
    """Neo4j schema management for Jackdaw Sentry"""

    def __init__(self, driver):
        self.driver = driver

    async def create_constraints(self):
        """Create database constraints for data integrity"""
        constraints = [
            # Address constraints
            "CREATE CONSTRAINT address_id_unique IF NOT EXISTS FOR (a:Address) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT blockchain_address_unique IF NOT EXISTS FOR (a:Address) REQUIRE (a.blockchain, a.address) IS UNIQUE",
            # Transaction constraints
            "CREATE CONSTRAINT tx_hash_unique IF NOT EXISTS FOR (t:Transaction) REQUIRE t.hash IS UNIQUE",
            "CREATE CONSTRAINT blockchain_tx_unique IF NOT EXISTS FOR (t:Transaction) REQUIRE (t.blockchain, t.hash) IS UNIQUE",
            # Block constraints
            "CREATE CONSTRAINT block_hash_unique IF NOT EXISTS FOR (b:Block) REQUIRE b.hash IS UNIQUE",
            "CREATE CONSTRAINT blockchain_block_unique IF NOT EXISTS FOR (b:Block) REQUIRE (b.blockchain, b.hash) IS UNIQUE",
            # Entity constraints
            "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT entity_name_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE",
            # Stablecoin constraints
            "CREATE CONSTRAINT stablecoin_symbol_blockchain_unique IF NOT EXISTS FOR (s:Stablecoin) REQUIRE (s.symbol, s.blockchain) IS UNIQUE",
            "CREATE CONSTRAINT stablecoin_contract_unique IF NOT EXISTS FOR (s:Stablecoin) REQUIRE (s.blockchain, s.contract_address) IS UNIQUE",
            # Lightning constraints
            "CREATE CONSTRAINT channel_id_unique IF NOT EXISTS FOR (c:LightningChannel) REQUIRE c.channel_id IS UNIQUE",
            "CREATE CONSTRAINT node_pubkey_unique IF NOT EXISTS FOR (n:LightningNode) REQUIRE n.pubkey IS UNIQUE",
        ]

        for constraint in constraints:
            try:
                async with self.driver.session() as session:
                    await session.run(constraint)
                logger.info(f"✅ Created constraint: {constraint}")
            except Exception as e:
                logger.error(
                    f"❌ Failed to create constraint: {constraint}, Error: {e}"
                )

    async def create_indexes(self):
        """Create performance indexes"""
        indexes = [
            # Address indexes
            "CREATE INDEX address_blockchain_index IF NOT EXISTS FOR (a:Address) ON (a.blockchain)",
            "CREATE INDEX address_type_index IF NOT EXISTS FOR (a:Address) ON (a.type)",
            "CREATE INDEX address_risk_score_index IF NOT EXISTS FOR (a:Address) ON (a.risk_score)",
            # Transaction indexes
            "CREATE INDEX tx_timestamp_index IF NOT EXISTS FOR (t:Transaction) ON (t.timestamp)",
            "CREATE INDEX tx_value_index IF NOT EXISTS FOR (t:Transaction) ON (t.value)",
            "CREATE INDEX tx_blockchain_index IF NOT EXISTS FOR (t:Transaction) ON (t.blockchain)",
            # Entity indexes
            "CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            "CREATE INDEX entity_category_index IF NOT EXISTS FOR (e:Entity) ON (e.category)",
            "CREATE INDEX entity_risk_level_index IF NOT EXISTS FOR (e:Entity) ON (e.risk_level)",
            # Stablecoin indexes
            "CREATE INDEX stablecoin_blockchain_index IF NOT EXISTS FOR (s:Stablecoin) ON (s.blockchain)",
            "CREATE INDEX stablecoin_type_index IF NOT EXISTS FOR (s:Stablecoin) ON (s.type)",
            # Lightning indexes
            "CREATE INDEX channel_capacity_index IF NOT EXISTS FOR (c:LightningChannel) ON (c.capacity)",
            "CREATE INDEX node_alias_index IF NOT EXISTS FOR (n:LightningNode) ON (n.alias)",
        ]

        for index in indexes:
            try:
                async with self.driver.session() as session:
                    await session.run(index)
                logger.info(f"✅ Created index: {index}")
            except Exception as e:
                logger.error(f"❌ Failed to create index: {index}, Error: {e}")

    async def create_schema(self):
        """Create complete database schema"""
        logger.info("Creating Neo4j schema for Jackdaw Sentry...")

        await self.create_constraints()
        await self.create_indexes()
        await self.create_procedures()

        logger.info("✅ Neo4j schema creation completed")

    async def create_procedures(self):
        """Create custom procedures for analysis"""
        procedures = [
            # Cross-chain transaction flow analysis
            """
            CREATE OR REPLACE PROCEDURE jackdaw.analyze_cross_chain_flow(
                start_address STRING, 
                max_depth INTEGER,
                min_value FLOAT
            )
            YIELD path, total_value, blockchains
            AS
            MATCH path = (start:Address {address: $start_address})-[:SENT*1..$max_depth]->(end:Address)
            WHERE ALL(rel IN relationships(path) WHERE rel.value >= $min_value)
            WITH path, sum(rel.value) as total_value, 
                 collect(DISTINCT rel.blockchain) as blockchains
            WHERE size(blockchains) > 1
            RETURN path, total_value, blockchains
            """,
            # Stablecoin bridge tracking
            """
            CREATE OR REPLACE PROCEDURE jackdaw.track_stablecoin_bridges(
                stablecoin_symbol STRING,
                time_range INTEGER
            )
            YIELD bridge_path, total_value, source_chain, target_chain
            AS
            MATCH (stablecoin:Stablecoin {symbol: $stablecoin_symbol})
            MATCH (stablecoin)-[:ISSUED_ON]->(source_chain:Blockchain)
            MATCH path = (source_chain)<-[:SENT]-(tx:Transaction)-[:SENT]->(target_chain:Blockchain)
            WHERE tx.timestamp > timestamp() - ($time_range * 24 * 3600 * 1000)
            WITH path, sum(tx.value) as total_value
            RETURN path, total_value, source_chain.name as source_chain, target_chain.name as target_chain
            """,
            # Lightning Network analysis
            """
            CREATE OR REPLACE PROCEDURE jackdaw.analyze_lightning_routes(
                source_pubkey STRING,
                target_pubkey STRING,
                max_hops INTEGER
            )
            YIELD route_path, total_capacity, total_fees
            AS
            MATCH route_path = (source:LightningNode {pubkey: $source_pubkey})-[:CHANNEL*1..$max_hops]->(target:LightningNode {pubkey: $target_pubkey})
            WITH route_path, sum(rel.capacity) as total_capacity, sum(rel.fee_rate) as total_fees
            RETURN route_path, total_capacity, total_fees
            ORDER BY total_capacity DESC
            """,
            # Address clustering
            """
            CREATE OR REPLACE PROCEDURE jackdaw.cluster_addresses(
                similarity_threshold FLOAT
            )
            YIELD cluster_id, addresses, common_patterns
            AS
            MATCH (a1:Address)-[:SENT]->(a2:Address)
            WITH a1, a2, count(*) as interaction_count
            WHERE interaction_count > 10
            MATCH (a1)-[:SENT]->(common)-[:SENT]->(a2)
            WITH a1, a2, count(common) as common_counterparties
            WHERE common_counterparties >= 3
            WITH a1, a2, (interaction_count * common_counterparties) as similarity_score
            WHERE similarity_score > $similarity_threshold
            MERGE (cluster:Entity {type: 'cluster', id: toString(id(a1)) + '_' + toString(id(a2))})
            MERGE (cluster)-[:CONTAINS]->(a1)
            MERGE (cluster)-[:CONTAINS]->(a2)
            RETURN cluster.id as cluster_id, collect(a1.address) + collect(a2.address) as addresses, 
                   'high_interaction' as common_patterns
            """,
        ]

        for procedure in procedures:
            try:
                async with self.driver.session() as session:
                    await session.run(procedure)
                logger.info(f"✅ Created procedure")
            except Exception as e:
                logger.error(f"❌ Failed to create procedure: {e}")


async def create_neo4j_schema():
    """Initialize Neo4j database schema"""
    from src.api.config import settings

    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    )

    try:
        schema = Neo4jSchema(driver)
        await schema.create_schema()

        # Create initial data
        await create_initial_blockchain_data(driver)
        await create_initial_stablecoin_data(driver)

    finally:
        await driver.close()


async def create_initial_blockchain_data(driver):
    """Create initial blockchain nodes"""
    blockchains = [
        {
            "name": "Bitcoin",
            "symbol": "BTC",
            "type": "utxo",
            "consensus": "Proof of Work",
            "block_time": 600,
            "supports_lightning": True,
        },
        {
            "name": "Ethereum",
            "symbol": "ETH",
            "type": "account",
            "consensus": "Proof of Stake",
            "block_time": 12,
            "supports_smart_contracts": True,
        },
        {
            "name": "Solana",
            "symbol": "SOL",
            "type": "account",
            "consensus": "Proof of History",
            "block_time": 0.4,
            "supports_smart_contracts": True,
        },
        {
            "name": "Tron",
            "symbol": "TRX",
            "type": "account",
            "consensus": "Delegated Proof of Stake",
            "block_time": 3,
            "supports_smart_contracts": True,
        },
        {
            "name": "BSC",
            "symbol": "BNB",
            "type": "account",
            "consensus": "Proof of Staked Authority",
            "block_time": 3,
            "supports_smart_contracts": True,
        },
        {
            "name": "Polygon",
            "symbol": "MATIC",
            "type": "account",
            "consensus": "Proof of Stake",
            "block_time": 2,
            "supports_smart_contracts": True,
        },
        {
            "name": "Arbitrum",
            "symbol": "ARB",
            "type": "account",
            "consensus": "Optimistic Rollup",
            "block_time": 0.25,
            "supports_smart_contracts": True,
        },
        {
            "name": "Base",
            "symbol": "ETH",
            "type": "account",
            "consensus": "Optimistic Rollup",
            "block_time": 2,
            "supports_smart_contracts": True,
        },
        {
            "name": "Avalanche",
            "symbol": "AVAX",
            "type": "account",
            "consensus": "Proof of Stake",
            "block_time": 2,
            "supports_smart_contracts": True,
        },
        {
            "name": "XRPL",
            "symbol": "XRP",
            "type": "account",
            "consensus": "Ripple Protocol",
            "block_time": 3.5,
            "supports_smart_contracts": False,
        },
        {
            "name": "Stellar",
            "symbol": "XLM",
            "type": "account",
            "consensus": "Stellar Consensus",
            "block_time": 3.5,
            "supports_smart_contracts": True,
        },
        {
            "name": "Sei",
            "symbol": "SEI",
            "type": "account",
            "consensus": "Tendermint",
            "block_time": 0.5,
            "supports_smart_contracts": True,
        },
        {
            "name": "Hyperliquid",
            "symbol": "HYPE",
            "type": "account",
            "consensus": "Custom",
            "block_time": 1,
            "supports_smart_contracts": True,
        },
        {
            "name": "Plasma",
            "symbol": "PLASMA",
            "type": "account",
            "consensus": "Proof of Stake",
            "block_time": 2,
            "supports_smart_contracts": True,
        },
    ]

    query = """
    MERGE (b:Blockchain {name: $name})
    SET b.symbol = $symbol,
        b.type = $type,
        b.consensus = $consensus,
        b.block_time = $block_time,
        b.supports_lightning = $supports_lightning,
        b.supports_smart_contracts = $supports_smart_contracts,
        b.created_at = timestamp()
    """

    async with driver.session() as session:
        for blockchain in blockchains:
            params = dict(blockchain)
            params.setdefault("supports_lightning", False)
            params.setdefault("supports_smart_contracts", False)
            await session.run(query, **params)

    logger.info("✅ Created initial blockchain data")


async def create_initial_stablecoin_data(driver):
    """Create initial stablecoin nodes"""
    stablecoins = [
        {
            "symbol": "USDT",
            "name": "Tether USD",
            "type": "fiat_backed",
            "blockchain": "Ethereum",
            "contract_address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            "decimals": 6,
        },
        {
            "symbol": "USDC",
            "name": "USD Coin",
            "type": "fiat_backed",
            "blockchain": "Ethereum",
            "contract_address": "0xA0b86a33E6441b6e8F9c2c2c4c4c4c4c4c4c4c4c",
            "decimals": 6,
        },
        {
            "symbol": "USDT",
            "name": "Tether USD",
            "type": "fiat_backed",
            "blockchain": "Tron",
            "contract_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
            "decimals": 6,
        },
        {
            "symbol": "USDT",
            "name": "Tether USD",
            "type": "fiat_backed",
            "blockchain": "Solana",
            "contract_address": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
            "decimals": 6,
        },
        {
            "symbol": "EURC",
            "name": "Euro Coin",
            "type": "fiat_backed",
            "blockchain": "Ethereum",
            "contract_address": "0x2A325e6831B0AD69618ebC6adD6f3B8c3C5d6B5f",
            "decimals": 6,
        },
        {
            "symbol": "EURT",
            "name": "Euro Tether",
            "type": "fiat_backed",
            "blockchain": "Ethereum",
            "contract_address": "0x0C10bF8FbC34C309b9F6D3394b5D1F5D6E7F8A9B",
            "decimals": 6,
        },
    ]

    query = """
    MATCH (b:Blockchain {name: $blockchain})
    MERGE (s:Stablecoin {symbol: $symbol, blockchain: $blockchain})
    SET s.name = $name,
        s.type = $type,
        s.contract_address = $contract_address,
        s.decimals = $decimals,
        s.created_at = timestamp()
    MERGE (s)-[:ISSUED_ON]->(b)
    """

    async with driver.session() as session:
        for stablecoin in stablecoins:
            await session.run(query, **stablecoin)

    logger.info("✅ Created initial stablecoin data")


if __name__ == "__main__":
    import asyncio

    asyncio.run(create_neo4j_schema())
