"""
Compliance Module Redis Caching

This module provides Redis caching functionality for compliance operations including:
- Risk assessment caching with TTL
- Regulatory report caching
- Case management caching
- Audit trail caching
- Performance optimization for compliance workflows
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Union
import redis.asyncio as redis
import pickle
import hashlib

logger = logging.getLogger(__name__)


class ComplianceCacheManager:
    """Manages Redis caching for compliance operations"""

    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.default_ttl = 3600  # 1 hour
        self.cache_prefix = "compliance:"
        
        # Cache TTL configurations
        self.ttl_config = {
            "risk_assessment": 7200,  # 2 hours
            "regulatory_report": 3600,  # 1 hour
            "case": 1800,  # 30 minutes
            "evidence": 3600,  # 1 hour
            "audit_event": 86400,  # 24 hours
            "risk_summary": 900,  # 15 minutes
            "case_statistics": 600,  # 10 minutes
            "compliance_logs": 1800,  # 30 minutes
            "thresholds": 3600,  # 1 hour
            "workflows": 3600  # 1 hour
        }

    async def cache_risk_assessment(self, assessment_id: str, assessment_data: Dict[str, Any]) -> bool:
        """Cache risk assessment data"""
        try:
            cache_key = f"{self.cache_prefix}risk_assessment:{assessment_id}"
            
            # Prepare cache data
            cache_data = {
                "assessment_id": assessment_id,
                "entity_id": assessment_data.get("entity_id"),
                "entity_type": assessment_data.get("entity_type"),
                "overall_score": assessment_data.get("overall_score"),
                "risk_level": assessment_data.get("risk_level"),
                "status": assessment_data.get("status"),
                "trigger_type": assessment_data.get("trigger_type"),
                "confidence": assessment_data.get("confidence"),
                "recommendations": assessment_data.get("recommendations", []),
                "risk_factors_count": len(assessment_data.get("risk_factors", [])),
                "created_at": assessment_data.get("created_at"),
                "updated_at": assessment_data.get("updated_at"),
                "cached_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Store in Redis with TTL
            success = await self.redis_client.setex(
                cache_key,
                self.ttl_config["risk_assessment"],
                json.dumps(cache_data, default=str)
            )
            
            if success:
                logger.debug(f"Cached risk assessment: {assessment_id}")
                
                # Also cache by entity for quick lookups
                await self._cache_entity_risk_lookup(
                    assessment_data.get("entity_id"),
                    assessment_data.get("entity_type"),
                    assessment_id
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to cache risk assessment {assessment_id}: {e}")
            return False

    async def get_cached_risk_assessment(self, assessment_id: str) -> Optional[Dict[str, Any]]:
        """Get cached risk assessment data"""
        try:
            cache_key = f"{self.cache_prefix}risk_assessment:{assessment_id}"
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                assessment_data = json.loads(cached_data)
                logger.debug(f"Retrieved cached risk assessment: {assessment_id}")
                return assessment_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached risk assessment {assessment_id}: {e}")
            return None

    async def cache_regulatory_report(self, report_id: str, report_data: Dict[str, Any]) -> bool:
        """Cache regulatory report data"""
        try:
            cache_key = f"{self.cache_prefix}regulatory_report:{report_id}"
            
            cache_data = {
                "report_id": report_id,
                "jurisdiction": report_data.get("jurisdiction"),
                "report_type": report_data.get("report_type"),
                "status": report_data.get("status"),
                "entity_id": report_data.get("entity_id"),
                "submitted_by": report_data.get("submitted_by"),
                "submitted_at": report_data.get("submitted_at"),
                "created_at": report_data.get("created_at"),
                "cached_at": datetime.now(timezone.utc).isoformat()
            }
            
            success = await self.redis_client.setex(
                cache_key,
                self.ttl_config["regulatory_report"],
                json.dumps(cache_data, default=str)
            )
            
            if success:
                logger.debug(f"Cached regulatory report: {report_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to cache regulatory report {report_id}: {e}")
            return False

    async def get_cached_regulatory_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get cached regulatory report data"""
        try:
            cache_key = f"{self.cache_prefix}regulatory_report:{report_id}"
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                report_data = json.loads(cached_data)
                logger.debug(f"Retrieved cached regulatory report: {report_id}")
                return report_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached regulatory report {report_id}: {e}")
            return None

    async def cache_case(self, case_id: str, case_data: Dict[str, Any]) -> bool:
        """Cache case data"""
        try:
            cache_key = f"{self.cache_prefix}case:{case_id}"
            
            cache_data = {
                "case_id": case_id,
                "title": case_data.get("title"),
                "case_type": case_data.get("case_type"),
                "status": case_data.get("status"),
                "priority": case_data.get("priority"),
                "assigned_to": case_data.get("assigned_to"),
                "created_by": case_data.get("created_by"),
                "created_at": case_data.get("created_at"),
                "updated_at": case_data.get("updated_at"),
                "evidence_count": case_data.get("evidence_count", 0),
                "cached_at": datetime.now(timezone.utc).isoformat()
            }
            
            success = await self.redis_client.setex(
                cache_key,
                self.ttl_config["case"],
                json.dumps(cache_data, default=str)
            )
            
            if success:
                logger.debug(f"Cached case: {case_id}")
                
                # Cache by assignee for user-specific lookups
                await self._cache_user_case_lookup(
                    case_data.get("assigned_to"),
                    case_id
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to cache case {case_id}: {e}")
            return False

    async def get_cached_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Get cached case data"""
        try:
            cache_key = f"{self.cache_prefix}case:{case_id}"
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                case_data = json.loads(cached_data)
                logger.debug(f"Retrieved cached case: {case_id}")
                return case_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached case {case_id}: {e}")
            return None

    async def cache_risk_summary(self, summary_data: Dict[str, Any]) -> bool:
        """Cache risk summary statistics"""
        try:
            cache_key = f"{self.cache_prefix}risk_summary:latest"
            
            cache_data = {
                "summary": summary_data,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=self.ttl_config["risk_summary"])).isoformat()
            }
            
            success = await self.redis_client.setex(
                cache_key,
                self.ttl_config["risk_summary"],
                json.dumps(cache_data, default=str)
            )
            
            if success:
                logger.debug("Cached risk summary statistics")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to cache risk summary: {e}")
            return False

    async def get_cached_risk_summary(self) -> Optional[Dict[str, Any]]:
        """Get cached risk summary statistics"""
        try:
            cache_key = f"{self.cache_prefix}risk_summary:latest"
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                summary_data = json.loads(cached_data)
                logger.debug("Retrieved cached risk summary")
                return summary_data.get("summary")
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached risk summary: {e}")
            return None

    async def cache_case_statistics(self, stats_data: Dict[str, Any]) -> bool:
        """Cache case statistics"""
        try:
            cache_key = f"{self.cache_prefix}case_statistics:latest"
            
            cache_data = {
                "statistics": stats_data,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=self.ttl_config["case_statistics"])).isoformat()
            }
            
            success = await self.redis_client.setex(
                cache_key,
                self.ttl_config["case_statistics"],
                json.dumps(cache_data, default=str)
            )
            
            if success:
                logger.debug("Cached case statistics")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to cache case statistics: {e}")
            return False

    async def get_cached_case_statistics(self) -> Optional[Dict[str, Any]]:
        """Get cached case statistics"""
        try:
            cache_key = f"{self.cache_prefix}case_statistics:latest"
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                stats_data = json.loads(cached_data)
                logger.debug("Retrieved cached case statistics")
                return stats_data.get("statistics")
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached case statistics: {e}")
            return None

    async def cache_user_cases(self, user_id: str, case_ids: List[str]) -> bool:
        """Cache user's assigned cases"""
        try:
            cache_key = f"{self.cache_prefix}user_cases:{user_id}"
            
            cache_data = {
                "user_id": user_id,
                "case_ids": case_ids,
                "cached_at": datetime.now(timezone.utc).isoformat()
            }
            
            success = await self.redis_client.setex(
                cache_key,
                self.ttl_config["case"],
                json.dumps(cache_data, default=str)
            )
            
            if success:
                logger.debug(f"Cached user cases for: {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to cache user cases for {user_id}: {e}")
            return False

    async def get_cached_user_cases(self, user_id: str) -> Optional[List[str]]:
        """Get cached user's assigned cases"""
        try:
            cache_key = f"{self.cache_prefix}user_cases:{user_id}"
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                logger.debug(f"Retrieved cached user cases for: {user_id}")
                return data.get("case_ids", [])
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached user cases for {user_id}: {e}")
            return None

    async def cache_entity_risk_lookup(self, entity_id: str, entity_type: str, assessment_id: str) -> bool:
        """Cache entity to risk assessment lookup"""
        try:
            cache_key = f"{self.cache_prefix}entity_risk:{entity_type}:{entity_id}"
            
            cache_data = {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "assessment_id": assessment_id,
                "cached_at": datetime.now(timezone.utc).isoformat()
            }
            
            success = await self.redis_client.setex(
                cache_key,
                self.ttl_config["risk_assessment"],
                json.dumps(cache_data, default=str)
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to cache entity risk lookup for {entity_id}: {e}")
            return False

    async def get_cached_entity_risk_assessment(self, entity_id: str, entity_type: str) -> Optional[str]:
        """Get cached risk assessment ID for entity"""
        try:
            cache_key = f"{self.cache_prefix}entity_risk:{entity_type}:{entity_id}"
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                return data.get("assessment_id")
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached entity risk assessment for {entity_id}: {e}")
            return None

    async def invalidate_cache(self, cache_type: str, identifier: str) -> bool:
        """Invalidate specific cache entry"""
        try:
            cache_key = f"{self.cache_prefix}{cache_type}:{identifier}"
            result = await self.redis_client.delete(cache_key)
            
            if result > 0:
                logger.debug(f"Invalidated cache: {cache_key}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to invalidate cache {cache_key}: {e}")
            return False

    async def invalidate_user_cache(self, user_id: str) -> bool:
        """Invalidate all cache entries for a user"""
        try:
            patterns = [
                f"{self.cache_prefix}user_cases:{user_id}",
                f"{self.cache_prefix}user_assignments:{user_id}",
                f"{self.cache_prefix}user_permissions:{user_id}"
            ]
            
            deleted_count = 0
            for pattern in patterns:
                result = await self.redis_client.delete(pattern)
                deleted_count += result
            
            logger.debug(f"Invalidated {deleted_count} cache entries for user: {user_id}")
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"Failed to invalidate user cache for {user_id}: {e}")
            return False

    async def invalidate_entity_cache(self, entity_id: str, entity_type: str) -> bool:
        """Invalidate all cache entries for an entity"""
        try:
            patterns = [
                f"{self.cache_prefix}entity_risk:{entity_type}:{entity_id}",
                f"{self.cache_prefix}entity_analysis:{entity_type}:{entity_id}",
                f"{self.cache_prefix}entity_monitoring:{entity_type}:{entity_id}"
            ]
            
            deleted_count = 0
            for pattern in patterns:
                result = await self.redis_client.delete(pattern)
                deleted_count += result
            
            logger.debug(f"Invalidated {deleted_count} cache entries for entity: {entity_id}")
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"Failed to invalidate entity cache for {entity_id}: {e}")
            return False

    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        try:
            info = await self.redis_client.info()
            
            stats = {
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory": info.get("used_memory_human"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
                "hit_rate": 0.0,
                "compliance_cache_keys": 0
            }
            
            # Calculate hit rate
            hits = stats["keyspace_hits"]
            misses = stats["keyspace_misses"]
            total = hits + misses
            if total > 0:
                stats["hit_rate"] = hits / total
            
            # Count compliance cache keys
            pattern = f"{self.cache_prefix}*"
            cursor = 0
            while cursor != 0:
                cursor, keys = await self.redis_client.scan(cursor=cursor, match=pattern, count=100)
                stats["compliance_cache_keys"] += len(keys)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get cache statistics: {e}")
            return {
                "error": str(e),
                "redis_connected": False
            }

    async def cleanup_expired_cache(self) -> Dict[str, int]:
        """Clean up expired cache entries"""
        try:
            cleanup_stats = {
                "risk_assessments": 0,
                "regulatory_reports": 0,
                "cases": 0,
                "audit_events": 0,
                "other": 0,
                "total_cleaned": 0
            }
            
            # Get all compliance cache keys
            pattern = f"{self.cache_prefix}*"
            cursor = 0
            keys_to_check = []
            
            while cursor != 0:
                cursor, keys = await self.redis_client.scan(cursor=cursor, match=pattern, count=1000)
                keys_to_check.extend(keys)
            
            # Check TTL for each key and clean up expired ones
            for key in keys_to_check:
                try:
                    ttl = await self.redis_client.ttl(key)
                    if ttl == -1:  # No expiration set, set default
                        await self.redis_client.expire(key, self.default_ttl)
                    elif ttl == -2:  # Key expired but not yet cleaned
                        await self.redis_client.delete(key)
                        
                        # Categorize cleanup
                        if "risk_assessment:" in key:
                            cleanup_stats["risk_assessments"] += 1
                        elif "regulatory_report:" in key:
                            cleanup_stats["regulatory_reports"] += 1
                        elif "case:" in key:
                            cleanup_stats["cases"] += 1
                        elif "audit_event:" in key:
                            cleanup_stats["audit_events"] += 1
                        else:
                            cleanup_stats["other"] += 1
                        
                        cleanup_stats["total_cleaned"] += 1
                
                except Exception as e:
                    logger.warning(f"Failed to check TTL for key {key}: {e}")
            
            logger.info(f"Cache cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
            return {"error": str(e), "total_cleaned": 0}

    async def warm_up_cache(self, data_provider) -> Dict[str, int]:
        """Warm up cache with frequently accessed data"""
        warmup_stats = {
            "risk_assessments": 0,
            "cases": 0,
            "regulatory_reports": 0,
            "summaries": 0,
            "total_warmed": 0
        }
        
        try:
            # Warm up recent risk assessments
            recent_assessments = await data_provider.get_recent_risk_assessments(limit=50)
            for assessment in recent_assessments:
                success = await self.cache_risk_assessment(
                    assessment["assessment_id"],
                    assessment
                )
                if success:
                    warmup_stats["risk_assessments"] += 1
                    warmup_stats["total_warmed"] += 1
            
            # Warm up active cases
            active_cases = await data_provider.get_active_cases(limit=50)
            for case in active_cases:
                success = await self.cache_case(case["case_id"], case)
                if success:
                    warmup_stats["cases"] += 1
                    warmup_stats["total_warmed"] += 1
            
            # Warm up recent regulatory reports
            recent_reports = await data_provider.get_recent_regulatory_reports(limit=20)
            for report in recent_reports:
                success = await self.cache_regulatory_report(
                    report["report_id"],
                    report
                )
                if success:
                    warmup_stats["regulatory_reports"] += 1
                    warmup_stats["total_warmed"] += 1
            
            # Warm up summaries
            risk_summary = await data_provider.get_risk_summary()
            if risk_summary:
                success = await self.cache_risk_summary(risk_summary)
                if success:
                    warmup_stats["summaries"] += 1
                    warmup_stats["total_warmed"] += 1
            
            case_stats = await data_provider.get_case_statistics()
            if case_stats:
                success = await self.cache_case_statistics(case_stats)
                if success:
                    warmup_stats["summaries"] += 1
                    warmup_stats["total_warmed"] += 1
            
            logger.info(f"Cache warm-up completed: {warmup_stats}")
            return warmup_stats
            
        except Exception as e:
            logger.error(f"Cache warm-up failed: {e}")
            return {"error": str(e), "total_warmed": 0}

    # Private helper methods
    async def _cache_entity_risk_lookup(self, entity_id: str, entity_type: str, assessment_id: str):
        """Helper to cache entity risk lookup"""
        await self.cache_entity_risk_lookup(entity_id, entity_type, assessment_id)

    async def _cache_user_case_lookup(self, user_id: str, case_id: str):
        """Helper to cache user case lookup"""
        try:
            cache_key = f"{self.cache_prefix}user_case_lookup:{user_id}:{case_id}"
            await self.redis_client.setex(
                cache_key,
                self.ttl_config["case"],
                json.dumps({"case_id": case_id, "cached_at": datetime.now(timezone.utc).isoformat()})
            )
        except Exception as e:
            logger.warning(f"Failed to cache user case lookup: {e}")


# Cache initialization function
async def initialize_compliance_cache(redis_client: redis.Redis) -> ComplianceCacheManager:
    """Initialize compliance cache manager"""
    cache_manager = ComplianceCacheManager(redis_client)
    
    # Test Redis connection
    try:
        await redis_client.ping()
        logger.info("Compliance cache initialized successfully")
    except Exception as e:
        logger.error(f"Failed to connect to Redis for compliance cache: {e}")
        raise
    
    return cache_manager
