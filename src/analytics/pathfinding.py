"""
Jackdaw Sentry - Multi-Route Pathfinding
Advanced pathfinding algorithms for blockchain transaction analysis
"""

import asyncio
import logging
from collections import defaultdict
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

import networkx as nx

from src.api.database import get_postgres_connection

from .models import PathfindingAlgorithm
from .models import PathfindingRequest
from .models import PathfindingResult
from .models import TransactionEdge
from .models import TransactionNode
from .models import TransactionPath

logger = logging.getLogger(__name__)


class MultiRoutePathfinder:
    """Advanced multi-route pathfinding for blockchain transaction analysis"""

    def __init__(self):
        self.max_paths_per_request = 1000
        self.max_hops_per_path = 50
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
        self._initialized = False

    async def initialize(self):
        """Initialize the pathfinding engine"""
        if self._initialized:
            return

        logger.info("Initializing Multi-Route Pathfinding Engine...")
        await self._create_pathfinding_tables()
        self._initialized = True
        logger.info("Multi-Route Pathfinding Engine initialized successfully")

    async def _create_pathfinding_tables(self):
        """Create pathfinding tables"""

        create_paths_table = """
        CREATE TABLE IF NOT EXISTS pathfinding_results (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            query_id VARCHAR(255) NOT NULL,
            source_address VARCHAR(255) NOT NULL,
            target_address VARCHAR(255) NOT NULL,
            blockchain VARCHAR(50) NOT NULL,
            algorithm VARCHAR(50) NOT NULL,
            paths JSONB DEFAULT '[]',
            total_paths_found INTEGER NOT NULL DEFAULT 0,
            processing_time_ms DECIMAL(10,2),
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_pathfinding_query ON pathfinding_results(query_id);
        CREATE INDEX IF NOT EXISTS idx_pathfinding_addresses ON pathfinding_results(source_address, target_address);
        CREATE INDEX IF NOT EXISTS idx_pathfinding_blockchain ON pathfinding_results(blockchain);
        CREATE INDEX IF NOT EXISTS idx_pathfinding_created ON pathfinding_results(created_at);
        """

        create_graph_cache_table = """
        CREATE TABLE IF NOT EXISTS transaction_graph_cache (
            blockchain VARCHAR(50) NOT NULL,
            address VARCHAR(255) NOT NULL,
            neighbors JSONB DEFAULT '[]',
            last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            PRIMARY KEY (blockchain, address)
        );
        
        CREATE INDEX IF NOT EXISTS idx_graph_cache_blockchain ON transaction_graph_cache(blockchain);
        CREATE INDEX IF NOT EXISTS idx_graph_cache_updated ON transaction_graph_cache(last_updated);
        """

        conn = await get_postgres_connection()
        try:
            await conn.execute(create_paths_table)
            await conn.execute(create_graph_cache_table)
            await conn.commit()
            logger.info("Pathfinding tables created/verified")
        except Exception as e:
            logger.error(f"Error creating pathfinding tables: {e}")
            await conn.rollback()
            raise
        finally:
            await conn.close()

    async def find_paths(self, request: PathfindingRequest) -> PathfindingResult:
        """
        Find paths between two addresses using specified algorithm

        Args:
            request: Pathfinding request with parameters

        Returns:
            PathfindingResult with all found paths
        """

        start_time = datetime.now(timezone.utc)

        # Check cache first
        cache_key = self._generate_cache_key(request)
        if cache_key in self.cache:
            cached_result = self.cache[cache_key]
            if (
                datetime.now(timezone.utc) - cached_result["timestamp"]
            ).seconds < self.cache_ttl:
                logger.debug(
                    f"Cache hit for pathfinding: {request.source_address} -> {request.target_address}"
                )
                return cached_result["result"]

        logger.info(
            f"Finding paths from {request.source_address} to {request.target_address} on {request.blockchain}"
        )

        try:
            # Build transaction graph
            graph = await self._build_transaction_graph(
                request.source_address,
                request.target_address,
                request.blockchain,
                request.max_hops,
                request.time_window_hours,
            )

            # Find paths based on algorithm
            if request.algorithm == PathfindingAlgorithm.SHORTEST_PATH:
                paths = await self._find_shortest_paths(graph, request)
            elif request.algorithm == PathfindingAlgorithm.ALL_PATHS:
                paths = await self._find_all_paths(graph, request)
            elif request.algorithm == PathfindingAlgorithm.DISCONNECTED_PATHS:
                paths = await self._find_disconnected_paths(graph, request)
            elif request.algorithm == PathfindingAlgorithm.FUNNEL_ANALYSIS:
                paths = await self._analyze_funnels(graph, request)
            elif request.algorithm == PathfindingAlgorithm.CIRCULAR_PATHS:
                paths = await self._find_circular_paths(graph, request)
            else:
                raise ValueError(f"Unsupported algorithm: {request.algorithm}")

            # Filter and rank paths
            filtered_paths = self._filter_paths(paths, request)
            ranked_paths = self._rank_paths(filtered_paths, request)

            # Calculate processing time
            processing_time = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000

            # Create result
            result = PathfindingResult(
                source_address=request.source_address,
                target_address=request.target_address,
                blockchain=request.blockchain,
                algorithm=request.algorithm,
                paths=ranked_paths[: request.max_paths],
                total_paths_found=len(ranked_paths),
                processing_time_ms=processing_time,
                metadata={
                    "graph_nodes": len(graph.nodes()),
                    "graph_edges": len(graph.edges()),
                    "cache_hit": False,
                    "algorithm_version": "1.0",
                },
            )

            # Cache result
            self.cache[cache_key] = {
                "result": result,
                "timestamp": datetime.now(timezone.utc),
            }

            # Store in database
            await self._store_pathfinding_result(result)

            logger.info(
                f"Pathfinding complete: {len(ranked_paths)} paths found in {processing_time:.2f}ms"
            )
            return result

        except Exception as e:
            logger.error(f"Error in pathfinding: {e}")
            processing_time = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds() * 1000

            return PathfindingResult(
                source_address=request.source_address,
                target_address=request.target_address,
                blockchain=request.blockchain,
                algorithm=request.algorithm,
                paths=[],
                total_paths_found=0,
                processing_time_ms=processing_time,
                metadata={"error": str(e), "cache_hit": False},
            )

    async def _build_transaction_graph(
        self,
        source_address: str,
        target_address: str,
        blockchain: str,
        max_hops: int,
        time_window_hours: int,
    ) -> nx.DiGraph:
        """Build transaction graph for pathfinding"""

        graph = nx.DiGraph()

        # Get transactions for source and target addresses
        source_txs = await self._get_address_transactions(
            source_address, blockchain, time_window_hours
        )
        target_txs = await self._get_address_transactions(
            target_address, blockchain, time_window_hours
        )

        # Add source and target nodes
        graph.add_node(source_address, address=source_address, blockchain=blockchain)
        graph.add_node(target_address, address=target_address, blockchain=blockchain)

        # Add transactions from source
        for tx in source_txs:
            self._add_transaction_to_graph(graph, tx, blockchain)

        # Add transactions to target
        for tx in target_txs:
            self._add_transaction_to_graph(graph, tx, blockchain)

        # Expand graph with intermediate nodes
        await self._expand_graph_with_intermediates(
            graph, blockchain, max_hops, time_window_hours
        )

        return graph

    async def _get_address_transactions(
        self, address: str, blockchain: str, time_window_hours: int
    ) -> List[Dict]:
        """Get transactions for an address within time window"""

        # This would integrate with existing transaction collectors
        # For now, return empty list as placeholder
        logger.debug(
            f"Transaction history not yet implemented for {address} on {blockchain}"
        )
        return []

    def _add_transaction_to_graph(self, graph: nx.DiGraph, tx: Dict, blockchain: str):
        """Add a transaction to the graph"""

        from_addr = tx.get("from_address")
        to_addr = tx.get("to_address")
        amount = tx.get("amount", 0.0)
        tx_hash = tx.get("hash")
        timestamp = tx.get("timestamp")

        if not from_addr or not to_addr or not tx_hash:
            return

        # Add nodes if they don't exist
        if from_addr not in graph:
            graph.add_node(from_addr, address=from_addr, blockchain=blockchain)

        if to_addr not in graph:
            graph.add_node(to_addr, address=to_addr, blockchain=blockchain)

        # Add edge
        edge_data = {
            "transaction_hash": tx_hash,
            "amount": amount,
            "timestamp": timestamp,
            "blockchain": blockchain,
        }

        graph.add_edge(from_addr, to_addr, **edge_data)

    async def _expand_graph_with_intermediates(
        self, graph: nx.DiGraph, blockchain: str, max_hops: int, time_window_hours: int
    ):
        """Expand graph with intermediate nodes for better pathfinding"""

        # Get all unique addresses in current graph
        current_addresses = set(graph.nodes())

        # For each address, get their transactions to expand the graph
        for address in current_addresses:
            # Limit expansion to prevent infinite growth
            if len(graph.nodes()) > 1000:
                break

            txs = await self._get_address_transactions(
                address, blockchain, time_window_hours
            )

            for tx in txs:
                self._add_transaction_to_graph(graph, tx, blockchain)

    async def _find_shortest_paths(
        self, graph: nx.DiGraph, request: PathfindingRequest
    ) -> List[TransactionPath]:
        """Find shortest paths between source and target"""

        paths = []

        try:
            # Find shortest path by amount (weighted)
            shortest_path = nx.shortest_path(
                graph,
                source=request.source_address,
                target=request.target_address,
                weight="amount",
            )

            if shortest_path:
                path = await self._create_transaction_path(
                    graph, shortest_path, request
                )
                if path:
                    paths.append(path)

        except nx.NetworkXNoPath:
            logger.debug(
                f"No path found between {request.source_address} and {request.target_address}"
            )
        except Exception as e:
            logger.error(f"Error finding shortest path: {e}")

        return paths

    async def _find_all_paths(
        self, graph: nx.DiGraph, request: PathfindingRequest
    ) -> List[TransactionPath]:
        """Find all possible paths between source and target"""

        paths = []

        try:
            # Find all simple paths (no repeated nodes)
            all_paths = nx.all_simple_paths(
                graph,
                source=request.source_address,
                target=request.target_address,
                cutoff=request.max_hops,
            )

            # Convert to list and limit number of paths
            path_list = list(all_paths)[: request.max_paths]

            for path_nodes in path_list:
                path = await self._create_transaction_path(graph, path_nodes, request)
                if path:
                    paths.append(path)

        except nx.NetworkXNoPath:
            logger.debug(
                f"No path found between {request.source_address} and {request.target_address}"
            )
        except Exception as e:
            logger.error(f"Error finding all paths: {e}")

        return paths

    async def _find_disconnected_paths(
        self, graph: nx.DiGraph, request: PathfindingRequest
    ) -> List[TransactionPath]:
        """Find disconnected path segments"""

        paths = []

        # Find connected components
        components = list(nx.weakly_connected_components(graph))

        # Check if source and target are in different components
        source_component = None
        target_component = None

        for component in components:
            if request.source_address in component:
                source_component = component
            if request.target_address in component:
                target_component = component

        if (
            source_component
            and target_component
            and source_component != target_component
        ):
            # Create paths showing the disconnected segments
            source_subgraph = graph.subgraph(source_component)
            target_subgraph = graph.subgraph(target_component)

            # Find paths within each component
            for component_graph, component_name in [
                (source_subgraph, "source"),
                (target_subgraph, "target"),
            ]:
                if len(component_graph.nodes()) > 1:
                    # Find internal paths
                    try:
                        internal_paths = nx.all_simple_paths(
                            component_graph,
                            source=list(component_graph.nodes())[0],
                            target=list(component_graph.nodes())[-1],
                            cutoff=min(5, request.max_hops),
                        )

                        for path_nodes in list(internal_paths)[
                            :10
                        ]:  # Limit internal paths
                            path = await self._create_transaction_path(
                                graph, path_nodes, request
                            )
                            if path:
                                path.path_type = f"disconnected_{component_name}"
                                paths.append(path)

                    except Exception as e:
                        logger.debug(
                            f"No internal paths in {component_name} component: {e}"
                        )

        return paths

    async def _analyze_funnels(
        self, graph: nx.DiGraph, request: PathfindingRequest
    ) -> List[TransactionPath]:
        """Analyze funnel patterns (multiple sources converging to target)"""

        paths = []

        # Find all nodes that can reach the target
        predecessors = set()
        for node in graph.nodes():
            if node != request.target_address and nx.has_path(
                graph, node, request.target_address
            ):
                predecessors.add(node)

        # Group predecessors by convergence points
        convergence_points = defaultdict(list)

        for predecessor in predecessors:
            try:
                path = nx.shortest_path(graph, predecessor, request.target_address)
                if len(path) > 1:
                    convergence_point = path[1]  # First hop from predecessor
                    convergence_points[convergence_point].append(predecessor)
            except nx.NetworkXNoPath:
                continue

        # Create funnel paths
        for convergence_point, sources in convergence_points.items():
            if len(sources) >= 2:  # At least 2 sources converging
                for source in sources:
                    try:
                        path_nodes = nx.shortest_path(
                            graph, source, request.target_address
                        )
                        path = await self._create_transaction_path(
                            graph, path_nodes, request
                        )
                        if path:
                            path.path_type = "funnel"
                            path.metadata["convergence_point"] = convergence_point
                            path.metadata["funnel_sources"] = len(sources)
                            paths.append(path)
                    except nx.NetworkXNoPath:
                        continue

        return paths

    async def _find_circular_paths(
        self, graph: nx.DiGraph, request: PathfindingRequest
    ) -> List[TransactionPath]:
        """Find circular paths in the transaction graph"""

        paths = []

        try:
            # Find all cycles in the graph
            cycles = list(nx.simple_cycles(graph))

            for cycle_nodes in cycles[: request.max_paths]:  # Limit number of cycles
                if len(cycle_nodes) >= 3:  # Minimum cycle length
                    # Create a circular path by adding the first node at the end
                    circular_path = cycle_nodes + [cycle_nodes[0]]

                    path = await self._create_transaction_path(
                        graph, circular_path, request
                    )
                    if path:
                        path.path_type = "circular"
                        path.metadata["cycle_length"] = len(cycle_nodes)
                        paths.append(path)

        except Exception as e:
            logger.error(f"Error finding circular paths: {e}")

        return paths

    async def _create_transaction_path(
        self, graph: nx.DiGraph, path_nodes: List[str], request: PathfindingRequest
    ) -> Optional[TransactionPath]:
        """Create a TransactionPath from node sequence"""

        if len(path_nodes) < 2:
            return None

        transactions = []
        total_amount = 0.0

        # Build transactions from consecutive nodes
        for i in range(len(path_nodes) - 1):
            from_node = path_nodes[i]
            to_node = path_nodes[i + 1]

            if graph.has_edge(from_node, to_node):
                edge_data = graph[from_node][to_node]

                transaction = TransactionEdge(
                    from_address=from_node,
                    to_address=to_node,
                    transaction_hash=edge_data.get("transaction_hash", ""),
                    amount=edge_data.get("amount", 0.0),
                    timestamp=edge_data.get("timestamp", datetime.now(timezone.utc)),
                    blockchain=edge_data.get("blockchain", request.blockchain),
                    metadata=edge_data,
                )

                transactions.append(transaction)
                total_amount += transaction.amount
            else:
                logger.warning(f"No edge between {from_node} and {to_node}")
                return None

        # Calculate risk score (simplified)
        risk_score = self._calculate_path_risk_score(transactions)

        return TransactionPath(
            addresses=path_nodes,
            transactions=transactions,
            total_amount=total_amount,
            hop_count=len(path_nodes) - 1,
            path_length=total_amount,
            confidence_score=1.0,  # Will be calculated later
            risk_score=risk_score,
            path_type="standard",
        )

    def _calculate_path_risk_score(self, transactions: List[TransactionEdge]) -> float:
        """Calculate risk score for a path"""

        if not transactions:
            return 0.0

        # Simple risk calculation based on transaction characteristics
        risk_factors = []

        for tx in transactions:
            # High amount increases risk
            if tx.amount > 10000:
                risk_factors.append(0.3)
            elif tx.amount > 1000:
                risk_factors.append(0.2)
            else:
                risk_factors.append(0.1)

            # Recent transactions increase risk
            if tx.timestamp:
                age_hours = (
                    datetime.now(timezone.utc) - tx.timestamp
                ).total_seconds() / 3600
                if age_hours < 24:
                    risk_factors.append(0.2)
                elif age_hours < 168:
                    risk_factors.append(0.1)
                else:
                    risk_factors.append(0.05)

        return min(sum(risk_factors) / len(risk_factors), 1.0)

    def _filter_paths(
        self, paths: List[TransactionPath], request: PathfindingRequest
    ) -> List[TransactionPath]:
        """Filter paths based on request criteria"""

        filtered = []

        for path in paths:
            # Filter by amount
            if request.min_amount and path.total_amount < request.min_amount:
                continue

            if request.max_amount and path.total_amount > request.max_amount:
                continue

            # Filter by confidence
            if path.confidence_score < request.confidence_threshold:
                continue

            # Filter by hops
            if path.hop_count > request.max_hops:
                continue

            filtered.append(path)

        return filtered

    def _rank_paths(
        self, paths: List[TransactionPath], request: PathfindingRequest
    ) -> List[TransactionPath]:
        """Rank paths by relevance"""

        def path_score(path: TransactionPath) -> float:
            score = 0.0

            # Prefer shorter paths
            score += (1.0 / max(path.hop_count, 1)) * 0.3

            # Prefer higher amounts (for money flow analysis)
            score += min(path.total_amount / 1000000, 1.0) * 0.2

            # Prefer lower risk
            score += (1.0 - path.risk_score) * 0.2

            # Prefer higher confidence
            score += path.confidence_score * 0.3

            return score

        return sorted(paths, key=path_score, reverse=True)

    def _generate_cache_key(self, request: PathfindingRequest) -> str:
        """Generate cache key for request"""

        key_parts = [
            request.source_address,
            request.target_address,
            request.blockchain,
            request.algorithm.value,
            str(request.max_hops),
            str(request.time_window_hours),
            str(request.confidence_threshold),
        ]

        return ":".join(key_parts)

    async def _store_pathfinding_result(self, result: PathfindingResult):
        """Store pathfinding result in database"""

        insert_query = """
        INSERT INTO pathfinding_results (
            query_id, source_address, target_address, blockchain, algorithm,
            paths, total_paths_found, processing_time_ms, metadata
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """

        conn = await get_postgres_connection()
        try:
            await conn.execute(
                insert_query,
                result.query_id,
                result.source_address,
                result.target_address,
                result.blockchain,
                result.algorithm.value,
                [path.model_dump() for path in result.paths],
                result.total_paths_found,
                result.processing_time_ms,
                result.metadata,
            )
            await conn.commit()
        except Exception as e:
            logger.error(f"Error storing pathfinding result: {e}")
            await conn.rollback()
        finally:
            await conn.close()

    def clear_cache(self):
        """Clear the pathfinding cache"""
        self.cache.clear()
        logger.info("Pathfinding cache cleared")


# Global pathfinder instance
_pathfinder = None


def get_pathfinder() -> MultiRoutePathfinder:
    """Get the global pathfinder instance"""
    global _pathfinder
    if _pathfinder is None:
        _pathfinder = MultiRoutePathfinder()
    return _pathfinder
