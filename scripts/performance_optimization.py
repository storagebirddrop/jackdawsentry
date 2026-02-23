#!/usr/bin/env python3
"""
Jackdaw Sentry - Database Performance Optimization
Creates indexes and optimizes queries for better performance
"""

import asyncio
import asyncpg
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """Database performance optimization utilities"""
    
    def __init__(self, postgres_pool: asyncpg.Pool):
        self.pool = postgres_pool
    
    async def create_performance_indexes(self) -> Dict[str, bool]:
        """Create performance-critical indexes"""
        indexes = {
            "users_username_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS users_username_idx ON users(username)",
            "users_email_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS users_email_idx ON users(email)",
            "users_role_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS users_role_idx ON users(role)",
            "users_active_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS users_active_idx ON users(is_active) WHERE is_active = true",
            
            "investigations_created_at_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS investigations_created_at_idx ON investigations(created_at DESC)",
            "investigations_status_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS investigations_status_idx ON investigations(status)",
            "investigations_priority_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS investigations_priority_idx ON investigations(priority)",
            "investigations_created_status_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS investigations_created_status_idx ON investigations(created_at DESC, status)",
            
            "entity_addresses_address_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS entity_addresses_address_idx ON entity_addresses(address)",
            "entity_addresses_entity_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS entity_addresses_entity_idx ON entity_addresses(entity_id)",
            "entity_addresses_blockchain_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS entity_addresses_blockchain_idx ON entity_addresses(blockchain)",
            "entity_addresses_active_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS entity_addresses_active_idx ON entity_addresses(removed_at IS NULL) WHERE removed_at IS NULL",
            "entity_addresses_composite_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS entity_addresses_composite_idx ON entity_addresses(address, blockchain) WHERE removed_at IS NULL",
            
            "transactions_hash_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS transactions_hash_idx ON transactions(hash)",
            "transactions_address_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS transactions_address_idx ON transactions(from_address)",
            "transactions_to_address_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS transactions_to_address_idx ON transactions(to_address)",
            "transactions_blockchain_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS transactions_blockchain_idx ON transactions(blockchain)",
            "transactions_timestamp_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS transactions_timestamp_idx ON transactions(timestamp DESC)",
            "transactions_composite_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS transactions_composite_idx ON transactions(from_address, blockchain, timestamp DESC)",
            
            "alerts_created_at_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS alerts_created_at_idx ON alerts(created_at DESC)",
            "alerts_status_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS alerts_status_idx ON alerts(status)",
            "alerts_severity_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS alerts_severity_idx ON alerts(severity)",
            "alerts_active_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS alerts_active_idx ON alerts(status) WHERE status = 'active'",
            
            "audit_logs_timestamp_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS audit_logs_timestamp_idx ON audit_logs(timestamp DESC)",
            "audit_logs_user_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS audit_logs_user_idx ON audit_logs(user_id)",
            "audit_logs_action_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS audit_logs_action_idx ON audit_logs(action)",
            "audit_logs_composite_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS audit_logs_composite_idx ON audit_logs(timestamp DESC, user_id)",
            
            "compliance_reports_created_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS compliance_reports_created_idx ON compliance_reports(created_at DESC)",
            "compliance_reports_status_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS compliance_reports_status_idx ON compliance_reports(status)",
            "compliance_reports_type_idx": "CREATE INDEX CONCURRENTLY IF NOT EXISTS compliance_reports_type_idx ON compliance_reports(report_type)",
        }
        
        results = {}
        
        for index_name, index_sql in indexes.items():
            try:
                await self.pool.execute(index_sql)
                logger.info(f"Created index: {index_name}")
                results[index_name] = True
            except Exception as e:
                logger.error(f"Failed to create index {index_name}: {e}")
                results[index_name] = False
        
        return results
    
    async def analyze_query_performance(self) -> Dict[str, Any]:
        """Analyze slow queries and suggest optimizations"""
        async with self.pool.acquire() as conn:
            # Check if pg_stat_statements extension exists
            try:
                extension_check = await conn.fetchval("""
                    SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                """)
                if not extension_check:
                    logger.warning("pg_stat_statements extension not found, skipping query analysis")
                    slow_queries = []
                else:
                    # Get query statistics
                    slow_queries = await conn.fetch("""
                        SELECT query, calls, total_time, mean_time, rows
                        FROM pg_stat_statements 
                        WHERE mean_time > 1000 
                        ORDER BY mean_time DESC 
                        LIMIT 10
                    """)
            except Exception as e:
                logger.warning(f"Failed to check pg_stat_statements extension: {e}")
                slow_queries = []
            
            # Get table sizes
            table_sizes = await conn.fetch("""
                SELECT schemaname, tablename, 
                       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                       pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 20
            """)
            
            # Get index usage
            index_usage = await conn.fetch("""
                SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
                FROM pg_stat_user_indexes 
                ORDER BY idx_scan DESC
                LIMIT 20
            """)
            
            return {
                "slow_queries": [dict(q) for q in slow_queries],
                "table_sizes": [dict(t) for t in table_sizes],
                "index_usage": [dict(i) for i in index_usage],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def update_table_statistics(self) -> bool:
        """Update table statistics for better query planning"""
        async with self.pool.acquire() as conn:
            try:
                # Get all user tables
                tables = await conn.fetch("""
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                """)
                
                for table in tables:
                    await conn.execute(f'ANALYZE public."{table["tablename"]}"')
                    logger.info(f"Analyzed table: {table['tablename']}")
                
                return True
            except Exception as e:
                logger.error(f"Failed to update statistics: {e}")
                return False
    
    async def optimize_database_settings(self) -> Dict[str, Any]:
        """Get recommended database settings"""
        async with self.pool.acquire() as conn:
            # Get current settings
            settings = await conn.fetch("""
                SELECT name, setting, unit, short_desc
                FROM pg_settings 
                WHERE name IN (
                    'shared_buffers', 'effective_cache_size', 'work_mem', 
                    'maintenance_work_mem', 'checkpoint_completion_target',
                    'wal_buffers', 'default_statistics_target', 'random_page_cost',
                    'effective_io_concurrency', 'max_connections'
                )
            """)
            
            return {
                "current_settings": [dict(s) for s in settings],
                "recommendations": self._get_performance_recommendations(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def _get_performance_recommendations(self) -> List[Dict[str, str]]:
        """Get performance optimization recommendations"""
        return [
            {
                "setting": "shared_buffers",
                "recommendation": "25% of total RAM",
                "reason": "Improves cache hit ratio"
            },
            {
                "setting": "effective_cache_size", 
                "recommendation": "75% of total RAM",
                "reason": "Helps query planner estimate memory availability"
            },
            {
                "setting": "work_mem",
                "recommendation": "4MB per connection",
                "reason": "Optimizes sort and hash operations"
            },
            {
                "setting": "maintenance_work_mem",
                "recommendation": "10% of RAM",
                "reason": "Speeds up index creation and VACUUM"
            },
            {
                "setting": "checkpoint_completion_target",
                "recommendation": "0.9",
                "reason": "Spreads out I/O for better performance"
            },
            {
                "setting": "random_page_cost",
                "recommendation": "1.1",
                "reason": "Better for SSD storage"
            }
        ]


async def run_optimization():
    """Run complete database optimization"""
    from src.api.database import get_postgres_connection
    
    logger.info("Starting database performance optimization...")
    
    async with get_postgres_connection() as pool:
        optimizer = DatabaseOptimizer(pool)
        
        # Create performance indexes
        logger.info("Creating performance indexes...")
        index_results = await optimizer.create_performance_indexes()
        
        # Update statistics
        logger.info("Updating table statistics...")
        stats_updated = await optimizer.update_table_statistics()
        
        # Analyze performance
        logger.info("Analyzing query performance...")
        performance_analysis = await optimizer.analyze_query_performance()
        
        # Get optimization recommendations
        logger.info("Getting optimization recommendations...")
        recommendations = await optimizer.optimize_database_settings()
        
        # Generate report
        report = {
            "index_results": index_results,
            "statistics_updated": stats_updated,
            "performance_analysis": performance_analysis,
            "recommendations": recommendations,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Save report
        import json
        with open("database_optimization_report.json", "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info("Database optimization completed. Report saved to database_optimization_report.json")
        
        return report


if __name__ == "__main__":
    asyncio.run(run_optimization())
