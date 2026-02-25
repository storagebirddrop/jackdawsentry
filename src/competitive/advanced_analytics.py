"""
Jackdaw Sentry - Advanced Analytics for Competitive Assessment
Machine learning predictions, anomaly detection, and predictive analytics
"""

import asyncio
import json
import statistics
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
import logging
import asyncpg
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

@dataclass
class PerformancePrediction:
    """Performance prediction result"""
    feature: str
    current_value: float
    predicted_value: float
    confidence: float
    trend: str  # 'improving', 'declining', 'stable'
    prediction_horizon: str  # '1h', '6h', '24h', '7d'
    timestamp: datetime
    factors: List[str]

@dataclass
class AnomalyDetection:
    """Anomaly detection result"""
    anomaly_type: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    feature: str
    current_value: float
    expected_range: Tuple[float, float]
    deviation_score: float
    description: str
    timestamp: datetime
    recommendations: List[str]

@dataclass
class CompetitiveInsight:
    """Competitive insight from ML analysis"""
    insight_type: str  # 'opportunity', 'threat', 'trend', 'prediction'
    title: str
    description: str
    impact: str  # 'high', 'medium', 'low'
    confidence: float
    data_points: List[Dict[str, Any]]
    actionable: bool
    timestamp: datetime

class AdvancedAnalytics:
    """Advanced analytics for competitive assessment"""
    
    def __init__(self, db_pool: Optional[asyncpg.Pool] = None, redis_client: Optional[aioredis.Redis] = None):
        self.db_pool = db_pool
        self.redis_client = redis_client
        
        # ML models
        self.isolation_forest = {}
        self.scalers = {}
        self.regression_models = {}
        
        # Analytics cache
        self.cache_ttl = 3600  # 1 hour
        self.cache_prefix = "advanced_analytics:"
        
        # Historical data for training
        self.historical_data = []
        self.training_data_size = 1000
        
        # Anomaly thresholds
        self.anomaly_thresholds = {
            'graph_expansion': (0.5, 2.0),  # Standard deviation multiplier
            'pattern_detection': (0.3, 1.5),
            'api_response': (0.2, 1.0),
            'memory_usage': (0.4, 1.8)
        }
    
    async def initialize_models(self) -> None:
        """Initialize ML models with historical data"""
        logger.info("Initializing advanced analytics models...")
        
        # Load historical data from database
        await self.load_historical_data()
        
        # Train models for each metric type
        metric_types = ['graph_expansion', 'pattern_detection', 'api_response', 'memory_usage']
        
        for metric_type in metric_types:
            await self.train_prediction_model(metric_type)
            await self.train_anomaly_detection(metric_type)
        
        logger.info(f"Advanced analytics models initialized for {len(metric_types)} metrics")
    
    async def load_historical_data(self) -> None:
        """Load historical competitive data from database"""
        if not self.db_pool:
            logger.warning("No database connection available for historical data")
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                # Get historical data using configurable training data size
                query = """
                SELECT test_name, metric_type, value, timestamp, success
                FROM competitive.benchmarks
                WHERE success = TRUE AND timestamp >= NOW() - INTERVAL '30 days'
                ORDER BY timestamp DESC
                LIMIT $1
                """
                
                rows = await conn.fetch(query, self.training_data_size)
                
                self.historical_data = [
                    {
                        'test_name': row['test_name'],
                        'metric_type': row['metric_type'],
                        'value': row['value'],
                        'timestamp': row['timestamp'],
                        'success': row['success']
                    }
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Failed to load historical data: {e}")
            self.historical_data = []
