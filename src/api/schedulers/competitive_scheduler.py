"""
Jackdaw Sentry - Competitive Assessment Scheduler
Automated scheduling of benchmarks, reports, and maintenance tasks
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import asdict, dataclass
import json
import asyncpg
import redis.asyncio as aioredis

from src.competitive.benchmarking_suite import CompetitiveBenchmarkingSuite
from src.competitive.advanced_analytics import AdvancedAnalytics
from src.competitive.expanded_competitors import ExpandedCompetitiveAnalysis
from src.competitive.cost_analysis import CostAnalysis
from ..webhooks.competitive_webhooks import webhook_manager

logger = logging.getLogger(__name__)

@dataclass
class ScheduledTask:
    """Represents a scheduled task"""
    task_id: str
    name: str
    schedule: str  # Cron-like expression
    function: Callable
    enabled: bool
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    success_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = None

class CompetitiveScheduler:
    """Scheduler for competitive assessment tasks"""
    
    def __init__(self, db_pool: Optional[asyncpg.Pool] = None, redis_client: Optional[aioredis.Redis] = None):
        self.db_pool = db_pool
        self.redis_client = redis_client
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.scheduler_task = None
        
        # Initialize competitive services
        self.benchmarking_suite = None
        self.advanced_analytics = None
        self.expanded_analysis = None
        self.cost_analysis = None
    
    async def initialize(self) -> None:
        """Initialize scheduler and services"""
        logger.info("Initializing competitive scheduler...")
        
        # Initialize competitive services
        await self.initialize_services()
        
        # Register default tasks
        self.register_default_tasks()
        
        # Load tasks from database
        await self.load_scheduled_tasks()
        
        logger.info(f"Scheduler initialized with {len(self.tasks)} tasks")
    
    async def initialize_services(self) -> None:
        """Initialize competitive analysis services"""
        self.benchmarking_suite = CompetitiveBenchmarkingSuite()
        await self.benchmarking_suite.__aenter__()
        
        self.advanced_analytics = AdvancedAnalytics(self.db_pool, self.redis_client)
        await self.advanced_analytics.initialize_models()
        
        self.expanded_analysis = ExpandedCompetitiveAnalysis()
        self.cost_analysis = CostAnalysis()
    
    def register_default_tasks(self) -> None:
        """Register default scheduled tasks"""
        
        # Hourly competitive benchmark
        self.register_task(
            task_id="hourly_benchmark",
            name="Hourly Competitive Benchmark",
            schedule="0 * * * *",  # Every hour at minute 0
            function=self.run_hourly_benchmark,
            enabled=True,
            metadata={"benchmark_type": "performance"}
        )
        
        # Daily comprehensive analysis
        self.register_task(
            task_id="daily_analysis",
            name="Daily Comprehensive Analysis",
            schedule="0 2 * * *",  # Every day at 2 AM
            function=self.run_daily_analysis,
            enabled=True,
            metadata={"analysis_type": "comprehensive"}
        )
        
        # Weekly competitive report
        self.register_task(
            task_id="weekly_report",
            name="Weekly Competitive Report",
            schedule="0 9 * * 1",  # Every Monday at 9 AM
            function=self.generate_weekly_report,
            enabled=True,
            metadata={"report_type": "executive"}
        )
        
        # Monthly cost analysis
        self.register_task(
            task_id="monthly_cost_analysis",
            name="Monthly Cost Analysis",
            schedule="0 3 1 * *",  # Every month on 1st at 3 AM
            function=self.run_monthly_cost_analysis,
            enabled=True,
            metadata={"analysis_type": "cost"}
        )
        
        # Performance anomaly check (every 30 minutes)
        self.register_task(
            task_id="anomaly_check",
            name="Performance Anomaly Check",
            schedule="*/30 * * * *",  # Every 30 minutes
            function=self.check_performance_anomalies,
            enabled=True,
            metadata={"check_type": "anomaly"}
        )
        
        # Database maintenance (daily at 4 AM)
        self.register_task(
            task_id="database_maintenance",
            name="Database Maintenance",
            schedule="0 4 * * *",  # Every day at 4 AM
            function=self.run_database_maintenance,
            enabled=True,
            metadata={"maintenance_type": "cleanup"}
        )
        
        # Model retraining (weekly on Sunday at 1 AM)
        self.register_task(
            task_id="model_retraining",
            name="ML Model Retraining",
            schedule="0 1 * * 0",  # Every Sunday at 1 AM
            function=self.retrain_ml_models,
            enabled=True,
            metadata={"retraining_type": "models"}
        )
    
    def register_task(self, task_id: str, name: str, schedule: str, function: Callable, 
                     enabled: bool = True, metadata: Dict[str, Any] = None) -> None:
        """Register a scheduled task"""
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            schedule=schedule,
            function=function,
            enabled=enabled,
            metadata=metadata or {}
        )
        
        # Calculate next run time
        task.next_run = self.calculate_next_run(schedule)
        
        self.tasks[task_id] = task
        logger.info(f"Registered task: {task_id} - {name}")
    
    def calculate_next_run(self, schedule: str) -> datetime:
        """Calculate next run time from cron-like schedule"""
        # Simple cron parser for basic schedules
        # Format: minute hour day month weekday
        
        now = datetime.now(timezone.utc)
        parts = schedule.split()
        
        if len(parts) != 5:
            logger.warning(f"Invalid schedule format: {schedule}")
            return now + timedelta(hours=1)  # Default to 1 hour from now
        
        minute, hour, day, month, weekday = parts
        
        # Handle common patterns
        if minute == "0" and hour == "*" and day == "*" and month == "*" and weekday == "*":
            # Every hour
            next_run = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        elif minute == "0" and hour.isdigit() and day == "*" and month == "*" and weekday == "*":
            # Specific hour daily
            target_hour = int(hour)
            next_run = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
        elif minute == "0" and hour.isdigit() and day == "*" and month == "*" and weekday.isdigit():
            # Specific hour on specific weekday
            target_hour = int(hour)
            target_weekday = int(weekday)
            next_run = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
            
            # Find next occurrence of target weekday
            days_ahead = (target_weekday - now.weekday()) % 7
            if days_ahead == 0 and next_run <= now:
                days_ahead = 7
            next_run += timedelta(days=days_ahead)
        elif minute.isdigit() and hour == "*" and day == "*" and month == "*" and weekday == "*":
            # Every X minutes
            target_minute = int(minute)
            next_run = now.replace(minute=(now.minute // target_minute + 1) * target_minute, second=0, microsecond=0)
        else:
            # Default to 1 hour from now for complex patterns
            next_run = now + timedelta(hours=1)
        
        return next_run
    
    async def start(self) -> None:
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.scheduler_task = asyncio.create_task(self.scheduler_loop())
        logger.info("Scheduler started")
    
    async def stop(self) -> None:
        """Stop the scheduler"""
        self.running = False
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler stopped")
    
    async def scheduler_loop(self) -> None:
        """Main scheduler loop"""
        logger.info("Scheduler loop started")
        
        while self.running:
            try:
                now = datetime.now(timezone.utc)
                
                # Check for tasks that need to run
                for task_id, task in self.tasks.items():
                    if task.enabled and task.next_run and task.next_run <= now:
                        await self.run_task(task)
                
                # Sleep for 1 minute before next check
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)
        
        logger.info("Scheduler loop stopped")
    
    async def run_task(self, task: ScheduledTask) -> None:
        """Run a scheduled task"""
        logger.info(f"Running task: {task.task_id} - {task.name}")
        
        task.last_run = datetime.now(timezone.utc)
        task.run_count += 1
        
        try:
            # Run the task function
            await task.function(task.metadata)
            
            task.success_count += 1
            task.last_error = None
            
            # Send success notification
            await webhook_manager.send_notification("task_completed", {
                "task_id": task.task_id,
                "task_name": task.name,
                "status": "success",
                "run_time": task.last_run.isoformat()
            })
            
            logger.info(f"Task completed successfully: {task.task_id}")
            
        except Exception as e:
            task.error_count += 1
            task.last_error = str(e)
            
            # Send error notification
            await webhook_manager.send_notification("task_failed", {
                "task_id": task.task_id,
                "task_name": task.name,
                "status": "failed",
                "error": str(e),
                "run_time": task.last_run.isoformat()
            })
            
            logger.error(f"Task failed: {task.task_id} - {e}")
        
        finally:
            # Calculate next run time
            task.next_run = self.calculate_next_run(task.schedule)
            
            # Save task status to database
            await self.save_task_status(task)
    
    async def save_task_status(self, task: ScheduledTask) -> None:
        """Save task status to database"""
        if not self.db_pool:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO competitive.scheduled_tasks (
                        task_id, name, schedule, enabled, last_run, next_run,
                        run_count, success_count, error_count, last_error, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (task_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        schedule = EXCLUDED.schedule,
                        enabled = EXCLUDED.enabled,
                        last_run = EXCLUDED.last_run,
                        next_run = EXCLUDED.next_run,
                        run_count = EXCLUDED.run_count,
                        success_count = EXCLUDED.success_count,
                        error_count = EXCLUDED.error_count,
                        last_error = EXCLUDED.last_error,
                        metadata = EXCLUDED.metadata
                """, 
                task.task_id, task.name, task.schedule, task.enabled,
                task.last_run, task.next_run, task.run_count, task.success_count,
                task.error_count, task.last_error, json.dumps(task.metadata)
                )
                
        except Exception as e:
            logger.error(f"Failed to save task status: {e}")
    
    async def load_scheduled_tasks(self) -> None:
        """Load scheduled tasks from database"""
        if not self.db_pool:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM competitive.scheduled_tasks WHERE enabled = TRUE
                """)
                
                for row in rows:
                    task = ScheduledTask(
                        task_id=row['task_id'],
                        name=row['name'],
                        schedule=row['schedule'],
                        function=self.get_task_function(row['task_id']),
                        enabled=row['enabled'],
                        last_run=row['last_run'],
                        next_run=row['next_run'],
                        run_count=row['run_count'],
                        success_count=row['success_count'],
                        error_count=row['error_count'],
                        last_error=row['last_error'],
                        metadata=row['metadata']
                    )
                    
                    self.tasks[row['task_id']] = task
                
                logger.info(f"Loaded {len(rows)} tasks from database")
                
        except Exception as e:
            logger.error(f"Failed to load scheduled tasks: {e}")
    
    def get_task_function(self, task_id: str) -> Callable:
        """Get task function by ID"""
        function_map = {
            "hourly_benchmark": self.run_hourly_benchmark,
            "daily_analysis": self.run_daily_analysis,
            "weekly_report": self.generate_weekly_report,
            "monthly_cost_analysis": self.run_monthly_cost_analysis,
            "anomaly_check": self.check_performance_anomalies,
            "database_maintenance": self.run_database_maintenance,
            "model_retraining": self.retrain_ml_models
        }
        
        return function_map.get(task_id, lambda metadata: None)
    
    # Task implementations
    async def run_hourly_benchmark(self, metadata: Dict[str, Any]) -> None:
        """Run hourly competitive benchmark"""
        benchmark_type = metadata.get("benchmark_type", "performance")
        
        if benchmark_type == "performance":
            results = await self.benchmarking_suite.run_performance_benchmarks()
        elif benchmark_type == "security":
            results = await self.benchmarking_suite.run_security_benchmarks()
        elif benchmark_type == "feature":
            results = await self.benchmarking_suite.run_feature_benchmarks()
        else:
            results = await self.benchmarking_suite.run_all_benchmarks()
        
        # Store results
        await self.benchmarking_suite.store_competitive_report(results)
        
        logger.info(f"Hourly {benchmark_type} benchmark completed")
    
    async def run_daily_analysis(self, metadata: Dict[str, Any]) -> None:
        """Run daily comprehensive analysis"""
        analysis_type = metadata.get("analysis_type", "comprehensive")
        
        if analysis_type == "comprehensive":
            # Run all analysis modules
            insights = await self.advanced_analytics.generate_competitive_insights()
            competitors = await self.expanded_analysis.analyze_expanded_competitive_landscape()
            cost_report = await self.cost_analysis.generate_cost_report()
            
            # Store comprehensive report
            report_data = {
                "insights": [asdict(insight) for insight in insights],
                "competitors": competitors,
                "cost_analysis": cost_report,
                "analysis_type": "comprehensive"
            }
        else:
            # Run specific analysis
            report_data = {"analysis_type": analysis_type}
        
        await self.benchmarking_suite.store_competitive_report(report_data)
        
        logger.info(f"Daily {analysis_type} analysis completed")
    
    async def generate_weekly_report(self, metadata: Dict[str, Any]) -> None:
        """Generate weekly competitive report"""
        report_type = metadata.get("report_type", "executive")
        
        # Get data for the past week
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        
        if self.db_pool:
            async with self.db_pool.acquire() as conn:
                # Get weekly metrics
                metrics = await conn.fetch("""
                    SELECT * FROM competitive.metrics 
                    WHERE timestamp >= $1
                    ORDER BY timestamp DESC
                """, week_ago)
                
                # Get weekly benchmarks
                benchmarks = await conn.fetch("""
                    SELECT * FROM competitive.benchmarks 
                    WHERE timestamp >= $1 AND success = TRUE
                    ORDER BY timestamp DESC
                """, week_ago)
                
                # Generate report
                report_data = {
                    "report_type": report_type,
                    "period": "weekly",
                    "start_date": week_ago.isoformat(),
                    "end_date": datetime.now(timezone.utc).isoformat(),
                    "metrics": [dict(row) for row in metrics],
                    "benchmarks": [dict(row) for row in benchmarks],
                    "summary": self.generate_weekly_summary(metrics, benchmarks)
                }
                
                await self.benchmarking_suite.store_competitive_report(report_data)
        
        logger.info(f"Weekly {report_type} report generated")
    
    def generate_weekly_summary(self, metrics: List, benchmarks: List) -> Dict[str, Any]:
        """Generate weekly summary statistics"""
        if not metrics and not benchmarks:
            return {"status": "no_data"}
        
        summary = {
            "total_metrics": len(metrics),
            "total_benchmarks": len(benchmarks),
            "avg_parity": 0,
            "performance_trends": {},
            "top_performers": [],
            "areas_for_improvement": []
        }
        
        if metrics:
            # Calculate average parity
            parities = [float(row['achieved_parity']) for row in metrics if 'achieved_parity' in row]
            if parities:
                summary["avg_parity"] = sum(parities) / len(parities)
        
        return summary
    
    async def run_monthly_cost_analysis(self, metadata: Dict[str, Any]) -> None:
        """Run monthly cost analysis"""
        cost_report = await self.cost_analysis.generate_cost_report()
        
        # Store cost analysis
        await self.benchmarking_suite.store_competitive_report({
            "cost_analysis": cost_report,
            "analysis_type": "cost",
            "period": "monthly"
        })
        
        logger.info("Monthly cost analysis completed")
    
    async def check_performance_anomalies(self, metadata: Dict[str, Any]) -> None:
        """Check for performance anomalies"""
        check_type = metadata.get("check_type", "anomaly")
        
        # Get recent metrics
        if self.db_pool:
            async with self.db_pool.acquire() as conn:
                recent_metrics = await conn.fetch("""
                    SELECT feature, jackdaw_value, timestamp
                    FROM competitive.metrics
                    WHERE timestamp >= NOW() - INTERVAL '1 hour'
                    ORDER BY timestamp DESC
                """)
                
                anomalies = []
                for metric in recent_metrics:
                    # Simple anomaly detection
                    if metric['jackdaw_value']:
                        anomaly = await self.advanced_analytics.detect_anomalies(
                            metric['feature'], 
                            float(metric['jackdaw_value'])
                        )
                        if anomaly:
                            anomalies.append(anomaly)
                
                if anomalies:
                    # Store anomalies
                    for anomaly in anomalies:
                        await self.advanced_analytics.store_performance_alert(
                            anomaly.alert_type,
                            anomaly.feature,
                            anomaly.description,
                            anomaly.recommendations[0] if anomaly.recommendations else None
                        )
                    
                    # Send notification
                    await webhook_manager.send_notification("anomalies_detected", {
                        "anomaly_count": len(anomalies),
                        "anomalies": [asdict(anomaly) for anomaly in anomalies[:5]]  # Top 5
                    })
        
        logger.info(f"Performance anomaly check completed: {len(anomalies)} anomalies found")
    
    async def run_database_maintenance(self, metadata: Dict[str, Any]) -> None:
        """Run database maintenance tasks"""
        if not self.db_pool:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                # Clean up old data (keep last 90 days)
                await conn.execute("SELECT competitive.cleanup_old_benchmarks()")
                
                # Update statistics
                await conn.execute("ANALYZE competitive.benchmarks")
                await conn.execute("ANALYZE competitive.metrics")
                await conn.execute("ANALYZE competitive.reports")
                
                logger.info("Database maintenance completed")
                
        except Exception as e:
            logger.error(f"Database maintenance failed: {e}")
    
    async def retrain_ml_models(self, metadata: Dict[str, Any]) -> None:
        """Retrain ML models"""
        try:
            # Reload historical data
            await self.advanced_analytics.load_historical_data()
            
            # Retrain models
            await self.advanced_analytics.initialize_models()
            
            logger.info("ML models retrained successfully")
            
        except Exception as e:
            logger.error(f"ML model retraining failed: {e}")
    
    async def get_task_status(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of scheduled tasks"""
        if task_id:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                return {
                    "task_id": task.task_id,
                    "name": task.name,
                    "enabled": task.enabled,
                    "last_run": task.last_run.isoformat() if task.last_run else None,
                    "next_run": task.next_run.isoformat() if task.next_run else None,
                    "run_count": task.run_count,
                    "success_count": task.success_count,
                    "error_count": task.error_count,
                    "success_rate": task.success_count / task.run_count if task.run_count > 0 else 0,
                    "last_error": task.last_error
                }
            else:
                return {"error": "Task not found"}
        else:
            # Return all tasks
            return {
                "tasks": {
                    task_id: {
                        "name": task.name,
                        "enabled": task.enabled,
                        "last_run": task.last_run.isoformat() if task.last_run else None,
                        "next_run": task.next_run.isoformat() if task.next_run else None,
                        "run_count": task.run_count,
                        "success_count": task.success_count,
                        "error_count": task.error_count,
                        "last_error": task.last_error
                    }
                    for task_id, task in self.tasks.items()
                },
                "total_tasks": len(self.tasks),
                "enabled_tasks": len([t for t in self.tasks.values() if t.enabled]),
                "scheduler_running": self.running
            }
    
    async def enable_task(self, task_id: str) -> bool:
        """Enable a scheduled task"""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
            await self.save_task_status(self.tasks[task_id])
            logger.info(f"Task enabled: {task_id}")
            return True
        return False
    
    async def disable_task(self, task_id: str) -> bool:
        """Disable a scheduled task"""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
            await self.save_task_status(self.tasks[task_id])
            logger.info(f"Task disabled: {task_id}")
            return True
        return False

# Global scheduler instance
scheduler = None

async def get_scheduler() -> CompetitiveScheduler:
    """Get or create global scheduler instance"""
    global scheduler
    if scheduler is None:
        from ..database import get_db_pool, get_redis_client
        db_pool = await get_db_pool()
        redis_client = await get_redis_client()
        scheduler = CompetitiveScheduler(db_pool, redis_client)
        await scheduler.initialize()
    return scheduler


async def startup() -> None:
    """Initialize the competitive scheduler on application startup"""
    logger.info("Competitive scheduler startup initiated")
    
    # Initialize and start the global scheduler
    scheduler_instance = await get_scheduler()
    await scheduler_instance.start()
    
    logger.info("Competitive scheduler startup complete")


async def shutdown() -> None:
    """Shut down the competitive scheduler on application shutdown"""
    global scheduler
    if scheduler is not None:
        try:
            # Stop the scheduler
            await scheduler.stop()
            
            # Clean up benchmarking_suite if it was initialized
            if scheduler.benchmarking_suite is not None:
                await scheduler.benchmarking_suite.__aexit__(None, None, None)
                
        except Exception as e:
            logger.error(f"Error during competitive scheduler shutdown: {e}")
        finally:
            # Clear the global scheduler
            scheduler = None
    
    logger.info("Competitive scheduler shutdown complete")
