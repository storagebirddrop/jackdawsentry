"""
Compliance Performance Optimization Module

This module provides performance optimization features for compliance operations including:
- Database query optimization
- Caching strategies and cache warming
- Batch processing optimization
- Memory management and cleanup
- Performance monitoring and metrics
"""

import asyncio
import gc
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from enum import Enum
from functools import wraps
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

import psutil

logger = logging.getLogger(__name__)


class OptimizationType(Enum):
    """Optimization type categories"""

    DATABASE = "database"
    CACHE = "cache"
    MEMORY = "memory"
    BATCH_PROCESSING = "batch_processing"
    QUERY_OPTIMIZATION = "query_optimization"


@dataclass
class PerformanceMetric:
    """Performance metric definition"""

    name: str
    value: float
    unit: str
    timestamp: datetime
    optimization_type: OptimizationType
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class OptimizationResult:
    """Optimization result definition"""

    optimization_type: OptimizationType
    success: bool
    improvement_percentage: float
    time_saved_ms: float
    memory_saved_mb: float
    metrics_before: List[PerformanceMetric]
    metrics_after: List[PerformanceMetric]
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None


class CompliancePerformanceOptimizer:
    """Compliance performance optimization engine"""

    def __init__(self):
        self.metrics_history = []
        self.optimization_results = []
        self.cache_warming_enabled = True
        self.batch_size = 100
        self.max_concurrent_operations = 10
        self.memory_threshold_mb = 1024  # 1GB
        self.query_timeout_seconds = 30
        self.optimization_interval_minutes = 15

    async def optimize_system(self) -> List[OptimizationResult]:
        """Run comprehensive system optimization"""
        results = []

        try:
            # Database optimization
            db_result = await self.optimize_database()
            results.append(db_result)

            # Cache optimization
            cache_result = await self.optimize_cache()
            results.append(cache_result)

            # Memory optimization
            memory_result = await self.optimize_memory()
            results.append(memory_result)

            # Batch processing optimization
            batch_result = await self.optimize_batch_processing()
            results.append(batch_result)

            # Query optimization
            query_result = await self.optimize_queries()
            results.append(query_result)

            logger.info(
                f"System optimization completed: {len(results)} optimizations applied"
            )
            return results

        except Exception as e:
            logger.error(f"System optimization failed: {e}")
            return results

    async def optimize_database(self) -> OptimizationResult:
        """Optimize database performance"""
        try:
            # Collect metrics before optimization
            metrics_before = await self._collect_database_metrics()

            start_time = time.time()

            # Apply database optimizations
            optimizations_applied = []

            # 1. Connection pool optimization
            await self._optimize_connection_pool()
            optimizations_applied.append("connection_pool")

            # 2. Query optimization
            await self._optimize_slow_queries()
            optimizations_applied.append("slow_queries")

            # 3. Index optimization
            await self._optimize_indexes()
            optimizations_applied.append("indexes")

            # 4. Database statistics update
            await self._update_database_statistics()
            optimizations_applied.append("statistics")

            end_time = time.time()
            time_saved = (end_time - start_time) * 1000

            # Collect metrics after optimization
            metrics_after = await self._collect_database_metrics()

            # Calculate improvement
            improvement = self._calculate_improvement(metrics_before, metrics_after)

            result = OptimizationResult(
                optimization_type=OptimizationType.DATABASE,
                success=True,
                improvement_percentage=improvement,
                time_saved_ms=time_saved,
                memory_saved_mb=0,
                metrics_before=metrics_before,
                metrics_after=metrics_after,
                timestamp=datetime.now(timezone.utc),
                details={"optimizations_applied": optimizations_applied},
            )

            self.optimization_results.append(result)
            logger.info(
                f"Database optimization completed: {improvement:.2f}% improvement"
            )

            return result

        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            return OptimizationResult(
                optimization_type=OptimizationType.DATABASE,
                success=False,
                improvement_percentage=0,
                time_saved_ms=0,
                memory_saved_mb=0,
                metrics_before=[],
                metrics_after=[],
                timestamp=datetime.now(timezone.utc),
                details={"error": str(e)},
            )

    async def optimize_cache(self) -> OptimizationResult:
        """Optimize cache performance"""
        try:
            # Collect metrics before optimization
            metrics_before = await self._collect_cache_metrics()

            start_time = time.time()

            # Apply cache optimizations
            optimizations_applied = []

            # 1. Cache warming
            if self.cache_warming_enabled:
                await self._warm_cache()
                optimizations_applied.append("cache_warming")

            # 2. Cache cleanup
            await self._cleanup_cache()
            optimizations_applied.append("cache_cleanup")

            # 3. Cache optimization
            await self._optimize_cache_settings()
            optimizations_applied.append("cache_settings")

            # 4. Preload frequently accessed data
            await self._preload_frequent_data()
            optimizations_applied.append("preload_data")

            end_time = time.time()
            time_saved = (end_time - start_time) * 1000

            # Collect metrics after optimization
            metrics_after = await self._collect_cache_metrics()

            # Calculate improvement
            improvement = self._calculate_improvement(metrics_before, metrics_after)

            result = OptimizationResult(
                optimization_type=OptimizationType.CACHE,
                success=True,
                improvement_percentage=improvement,
                time_saved_ms=time_saved,
                memory_saved_mb=0,
                metrics_before=metrics_before,
                metrics_after=metrics_after,
                timestamp=datetime.now(timezone.utc),
                details={"optimizations_applied": optimizations_applied},
            )

            self.optimization_results.append(result)
            logger.info(f"Cache optimization completed: {improvement:.2f}% improvement")

            return result

        except Exception as e:
            logger.error(f"Cache optimization failed: {e}")
            return OptimizationResult(
                optimization_type=OptimizationType.CACHE,
                success=False,
                improvement_percentage=0,
                time_saved_ms=0,
                memory_saved_mb=0,
                metrics_before=[],
                metrics_after=[],
                timestamp=datetime.now(timezone.utc),
                details={"error": str(e)},
            )

    async def optimize_memory(self) -> OptimizationResult:
        """Optimize memory usage"""
        try:
            # Collect metrics before optimization
            metrics_before = await self._collect_memory_metrics()

            start_time = time.time()
            memory_before = psutil.Process().memory_info().rss / 1024 / 1024  # MB

            # Apply memory optimizations
            optimizations_applied = []

            # 1. Garbage collection
            collected = gc.collect()
            optimizations_applied.append(f"garbage_collection_{collected}")

            # 2. Clear unused caches
            await self._clear_unused_caches()
            optimizations_applied.append("clear_caches")

            # 3. Optimize data structures
            await self._optimize_data_structures()
            optimizations_applied.append("optimize_structures")

            # 4. Memory pool cleanup
            await self._cleanup_memory_pools()
            optimizations_applied.append("memory_pools")

            end_time = time.time()
            memory_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            time_saved = (end_time - start_time) * 1000
            memory_saved = memory_before - memory_after

            # Collect metrics after optimization
            metrics_after = await self._collect_memory_metrics()

            # Calculate improvement
            improvement = self._calculate_improvement(metrics_before, metrics_after)

            result = OptimizationResult(
                optimization_type=OptimizationType.MEMORY,
                success=True,
                improvement_percentage=improvement,
                time_saved_ms=time_saved,
                memory_saved_mb=memory_saved,
                metrics_before=metrics_before,
                metrics_after=metrics_after,
                timestamp=datetime.now(timezone.utc),
                details={"optimizations_applied": optimizations_applied},
            )

            self.optimization_results.append(result)
            logger.info(f"Memory optimization completed: {memory_saved:.2f}MB saved")

            return result

        except Exception as e:
            logger.error(f"Memory optimization failed: {e}")
            return OptimizationResult(
                optimization_type=OptimizationType.MEMORY,
                success=False,
                improvement_percentage=0,
                time_saved_ms=0,
                memory_saved_mb=0,
                metrics_before=[],
                metrics_after=[],
                timestamp=datetime.now(timezone.utc),
                details={"error": str(e)},
            )

    async def optimize_batch_processing(self) -> OptimizationResult:
        """Optimize batch processing performance"""
        try:
            # Collect metrics before optimization
            metrics_before = await self._collect_batch_metrics()

            start_time = time.time()

            # Apply batch processing optimizations
            optimizations_applied = []

            # 1. Optimize batch size
            await self._optimize_batch_size()
            optimizations_applied.append("batch_size")

            # 2. Parallel processing optimization
            await self._optimize_parallel_processing()
            optimizations_applied.append("parallel_processing")

            # 3. Queue optimization
            await self._optimize_processing_queues()
            optimizations_applied.append("processing_queues")

            # 4. Resource allocation optimization
            await self._optimize_resource_allocation()
            optimizations_applied.append("resource_allocation")

            end_time = time.time()
            time_saved = (end_time - start_time) * 1000

            # Collect metrics after optimization
            metrics_after = await self._collect_batch_metrics()

            # Calculate improvement
            improvement = self._calculate_improvement(metrics_before, metrics_after)

            result = OptimizationResult(
                optimization_type=OptimizationType.BATCH_PROCESSING,
                success=True,
                improvement_percentage=improvement,
                time_saved_ms=time_saved,
                memory_saved_mb=0,
                metrics_before=metrics_before,
                metrics_after=metrics_after,
                timestamp=datetime.now(timezone.utc),
                details={"optimizations_applied": optimizations_applied},
            )

            self.optimization_results.append(result)
            logger.info(
                f"Batch processing optimization completed: {improvement:.2f}% improvement"
            )

            return result

        except Exception as e:
            logger.error(f"Batch processing optimization failed: {e}")
            return OptimizationResult(
                optimization_type=OptimizationType.BATCH_PROCESSING,
                success=False,
                improvement_percentage=0,
                time_saved_ms=0,
                memory_saved_mb=0,
                metrics_before=[],
                metrics_after=[],
                timestamp=datetime.now(timezone.utc),
                details={"error": str(e)},
            )

    async def optimize_queries(self) -> OptimizationResult:
        """Optimize query performance"""
        try:
            # Collect metrics before optimization
            metrics_before = await self._collect_query_metrics()

            start_time = time.time()

            # Apply query optimizations
            optimizations_applied = []

            # 1. Query plan optimization
            await self._optimize_query_plans()
            optimizations_applied.append("query_plans")

            # 2. Index usage optimization
            await self._optimize_index_usage()
            optimizations_applied.append("index_usage")

            # 3. Query caching
            await self._optimize_query_cache()
            optimizations_applied.append("query_cache")

            # 4. Slow query optimization
            await self._optimize_slow_queries()
            optimizations_applied.append("slow_queries")

            end_time = time.time()
            time_saved = (end_time - start_time) * 1000

            # Collect metrics after optimization
            metrics_after = await self._collect_query_metrics()

            # Calculate improvement
            improvement = self._calculate_improvement(metrics_before, metrics_after)

            result = OptimizationResult(
                optimization_type=OptimizationType.QUERY_OPTIMIZATION,
                success=True,
                improvement_percentage=improvement,
                time_saved_ms=time_saved,
                memory_saved_mb=0,
                metrics_before=metrics_before,
                metrics_after=metrics_after,
                timestamp=datetime.now(timezone.utc),
                details={"optimizations_applied": optimizations_applied},
            )

            self.optimization_results.append(result)
            logger.info(f"Query optimization completed: {improvement:.2f}% improvement")

            return result

        except Exception as e:
            logger.error(f"Query optimization failed: {e}")
            return OptimizationResult(
                optimization_type=OptimizationType.QUERY_OPTIMIZATION,
                success=False,
                improvement_percentage=0,
                time_saved_ms=0,
                memory_saved_mb=0,
                metrics_before=[],
                metrics_after=[],
                timestamp=datetime.now(timezone.utc),
                details={"error": str(e)},
            )

    # Helper methods for optimization implementations
    async def _optimize_connection_pool(self):
        """Optimize database connection pool"""
        try:
            # Implementation would optimize connection pool settings
            # This is a placeholder for the actual implementation
            logger.debug("Optimizing connection pool")
        except Exception as e:
            logger.error(f"Connection pool optimization failed: {e}")

    async def _optimize_slow_queries(self):
        """Optimize slow queries"""
        try:
            # Implementation would identify and optimize slow queries
            logger.debug("Optimizing slow queries")
        except Exception as e:
            logger.error(f"Slow query optimization failed: {e}")

    async def _optimize_indexes(self):
        """Optimize database indexes"""
        try:
            # Implementation would analyze and optimize indexes
            logger.debug("Optimizing indexes")
        except Exception as e:
            logger.error(f"Index optimization failed: {e}")

    async def _update_database_statistics(self):
        """Update database statistics"""
        try:
            # Implementation would update database statistics
            logger.debug("Updating database statistics")
        except Exception as e:
            logger.error(f"Database statistics update failed: {e}")

    async def _warm_cache(self):
        """Warm up cache with frequently accessed data"""
        try:
            # Implementation would pre-load frequently accessed data
            logger.debug("Warming cache")
        except Exception as e:
            logger.error(f"Cache warming failed: {e}")

    async def _cleanup_cache(self):
        """Clean up expired cache entries"""
        try:
            # Implementation would clean up expired cache entries
            logger.debug("Cleaning cache")
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")

    async def _optimize_cache_settings(self):
        """Optimize cache configuration"""
        try:
            # Implementation would optimize cache settings
            logger.debug("Optimizing cache settings")
        except Exception as e:
            logger.error(f"Cache settings optimization failed: {e}")

    async def _preload_frequent_data(self):
        """Preload frequently accessed data"""
        try:
            # Implementation would preload frequently accessed data
            logger.debug("Preloading frequent data")
        except Exception as e:
            logger.error(f"Frequent data preload failed: {e}")

    async def _clear_unused_caches(self):
        """Clear unused caches"""
        try:
            # Implementation would clear unused caches
            logger.debug("Clearing unused caches")
        except Exception as e:
            logger.error(f"Cache clearing failed: {e}")

    async def _optimize_data_structures(self):
        """Optimize data structures"""
        try:
            # Implementation would optimize data structures
            logger.debug("Optimizing data structures")
        except Exception as e:
            logger.error(f"Data structure optimization failed: {e}")

    async def _cleanup_memory_pools(self):
        """Clean up memory pools"""
        try:
            # Implementation would clean up memory pools
            logger.debug("Cleaning memory pools")
        except Exception as e:
            logger.error(f"Memory pool cleanup failed: {e}")

    async def _optimize_batch_size(self):
        """Optimize batch processing size"""
        try:
            # Implementation would optimize batch size based on system performance
            logger.debug("Optimizing batch size")
        except Exception as e:
            logger.error(f"Batch size optimization failed: {e}")

    async def _optimize_parallel_processing(self):
        """Optimize parallel processing"""
        try:
            # Implementation would optimize parallel processing settings
            logger.debug("Optimizing parallel processing")
        except Exception as e:
            logger.error(f"Parallel processing optimization failed: {e}")

    async def _optimize_processing_queues(self):
        """Optimize processing queues"""
        try:
            # Implementation would optimize processing queues
            logger.debug("Optimizing processing queues")
        except Exception as e:
            logger.error(f"Processing queue optimization failed: {e}")

    async def _optimize_resource_allocation(self):
        """Optimize resource allocation"""
        try:
            # Implementation would optimize resource allocation
            logger.debug("Optimizing resource allocation")
        except Exception as e:
            logger.error(f"Resource allocation optimization failed: {e}")

    async def _optimize_query_plans(self):
        """Optimize query execution plans"""
        try:
            # Implementation would optimize query execution plans
            logger.debug("Optimizing query plans")
        except Exception as e:
            logger.error(f"Query plan optimization failed: {e}")

    async def _optimize_index_usage(self):
        """Optimize index usage"""
        try:
            # Implementation would optimize index usage
            logger.debug("Optimizing index usage")
        except Exception as e:
            logger.error(f"Index usage optimization failed: {e}")

    async def _optimize_query_cache(self):
        """Optimize query cache"""
        try:
            # Implementation would optimize query cache
            logger.debug("Optimizing query cache")
        except Exception as e:
            logger.error(f"Query cache optimization failed: {e}")

    # Metric collection methods
    async def _collect_database_metrics(self) -> List[PerformanceMetric]:
        """Collect database performance metrics"""
        try:
            metrics = []

            # Connection pool metrics
            metrics.append(
                PerformanceMetric(
                    name="connection_pool_size",
                    value=10.0,  # Placeholder
                    unit="count",
                    timestamp=datetime.now(timezone.utc),
                    optimization_type=OptimizationType.DATABASE,
                )
            )

            # Query performance metrics
            metrics.append(
                PerformanceMetric(
                    name="avg_query_time",
                    value=50.0,  # Placeholder
                    unit="ms",
                    timestamp=datetime.now(timezone.utc),
                    optimization_type=OptimizationType.DATABASE,
                )
            )

            return metrics

        except Exception as e:
            logger.error(f"Failed to collect database metrics: {e}")
            return []

    async def _collect_cache_metrics(self) -> List[PerformanceMetric]:
        """Collect cache performance metrics"""
        try:
            metrics = []

            # Cache hit rate
            metrics.append(
                PerformanceMetric(
                    name="cache_hit_rate",
                    value=0.85,  # Placeholder
                    unit="ratio",
                    timestamp=datetime.now(timezone.utc),
                    optimization_type=OptimizationType.CACHE,
                )
            )

            # Cache size
            metrics.append(
                PerformanceMetric(
                    name="cache_size",
                    value=100.0,  # Placeholder
                    unit="MB",
                    timestamp=datetime.now(timezone.utc),
                    optimization_type=OptimizationType.CACHE,
                )
            )

            return metrics

        except Exception as e:
            logger.error(f"Failed to collect cache metrics: {e}")
            return []

    async def _collect_memory_metrics(self) -> List[PerformanceMetric]:
        """Collect memory usage metrics"""
        try:
            metrics = []

            # Memory usage
            memory_info = psutil.Process().memory_info()
            metrics.append(
                PerformanceMetric(
                    name="memory_usage",
                    value=memory_info.rss / 1024 / 1024,  # MB
                    unit="MB",
                    timestamp=datetime.now(timezone.utc),
                    optimization_type=OptimizationType.MEMORY,
                )
            )

            # Memory percentage
            memory_percent = psutil.Process().memory_percent()
            metrics.append(
                PerformanceMetric(
                    name="memory_percentage",
                    value=memory_percent,
                    unit="percent",
                    timestamp=datetime.now(timezone.utc),
                    optimization_type=OptimizationType.MEMORY,
                )
            )

            return metrics

        except Exception as e:
            logger.error(f"Failed to collect memory metrics: {e}")
            return []

    async def _collect_batch_metrics(self) -> List[PerformanceMetric]:
        """Collect batch processing metrics"""
        try:
            metrics = []

            # Batch processing time
            metrics.append(
                PerformanceMetric(
                    name="batch_processing_time",
                    value=100.0,  # Placeholder
                    unit="ms",
                    timestamp=datetime.now(timezone.utc),
                    optimization_type=OptimizationType.BATCH_PROCESSING,
                )
            )

            # Batch throughput
            metrics.append(
                PerformanceMetric(
                    name="batch_throughput",
                    value=1000.0,  # Placeholder
                    unit="records/sec",
                    timestamp=datetime.now(timezone.utc),
                    optimization_type=OptimizationType.BATCH_PROCESSING,
                )
            )

            return metrics

        except Exception as e:
            logger.error(f"Failed to collect batch metrics: {e}")
            return []

    async def _collect_query_metrics(self) -> List[PerformanceMetric]:
        """Collect query performance metrics"""
        try:
            metrics = []

            # Query execution time
            metrics.append(
                PerformanceMetric(
                    name="query_execution_time",
                    value=25.0,  # Placeholder
                    unit="ms",
                    timestamp=datetime.now(timezone.utc),
                    optimization_type=OptimizationType.QUERY_OPTIMIZATION,
                )
            )

            # Query cache hit rate
            metrics.append(
                PerformanceMetric(
                    name="query_cache_hit_rate",
                    value=0.90,  # Placeholder
                    unit="ratio",
                    timestamp=datetime.now(timezone.utc),
                    optimization_type=OptimizationType.QUERY_OPTIMIZATION,
                )
            )

            return metrics

        except Exception as e:
            logger.error(f"Failed to collect query metrics: {e}")
            return []

    def _calculate_improvement(
        self, before: List[PerformanceMetric], after: List[PerformanceMetric]
    ) -> float:
        """Calculate improvement percentage"""
        try:
            if not before or not after:
                return 0.0

            improvements = []

            for before_metric in before:
                after_metric = next(
                    (m for m in after if m.name == before_metric.name), None
                )
                if after_metric:
                    if (
                        "time" in before_metric.name.lower()
                        or "ms" in before_metric.unit
                    ):
                        # For time metrics, lower is better
                        improvement = (
                            (before_metric.value - after_metric.value)
                            / before_metric.value
                        ) * 100
                    elif (
                        "rate" in before_metric.name.lower()
                        or "ratio" in before_metric.unit
                    ):
                        # For rate metrics, higher is better
                        improvement = (
                            (after_metric.value - before_metric.value)
                            / before_metric.value
                        ) * 100
                    else:
                        # For other metrics, assume lower is better
                        improvement = (
                            (before_metric.value - after_metric.value)
                            / before_metric.value
                        ) * 100

                    improvements.append(improvement)

            # Return average improvement
            return sum(improvements) / len(improvements) if improvements else 0.0

        except Exception as e:
            logger.error(f"Failed to calculate improvement: {e}")
            return 0.0

    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance optimization summary"""
        try:
            recent_optimizations = [
                result
                for result in self.optimization_results
                if result.timestamp > datetime.now(timezone.utc) - timedelta(hours=24)
            ]

            summary = {
                "total_optimizations": len(self.optimization_results),
                "recent_optimizations_24h": len(recent_optimizations),
                "optimization_types": {},
                "average_improvement": 0.0,
                "total_time_saved_ms": 0.0,
                "total_memory_saved_mb": 0.0,
                "success_rate": 0.0,
            }

            if self.optimization_results:
                # Calculate statistics
                successful_optimizations = [
                    r for r in self.optimization_results if r.success
                ]
                summary["success_rate"] = (
                    len(successful_optimizations) / len(self.optimization_results) * 100
                    if len(self.optimization_results) > 0
                    else 0
                )
                summary["average_improvement"] = (
                    sum(r.improvement_percentage for r in successful_optimizations)
                    / len(successful_optimizations)
                    if len(successful_optimizations) > 0
                    else 0
                )
                summary["total_time_saved_ms"] = sum(
                    r.time_saved_ms for r in successful_optimizations
                )
                summary["total_memory_saved_mb"] = sum(
                    r.memory_saved_mb for r in successful_optimizations
                )

                # Count by optimization type
                for result in self.optimization_results:
                    opt_type = result.optimization_type.value
                    if opt_type not in summary["optimization_types"]:
                        summary["optimization_types"][opt_type] = {
                            "total": 0,
                            "successful": 0,
                        }
                    summary["optimization_types"][opt_type]["total"] += 1
                    if result.success:
                        summary["optimization_types"][opt_type]["successful"] += 1

            return summary

        except Exception as e:
            logger.error(f"Failed to get performance summary: {e}")
            return {"error": str(e)}

    async def start_optimization_scheduler(self):
        """Start automatic optimization scheduler"""
        logger.info("Starting performance optimization scheduler")

        while True:
            try:
                await asyncio.sleep(self.optimization_interval_minutes * 60)

                # Check if optimization is needed
                if await self._should_optimize():
                    await self.optimize_system()

            except Exception as e:
                logger.error(f"Optimization scheduler error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _should_optimize(self) -> bool:
        """Check if optimization should be performed"""
        try:
            # Check memory usage
            memory_percent = psutil.Process().memory_percent()
            if memory_percent > 80:  # If memory usage > 80%
                return True

            # Check if it's been a while since last optimization
            if self.optimization_results:
                last_optimization = max(r.timestamp for r in self.optimization_results)
                if datetime.now(timezone.utc) - last_optimization > timedelta(hours=1):
                    return True
            else:
                return True  # No optimizations performed yet

            return False

        except Exception as e:
            logger.error(f"Failed to check optimization need: {e}")
            return False


# Performance monitoring decorator
def monitor_performance(operation_type: OptimizationType):
    """Decorator to monitor performance of functions"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024

            try:
                result = await func(*args, **kwargs)

                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss / 1024 / 1024

                execution_time = (end_time - start_time) * 1000
                memory_delta = end_memory - start_memory

                # Log performance metrics
                logger.debug(
                    f"Performance: {func.__name__} took {execution_time:.2f}ms, memory delta: {memory_delta:.2f}MB"
                )

                return result

            except Exception as e:
                end_time = time.time()
                execution_time = (end_time - start_time) * 1000
                logger.error(
                    f"Performance: {func.__name__} failed after {execution_time:.2f}ms: {e}"
                )
                raise

        return wrapper

    return decorator


# Global performance optimizer instance
compliance_performance_optimizer = CompliancePerformanceOptimizer()
