"""
Jackdaw Sentry - Advanced Analytics Engine
Orchestrates multi-route pathfinding, seed analysis, and transaction fingerprinting
"""

import asyncio
import logging
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timezone, timedelta
import time as _time

from .models import (
    AnalyticsRequest, AnalyticsResponse, PathfindingRequest, PathfindingResult,
    SeedAnalysisRequest, SeedAnalysisResult, FingerprintingRequest, FingerprintResult,
    BatchAnalyticsRequest, BatchAnalyticsResponse
)
from .pathfinding import get_pathfinder, MultiRoutePathfinder
from .seed_analysis import get_seed_analyzer, SeedPhraseAnalyzer
from .fingerprinting import get_transaction_fingerprinter, TransactionFingerprinter
from src.api.database import get_postgres_connection

logger = logging.getLogger(__name__)


class AdvancedAnalyticsEngine:
    """Advanced analytics engine for blockchain intelligence"""
    
    def __init__(self):
        self.pathfinder = get_pathfinder()
        self.seed_analyzer = get_seed_analyzer()
        self.fingerprinter = get_transaction_fingerprinter()
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
        self._initialized = False
        self.metrics = {
            'total_requests': 0,
            'pathfinding_requests': 0,
            'seed_analyses': 0,
            'fingerprint_queries': 0,
            'batch_requests': 0,
            'avg_processing_time': 0.0,
            'cache_hit_rate': 0.0,
            'success_rate': 1.0,
            'last_update': None
        }
    
    async def initialize(self):
        """Initialize the advanced analytics engine"""
        if self._initialized:
            return
        
        logger.info("Initializing Advanced Analytics Engine...")
        
        # Initialize all components
        await self.pathfinder.initialize()
        await self.seed_analyzer.initialize()
        await self.fingerprinter.initialize()
        
        self._initialized = True
        logger.info("Advanced Analytics Engine initialized successfully")
    
    async def process_request(self, request: AnalyticsRequest) -> AnalyticsResponse:
        """
        Process an analytics request
        
        Args:
            request: Analytics request with type and parameters
            
        Returns:
            AnalyticsResponse with result or error
        """
        
        start_time = _time.time()
        request_id = request.request_id or str(_time.time())
        
        logger.info(f"Processing analytics request: {request.request_type}")
        
        try:
            # Update metrics
            self.metrics['total_requests'] += 1
            self._update_request_type_metric(request.request_type)
            
            # Process based on request type
            if request.request_type == "pathfinding":
                result = await self._process_pathfinding_request(request)
            elif request.request_type == "seed_analysis":
                result = await self._process_seed_analysis_request(request)
            elif request.request_type == "fingerprinting":
                result = await self._process_fingerprinting_request(request)
            elif request.request_type == "batch":
                result = await self._process_batch_request(request)
            else:
                raise ValueError(f"Unsupported request type: {request.request_type}")
            
            # Calculate processing time
            processing_time = (_time.time() - start_time) * 1000
            self._update_processing_metrics(processing_time, True)
            
            # Create response
            response = AnalyticsResponse(
                request_id=request_id,
                request_type=request.request_type,
                status="completed",
                result=result,
                processing_time_ms=processing_time,
                completed_at=datetime.now(timezone.utc),
                metadata=request.metadata
            )
            
            logger.info(f"Analytics request completed: {request.request_type} in {processing_time:.2f}ms")
            return response
            
        except Exception as e:
            # Calculate processing time
            processing_time = (_time.time() - start_time) * 1000
            self._update_processing_metrics(processing_time, False)
            
            logger.error(f"Error processing analytics request {request.request_type}: {e}")
            
            return AnalyticsResponse(
                request_id=request_id,
                request_type=request.request_type,
                status="failed",
                error_message=str(e),
                processing_time_ms=processing_time,
                completed_at=datetime.now(timezone.utc),
                metadata=request.metadata
            )
    
    async def _process_pathfinding_request(self, request: AnalyticsRequest) -> PathfindingResult:
        """Process pathfinding request"""
        
        parameters = request.parameters
        pathfinding_request = PathfindingRequest(
            source_address=parameters.get("source_address"),
            target_address=parameters.get("target_address"),
            blockchain=parameters.get("blockchain"),
            algorithm=parameters.get("algorithm", "all_paths"),
            max_paths=parameters.get("max_paths", 100),
            max_hops=parameters.get("max_hops", 10),
            min_amount=parameters.get("min_amount"),
            max_amount=parameters.get("max_amount"),
            time_window_hours=parameters.get("time_window_hours", 168),
            include_intermediate=parameters.get("include_intermediate", True),
            confidence_threshold=parameters.get("confidence_threshold", 0.5)
        )
        
        return await self.pathfinder.find_paths(pathfinding_request)
    
    async def _process_seed_analysis_request(self, request: AnalyticsRequest) -> SeedAnalysisResult:
        """Process seed analysis request"""
        
        parameters = request.parameters
        seed_request = SeedAnalysisRequest(
            seed_phrase=parameters.get("seed_phrase"),
            derivation_types=parameters.get("derivation_types", ["bip44"]),
            blockchains=parameters.get("blockchains", ["bitcoin", "ethereum"]),
            max_derivations=parameters.get("max_derivations", 100),
            check_balances=parameters.get("check_balances", True),
            include_inactive=parameters.get("include_inactive", True)
        )
        
        return await self.seed_analyzer.analyze_seed_phrase(seed_request)
    
    async def _process_fingerprinting_request(self, request: AnalyticsRequest) -> FingerprintResult:
        """Process fingerprinting request"""
        
        parameters = request.parameters
        fingerprint_request = FingerprintingRequest(
            query_type=parameters.get("query_type"),
            parameters=parameters.get("query_parameters", {}),
            blockchain=parameters.get("blockchain"),
            time_window_hours=parameters.get("time_window_hours", 168),
            min_confidence=parameters.get("min_confidence", 0.5),
            max_results=parameters.get("max_results", 100)
        )
        
        return await self.fingerprinter.fingerprint_transactions(fingerprint_request)
    
    async def _process_batch_request(self, request: AnalyticsRequest) -> BatchAnalyticsResponse:
        """Process batch analytics request"""
        
        parameters = request.parameters
        batch_request = BatchAnalyticsRequest(
            requests=parameters.get("requests", []),
            parallel_processing=parameters.get("parallel_processing", True),
            max_concurrent=parameters.get("max_concurrent", 5)
        )
        
        return await self.process_batch_requests(batch_request)
    
    async def process_batch_requests(self, request: BatchAnalyticsRequest) -> BatchAnalyticsResponse:
        """
        Process multiple analytics requests in batch
        
        Args:
            request: Batch request with multiple analytics requests
            
        Returns:
            BatchAnalyticsResponse with all results
        """
        
        start_time = _time.time()
        batch_id = str(_time.time())
        
        logger.info(f"Processing batch analytics request: {len(request.requests)} requests")
        
        # Update metrics
        self.metrics['batch_requests'] += 1
        
        try:
            if request.parallel_processing:
                results = await self._process_batch_parallel(request)
            else:
                results = await self._process_batch_sequential(request)
            
            # Calculate statistics
            successful = len([r for r in results if r.status == "completed"])
            failed = len([r for r in results if r.status == "failed"])
            total_processing_time = (_time.time() - start_time) * 1000
            
            # Create batch response
            batch_response = BatchAnalyticsResponse(
                batch_id=batch_id,
                results=results,
                successful_requests=successful,
                failed_requests=failed,
                total_processing_time_ms=total_processing_time,
                created_at=datetime.now(timezone.utc)
            )
            
            logger.info(f"Batch processing complete: {successful} successful, {failed} failed in {total_processing_time:.2f}ms")
            return batch_response
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            total_processing_time = (_time.time() - start_time) * 1000
            
            return BatchAnalyticsResponse(
                batch_id=batch_id,
                results=[],
                successful_requests=0,
                failed_requests=len(request.requests),
                total_processing_time_ms=total_processing_time,
                created_at=datetime.now(timezone.utc)
            )
    
    async def _process_batch_parallel(self, request: BatchAnalyticsRequest) -> List[AnalyticsResponse]:
        """Process batch requests in parallel"""
        
        semaphore = asyncio.Semaphore(request.max_concurrent)
        
        async def process_single(single_request: AnalyticsRequest) -> AnalyticsResponse:
            async with semaphore:
                return await self.process_request(single_request)
        
        # Execute all requests concurrently
        tasks = [process_single(req) for req in request.requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(AnalyticsResponse(
                    request_id=str(i),
                    request_type=request.requests[i].request_type,
                    status="failed",
                    error_message=str(result),
                    processing_time_ms=0.0,
                    completed_at=datetime.now(timezone.utc)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _process_batch_sequential(self, request: BatchAnalyticsRequest) -> List[AnalyticsResponse]:
        """Process batch requests sequentially"""
        
        results = []
        
        for single_request in request.requests:
            result = await self.process_request(single_request)
            results.append(result)
        
        return results
    
    async def get_analytics_statistics(self) -> Dict[str, Any]:
        """Get analytics engine statistics"""
        
        # Get component statistics
        pathfinder_metrics = self.pathfinder.get_metrics() if hasattr(self.pathfinder, 'get_metrics') else {}
        
        return {
            **self.metrics,
            "pathfinder_metrics": pathfinder_metrics,
            "cache_size": len(self.cache),
            "components_initialized": self._initialized,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def clear_all_caches(self):
        """Clear all analytics caches"""
        
        self.cache.clear()
        self.pathfinder.clear_cache()
        self.seed_analyzer.clear_cache()
        self.fingerprinter.clear_cache()
        
        logger.info("All analytics caches cleared")
    
    def _update_request_type_metric(self, request_type: str):
        """Update request type metrics"""
        
        if request_type == "pathfinding":
            self.metrics['pathfinding_requests'] += 1
        elif request_type == "seed_analysis":
            self.metrics['seed_analyses'] += 1
        elif request_type == "fingerprinting":
            self.metrics['fingerprint_queries'] += 1
    
    def _update_processing_metrics(self, processing_time_ms: float, success: bool):
        """Update processing metrics"""
        
        # Update average processing time
        current_avg = self.metrics['avg_processing_time']
        total_requests = self.metrics['total_requests']
        
        if total_requests > 0:
            self.metrics['avg_processing_time'] = (
                (current_avg * (total_requests - 1) + processing_time_ms) / total_requests
            )
        
        # Update success rate
        if not success:
            current_success_rate = self.metrics['success_rate']
            self.metrics['success_rate'] = max(0.0, current_success_rate - (1.0 / total_requests))
        
        self.metrics['last_update'] = datetime.now(timezone.utc)
    
    def _update_cache_hit_rate(self, hit: bool):
        """Update cache hit rate metrics"""
        
        # Simple moving average for cache hit rate
        if not hasattr(self, '_cache_requests'):
            self._cache_requests = 0
            self._cache_hits = 0
        
        self._cache_requests += 1
        if hit:
            self._cache_hits += 1
        
        self.metrics['cache_hit_rate'] = self._cache_hits / self._cache_requests


# Global analytics engine instance
_analytics_engine = None

def get_analytics_engine() -> AdvancedAnalyticsEngine:
    """Get the global analytics engine instance"""
    global _analytics_engine
    if _analytics_engine is None:
        _analytics_engine = AdvancedAnalyticsEngine()
    return _analytics_engine
