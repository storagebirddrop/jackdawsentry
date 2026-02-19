"""
Jackdaw Sentry - BlokBustr Integration
Integration with BlokBustr blockchain forensics platform
Inspired by AbdelH2O/blokbustr (MIT License)
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
import aiohttp
import json
from enum import Enum

from src.api.database import get_neo4j_session, get_redis_connection
from src.api.config import settings

logger = logging.getLogger(__name__)


class BlokBustrFeature(Enum):
    """BlokBustr platform features"""
    WATCHER_SERVICE = "watcher_service"
    EXPLORER_SERVICE = "explorer_service"
    IDENTIFIER_SERVICE = "identifier_service"
    FRONTEND = "frontend"
    INTEGRATION_API = "integration_api"


@dataclass
class BlokBustrConfig:
    """BlokBustr configuration"""
    api_endpoint: str
    api_key: str = ""
    cache_ttl: int = 3600  # 1 hour
    rate_limit: int = 1000  # requests per hour
    timeout: int = 30
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BlokBustrResult:
    """BlokBustr operation result"""
    feature: BlokBustrFeature
    success: bool
    data: Any = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BlokBustrIntegration:
    """BlokBustr integration for blockchain forensics"""
    
    def __init__(self, config: BlokBustrConfig = None):
        self.config = config or BlokBustrConfig(
            api_endpoint="https://api.blokbustr.com",
            api_key=settings.BLOKBUSTR_API_KEY or "",
            cache_ttl=3600,
            rate_limit=1000,
            timeout=30
        )
        self.session = None
        self.cache = {}
        
        # Initialize with sample data
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """Initialize with sample BlokBustr data"""
        self.cache = {
            'sample_address': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
            'sample_transactions': [
                'tx_001', 'tx_002', 'tx_003'
            ],
            'sample_clusters': [
                {
                    'cluster_id': 'cluster_001',
                    'addresses': ['1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa', '1B1zP1eP5QGefi2DMPTfTL5SLmv7DivfNb'],
                    'confidence': 0.85,
                    'labels': ['exchange', 'high_volume']
                },
                {
                    'cluster_id': 'cluster_002',
                    'addresses': ['1C1zP1eP5QGefi2DMPTfTL5SLmv7DivfNc'],
                    'confidence': 0.90,
                    'labels': ['exchange', 'high_volume']
                }
            ],
            'sample_investigations': [
                {
                    'investigation_id': 'inv_001',
                    'target': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
                    'status': 'completed',
                    'created_at': '2024-01-15T10:30:00Z',
                    'findings': ['mixing_pattern_detected', 'high_volume_transactions']
                }
            ]
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def monitor_address(self, address: str) -> BlokBustrResult:
        """Monitor address using BlokBustr"""
        try:
            cache_key = f"blokbustr_monitor_{address}"
            
            # Check cache first
            cached_result = await self.get_cached_result(cache_key)
            if cached_result:
                return cached_result
            
            # Simulate BlokBustr API call
            url = f"{self.config.api_endpoint}/api/v1/address/{address}/monitor"
            headers = {
                'X-API-Key': self.config.api_key,
                'Content-Type': 'application/json'
            }
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return BlokBustrResult(
                        feature=BlokBustrFeature.WATCHER_SERVICE,
                        success=True,
                        data=data,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        metadata={'cache_key': cache_key}
                    )
                else:
                    error_text = await response.text()
                    return BlokBustrResult(
                        feature=BlokBustrFeature.WATCHER_SERVICE,
                        success=False,
                        error=f"HTTP {response.status}: {error_text}",
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )
            
        except Exception as e:
            logger.error(f"BlokBustr monitoring failed: {e}")
            return BlokBustrResult(
                feature=BlokBustrFeature.WATCHER_SERVICE,
                success=False,
                error=str(e),
                timestamp=datetime.now(timezone.utc).isoformat()
            )
    
    async def explore_transactions(self, address: str, limit: int = 100) -> BlokBustrResult:
        """Explore transactions using BlokBustr"""
        try:
            cache_key = f"blokbustr_explore_{address}_{limit}"
            
            # Check cache first
            cached_result = await self.get_cached_result(cache_key)
            if cached_result:
                return cached_result
            
            url = f"{self.config.api_endpoint}/api/v1/address/{address}/transactions"
            params = {'limit': limit}
            
            async with self.session.get(url, params=params, headers=self._get_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    return BlokBustrResult(
                        feature=BlokBustrFeature.EXPLORER_SERVICE,
                        success=True,
                        data=data,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        metadata={'cache_key': cache_key}
                    )
                else:
                    error_text = await response.text()
                    return BlokBustrResult(
                        feature=BlokBustrFeature.EXPLORER_SERVICE,
                        success=False,
                        error=f"HTTP {response.status}: {error_text}",
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )
            
        except Exception as e:
            logger.error(f"BlokBustr transaction exploration failed: {e}")
            return BlokBustrResult(
                feature=BlokBustrFeature.EXPLORER_SERVICE,
                success=False,
                error=str(e),
                timestamp=datetime.now(timezone.utc).isoformat()
            )
    
    async def identify_address(self, address: str) -> BlokBustrResult:
        """Identify address using BlokBustr"""
        try:
            cache_key = f"blokbustr_identify_{address}"
            
            # Check cache first
            cached_result = await self.get_cached_result(cache_key)
            if cached_result:
                return cached_result
            
            url = f"{self.config.api_endpoint}/api/v1/address/{address}/identify"
            headers = self._get_headers()
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return BlokBustrResult(
                        feature=BlokBustrFeature.IDENTIFIER_SERVICE,
                        success=True,
                        data=data,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        metadata={'cache_key': cache_key}
                    )
                else:
                    error_text = await response.text()
                    return BlokBustrResult(
                        feature=BlokBustrFeature.IDENTIFIER_SERVICE,
                        success=False,
                        error=f"HTTP {response.status}: {error_text}",
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )
            
        except Exception as e:
            logger.error(f"BlokBustr address identification failed: {e}")
            return BlokBustrResult(
                feature=BlokBustrFeature.IDENTIFIER_SERVICE,
                success=False,
                error=str(e),
                timestamp=datetime.now(timezone.utc).isoformat()
            )
    
    async def get_address_clusters(self, address: str) -> BlokBustrResult:
        """Get address clusters using BlokBustr"""
        try:
            cache_key = f"blokbustr_clusters_{address}"
            
            # Check cache first
            cached_result = await self.get_cached_result(cache_key)
            if cached_result:
                return cached_result
            
            url = f"{self.config.api_endpoint}/api/v1/address/{address}/clusters"
            headers = self._get_headers()
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return BlokBustrResult(
                        feature=BlokBustrFeature.EXPLORER_SERVICE,
                        success=True,
                        data=data,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        metadata={'cache_key': cache_key}
                    )
                else:
                    error_text = await response.text()
                    return BlokBustrResult(
                        feature=BlokBustrFeature.EXPLORER_SERVICE,
                        success=False,
                        error=f"HTTP {response.status}: {error_text}",
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )
            
        except Exception as e:
            logger.error(f"BlokBustr cluster analysis failed: {e}")
            return BlokBustrResult(
                feature=BlokBustrFeature.EXPLORER_SERVICE,
                success=False,
                error=str(e),
                timestamp=datetime.now(timezone.utc).isoformat()
            )
    
    async def create_investigation(self, target: str, investigation_data: Dict[str, Any]) -> BlokBustrResult:
        """Create investigation using BlokBustr"""
        try:
            cache_key = f"blokbustr_investigation_{target}"
            
            url = f"{self.config.api_endpoint}/api/v1/investigations"
            headers = self._get_headers()
            
            payload = {
                'target': target,
                'type': 'blockchain_analysis',
                'data': investigation_data,
                'priority': 'medium'
            }
            
            async with self.session.post(url, headers=headers, json=payload) as response:
                if 200 <= response.status < 300:
                    data = await response.json()
                    return BlokBustrResult(
                        feature=BlokBustrFeature.INTEGRATION_API,
                        success=True,
                        data=data,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        metadata={'cache_key': cache_key}
                    )
                else:
                    error_text = await response.text()
                    return BlokBustrResult(
                        feature=BlokBustrFeature.INTEGRATION_API,
                        success=False,
                        error=f"HTTP {response.status}: {error_text}",
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )
            
        except Exception as e:
            logger.error(f"BlokBustr investigation creation failed: {e}")
            return BlokBustrResult(
                feature=BlokBustrFeature.INTEGRATION_API,
                success=False,
                error=str(e),
                timestamp=datetime.now(timezone.utc).isoformat()
            )
    
    async def get_investigation_status(self, investigation_id: str) -> BlokBustrResult:
        """Get investigation status using BlokBustr"""
        try:
            url = f"{self.config.api_endpoint}/api/v1/investigations/{investigation_id}"
            headers = self._get_headers()
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return BlokBustrResult(
                        feature=BlokBustrFeature.INTEGRATION_API,
                        success=True,
                        data=data,
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )
                else:
                    error_text = await response.text()
                    return BlokBustrResult(
                        feature=BlokBustrFeature.INTEGRATION_API,
                        success=False,
                        error=f"HTTP {response.status}: {error_text}",
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )
            
        except Exception as e:
            logger.error(f"BlokBustr investigation status check failed: {e}")
            return BlokBustrResult(
                feature=BlokBustrFeature.INTEGRATION_API,
                success=False,
                error=str(e),
                timestamp=datetime.now(timezone.utc).isoformat()
            )
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers"""
        return {
            'X-API-Key': self.config.api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'Jackdaw-Sentry/1.0'
        }
    
    async def get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached result"""
        try:
            async with get_redis_connection() as redis:
                cached = await redis.get(cache_key)
                if cached:
                    return json.loads(cached)
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
        return None
    
    async def cache_result(self, cache_key: str, result: Dict[str, Any]):
        """Cache result"""
        try:
            async with get_redis_connection() as redis:
                await redis.setex(cache_key, self.config.cache_ttl, json.dumps(result))
        except Exception as e:
            logger.error(f"Cache storage error: {e}")


# Global BlokBustr integration instance
_blokbustr_integration: Optional[BlokBustrIntegration] = None


def get_blokbustr_integration() -> BlokBustrIntegration:
    """Get global BlokBustr integration instance"""
    global _blokbustr_integration
    if _blokbustr_integration is None:
        _blokbustr_integration = BlokBustrIntegration()
    return _blokbustr_integration
