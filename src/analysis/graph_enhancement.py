"""
Jackdaw Sentry - Graph Enhancement Tools
Advanced graph analysis and visualization enhancement tools
"""

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
import json
import uuid
import networkx as nx
import numpy as np
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


class GraphType(Enum):
    """Types of graphs for analysis"""
    TRANSACTION = "transaction"
    ADDRESS = "address"
    ENTITY = "entity"
    TEMPORAL = "temporal"
    ATTRIBUTION = "attribution"
    RISK = "risk"
    FLOW = "flow"


class EnhancementType(Enum):
    """Types of graph enhancements"""
    CLUSTERING = "clustering"
    COMMUNITY_DETECTION = "community_detection"
    CENTRALITY_ANALYSIS = "centrality_analysis"
    PATH_OPTIMIZATION = "path_optimization"
    ANOMALY_DETECTION = "anomaly_detection"
    RISK_SCORING = "risk_scoring"
    TEMPORAL_ANALYSIS = "temporal_analysis"
    FLOW_ANALYSIS = "flow_analysis"


class VisualizationType(Enum):
    """Visualization enhancement types"""
    FORCE_DIRECTED = "force_directed"
    HIERARCHICAL = "hierarchical"
    CIRCULAR = "circular"
    GEOGRAPHIC = "geographic"
    TEMPORAL = "temporal"
    MATRIX = "matrix"
    TREE = "tree"


@dataclass
class GraphMetrics:
    """Graph analysis metrics"""
    nodes: int = 0
    edges: int = 0
    density: float = 0.0
    average_degree: float = 0.0
    clustering_coefficient: float = 0.0
    connected_components: int = 0
    diameter: Optional[int] = None
    average_path_length: Optional[float] = None
    centrality_scores: Dict[str, float] = field(default_factory=dict)
    community_count: int = 0
    modularity: float = 0.0
    risk_score: float = 0.0
    anomaly_count: int = 0


@dataclass
class GraphCluster:
    """Graph cluster information"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nodes: List[str] = field(default_factory=list)
    edges: List[Tuple[str, str]] = field(default_factory=list)
    size: int = 0
    density: float = 0.0
    centrality_score: float = 0.0
    risk_score: float = 0.0
    community_id: Optional[int] = None
    modularity_contribution: float = 0.0
    key_nodes: List[str] = field(default_factory=list)
    created_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def calculate_metrics(self) -> None:
        """Calculate cluster metrics"""
        self.size = len(self.nodes)
        if self.size > 1:
            possible_edges = self.size * (self.size - 1) / 2
            self.density = len(self.edges) / possible_edges if possible_edges > 0 else 0.0


@dataclass
class GraphEnhancement:
    """Graph enhancement configuration and results"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    graph_id: str = ""
    enhancement_type: EnhancementType = EnhancementType.CLUSTERING
    parameters: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    metrics_before: Optional[GraphMetrics] = None
    metrics_after: Optional[GraphMetrics] = None
    performance_improvement: float = 0.0
    created_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processing_time: float = 0.0
    success: bool = False
    error_message: Optional[str] = None


@dataclass
class VisualizationConfig:
    """Visualization configuration"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    graph_id: str = ""
    visualization_type: VisualizationType = VisualizationType.FORCE_DIRECTED
    layout_algorithm: str = ""
    color_scheme: str = ""
    size_mapping: str = ""
    edge_weight_mapping: str = ""
    node_labels: bool = True
    edge_labels: bool = False
    interactive: bool = True
    filters: Dict[str, Any] = field(default_factory=dict)
    styling: Dict[str, Any] = field(default_factory=dict)
    export_format: str = "png"
    resolution: Tuple[int, int] = (1920, 1080)
    created_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class GraphEnhancementTools:
    """Advanced graph analysis and enhancement tools"""
    
    def __init__(self, db_pool=None):
        self.db_pool = db_pool
        self.graphs: Dict[str, nx.Graph] = {}
        self.enhancements: Dict[str, GraphEnhancement] = {}
        self.clusters: Dict[str, GraphCluster] = {}
        self.visualizations: Dict[str, VisualizationConfig] = {}
        self.running = False
        self._cache = {}
        self._cache_ttl = 3600  # 1 hour
        
        logger.info("GraphEnhancementTools initialized")
    
    async def initialize(self) -> None:
        """Initialize graph enhancement tools"""
        if self.db_pool:
            await self._create_database_schema()
        
        self.running = True
        logger.info("GraphEnhancementTools started")
    
    async def shutdown(self) -> None:
        """Shutdown graph enhancement tools"""
        self.running = False
        logger.info("GraphEnhancementTools shutdown")
    
    async def _create_database_schema(self) -> None:
        """Create graph enhancement database tables"""
        schema_queries = [
            """
            CREATE TABLE IF NOT EXISTS graph_enhancements (
                id UUID PRIMARY KEY,
                graph_id TEXT NOT NULL,
                enhancement_type TEXT NOT NULL,
                parameters JSONB DEFAULT '{}',
                results JSONB DEFAULT '{}',
                metrics_before JSONB,
                metrics_after JSONB,
                performance_improvement FLOAT DEFAULT 0.0,
                created_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                processing_time FLOAT DEFAULT 0.0,
                success BOOLEAN DEFAULT FALSE,
                error_message TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS graph_clusters (
                id UUID PRIMARY KEY,
                graph_id TEXT NOT NULL,
                nodes JSONB DEFAULT '[]',
                edges JSONB DEFAULT '[]',
                size INTEGER DEFAULT 0,
                density FLOAT DEFAULT 0.0,
                centrality_score FLOAT DEFAULT 0.0,
                risk_score FLOAT DEFAULT 0.0,
                community_id INTEGER,
                modularity_contribution FLOAT DEFAULT 0.0,
                key_nodes JSONB DEFAULT '[]',
                created_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS visualization_configs (
                id UUID PRIMARY KEY,
                graph_id TEXT NOT NULL,
                visualization_type TEXT NOT NULL,
                layout_algorithm TEXT,
                color_scheme TEXT,
                size_mapping TEXT,
                edge_weight_mapping TEXT,
                node_labels BOOLEAN DEFAULT TRUE,
                edge_labels BOOLEAN DEFAULT FALSE,
                interactive BOOLEAN DEFAULT TRUE,
                filters JSONB DEFAULT '{}',
                styling JSONB DEFAULT '{}',
                export_format TEXT DEFAULT 'png',
                resolution JSONB DEFAULT '[1920, 1080]',
                created_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_graph_enhancements_graph ON graph_enhancements(graph_id);
            CREATE INDEX IF NOT EXISTS idx_graph_enhancements_type ON graph_enhancements(enhancement_type);
            CREATE INDEX IF NOT EXISTS idx_graph_clusters_graph ON graph_clusters(graph_id);
            CREATE INDEX IF NOT EXISTS idx_visualization_configs_graph ON visualization_configs(graph_id);
            """
        ]
        
        async with self.db_pool.acquire() as conn:
            for query in schema_queries:
                await conn.execute(query)
        
        logger.info("Graph enhancement database schema created")
    
    async def load_graph(self, graph_id: str, graph_data: Dict[str, Any]) -> nx.Graph:
        """Load graph from data"""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Create NetworkX graph
            if graph_data.get("directed", False):
                graph = nx.DiGraph()
            else:
                graph = nx.Graph()
            
            # Add nodes
            nodes = graph_data.get("nodes", [])
            for node in nodes:
                node_id = node.get("id", str(uuid.uuid4()))
                attributes = {k: v for k, v in node.items() if k != "id"}
                graph.add_node(node_id, **attributes)
            
            # Add edges
            edges = graph_data.get("edges", [])
            for edge in edges:
                source = edge.get("source")
                target = edge.get("target")
                if source and target:
                    attributes = {k: v for k, v in edge.items() if k not in ["source", "target"]}
                    graph.add_edge(source, target, **attributes)
            
            self.graphs[graph_id] = graph
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(f"Loaded graph {graph_id} with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges in {processing_time:.2f}s")
            
            return graph
            
        except Exception as e:
            logger.error(f"Failed to load graph {graph_id}: {e}")
            raise
    
    async def calculate_graph_metrics(self, graph_id: str) -> GraphMetrics:
        """Calculate comprehensive graph metrics"""
        if graph_id not in self.graphs:
            raise ValueError(f"Graph {graph_id} not found")
        
        graph = self.graphs[graph_id]
        metrics = GraphMetrics()
        
        # Basic metrics
        metrics.nodes = graph.number_of_nodes()
        metrics.edges = graph.number_of_edges()
        
        if metrics.nodes > 0:
            metrics.density = nx.density(graph)
            degrees = dict(graph.degree())
            metrics.average_degree = sum(degrees.values()) / len(degrees)
            
            # Clustering coefficient
            if nx.is_connected(graph):
                metrics.clustering_coefficient = nx.average_clustering(graph)
                metrics.diameter = nx.diameter(graph)
                metrics.average_path_length = nx.average_shortest_path_length(graph)
            else:
                # For disconnected graphs, calculate for largest component
                largest_cc = max(nx.connected_components(graph), key=len)
                subgraph = graph.subgraph(largest_cc)
                metrics.clustering_coefficient = nx.average_clustering(subgraph)
                metrics.diameter = nx.diameter(subgraph)
                metrics.average_path_length = nx.average_shortest_path_length(subgraph)
            
            metrics.connected_components = nx.number_connected_components(graph)
            
            # Centrality scores
            centrality_measures = {
                "degree": nx.degree_centrality(graph),
                "betweenness": nx.betweenness_centrality(graph),
                "closeness": nx.closeness_centrality(graph),
                "eigenvector": nx.eigenvector_centrality(graph, max_iter=1000)
            }
            
            # Combine centrality scores
            for node in graph.nodes():
                node_centrality = 0.0
                for measure_name, measure_values in centrality_measures.items():
                    if node in measure_values:
                        node_centrality += measure_values[node]
                metrics.centrality_scores[node] = node_centrality / len(centrality_measures)
        
        return metrics
    
    async def detect_communities(self, graph_id: str, algorithm: str = "louvain") -> Dict[str, Any]:
        """Detect communities in graph"""
        if graph_id not in self.graphs:
            raise ValueError(f"Graph {graph_id} not found")
        
        graph = self.graphs[graph_id]
        start_time = datetime.now(timezone.utc)
        
        try:
            if algorithm == "louvain":
                import community as community_louvain
                communities = community_louvain.best_partition(graph)
                modularity = community_louvain.modularity(communities, graph)
            elif algorithm == "label_propagation":
                communities = nx.community.label_propagation_communities(graph)
                communities = {node: i for i, comm in enumerate(communities) for node in comm}
                modularity = nx.community.modularity(graph, list(nx.community.label_propagation_communities(graph)))
            else:
                # Default to simple connected components
                communities = {}
                for i, component in enumerate(nx.connected_components(graph)):
                    for node in component:
                        communities[node] = i
                modularity = 0.0
            
            # Group nodes by community
            community_groups = defaultdict(list)
            for node, community_id in communities.items():
                community_groups[community_id].append(node)
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            result = {
                "communities": dict(community_groups),
                "modularity": modularity,
                "community_count": len(community_groups),
                "algorithm": algorithm,
                "processing_time": processing_time
            }
            
            logger.info(f"Detected {len(community_groups)} communities in graph {graph_id} using {algorithm}")
            return result
            
        except Exception as e:
            logger.error(f"Community detection failed for graph {graph_id}: {e}")
            raise
    
    async def find_central_nodes(self, graph_id: str, top_k: int = 10) -> Dict[str, List[str]]:
        """Find central nodes using various centrality measures"""
        if graph_id not in self.graphs:
            raise ValueError(f"Graph {graph_id} not found")
        
        graph = self.graphs[graph_id]
        
        centrality_measures = {
            "degree": nx.degree_centrality(graph),
            "betweenness": nx.betweenness_centrality(graph),
            "closeness": nx.closeness_centrality(graph),
            "pagerank": nx.pagerank(graph)
        }
        
        central_nodes = {}
        for measure_name, centrality_values in centrality_measures.items():
            # Sort by centrality score and get top k
            sorted_nodes = sorted(centrality_values.items(), key=lambda x: x[1], reverse=True)
            central_nodes[measure_name] = [node for node, score in sorted_nodes[:top_k]]
        
        return central_nodes
    
    async def detect_anomalies(self, graph_id: str, method: str = "statistical") -> Dict[str, Any]:
        """Detect anomalies in graph structure"""
        if graph_id not in self.graphs:
            raise ValueError(f"Graph {graph_id} not found")
        
        graph = self.graphs[graph_id]
        anomalies = {
            "isolated_nodes": [],
            "high_degree_nodes": [],
            "bridge_edges": [],
            "structural_holes": [],
            "unusual_patterns": []
        }
        
        # Find isolated nodes
        for node in graph.nodes():
            if graph.degree(node) == 0:
                anomalies["isolated_nodes"].append(node)
        
        # Find high-degree nodes (outliers)
        degrees = dict(graph.degree())
        if degrees:
            degree_values = list(degrees.values())
            mean_degree = np.mean(degree_values)
            std_degree = np.std(degree_values)
            threshold = mean_degree + 2 * std_degree
            
            for node, degree in degrees.items():
                if degree > threshold:
                    anomalies["high_degree_nodes"].append({"node": node, "degree": degree})
        
        # Find bridge edges
        bridges = list(nx.bridges(graph))
        for edge in bridges:
            anomalies["bridge_edges"].append({"source": edge[0], "target": edge[1]})
        
        # Find structural holes (using betweenness centrality)
        betweenness = nx.betweenness_centrality(graph)
        if betweenness:
            betweenness_values = list(betweenness.values())
            mean_betweenness = np.mean(betweenness_values)
            std_betweenness = np.std(betweenness_values)
            threshold = mean_betweenness + 2 * std_betweenness
            
            for node, score in betweenness.items():
                if score > threshold:
                    anomalies["structural_holes"].append({"node": node, "betweenness": score})
        
        return {
            "anomalies": anomalies,
            "total_anomalies": sum(len(v) if isinstance(v, list) else len(v) for v in anomalies.values()),
            "method": method
        }
    
    async def optimize_graph_layout(self, graph_id: str, layout_algorithm: str = "spring") -> Dict[str, Any]:
        """Optimize graph layout for visualization"""
        if graph_id not in self.graphs:
            raise ValueError(f"Graph {graph_id} not found")
        
        graph = self.graphs[graph_id]
        
        layout_functions = {
            "spring": nx.spring_layout,
            "circular": nx.circular_layout,
            "random": nx.random_layout,
            "shell": nx.shell_layout,
            "kamada_kawai": nx.kamada_kawai_layout
        }
        
        if layout_algorithm not in layout_functions:
            layout_algorithm = "spring"
        
        try:
            pos = layout_functions[layout_algorithm](graph)
            
            # Convert positions to serializable format
            positions = {node: {"x": float(pos[node][0]), "y": float(pos[node][1])} for node in pos}
            
            return {
                "layout": positions,
                "algorithm": layout_algorithm,
                "bounds": self._calculate_layout_bounds(positions)
            }
            
        except Exception as e:
            logger.error(f"Layout optimization failed for graph {graph_id}: {e}")
            raise
    
    def _calculate_layout_bounds(self, positions: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """Calculate bounds of layout positions"""
        if not positions:
            return {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0}
        
        x_coords = [pos["x"] for pos in positions.values()]
        y_coords = [pos["y"] for pos in positions.values()]
        
        return {
            "min_x": min(x_coords),
            "max_x": max(x_coords),
            "min_y": min(y_coords),
            "max_y": max(y_coords)
        }
    
    async def apply_enhancement(self, graph_id: str, enhancement_type: EnhancementType, 
                              parameters: Dict[str, Any]) -> GraphEnhancement:
        """Apply graph enhancement"""
        if graph_id not in self.graphs:
            raise ValueError(f"Graph {graph_id} not found")
        
        start_time = datetime.now(timezone.utc)
        
        # Calculate metrics before enhancement
        metrics_before = await self.calculate_graph_metrics(graph_id)
        
        enhancement = GraphEnhancement(
            graph_id=graph_id,
            enhancement_type=enhancement_type,
            parameters=parameters,
            metrics_before=metrics_before
        )
        
        try:
            if enhancement_type == EnhancementType.COMMUNITY_DETECTION:
                results = await self.detect_communities(graph_id, parameters.get("algorithm", "louvain"))
            elif enhancement_type == EnhancementType.CENTRALITY_ANALYSIS:
                results = await self.find_central_nodes(graph_id, parameters.get("top_k", 10))
            elif enhancement_type == EnhancementType.ANOMALY_DETECTION:
                results = await self.detect_anomalies(graph_id, parameters.get("method", "statistical"))
            elif enhancement_type == EnhancementType.PATH_OPTIMIZATION:
                results = await self.optimize_graph_layout(graph_id, parameters.get("algorithm", "spring"))
            else:
                results = {"message": f"Enhancement type {enhancement_type.value} not implemented"}
            
            enhancement.results = results
            enhancement.success = True
            
            # Calculate metrics after enhancement (if applicable)
            if enhancement_type in [EnhancementType.COMMUNITY_DETECTION, EnhancementType.CLUSTERING]:
                metrics_after = await self.calculate_graph_metrics(graph_id)
                enhancement.metrics_after = metrics_after
                
                # Calculate performance improvement
                improvement = 0.0
                if metrics_before.clustering_coefficient > 0:
                    improvement = (metrics_after.clustering_coefficient - metrics_before.clustering_coefficient) / metrics_before.clustering_coefficient
                enhancement.performance_improvement = improvement
            
        except Exception as e:
            enhancement.success = False
            enhancement.error_message = str(e)
            logger.error(f"Enhancement failed for graph {graph_id}: {e}")
        
        enhancement.processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        if self.db_pool:
            await self._save_enhancement_to_db(enhancement)
        
        self.enhancements[enhancement.id] = enhancement
        return enhancement
    
    async def create_visualization_config(self, graph_id: str, config_data: Dict[str, Any]) -> VisualizationConfig:
        """Create visualization configuration"""
        config = VisualizationConfig(
            graph_id=graph_id,
            visualization_type=VisualizationType(config_data.get("visualization_type", "force_directed")),
            layout_algorithm=config_data.get("layout_algorithm", "spring"),
            color_scheme=config_data.get("color_scheme", "default"),
            size_mapping=config_data.get("size_mapping", "degree"),
            edge_weight_mapping=config_data.get("edge_weight_mapping", "weight"),
            node_labels=config_data.get("node_labels", True),
            edge_labels=config_data.get("edge_labels", False),
            interactive=config_data.get("interactive", True),
            filters=config_data.get("filters", {}),
            styling=config_data.get("styling", {}),
            export_format=config_data.get("export_format", "png"),
            resolution=tuple(config_data.get("resolution", [1920, 1080]))
        )
        
        if self.db_pool:
            await self._save_visualization_config_to_db(config)
        
        self.visualizations[config.id] = config
        logger.info(f"Created visualization config: {config.id}")
        return config
    
    async def get_graph_summary(self, graph_id: str) -> Dict[str, Any]:
        """Get comprehensive graph summary"""
        if graph_id not in self.graphs:
            raise ValueError(f"Graph {graph_id} not found")
        
        metrics = await self.calculate_graph_metrics(graph_id)
        central_nodes = await self.find_central_nodes(graph_id, 5)
        anomalies = await self.detect_anomalies(graph_id)
        
        return {
            "graph_id": graph_id,
            "metrics": {
                "nodes": metrics.nodes,
                "edges": metrics.edges,
                "density": metrics.density,
                "average_degree": metrics.average_degree,
                "clustering_coefficient": metrics.clustering_coefficient,
                "connected_components": metrics.connected_components,
                "diameter": metrics.diameter,
                "average_path_length": metrics.average_path_length
            },
            "central_nodes": central_nodes,
            "anomalies": anomalies,
            "enhancements": len([e for e in self.enhancements.values() if e.graph_id == graph_id])
        }
    
    # Database helper methods
    async def _save_enhancement_to_db(self, enhancement: GraphEnhancement) -> None:
        """Save enhancement to database"""
        query = """
        INSERT INTO graph_enhancements 
        (id, graph_id, enhancement_type, parameters, results, metrics_before, metrics_after,
         performance_improvement, created_date, processing_time, success, error_message)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        ON CONFLICT (id) DO UPDATE SET
        results = EXCLUDED.results,
        metrics_after = EXCLUDED.metrics_after,
        performance_improvement = EXCLUDED.performance_improvement,
        processing_time = EXCLUDED.processing_time,
        success = EXCLUDED.success,
        error_message = EXCLUDED.error_message
        """
        
        metrics_before_json = json.dumps(enhancement.metrics_before.__dict__) if enhancement.metrics_before else None
        metrics_after_json = json.dumps(enhancement.metrics_after.__dict__) if enhancement.metrics_after else None
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(query, enhancement.id, enhancement.graph_id, enhancement.enhancement_type.value,
                             json.dumps(enhancement.parameters), json.dumps(enhancement.results),
                             metrics_before_json, metrics_after_json, enhancement.performance_improvement,
                             enhancement.created_date, enhancement.processing_time, enhancement.success,
                             enhancement.error_message)
    
    async def _save_visualization_config_to_db(self, config: VisualizationConfig) -> None:
        """Save visualization configuration to database"""
        query = """
        INSERT INTO visualization_configs 
        (id, graph_id, visualization_type, layout_algorithm, color_scheme, size_mapping,
         edge_weight_mapping, node_labels, edge_labels, interactive, filters, styling,
         export_format, resolution, created_date)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
        ON CONFLICT (id) DO UPDATE SET
        layout_algorithm = EXCLUDED.layout_algorithm,
        color_scheme = EXCLUDED.color_scheme,
        size_mapping = EXCLUDED.size_mapping,
        edge_weight_mapping = EXCLUDED.edge_weight_mapping,
        node_labels = EXCLUDED.node_labels,
        edge_labels = EXCLUDED.edge_labels,
        interactive = EXCLUDED.interactive,
        filters = EXCLUDED.filters,
        styling = EXCLUDED.styling,
        export_format = EXCLUDED.export_format,
        resolution = EXCLUDED.resolution
        """
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(query, config.id, config.graph_id, config.visualization_type.value,
                             config.layout_algorithm, config.color_scheme, config.size_mapping,
                             config.edge_weight_mapping, config.node_labels, config.edge_labels,
                             config.interactive, json.dumps(config.filters), json.dumps(config.styling),
                             config.export_format, json.dumps(config.resolution), config.created_date)
