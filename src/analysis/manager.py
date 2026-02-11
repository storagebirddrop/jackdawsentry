"""
Jackdaw Sentry - Analysis Manager
Orchestrates all analysis engines and workflows
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

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
        
        # Initialize bridge tracker
        self.engines['bridge_tracker'] = BridgeTracker()
        
        # Initialize other engines when implemented
        # self.engines['risk_scorer'] = RiskScorer()
        # self.engines['address_clustering'] = AddressClustering()
        # self.engines['ml_models'] = MLModels()
        
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
        for name, engine in self.engines.items():
            task = asyncio.create_task(self.start_engine(name, engine))
            tasks.append(task)
        
        # Start metrics collection
        tasks.append(asyncio.create_task(self.collect_metrics()))
        
        # Start health monitoring
        tasks.append(asyncio.create_task(self.monitor_health()))
        
        # Start coordination tasks
        tasks.append(asyncio.create_task(self.coordinate_analysis()))
        
        # Wait for all tasks
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def start_engine(self, name: str, engine):
        """Start individual analysis engine"""
        try:
            logger.info(f"Starting {name} analysis engine...")
            await engine.start()
        except Exception as e:
            logger.error(f"Failed to start {name} analysis engine: {e}")
    
    async def stop_all(self):
        """Stop all analysis engines"""
        logger.info("Stopping all analysis engines...")
        self.is_running = False
        
        # Stop all engines
        tasks = []
        for name, engine in self.engines.items():
            task = asyncio.create_task(self.stop_engine(name, engine))
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("All analysis engines stopped")
    
    async def stop_engine(self, name: str, engine):
        """Stop individual analysis engine"""
        try:
            logger.info(f"Stopping {name} analysis engine...")
            await engine.stop()
        except Exception as e:
            logger.error(f"Failed to stop {name} analysis engine: {e}")
    
    async def restart_engine(self, name: str):
        """Restart a specific analysis engine"""
        if name not in self.engines:
            logger.error(f"Analysis engine {name} not found")
            return
        
        engine = self.engines[name]
        logger.info(f"Restarting {name} analysis engine...")
        
        try:
            await engine.stop()
            await asyncio.sleep(5)  # Wait before restart
            await engine.start()
            logger.info(f"Successfully restarted {name} analysis engine")
        except Exception as e:
            logger.error(f"Failed to restart {name} analysis engine: {e}")
    
    async def get_engine_status(self, name: str) -> Optional[Dict]:
        """Get status of specific analysis engine"""
        if name not in self.engines:
            return None
        
        engine = self.engines[name]
        try:
            if hasattr(engine, 'get_metrics'):
                return await engine.get_metrics()
            else:
                return {
                    'name': name,
                    'is_running': getattr(engine, 'is_running', False)
                }
        except Exception as e:
            logger.error(f"Error getting {name} engine status: {e}")
            return {
                'name': name,
                'error': str(e),
                'is_running': False
            }
    
    async def get_all_status(self) -> Dict[str, Any]:
        """Get status of all analysis engines"""
        status = {
            'manager': {
                'is_running': self.is_running,
                'total_engines': len(self.engines),
                'running_engines': sum(1 for e in self.engines.values() if getattr(e, 'is_running', False))
            },
            'engines': {},
            'metrics': self.metrics
        }
        
        # Get individual engine status
        for name, engine in self.engines.items():
            try:
                status['engines'][name] = await self.get_engine_status(name)
            except Exception as e:
                status['engines'][name] = {
                    'error': str(e),
                    'is_running': False
                }
        
        return status
    
    async def coordinate_analysis(self):
        """Coordinate analysis between engines"""
        while self.is_running:
            try:
                # Share data between engines
                await self.share_analysis_data()
                
                # Trigger coordinated analysis
                await self.trigger_coordinated_analysis()
                
                await asyncio.sleep(300)  # Coordinate every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in analysis coordination: {e}")
                await asyncio.sleep(60)
    
    async def share_analysis_data(self):
        """Share analysis data between engines"""
        try:
            # Get data from each engine
            engine_data = {}
            for name, engine in self.engines.items():
                if hasattr(engine, 'get_analysis_data'):
                    data = await engine.get_analysis_data()
                    if data:
                        engine_data[name] = data
            
            # Share data via Redis for other engines to use
            if engine_data:
                await self.cache_analysis_data(engine_data)
                
        except Exception as e:
            logger.error(f"Error sharing analysis data: {e}")
    
    async def trigger_coordinated_analysis(self):
        """Trigger coordinated analysis workflows"""
        try:
            # Example: Cross-reference bridge data with risk scoring
            bridge_data = await self.get_cached_data('bridge_tracker')
            if bridge_data:
                await self.analyze_bridge_risks(bridge_data)
            
            # Example: Correlate Lightning Network with on-chain transactions
            lightning_data = await self.get_cached_data('lightning_monitor')
            if lightning_data:
                await self.correlate_lightning_onchain(lightning_data)
                
        except Exception as e:
            logger.error(f"Error in coordinated analysis: {e}")
    
    async def analyze_bridge_risks(self, bridge_data: Dict):
        """Analyze risks in bridge data"""
        try:
            # Check for suspicious bridge patterns
            if bridge_data.get('suspicious_bridges', 0) > 0:
                await self.generate_coordinated_alert(
                    'bridge_risk',
                    'Suspicious bridge activity detected',
                    bridge_data
                )
                
        except Exception as e:
            logger.error(f"Error analyzing bridge risks: {e}")
    
    async def correlate_lightning_onchain(self, lightning_data: Dict):
        """Correlate Lightning Network with on-chain transactions"""
        try:
            # Look for patterns between Lightning and on-chain
            # This would implement correlation logic
            
            if lightning_data.get('high_value_payments', 0) > 0:
                await self.generate_coordinated_alert(
                    'lightning_onchain',
                    'High-value Lightning payments detected',
                    lightning_data
                )
                
        except Exception as e:
            logger.error(f"Error correlating Lightning and on-chain: {e}")
    
    async def generate_coordinated_alert(self, alert_type: str, message: str, data: Dict):
        """Generate coordinated alert from multiple engines"""
        logger.warning(f"Coordinated alert ({alert_type}): {message}")
        
        # Store coordinated alert
        query = """
        MERGE (a:CoordinatedAlert {type: $alert_type})
        SET a.message = $message,
            a.data = $data,
            a.engines_involved = $engines,
            a.severity = 'high',
            a.created_at = timestamp()
        """
        
        from src.api.database import get_neo4j_session
        async with get_neo4j_session() as session:
            await session.run(query,
                alert_type=alert_type,
                message=message,
                data=json.dumps(data),
                engines=list(data.keys())
            )
        
        self.metrics['alerts_generated'] += 1
    
    async def cache_analysis_data(self, engine_data: Dict):
        """Cache analysis data for sharing"""
        try:
            async with get_redis_connection() as redis:
                for engine_name, data in engine_data.items():
                    await redis.setex(
                        f'analysis_data:{engine_name}',
                        300,  # 5 minutes
                        json.dumps(data)
                    )
        except Exception as e:
            logger.error(f"Error caching analysis data: {e}")
    
    async def get_cached_data(self, engine_name: str) -> Optional[Dict]:
        """Get cached analysis data"""
        try:
            async with get_redis_connection() as redis:
                data = await redis.get(f'analysis_data:{engine_name}')
                return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Error getting cached data: {e}")
            return None
    
    async def monitor_health(self):
        """Monitor health of all analysis engines"""
        while self.is_running:
            try:
                for name, engine in self.engines.items():
                    if not getattr(engine, 'is_running', False):
                        logger.warning(f"Analysis engine {name} is not running, attempting restart...")
                        asyncio.create_task(self.restart_engine(name))
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(60)
    
    async def collect_metrics(self):
        """Collect and aggregate metrics from all engines"""
        while self.is_running:
            try:
                total_analysis = 0
                total_alerts = 0
                running_engines = 0
                
                for engine in self.engines.values():
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
                    'last_update': datetime.utcnow().isoformat()
                })
                
                # Cache metrics
                await self.cache_metrics()
                
                await asyncio.sleep(60)  # Update every minute
                
            except Exception as e:
                logger.error(f"Error collecting analysis metrics: {e}")
                await asyncio.sleep(30)
    
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
                    'timestamp': datetime.utcnow().isoformat()
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
                'timestamp': datetime.utcnow().isoformat()
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
                'timestamp': datetime.utcnow().isoformat()
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
