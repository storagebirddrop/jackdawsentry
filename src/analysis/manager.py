"""
Jackdaw Sentry - Analysis Manager
Orchestrates all analysis engines and workflows
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import hashlib
import json

from .cross_chain import CrossChainAnalyzer, get_cross_chain_analyzer
from .stablecoin_flows import StablecoinFlowTracker, get_stablecoin_flow_tracker
from .pattern_detection import MLPatternDetector, get_ml_pattern_detector
from .mixer_detection import MixerDetector, get_mixer_detector
from .ml_clustering import MLClusteringEngine, get_ml_clustering_engine
from .bridge_tracker import BridgeTracker
from src.api.database import get_redis_connection
from src.api.config import settings

logger = logging.getLogger(__name__)


class AnalysisManager:
    """Manages all analysis engines"""
    
    def __init__(self):
        self.is_running = False
        self.engines = {}
        self.metrics = {
            'total_engines': 0,
            'running_engines': 0,
            'analysis_completed': 0,
            'alerts_generated': 0,
            'last_update': None
        }
    
    async def initialize(self):
        """Initialize all analysis engines"""
        logger.info("Initializing analysis engines...")
        
        # Initialize cross-chain analyzer
        self.engines['cross_chain'] = get_cross_chain_analyzer()
        
        # Initialize stablecoin flow tracker
        self.engines['stablecoin_flows'] = get_stablecoin_flow_tracker()
        
        # Initialize ML pattern detector
        self.engines['pattern_detection'] = get_ml_pattern_detector()
        
        # Initialize mixer detector
        self.engines['mixer_detection'] = get_mixer_detector()
        
        # Initialize ML clustering engine
        self.engines['ml_clustering'] = get_ml_clustering_engine()
        
        # Initialize bridge tracker
        self.engines['bridge_tracker'] = BridgeTracker()
        
        # Initialize other engines when implemented
        # self.engines['risk_scorer'] = RiskScorer()
        
        self.metrics['total_engines'] = len(self.engines)
        logger.info(f"Initialized {len(self.engines)} analysis engines")
    
    async def start_all(self):
        """Start all analysis engines"""
        if self.is_running:
            logger.warning("Analysis manager is already running")
            return
        
        logger.info("Starting all analysis engines...")
        self.is_running = True
        
        # Start all engines
        tasks = []
        for engine_name, engine in self.engines.items():
            task = asyncio.create_task(self.start_engine(engine_name, engine))
            tasks.append(task)
        
        # Start metrics collection
        tasks.append(asyncio.create_task(self.collect_metrics()))
        
        # Start health monitoring
        tasks.append(asyncio.create_task(self.monitor_health()))
        
        # Wait for all tasks
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def start_engine(self, engine_name: str, engine):
        """Start individual analysis engine"""
        try:
            logger.info(f"Starting {engine_name} engine...")
            # Most engines don't need explicit start methods
            # They work on-demand
            logger.info(f"Started {engine_name} engine")
        except Exception as e:
            logger.error(f"Failed to start {engine_name} engine: {e}")
    
    async def stop_all(self):
        """Stop all analysis engines"""
        logger.info("Stopping all analysis engines...")
        self.is_running = False
        
        # Stop all engines
        tasks = []
        for engine_name, engine in self.engines.items():
            task = asyncio.create_task(self.stop_engine(engine_name, engine))
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("All analysis engines stopped")
    
    async def stop_engine(self, engine_name: str, engine):
        """Stop individual analysis engine"""
        try:
            logger.info(f"Stopping {engine_name} engine...")
            # Most engines don't need explicit stop methods
            logger.info(f"Stopped {engine_name} engine")
        except Exception as e:
            logger.error(f"Failed to stop {engine_name} engine: {e}")
    
    async def analyze_address(self, address: str, blockchain: str, time_range: int = 24) -> Dict[str, Any]:
        """Comprehensive address analysis"""
        try:
            logger.info(f"Analyzing address {address} on {blockchain}")
            
            analysis_results = {
                'address': address,
                'blockchain': blockchain,
                'time_range_hours': time_range,
                'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
                'cross_chain_analysis': {},
                'stablecoin_flows': {},
                'ml_patterns': {},
                'mixer_analysis': {},
                'risk_assessment': {},
                'cluster_info': {},
                'overall_risk_score': 0.0,
                'recommendations': []
            }
            
            # Cross-chain analysis
            if 'cross_chain' in self.engines:
                cross_chain_analysis = await self.engines['cross_chain'].get_cross_chain_analysis(address, time_range)
                analysis_results['cross_chain_analysis'] = cross_chain_analysis
            
            # Stablecoin flow analysis
            if 'stablecoin_flows' in self.engines:
                stablecoin_flows = await self.engines['stablecoin_flows'].analyze_stablecoin_flows(address, time_range)
                analysis_results['stablecoin_flows'] = stablecoin_flows
            
            # ML pattern detection
            if 'pattern_detection' in self.engines:
                ml_patterns = await self.engines['pattern_detection'].detect_patterns(address, blockchain, time_range)
                analysis_results['ml_patterns'] = {
                    'patterns_detected': len(ml_patterns),
                    'patterns': [pattern.__dict__ for pattern in ml_patterns]
                }
            
            # Mixer detection
            if 'mixer_detection' in self.engines:
                mixer_analysis = await self.engines['mixer_detection'].detect_mixer_usage(address, blockchain, time_range)
                analysis_results['mixer_analysis'] = {
                    'total_mixer_transactions': mixer_analysis.total_mixer_transactions,
                    'total_amount_mixed': mixer_analysis.total_amount_mixed,
                    'mixers_used': [mixer.value for mixer in mixer_analysis.mixers_used],
                    'risk_score': mixer_analysis.risk_score,
                    'patterns': mixer_analysis.mixing_patterns
                }
            
            # Privacy tool detection
            if 'mixer_detection' in self.engines:
                privacy_analysis = await self.engines['mixer_detection'].detect_privacy_tool_usage(address, blockchain, time_range)
                analysis_results['privacy_tool_analysis'] = privacy_analysis
            
            # ML risk assessment
            if 'ml_clustering' in self.engines:
                risk_assessment = await self.engines['ml_clustering'].get_address_risk_assessment(address, blockchain, time_range)
                analysis_results['risk_assessment'] = {
                    'risk_score': risk_assessment.risk_score,
                    'risk_level': risk_assessment.risk_level.value,
                    'confidence': risk_assessment.confidence,
                    'primary_risk_factors': risk_assessment.primary_risk_factors,
                    'secondary_risk_factors': risk_assessment.secondary_risk_factors,
                    'recommended_actions': risk_assessment.recommended_actions,
                    'cluster_affiliation': risk_assessment.cluster_affiliation
                }
                analysis_results['overall_risk_score'] = risk_assessment.risk_score
                analysis_results['recommendations'] = risk_assessment.recommended_actions
            
            # Cluster information
            if 'ml_clustering' in self.engines and analysis_results['risk_assessment'].get('cluster_affiliation'):
                cluster_id = analysis_results['risk_assessment']['cluster_affiliation']
                # Get cluster details would be implemented here
                analysis_results['cluster_info'] = {'cluster_id': cluster_id}
            
            # Cache results
            await self.cache_analysis_results(f"address_{address}_{blockchain}", analysis_results)
            
            # Update metrics
            self.metrics['analysis_completed'] += 1
            
            logger.info(f"Completed analysis for address {address}")
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error analyzing address {address}: {e}")
            return {}
    
    async def analyze_transaction(self, tx_hash: str, blockchain: str) -> Dict[str, Any]:
        """Comprehensive transaction analysis"""
        try:
            logger.info(f"Analyzing transaction {tx_hash} on {blockchain}")
            
            analysis_results = {
                'tx_hash': tx_hash,
                'blockchain': blockchain,
                'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
                'cross_chain_analysis': {},
                'stablecoin_flow': {},
                'ml_patterns': {},
                'mixer_analysis': {},
                'risk_assessment': {},
                'overall_risk_score': 0.0,
                'alerts': []
            }
            
            # Cross-chain analysis
            if 'cross_chain' in self.engines:
                cross_chain_tx = await self.engines['cross_chain'].analyze_transaction(tx_hash, blockchain)
                if cross_chain_tx:
                    analysis_results['cross_chain_analysis'] = {
                        'patterns': [pattern.value for pattern in cross_chain_tx.patterns],
                        'risk_score': cross_chain_tx.risk_score,
                        'confidence': cross_chain_tx.confidence,
                        'related_transactions': cross_chain_tx.related_transactions
                    }
                    analysis_results['overall_risk_score'] = cross_chain_tx.risk_score
            
            # Stablecoin flow tracking
            if 'stablecoin_flows' in self.engines:
                stablecoin_flow = await self.engines['stablecoin_flows'].track_stablecoin_flow(tx_hash, blockchain)
                if stablecoin_flow:
                    analysis_results['stablecoin_flow'] = {
                        'flow_type': stablecoin_flow.flow_type.value,
                        'total_amount': stablecoin_flow.total_amount,
                        'hop_count': stablecoin_flow.hop_count,
                        'risk_score': stablecoin_flow.risk_score,
                        'confidence': stablecoin_flow.confidence,
                        'blockchains': stablecoin_flow.blockchains
                    }
            
            # Generate alerts for high-risk transactions
            if analysis_results['overall_risk_score'] > 0.7:
                analysis_results['alerts'].append({
                    'type': 'high_risk_transaction',
                    'severity': 'high',
                    'message': f"High-risk transaction detected: {tx_hash}",
                    'risk_score': analysis_results['overall_risk_score']
                })
                self.metrics['alerts_generated'] += 1
            
            # Cache results
            await self.cache_analysis_results(f"transaction_{tx_hash}_{blockchain}", analysis_results)
            
            # Update metrics
            self.metrics['analysis_completed'] += 1
            
            logger.info(f"Completed analysis for transaction {tx_hash}")
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error analyzing transaction {tx_hash}: {e}")
            return {}
    
    async def analyze_transaction_flow(self, start_address: str, end_address: str, blockchain: str) -> Dict[str, Any]:
        """Analyze transaction flow between addresses"""
        try:
            logger.info(f"Analyzing transaction flow from {start_address} to {end_address}")
            
            flow_analysis = {}
            
            # Cross-chain flow analysis
            if 'cross_chain' in self.engines:
                transaction_flow = await self.engines['cross_chain'].analyze_transaction_flow(start_address, end_address)
                if transaction_flow:
                    flow_analysis = {
                        'flow_id': transaction_flow.flow_id,
                        'total_amount': transaction_flow.total_amount,
                        'path_length': len(transaction_flow.path),
                        'blockchains': transaction_flow.blockchains,
                        'duration_seconds': transaction_flow.duration.total_seconds(),
                        'patterns': [pattern.value for pattern in transaction_flow.patterns],
                        'risk_score': transaction_flow.risk_score,
                        'confidence': transaction_flow.confidence,
                        'transactions': [tx.__dict__ for tx in transaction_flow.path]
                    }
            
            # Cache results
            await self.cache_analysis_results(f"flow_{start_address}_{end_address}_{blockchain}", flow_analysis)
            
            return flow_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing transaction flow: {e}")
            return {}
    
    async def get_system_statistics(self) -> Dict[str, Any]:
        """Get system-wide analysis statistics"""
        try:
            stats = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'engines': {
                    'total': len(self.engines),
                    'running': sum(1 for engine in self.engines.values() if hasattr(engine, 'is_running') and engine.is_running)
                },
                'metrics': self.metrics,
                'performance': {}
            }
            
            # Get engine-specific statistics
            if 'mixer_detection' in self.engines:
                mixer_stats = await self.engines['mixer_detection'].get_mixer_statistics(24)
                stats['mixer_statistics'] = mixer_stats
            
            if 'stablecoin_flows' in self.engines:
                # Would get stablecoin flow statistics here
                stats['stablecoin_statistics'] = {'status': 'available'}
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting system statistics: {e}")
            return {}
    
    async def collect_metrics(self):
        """Collect and aggregate metrics from all engines"""
        while self.is_running:
            try:
                total_analysis = 0
                total_alerts = 0
                running_engines = 0
                
                for engine in self.engines.values():
                    # Engine-specific metrics collection would go here
                    if hasattr(engine, 'get_metrics'):
                        metrics = await engine.get_metrics()
                        if 'analysis_completed' in metrics:
                            total_analysis += metrics['analysis_completed']
                        if 'alerts_generated' in metrics:
                            total_alerts += metrics['alerts_generated']
                    
                    if getattr(engine, 'is_running', False):
                        running_engines += 1
                
                self.metrics.update({
                    'analysis_completed': total_analysis,
                    'alerts_generated': total_alerts,
                    'running_engines': running_engines,
                    'last_update': datetime.now(timezone.utc).isoformat()
                })
                
                # Cache metrics in Redis
                await self.cache_metrics()
                
                await asyncio.sleep(60)  # Update every minute
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(30)
    
    async def monitor_health(self):
        """Monitor health of all analysis engines"""
        while self.is_running:
            try:
                for engine_name, engine in self.engines.items():
                    if hasattr(engine, 'is_healthy'):
                        healthy = await engine.is_healthy()
                        if not healthy:
                            logger.warning(f"Engine {engine_name} is unhealthy")
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Error monitoring health: {e}")
                await asyncio.sleep(30)

    async def cache_analysis_results(self, key: str, results: Dict[str, Any], ttl: int = 3600):
        """Cache analysis results in Redis"""
        try:
            safe_key = hashlib.sha256(key.encode()).hexdigest()[:32]
            async with get_redis_connection() as redis:
                await redis.setex(
                    f'analysis:{safe_key}',
                    ttl,
                    json.dumps(results, default=str)
                )
        except Exception as e:
            logger.error(f"Error caching analysis results: {e}")

    async def cache_metrics(self):
        """Cache analysis metrics"""
        try:
            async with get_redis_connection() as redis:
                await redis.setex(
                    'analysis_metrics',
                    300,  # 5 minutes
                    json.dumps(self.metrics)
                )
        except Exception as e:
            logger.error(f"Error caching analysis metrics: {e}")
    
    async def run_analysis_workflow(self, workflow_name: str, parameters: Dict) -> Dict:
        """Run a specific analysis workflow"""
        try:
            logger.info(f"Running analysis workflow: {workflow_name}")
            
            if workflow_name == "cross_chain_stablecoin_analysis":
                return await self.cross_chain_stablecoin_analysis(parameters)
            elif workflow_name == "lightning_risk_analysis":
                return await self.lightning_risk_analysis(parameters)
            elif workflow_name == "bridge_anomaly_detection":
                return await self.bridge_anomaly_detection(parameters)
            else:
                return {'error': f'Unknown workflow: {workflow_name}'}
                
        except Exception as e:
            logger.error(f"Error running workflow {workflow_name}: {e}")
            return {'error': str(e)}
    
    async def cross_chain_stablecoin_analysis(self, parameters: Dict) -> Dict:
        """Cross-chain stablecoin analysis workflow"""
        try:
            # Get stablecoin transfers across all chains
            query = """
            MATCH (b:BridgeTransfer)-[:INVOLVES]->(s:Stablecoin)
            WHERE b.created_at > timestamp() - $time_range
            RETURN b.bridge_name as bridge,
                   b.source_chain as source,
                   b.destination_chain as dest,
                   s.symbol as symbol,
                   b.amount as amount,
                   b.created_at as timestamp
            ORDER BY timestamp DESC
            LIMIT $limit
            """
            
            from src.api.database import get_neo4j_session
            async with get_neo4j_session() as session:
                result = await session.run(query,
                    time_range=parameters.get('time_range', 86400000),  # 24 hours
                    limit=parameters.get('limit', 1000)
                )
                
                transfers = [record for record in result]
                
                # Analyze patterns
                analysis = await self.analyze_transfer_patterns(transfers)
                
                return {
                    'workflow': 'cross_chain_stablecoin_analysis',
                    'transfers_analyzed': len(transfers),
                    'patterns_detected': analysis,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error in cross-chain stablecoin analysis: {e}")
            return {'error': str(e)}
    
    async def lightning_risk_analysis(self, parameters: Dict) -> Dict:
        """Lightning Network risk analysis workflow"""
        try:
            # Get Lightning Network data
            lightning_data = await self.get_cached_data('lightning_monitor')
            if not lightning_data:
                return {'error': 'Lightning data not available'}
            
            # Analyze for risks
            risks = await self.analyze_lightning_risks(lightning_data)
            
            return {
                'workflow': 'lightning_risk_analysis',
                'risks_detected': risks,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in lightning risk analysis: {e}")
            return {'error': str(e)}
    
    async def bridge_anomaly_detection(self, parameters: Dict) -> Dict:
        """Bridge anomaly detection workflow"""
        try:
            # Get bridge data
            bridge_data = await self.get_cached_data('bridge_tracker')
            if not bridge_data:
                return {'error': 'Bridge data not available'}
            
            # Detect anomalies
            anomalies = await self.detect_bridge_anomalies(bridge_data)
            
            return {
                'workflow': 'bridge_anomaly_detection',
                'anomalies_detected': anomalies,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in bridge anomaly detection: {e}")
            return {'error': str(e)}
    
    async def analyze_transfer_patterns(self, transfers: List[Dict]) -> Dict:
        """Analyze patterns in stablecoin transfers"""
        patterns = {
            'high_volume_bridges': {},
            'frequent_destinations': {},
            'unusual_timing': [],
            'round_amounts': []
        }
        
        try:
            # Analyze high volume bridges
            bridge_volumes = {}
            for transfer in transfers:
                bridge = transfer.get('bridge')
                amount = transfer.get('amount', 0)
                
                if bridge not in bridge_volumes:
                    bridge_volumes[bridge] = 0
                bridge_volumes[bridge] += amount
            
            # Top bridges by volume
            sorted_bridges = sorted(bridge_volumes.items(), key=lambda x: x[1], reverse=True)
            patterns['high_volume_bridges'] = dict(sorted_bridges[:5])
            
            # Analyze frequent destinations
            destinations = {}
            for transfer in transfers:
                dest = transfer.get('dest')
                if dest:
                    destinations[dest] = destinations.get(dest, 0) + 1
            
            sorted_dests = sorted(destinations.items(), key=lambda x: x[1], reverse=True)
            patterns['frequent_destinations'] = dict(sorted_dests[:10])
            
        except Exception as e:
            logger.error(f"Error analyzing transfer patterns: {e}")
        
        return patterns
    
    async def analyze_lightning_risks(self, lightning_data: Dict) -> List[Dict]:
        """Analyze Lightning Network for risks"""
        risks = []
        
        try:
            # Check for high-value payments
            if lightning_data.get('payments_tracked', 0) > 0:
                # This would analyze Lightning payment patterns
                pass
            
        except Exception as e:
            logger.error(f"Error analyzing Lightning risks: {e}")
        
        return risks
    
    async def detect_bridge_anomalies(self, bridge_data: Dict) -> List[Dict]:
        """Detect anomalies in bridge data"""
        anomalies = []
        
        try:
            # Check for volume anomalies
            if bridge_data.get('total_volume', 0) > 1000000:  # > $1M
                anomalies.append({
                    'type': 'high_volume',
                    'description': 'Unusually high bridge volume',
                    'severity': 'medium'
                })
            
        except Exception as e:
            logger.error(f"Error detecting bridge anomalies: {e}")
        
        return anomalies
    
    async def start(self):
        """Start the analysis manager"""
        await self.initialize()
        await self.start_all()
    
    async def stop(self):
        """Stop the analysis manager"""
        await self.stop_all()


# Global analysis manager instance
_analysis_manager: Optional[AnalysisManager] = None


def get_analysis_manager() -> AnalysisManager:
    """Get global analysis manager instance"""
    global _analysis_manager
    if _analysis_manager is None:
        _analysis_manager = AnalysisManager()
    return _analysis_manager
