"""
Jackdaw Sentry - Cross-Chain Bridge Tracker
Detects and tracks stablecoin movements across blockchain bridges
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from src.api.config import settings
from src.api.database import get_neo4j_session
from src.api.database import get_redis_connection

logger = logging.getLogger(__name__)


class BridgeTracker:
    """Cross-chain bridge tracking and analysis"""

    def __init__(self):
        self.supported_stablecoins = {
            "USDT",
            "USDC",
            "RLUSD",
            "USDe",
            "USDS",
            "USD1",
            "BUSD",
            "A7A5",
            "EURC",
            "EURT",
            "BRZ",
            "EURS",
        }

        self.supported_blockchains = {
            "ethereum",
            "bsc",
            "polygon",
            "arbitrum",
            "base",
            "avalanche",
            "solana",
            "tron",
            "bitcoin",
            "xrpl",
            "stellar",
            "sei",
            "hyperliquid",
            "plasma",
        }

        # Known bridge contracts and addresses
        self.bridge_contracts = self.initialize_bridge_contracts()

        # Bridge detection patterns
        self.bridge_patterns = self.initialize_bridge_patterns()

        self.is_running = False
        self.metrics = {
            "bridges_detected": 0,
            "stablecoin_transfers": 0,
            "total_volume": 0,
            "suspicious_bridges": 0,
            "last_update": None,
        }

    def initialize_bridge_contracts(self) -> Dict[str, Dict]:
        """Initialize known bridge contracts and addresses"""
        return {
            "ethereum": {
                "wormhole": {
                    "token_bridge": "0x98f3c9e6E3fAce36bAAdCc98Ca250598283Cc8f",
                    "bridge": "0x3ee18B2A5b80FB7612945b224cE34e2E0B03c5",
                },
                "layer_zero": {
                    "endpoint": "0x66A71Dcef29A0fFBDBE95c4201fe3230f7b6A8f",
                    "ultra_light_node": "0x1a0a0ac733d2d0e7e8c4a0ed0c3788a1b7af9",
                },
                "multichain": {
                    "router": "0xdF9285C8B0F0eF5B8486f3e0BEBE5D7950D8a",
                    "token_manager": "0x7e7B32C1a4905C4A0A35D6789C5e72aC6d4656",
                },
            },
            "bsc": {
                "wormhole": {
                    "token_bridge": "0x98f3c9e6E3fAce36bAAdCc98Ca250598283Cc8f",
                    "bridge": "0x3ee18B2A5b80FB7612945b224cE34e2E0B03c5",
                },
                "multichain": {
                    "router": "0xdF9285C8B0F0eF5B8486f3e0BEBE5D7950D8a",
                    "token_manager": "0x7e7B32C1a4905C4A0A35D6789C5e72aC6d4656",
                },
            },
            "polygon": {
                "wormhole": {
                    "token_bridge": "0x98f3c9e6E3fAce36bAAdCc98Ca250598283Cc8f",
                    "bridge": "0x3ee18B2A5b80FB7612945b224cE34e2E0B03c5",
                },
                "multichain": {
                    "router": "0xdF9285C8B0F0eF5B8486f3e0BEBE5D7950D8a",
                    "token_manager": "0x7e7B32C1a4905C4A0A35D6789C5e72aC6d4656",
                },
            },
            "arbitrum": {
                "wormhole": {
                    "token_bridge": "0x98f3c9e6E3fAce36bAAdCc98Ca250598283Cc8f",
                    "bridge": "0x3ee18B2A5b80FB7612945b224cE34e2E0B03c5",
                },
                "layer_zero": {
                    "endpoint": "0x66A71Dcef29A0fFBDBE95c4201fe3230f7b6A8f",
                    "ultra_light_node": "0x1a0a0ac733d2d0e7e8c4a0ed0c3788a1b7af9",
                },
            },
            "base": {
                "wormhole": {
                    "token_bridge": "0x98f3c9e6E3fAce36bAAdCc98Ca250598283Cc8f",
                    "bridge": "0x3ee18B2A5b80FB7612945b224cE34e2E0B03c5",
                }
            },
            "avalanche": {
                "wormhole": {
                    "token_bridge": "0x98f3c9e6E3fAce36bAAdCc98Ca250598283Cc8f",
                    "bridge": "0x3ee18B2A5b80FB7612945b224cE34e2E0B03c5",
                }
            },
        }

    def initialize_bridge_patterns(self) -> List[Dict]:
        """Initialize bridge detection patterns"""
        return [
            {
                "name": "wormhole_vaa",
                "description": "Wormhole VAA (Verified Action Approval) patterns",
                "event_signatures": [
                    "0x1e8ce30e",  # TransferCompleted
                    "0x8c5be1e5",  # MessagePublished
                ],
                "contract_types": ["token_bridge", "bridge"],
            },
            {
                "name": "layer_zero",
                "description": "LayerZero cross-chain messaging",
                "event_signatures": [
                    "0x84c0e040",  # MessageSent
                    "0x3d5a0e7a",  # MessageReceived
                ],
                "contract_types": ["endpoint", "ultra_light_node"],
            },
            {
                "name": "multichain",
                "description": "Multichain bridge transfers",
                "event_signatures": [
                    "0x1032fbe4",  # TokenSent
                    "0x949d5d47",  # TokenReceived
                ],
                "contract_types": ["router", "token_manager"],
            },
            {
                "name": "any_swap",
                "description": "AnySwap cross-chain transfers",
                "event_signatures": [
                    "0x44a0e612",  # LogAnySwap
                    "0x8c3be2e1",  # LogAnySwapOut
                ],
                "contract_types": ["router"],
            },
            {
                "name": "cbridge",
                "description": "cBridge cross-chain transfers",
                "event_signatures": [
                    "0x940b2029",  # Send
                    "0x4a393069",  # Receive
                ],
                "contract_types": ["bridge"],
            },
        ]

    async def start(self):
        """Start bridge tracking"""
        logger.info("Starting cross-chain bridge tracking...")
        self.is_running = True

        try:
            # Start monitoring tasks
            tasks = [
                asyncio.create_task(self.monitor_bridge_transactions()),
                asyncio.create_task(self.analyze_bridge_patterns()),
                asyncio.create_task(self.detect_new_bridges()),
                asyncio.create_task(self.track_bridge_liquidity()),
                asyncio.create_task(self.collect_metrics()),
            ]

            await asyncio.gather(*tasks)

        except Exception as e:
            logger.error(f"Error in bridge tracking: {e}")
        finally:
            await self.stop()

    async def stop(self):
        """Stop bridge tracking"""
        logger.info("Stopping bridge tracking...")
        self.is_running = False

    async def monitor_bridge_transactions(self):
        """Monitor transactions involving known bridges"""
        logger.info("Starting bridge transaction monitoring...")

        while self.is_running:
            try:
                # Query recent transactions involving bridge contracts
                await self.query_bridge_transactions()
                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error in bridge transaction monitoring: {e}")
                await asyncio.sleep(15)

    async def query_bridge_transactions(self):
        """Query database for bridge transactions"""
        for blockchain, bridges in self.bridge_contracts.items():
            for bridge_name, bridge_info in bridges.items():
                for contract_type, contract_address in bridge_info.items():
                    await self.analyze_bridge_contract(
                        blockchain, bridge_name, contract_type, contract_address
                    )

    async def analyze_bridge_contract(
        self,
        blockchain: str,
        bridge_name: str,
        contract_type: str,
        contract_address: str,
    ):
        """Analyze transactions for a specific bridge contract"""
        try:
            # Query recent transactions for this contract
            query = """
            MATCH (t:Transaction {blockchain: $blockchain})
            WHERE t.contract_address = $contract_address
               AND t.timestamp > timestamp() - 3600000  // Last hour
            RETURN t
            ORDER BY t.timestamp DESC
            LIMIT 100
            """

            async with get_neo4j_session() as session:
                result = await session.run(
                    query,
                    blockchain=blockchain,
                    contract_address=contract_address.lower(),
                )

                transactions = [record["t"] for record in result]

                for tx in transactions:
                    await self.analyze_bridge_transaction(
                        tx, blockchain, bridge_name, contract_type
                    )

        except Exception as e:
            logger.error(f"Error analyzing bridge contract {contract_address}: {e}")

    async def analyze_bridge_transaction(
        self, tx: Dict, blockchain: str, bridge_name: str, contract_type: str
    ):
        """Analyze individual bridge transaction"""
        try:
            # Extract stablecoin transfers
            stablecoin_transfers = await self.extract_stablecoin_transfers(tx)

            if stablecoin_transfers:
                for transfer in stablecoin_transfers:
                    # Determine if this is a cross-chain transfer
                    cross_chain_info = await self.determine_cross_chain_direction(
                        transfer, blockchain, bridge_name
                    )

                    if cross_chain_info:
                        await self.store_bridge_transfer(tx, transfer, cross_chain_info)

                        # Update metrics
                        self.metrics["stablecoin_transfers"] += 1
                        self.metrics["total_volume"] += transfer.get("amount", 0)

                        # Check for suspicious patterns
                        await self.analyze_suspicious_patterns(
                            tx, transfer, cross_chain_info
                        )

        except Exception as e:
            logger.error(f"Error analyzing bridge transaction: {e}")

    async def extract_stablecoin_transfers(self, tx: Dict) -> List[Dict]:
        """Extract stablecoin transfers from transaction"""
        transfers = []

        try:
            # Check token transfers in transaction
            token_transfers = tx.get("token_transfers", [])

            for transfer in token_transfers:
                symbol = transfer.get("symbol")
                if symbol in self.supported_stablecoins:
                    transfers.append(transfer)

        except Exception as e:
            logger.error(f"Error extracting stablecoin transfers: {e}")

        return transfers

    async def determine_cross_chain_direction(
        self, transfer: Dict, blockchain: str, bridge_name: str
    ) -> Optional[Dict]:
        """Determine cross-chain transfer direction"""
        try:
            # This would analyze the bridge transaction to determine
            # source and destination chains

            # For now, return placeholder
            return {
                "bridge_name": bridge_name,
                "source_chain": blockchain,
                "destination_chain": "unknown",  # Would be determined from bridge logic
                "transfer_type": "bridge_out",  # bridge_out or bridge_in
                "confidence": 0.8,
            }

        except Exception as e:
            logger.error(f"Error determining cross-chain direction: {e}")

        return None

    async def store_bridge_transfer(
        self, tx: Dict, transfer: Dict, cross_chain_info: Dict
    ):
        """Store bridge transfer information"""
        query = """
        MATCH (t:Transaction {hash: $tx_hash})
        MATCH (s:Stablecoin {symbol: $symbol})
        MERGE (b:BridgeTransfer {id: $bridge_id})
        SET b.bridge_name = $bridge_name,
            b.source_chain = $source_chain,
            b.destination_chain = $destination_chain,
            b.transfer_type = $transfer_type,
            b.amount = $amount,
            b.confidence = $confidence,
            b.created_at = timestamp()
        
        MERGE (t)-[:BRIDGE_TRANSFER]->(b)
        MERGE (b)-[:INVOLVES]->(s)
        """

        bridge_id = (
            f"{tx['hash']}_{transfer.get('symbol')}_{cross_chain_info['bridge_name']}"
        )

        async with get_neo4j_session() as session:
            await session.run(
                query,
                tx_hash=tx["hash"],
                symbol=transfer.get("symbol"),
                bridge_id=bridge_id,
                bridge_name=cross_chain_info["bridge_name"],
                source_chain=cross_chain_info["source_chain"],
                destination_chain=cross_chain_info["destination_chain"],
                transfer_type=cross_chain_info["transfer_type"],
                amount=transfer.get("amount"),
                confidence=cross_chain_info["confidence"],
            )

    async def analyze_bridge_patterns(self):
        """Analyze bridge usage patterns"""
        logger.info("Starting bridge pattern analysis...")

        while self.is_running:
            try:
                await self.detect_bridge_anomalies()
                await self.analyze_liquidity_patterns()
                await self.track_bridge_volumes()

                await asyncio.sleep(300)  # Analyze every 5 minutes

            except Exception as e:
                logger.error(f"Error in bridge pattern analysis: {e}")
                await asyncio.sleep(60)

    async def detect_bridge_anomalies(self):
        """Detect anomalies in bridge usage"""
        try:
            # Query recent bridge transfers
            query = """
            MATCH (b:BridgeTransfer)
            WHERE b.created_at > timestamp() - 3600000  // Last hour
            RETURN b.bridge_name as bridge,
                   b.amount as amount,
                   b.source_chain as source,
                   b.destination_chain as dest,
                   b.created_at as timestamp
            ORDER BY timestamp DESC
            """

            async with get_neo4j_session() as session:
                result = await session.run(query)

                transfers = [record for record in result]

                # Analyze for anomalies
                await self.check_volume_anomalies(transfers)
                await self.check_frequency_anomalies(transfers)
                await self.check_timing_anomalies(transfers)

        except Exception as e:
            logger.error(f"Error detecting bridge anomalies: {e}")

    async def check_volume_anomalies(self, transfers: List[Dict]):
        """Check for unusual volume patterns"""
        try:
            # Group by bridge and calculate statistics
            bridge_volumes = {}
            for transfer in transfers:
                bridge = transfer["bridge"]
                amount = transfer["amount"]

                if bridge not in bridge_volumes:
                    bridge_volumes[bridge] = []
                bridge_volumes[bridge].append(amount)

            # Check for unusually large transfers
            for bridge, volumes in bridge_volumes.items():
                avg_volume = sum(volumes) / len(volumes)
                max_volume = max(volumes)

                # If max volume is 10x average, flag as suspicious
                if max_volume > avg_volume * 10:
                    await self.alert_volume_anomaly(bridge, max_volume, avg_volume)

        except Exception as e:
            logger.error(f"Error checking volume anomalies: {e}")

    async def check_frequency_anomalies(self, transfers: List[Dict]):
        """Check for unusual frequency patterns"""
        try:
            # Group by time windows
            time_windows = {}
            for transfer in transfers:
                timestamp = transfer["timestamp"]
                window = timestamp // (60 * 1000)  # 1-minute windows

                if window not in time_windows:
                    time_windows[window] = 0
                time_windows[window] += 1

            # Check for unusual frequency spikes
            if time_windows:
                avg_frequency = sum(time_windows.values()) / len(time_windows)
                max_frequency = max(time_windows.values())

                # If frequency spikes by 5x, flag as suspicious
                if max_frequency > avg_frequency * 5:
                    await self.alert_frequency_anomaly(max_frequency, avg_frequency)

        except Exception as e:
            logger.error(f"Error checking frequency anomalies: {e}")

    async def check_timing_anomalies(self, transfers: List[Dict]):
        """Check for unusual timing patterns"""
        try:
            # Look for transfers at unusual hours (e.g., 2-4 AM)
            unusual_hours = []

            for transfer in transfers:
                timestamp = transfer["timestamp"]
                hour = (timestamp / 1000 / 3600) % 24  # Convert to hour

                if 2 <= hour <= 4:  # Unusual hours
                    unusual_hours.append(hour)

            # If many transfers at unusual hours, flag as suspicious
            if len(unusual_hours) > len(transfers) * 0.3:  # >30% at unusual hours
                await self.alert_timing_anomaly(unusual_hours)

        except Exception as e:
            logger.error(f"Error checking timing anomalies: {e}")

    async def alert_volume_anomaly(
        self, bridge: str, max_volume: float, avg_volume: float
    ):
        """Alert on volume anomaly"""
        logger.warning(
            f"Volume anomaly detected on {bridge}: max={max_volume}, avg={avg_volume}"
        )

        query = """
        MERGE (a:Alert {type: 'bridge_volume_anomaly'})
        SET a.bridge_name = $bridge_name,
            a.max_volume = $max_volume,
            a.avg_volume = $avg_volume,
            a.severity = 'high',
            a.created_at = timestamp()
        """

        async with get_neo4j_session() as session:
            await session.run(
                query, bridge_name=bridge, max_volume=max_volume, avg_volume=avg_volume
            )

    async def alert_frequency_anomaly(self, max_frequency: int, avg_frequency: float):
        """Alert on frequency anomaly"""
        logger.warning(
            f"Frequency anomaly detected: max={max_frequency}, avg={avg_frequency}"
        )

        query = """
        MERGE (a:Alert {type: 'bridge_frequency_anomaly'})
        SET a.max_frequency = $max_frequency,
            a.avg_frequency = $avg_frequency,
            a.severity = 'medium',
            a.created_at = timestamp()
        """

        async with get_neo4j_session() as session:
            await session.run(
                query, max_frequency=max_frequency, avg_frequency=avg_frequency
            )

    async def alert_timing_anomaly(self, unusual_hours: List[int]):
        """Alert on timing anomaly"""
        logger.warning(f"Timing anomaly detected: unusual hours={unusual_hours}")

        query = """
        MERGE (a:Alert {type: 'bridge_timing_anomaly'})
        SET a.unusual_hours = $unusual_hours,
            a.severity = 'medium',
            a.created_at = timestamp()
        """

        async with get_neo4j_session() as session:
            await session.run(query, unusual_hours=unusual_hours)

    async def detect_new_bridges(self):
        """Detect new bridge contracts"""
        logger.info("Starting new bridge detection...")

        while self.is_running:
            try:
                await self.scan_for_new_bridges()
                await asyncio.sleep(3600)  # Scan every hour

            except Exception as e:
                logger.error(f"Error detecting new bridges: {e}")
                await asyncio.sleep(300)

    async def scan_for_new_bridges(self):
        """Scan for new bridge contracts"""
        try:
            # Look for contracts with bridge-like patterns
            # This would analyze new contracts for bridge characteristics

            query = """
            MATCH (t:Transaction)
            WHERE t.contract_address IS NOT NULL
               AND t.timestamp > timestamp() - 86400000  // Last 24 hours
               AND size(t.token_transfers) > 0
            WITH t.contract_address as contract, count(*) as tx_count
            WHERE tx_count > 10  // High activity contracts
            RETURN contract, tx_count
            ORDER BY tx_count DESC
            LIMIT 50
            """

            async with get_neo4j_session() as session:
                result = await session.run(query)

                for record in result:
                    contract = record["contract"]
                    tx_count = record["tx_count"]

                    # Analyze if this might be a bridge
                    await self.analyze_potential_bridge(contract, tx_count)

        except Exception as e:
            logger.error(f"Error scanning for new bridges: {e}")

    async def analyze_potential_bridge(self, contract_address: str, tx_count: int):
        """Analyze if a contract might be a new bridge"""
        try:
            # This would analyze contract code and patterns
            # to determine if it's likely a bridge

            # For now, simple heuristic based on activity
            if tx_count > 50:  # High activity threshold
                logger.info(
                    f"Potential new bridge detected: {contract_address} ({tx_count} txs)"
                )

                query = """
                MERGE (p:PotentialBridge {address: $address})
                SET p.tx_count = $tx_count,
                    p.confidence = 0.6,
                    p.discovered_at = timestamp(),
                    p.status = 'investigating'
                """

                async with get_neo4j_session() as session:
                    await session.run(
                        query, address=contract_address, tx_count=tx_count
                    )

        except Exception as e:
            logger.error(f"Error analyzing potential bridge: {e}")

    async def track_bridge_liquidity(self):
        """Track bridge liquidity and availability"""
        while self.is_running:
            try:
                await self.update_liquidity_data()
                await asyncio.sleep(600)  # Update every 10 minutes

            except Exception as e:
                logger.error(f"Error tracking bridge liquidity: {e}")
                await asyncio.sleep(120)

    async def update_liquidity_data(self):
        """Update bridge liquidity information"""
        try:
            # This would query bridge contracts for current liquidity
            # and store the data for analysis

            for blockchain, bridges in self.bridge_contracts.items():
                for bridge_name, bridge_info in bridges.items():
                    # Query liquidity for each bridge
                    liquidity = await self.query_bridge_liquidity(
                        blockchain, bridge_name, bridge_info
                    )

                    if liquidity:
                        await self.store_liquidity_data(
                            blockchain, bridge_name, liquidity
                        )

        except Exception as e:
            logger.error(f"Error updating liquidity data: {e}")

    async def query_bridge_liquidity(
        self, blockchain: str, bridge_name: str, bridge_info: Dict
    ) -> Optional[Dict]:
        """Query liquidity for a specific bridge"""
        # This would implement bridge-specific liquidity queries
        # For now, return placeholder
        return {
            "blockchain": blockchain,
            "bridge_name": bridge_name,
            "total_liquidity": 1000000,  # Placeholder
            "available_liquidity": 800000,  # Placeholder
            "utilization": 0.2,  # Placeholder
            "last_updated": datetime.now(timezone.utc),
        }

    async def store_liquidity_data(
        self, blockchain: str, bridge_name: str, liquidity: Dict
    ):
        """Store bridge liquidity data"""
        query = """
        MERGE (l:BridgeLiquidity {bridge_name: $bridge_name, blockchain: $blockchain})
        SET l.total_liquidity = $total_liquidity,
            l.available_liquidity = $available_liquidity,
            l.utilization = $utilization,
            l.last_updated = $last_updated,
            l.updated_at = timestamp()
        """

        async with get_neo4j_session() as session:
            await session.run(
                query,
                blockchain=blockchain,
                bridge_name=bridge_name,
                total_liquidity=liquidity.get("total_liquidity"),
                available_liquidity=liquidity.get("available_liquidity"),
                utilization=liquidity.get("utilization"),
                last_updated=liquidity.get("last_updated"),
            )

    async def analyze_suspicious_patterns(
        self, tx: Dict, transfer: Dict, cross_chain_info: Dict
    ):
        """Analyze transfer for suspicious patterns"""
        try:
            # Check for mixer-like behavior
            if await self.is_mixer_pattern(transfer, cross_chain_info):
                await self.alert_mixer_pattern(tx, transfer)

            # Check for rapid chain hopping
            if await self.is_rapid_chain_hopping(transfer, cross_chain_info):
                await self.alert_rapid_hopping(tx, transfer)

            # Check for round amounts (privacy coins)
            if await self.is_round_amount(transfer):
                await self.alert_round_amount(tx, transfer)

        except Exception as e:
            logger.error(f"Error analyzing suspicious patterns: {e}")

    async def is_mixer_pattern(self, transfer: Dict, cross_chain_info: Dict) -> bool:
        """Check if transfer follows mixer pattern"""
        # This would implement mixer detection logic
        # For now, simple heuristic
        amount = transfer.get("amount", 0)
        return amount > 100000 and amount % 10000 == 0  # Large round amounts

    async def is_rapid_chain_hopping(
        self, transfer: Dict, cross_chain_info: Dict
    ) -> bool:
        """Check for rapid chain hopping"""
        # This would check if the same user is rapidly moving
        # funds across multiple chains
        return False

    async def is_round_amount(self, transfer: Dict) -> bool:
        """Check if amount is suspiciously round"""
        amount = transfer.get("amount", 0)
        return amount > 10000 and amount % 1000 == 0

    async def alert_mixer_pattern(self, tx: Dict, transfer: Dict):
        """Alert on mixer pattern"""
        logger.warning(
            f"Mixer pattern detected: {tx['hash']} - {transfer.get('amount')}"
        )

        query = """
        MATCH (t:Transaction {hash: $tx_hash})
        MERGE (a:Alert {type: 'mixer_pattern'})
        MERGE (t)-[:TRIGGERED]->(a)
        SET a.amount = $amount,
            a.bridge_name = $bridge_name,
            a.severity = 'high',
            a.created_at = timestamp()
        """

        async with get_neo4j_session() as session:
            await session.run(
                query,
                tx_hash=tx["hash"],
                amount=transfer.get("amount"),
                bridge_name=transfer.get("bridge_name"),
            )

    async def alert_rapid_hopping(self, tx: Dict, transfer: Dict):
        """Alert on rapid chain hopping"""
        logger.warning(f"Rapid chain hopping detected: {tx['hash']}")

        query = """
        MATCH (t:Transaction {hash: $tx_hash})
        MERGE (a:Alert {type: 'rapid_chain_hopping'})
        MERGE (t)-[:TRIGGERED]->(a)
        SET a.amount = $amount,
            a.severity = 'medium',
            a.created_at = timestamp()
        """

        async with get_neo4j_session() as session:
            await session.run(query, tx_hash=tx["hash"], amount=transfer.get("amount"))

    async def alert_round_amount(self, tx: Dict, transfer: Dict):
        """Alert on round amounts"""
        logger.warning(
            f"Round amount detected: {tx['hash']} - {transfer.get('amount')}"
        )

        query = """
        MATCH (t:Transaction {hash: $tx_hash})
        MERGE (a:Alert {type: 'round_amount'})
        MERGE (t)-[:TRIGGERED]->(a)
        SET a.amount = $amount,
            a.severity = 'low',
            a.created_at = timestamp()
        """

        async with get_neo4j_session() as session:
            await session.run(query, tx_hash=tx["hash"], amount=transfer.get("amount"))

    async def track_bridge_volumes(self):
        """Track volume through each bridge"""
        try:
            query = """
            MATCH (b:BridgeTransfer)
            WHERE b.created_at > timestamp() - 86400000  // Last 24 hours
            RETURN b.bridge_name as bridge,
                   b.source_chain as source,
                   b.destination_chain as dest,
                   sum(b.amount) as volume,
                   count(*) as count
            ORDER BY volume DESC
            """

            async with get_neo4j_session() as session:
                result = await session.run(query)

                bridge_volumes = [record for record in result]

                # Cache volume data
                await self.cache_volume_data(bridge_volumes)

        except Exception as e:
            logger.error(f"Error tracking bridge volumes: {e}")

    async def cache_volume_data(self, bridge_volumes: List[Dict]):
        """Cache bridge volume data"""
        try:
            async with get_redis_connection() as redis:
                await redis.setex(
                    "bridge_volumes", 300, json.dumps(bridge_volumes)  # 5 minutes
                )
        except Exception as e:
            logger.error(f"Error caching volume data: {e}")

    async def collect_metrics(self):
        """Collect bridge tracking metrics"""
        while self.is_running:
            try:
                # Update metrics
                self.metrics["last_update"] = datetime.now(timezone.utc)

                # Cache metrics
                async with get_redis_connection() as redis:
                    await redis.setex(
                        "bridge_metrics", 300, json.dumps(self.metrics)  # 5 minutes
                    )

                await asyncio.sleep(60)  # Update every minute

            except Exception as e:
                logger.error(f"Error collecting bridge metrics: {e}")
                await asyncio.sleep(30)

    async def get_bridge_stats(self) -> Dict[str, Any]:
        """Get bridge tracking statistics"""
        return {
            "bridges_detected": self.metrics.get("bridges_detected", 0),
            "stablecoin_transfers": self.metrics.get("stablecoin_transfers", 0),
            "total_volume": self.metrics.get("total_volume", 0),
            "suspicious_bridges": self.metrics.get("suspicious_bridges", 0),
            "last_update": self.metrics.get("last_update"),
        }
