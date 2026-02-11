"""
Compliance Scheduler Service

This module provides scheduled tasks for compliance operations including:
- Deadline monitoring and reminders
- Data retention and cleanup
- Periodic compliance checks
- Report generation and distribution
- Cache warming and optimization
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import json
import schedule
import time

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskFrequency(Enum):
    """Task execution frequency"""
    MINUTELY = "minutely"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class ScheduledTask:
    """Scheduled task definition"""
    task_id: str
    name: str
    description: str
    frequency: TaskFrequency
    function: callable
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    error_count: int = 0
    max_retries: int = 3
    metadata: Optional[Dict[str, Any]] = None


class ComplianceScheduler:
    """Compliance task scheduler"""

    def __init__(self):
        self.tasks = {}
        self.running = False
        self.scheduler = schedule
        self.deadline_check_interval = 300  # 5 minutes
        self.data_retention_interval = 3600  # 1 hour
        self.cache_cleanup_interval = 1800  # 30 minutes
        self.report_generation_interval = 86400  # 24 hours
        
        # Initialize default tasks
        self._setup_default_tasks()

    def _setup_default_tasks(self):
        """Setup default scheduled tasks"""
        # Deadline monitoring
        self.add_task(
            task_id="deadline_monitoring",
            name="Regulatory Deadline Monitoring",
            description="Check upcoming regulatory deadlines and send reminders",
            frequency=TaskFrequency.MINUTELY,
            function=self._monitor_deadlines,
            metadata={"interval_minutes": 5}
        )
        
        # Data retention cleanup
        self.add_task(
            task_id="data_retention",
            name="Data Retention Cleanup",
            description="Clean up expired compliance data according to retention policies",
            frequency=TaskFrequency.HOURLY,
            function=self._cleanup_expired_data,
            metadata={"retention_days": 2555}  # 7 years
        )
        
        # Cache cleanup
        self.add_task(
            task_id="cache_cleanup",
            name="Cache Cleanup",
            description="Clean up expired cache entries and optimize cache performance",
            frequency=TaskFrequency.MINUTELY,
            function=self._cleanup_cache,
            metadata={"interval_minutes": 30}
        )
        
        # Compliance health check
        self.add_task(
            task_id="health_check",
            name="Compliance Health Check",
            description="Perform comprehensive compliance system health check",
            frequency=TaskFrequency.HOURLY,
            function=self._perform_health_check,
            metadata={}
        )
        
        # Report generation
        self.add_task(
            task_id="report_generation",
            name="Compliance Report Generation",
            description="Generate daily compliance reports and summaries",
            frequency=TaskFrequency.DAILY,
            function=self._generate_daily_reports,
            metadata={"report_types": ["summary", "risk_assessment", "case_statistics"]}
        )
        
        # Cache warming
        self.add_task(
            task_id="cache_warming",
            name="Cache Warming",
            description="Warm up cache with frequently accessed compliance data",
            frequency=TaskFrequency.HOURLY,
            function=self._warm_cache,
            metadata={}
        )
        
        # Database maintenance
        self.add_task(
            task_id="database_maintenance",
            name="Database Maintenance",
            description="Perform routine database maintenance tasks",
            frequency=TaskFrequency.WEEKLY,
            function=self._database_maintenance,
            metadata={}
        )

    def add_task(self, task: ScheduledTask) -> bool:
        """Add a scheduled task"""
        try:
            self.tasks[task.task_id] = task
            self._schedule_task(task)
            logger.info(f"Added scheduled task: {task.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add task {task.task_id}: {e}")
            return False

    def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task"""
        try:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                # Cancel the scheduled job
                schedule.cancel_job(task.function)
                del self.tasks[task_id]
                logger.info(f"Removed scheduled task: {task_id}")
                return True
            else:
                logger.warning(f"Task not found: {task_id}")
                return False
        except Exception as e:
            logger.error(f"Failed to remove task {task_id}: {e}")
            return False

    def enable_task(self, task_id: str) -> bool:
        """Enable a scheduled task"""
        try:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.enabled = True
                self._schedule_task(task)
                logger.info(f"Enabled task: {task_id}")
                return True
            else:
                logger.warning(f"Task not found: {task_id}")
                return False
        except Exception as e:
            logger.error(f"Failed to enable task {task_id}: {e}")
            return False

    def disable_task(self, task_id: str) -> bool:
        """Disable a scheduled task"""
        try:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.enabled = False
                schedule.cancel_job(task.function)
                logger.info(f"Disabled task: {task_id}")
                return True
            else:
                logger.warning(f"Task not found: {task_id}")
                return False
        except Exception as e:
            logger.error(f"Failed to disable task {task_id}: {e}")
            return False

    def _schedule_task(self, task: ScheduledTask):
        """Schedule a task based on its frequency"""
        try:
            # Cancel existing job if any
            if hasattr(task.function, 'cancel'):
                task.function.cancel()
            
            # Schedule new job
            if task.frequency == TaskFrequency.MINUTELY:
                interval = task.metadata.get("interval_minutes", 1)
                task.function = schedule.every(interval).minutes.do(self._execute_task, task)
            elif task.frequency == TaskFrequency.HOURLY:
                task.function = schedule.every().hour.do(self._execute_task, task)
            elif task.frequency == TaskFrequency.DAILY:
                task.function = schedule.every().day.at("02:00").do(self._execute_task, task)
            elif task.frequency == TaskFrequency.WEEKLY:
                task.function = schedule.every().sunday.at("03:00").do(self._execute_task, task)
            elif task.frequency == TaskFrequency.MONTHLY:
                task.function = schedule.every().month.do(self._execute_task, task)
            
            # Set next run time
            task.next_run = schedule.next_run() if hasattr(schedule, 'next_run') else None
            
        except Exception as e:
            logger.error(f"Failed to schedule task {task.task_id}: {e}")

    async def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task"""
        if not task.enabled:
            return
        
        task.status = TaskStatus.RUNNING
        task.last_run = datetime.utcnow()
        
        try:
            logger.info(f"Executing task: {task.name}")
            
            # Execute the task function
            if asyncio.iscoroutinefunction(task.function):
                result = await task.function()
            else:
                result = task.function()
            
            task.status = TaskStatus.COMPLETED
            task.error_count = 0
            
            # Update next run time
            task.next_run = schedule.next_run() if hasattr(schedule, 'next_run') else None
            
            logger.info(f"Task completed: {task.name}")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_count += 1
            
            logger.error(f"Task failed: {task.name} - {e}")
            
            # Retry logic
            if task.error_count < task.max_retries:
                logger.info(f"Retrying task {task.name} (attempt {task.error_count + 1}/{task.max_retries})")
                # Schedule retry after delay
                retry_delay = min(300, 60 * task.error_count)  # Max 5 minutes
                await asyncio.sleep(retry_delay)
                await self._execute_task(task)
            else:
                logger.error(f"Task {task.name} failed after {task.max_retries} attempts")
                task.status = TaskStatus.FAILED

    async def _monitor_deadlines(self) -> Dict[str, Any]:
        """Monitor regulatory deadlines and send reminders"""
        try:
            from src.compliance.regulatory_reporting import RegulatoryReportingEngine
            from src.compliance.case_management import CaseManagementEngine
            from src.api.routers.compliance import router
            
            # Initialize engines
            await router.regulatory_engine.initialize()
            await router.case_engine.initialize()
            
            results = {
                "upcoming_deadlines": [],
                "overdue_deadlines": [],
                "reminders_sent": 0,
                "errors": []
            }
            
            # Get upcoming deadlines
            upcoming_deadlines = await router.regulatory_engine.get_upcoming_deadlines(hours_ahead=72)
            results["upcoming_deadlines"] = upcoming_deadlines
            
            # Check for overdue deadlines
            overdue_deadlines = await router.regulatory_engine.get_overdue_deadlines()
            results["overdue_deadlines"] = overdue_deadlines
            
            # Send reminders for deadlines within 24 hours
            for deadline in upcoming_deadlines:
                hours_until = self._calculate_hours_until(deadline["deadline"])
                
                if hours_until <= 24 and hours_until > 0:
                    await self._send_deadline_reminder(deadline)
                    results["reminders_sent"] += 1
            
            # Create alerts for overdue deadlines
            for deadline in overdue_deadlines:
                await self._create_overdue_deadline_alert(deadline)
            
            logger.info(f"Deadline monitoring completed: {len(results['upcoming_deadlines'])} upcoming, {len(results['overdue_deadlines'])} overdue")
            return results
            
        except Exception as e:
            logger.error(f"Deadline monitoring failed: {e}")
            return {"error": str(e)}

    async def _cleanup_expired_data(self) -> Dict[str, Any]:
        """Clean up expired compliance data"""
        try:
            from src.database.compliance_schema import ComplianceSchemaManager
            from src.database.neo4j_client import get_neo4j_session
            from src.cache.compliance_cache import ComplianceCacheManager
            from src.api.routers.compliance import router
            
            retention_days = 2555  # 7 years
            
            results = {
                "audit_events_deleted": 0,
                "compliance_logs_deleted": 0,
                "cases_archived": 0,
                "cache_entries_deleted": 0,
                "errors": []
            }
            
            # Get database session
            session = await get_neo4j_session()
            schema_manager = ComplianceSchemaManager()
            
            # Clean up expired data
            cleanup_stats = await schema_manager.cleanup_old_data(session, retention_days)
            results.update(cleanup_stats)
            
            # Clean up cache
            cache_manager = ComplianceCacheManager(router.redis_client)
            cache_cleanup_stats = await cache_manager.cleanup_expired_cache()
            results["cache_entries_deleted"] = cache_cleanup_stats.get("total_cleaned", 0)
            
            logger.info(f"Data cleanup completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Data cleanup failed: {e}")
            return {"error": str(e)}

    async def _cleanup_cache(self) -> Dict[str, Any]:
        """Clean up expired cache entries"""
        try:
            from src.cache.compliance_cache import ComplianceCacheManager
            from src.api.routers.compliance import router
            
            cache_manager = ComplianceCacheManager(router.redis_client)
            
            results = await cache_manager.cleanup_expired_cache()
            
            logger.info(f"Cache cleanup completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
            return {"error": str(e)}

    async def _perform_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive compliance system health check"""
        try:
            from src.monitoring.compliance_monitoring import compliance_monitor
            
            health_results = {
                "overall_status": "healthy",
                "checks": {},
                "timestamp": datetime.utcnow().isoformat(),
                "issues": []
            }
            
            # Database connectivity
            db_check = await compliance_monitor.perform_health_check(
                "database_connectivity",
                self._check_database_connectivity
            )
            health_results["checks"]["database"] = db_check
            if db_check.status != "healthy":
                health_results["overall_status"] = "unhealthy"
                health_results["issues"].append("Database connectivity issues")
            
            # Cache connectivity
            cache_check = await compliance_monitor.perform_health_check(
                "cache_connectivity",
                self._check_cache_connectivity
            )
            health_results["checks"]["cache"] = cache_check
            if cache_check.status != "healthy":
                health_results["overall_status"] = "unhealthy"
                health_results["issues"].append("Cache connectivity issues")
            
            # API responsiveness
            api_check = await compliance_monitor.perform_health_check(
                "api_responsiveness",
                self._check_api_responsiveness
            )
            health_results["checks"]["api"] = api_check
            if api_check.status != "healthy":
                health_results["overall_status"] = "unhealthy"
                health_results["issues"].append("API responsiveness issues")
            
            # Compliance engine status
            engine_check = await compliance_monitor.perform_health_check(
                "compliance_engine_status",
                self._check_compliance_engine_status
            )
            health_results["checks"]["compliance_engine"] = engine_check
            if engine_check.status != "healthy":
                health_results["overall_status"] = "unhealthy"
                health_results["issues"].append("Compliance engine issues")
            
            logger.info(f"Health check completed: {health_results['overall_status']}")
            return health_results
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"overall_status": "error", "error": str(e)}

    async def _generate_daily_reports(self) -> Dict[str, Any]:
        """Generate daily compliance reports"""
        try:
            from src.api.routers.compliance import router
            
            results = {
                "reports_generated": [],
                "errors": []
            }
            
            # Initialize engines
            await router.regulatory_engine.initialize()
            await router.case_engine.initialize()
            await router.risk_engine.initialize()
            await router.audit_engine.initialize()
            
            # Generate different types of reports
            report_types = ["summary", "risk_assessment", "case_statistics", "audit_summary"]
            
            for report_type in report_types:
                try:
                    if report_type == "summary":
                        report = await self._generate_summary_report()
                    elif report_type == "risk_assessment":
                        report = await self._generate_risk_assessment_report()
                    elif report_type == "case_statistics":
                        report = await self._generate_case_statistics_report()
                    elif report_type == "audit_summary":
                        report = await self._generate_audit_summary_report()
                    
                    results["reports_generated"].append({
                        "type": report_type,
                        "generated_at": datetime.utcnow().isoformat(),
                        "report_id": report.get("report_id", "unknown")
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to generate {report_type} report: {e}")
                    results["errors"].append(f"{report_type}: {str(e)}")
            
            logger.info(f"Daily report generation completed: {len(results['reports_generated'])} reports, {len(results['errors'])} errors")
            return results
            
        except Exception as e:
            logger.error(f"Daily report generation failed: {e}")
            return {"error": str(e), "reports_generated": [], "errors": [str(e)]}

    async def _warm_cache(self) -> Dict[str, Any]:
        """Warm up cache with frequently accessed data"""
        try:
            from src.cache.compliance_cache import ComplianceCacheManager
            from src.api.routers.compliance import router
            
            cache_manager = ComplianceCacheManager(router.redis_client)
            
            # Mock data provider (in production, this would query actual data)
            class MockDataProvider:
                async def get_recent_risk_assessments(self, limit=50):
                    return []
                async def get_active_cases(self, limit=50):
                    return []
                async def get_recent_regulatory_reports(self, limit=20):
                    return []
                async def get_risk_summary(self):
                    return {}
                async def get_case_statistics(self):
                    return {}
            
            data_provider = MockDataProvider()
            
            warmup_stats = await cache_manager.warm_up_cache(data_provider)
            
            logger.info(f"Cache warming completed: {warmup_stats}")
            return warmup_stats
            
        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
            return {"error": str(e)}

    async def _database_maintenance(self) -> Dict[str, Any]:
        """Perform routine database maintenance"""
        try:
            from src.database.compliance_schema import ComplianceSchemaManager
            from src.database.neo4j_client import get_neo4j_session
            
            results = {
                "operations_completed": [],
                "errors": []
            }
            
            session = await get_neo4j_session()
            schema_manager = ComplianceSchemaManager()
            
            # Verify schema integrity
            integrity_result = await schema_manager.verify_schema_integrity(session)
            results["operations_completed"].append("schema_integrity_check")
            
            if not integrity_result["constraints"]["valid"]:
                results["errors"].append("Schema constraints issues detected")
            
            if not integrity_result["indexes"]["valid"]:
                results["errors"].append("Schema indexes issues detected")
            
            # Get schema statistics
            stats = await schema_manager.get_schema_statistics(session)
            results["schema_statistics"] = stats
            
            # Optimize database
            await session.run("CALL dbms.stats.retrieve('GRAPH NAME')")  # Get graph statistics
            results["operations_completed"].append("database_optimization")
            
            logger.info(f"Database maintenance completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Database maintenance failed: {e}")
            return {"error": str(e), "operations_completed": [], "errors": [str(e)]}

    # Helper methods
    def _calculate_hours_until(self, deadline_str: str) -> int:
        """Calculate hours until deadline"""
        try:
            deadline = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
            now = datetime.utcnow()
            delta = deadline - now
            return max(0, int(delta.total_seconds() / 3600))
        except Exception:
            return 0

    async def _send_deadline_reminder(self, deadline: Dict[str, Any]):
        """Send deadline reminder notification"""
        # Implementation would send email, Slack, or other notification
        logger.warning(f"Deadline reminder: {deadline['report_id']} due in {deadline.get('hours_until', 'unknown')} hours")

    async def _create_overdue_deadline_alert(self, deadline: Dict[str, Any]):
        """Create alert for overdue deadline"""
        # Implementation would create high-priority alert
        logger.error(f"OVERDUE DEADLINE: {deadline['report_id']} was due on {deadline['deadline']}")

    async def _check_database_connectivity(self) -> bool:
        """Check database connectivity"""
        # Implementation would check Neo4j and PostgreSQL
        return True

    async def _check_cache_connectivity(self) -> bool:
        """Check cache connectivity"""
        # Implementation would check Redis
        return True

    async def _check_api_responsiveness(self) -> bool:
        """Check API responsiveness"""
        # Implementation would check API endpoints
        return True

    async def _check_compliance_engine_status(self) -> bool:
        """Check compliance engine status"""
        # Implementation would check compliance engines
        return True

    async def _generate_summary_report(self) -> Dict[str, Any]:
        """Generate compliance summary report"""
        # Implementation would generate summary report
        return {"report_id": f"summary_{datetime.utcnow().strftime('%Y%m%d')}", "type": "summary"}

    async def _generate_risk_assessment_report(self) -> Dict[str, Any]:
        """Generate risk assessment report"""
        # Implementation would generate risk assessment report
        return {"report_id": f"risk_{datetime.utcnow().strftime('%Y%m%d')}", "type": "risk_assessment"}

    async def _generate_case_statistics_report(self) -> Dict[str, Any]:
        """Generate case statistics report"""
        # Implementation would generate case statistics report
        return {"report_id": f"cases_{datetime.utcnow().strftime('%Y%m%d')}", "type": "case_statistics"}

    async def _generate_audit_summary_report(self) -> Dict[str, Any]:
        """Generate audit summary report"""
        # Implementation would generate audit summary report
        return {"report_id": f"audit_{datetime.utcnow().strftime('%Y%m%d')}", "type": "audit_summary"}

    def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        logger.info("Starting compliance scheduler")
        
        # Start scheduler in background thread
        import threading
        
        def run_scheduler():
            while self.running:
                    schedule.run_pending()
                    time.sleep(1)
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        logger.info("Compliance scheduler started")

    def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("Compliance scheduler stopped")

    def get_task_status(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """Get task status"""
        if task_id:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                return {
                    "task_id": task.task_id,
                    "name": task.name,
                    "description": task.description,
                    "frequency": task.frequency.value,
                    "enabled": task.enabled,
                    "status": task.status.value,
                    "last_run": task.last_run.isoformat() if task.last_run else None,
                    "next_run": task.next_run.isoformat() if task.next_run else None,
                    "error_count": task.error_count,
                    "max_retries": task.max_retries
                }
            else:
                return {"error": f"Task not found: {task_id}"}
        else:
            return {
                "total_tasks": len(self.tasks),
                "enabled_tasks": len([t for t in self.tasks.values() if t.enabled]),
                "running": self.running,
                "tasks": {
                    task_id: {
                        "name": task.name,
                        "status": task.status.value,
                        "enabled": task.enabled,
                        "last_run": task.last_run.isoformat() if task.last_run else None,
                        "next_run": task.next_run.isoformat() if task.next_run else None
                    }
                    for task_id, task in self.tasks.items()
                }
            }

    async def run_task_now(self, task_id: str) -> bool:
        """Run a task immediately"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            await self._execute_task(task)
            return True
        else:
            logger.error(f"Task not found: {task_id}")
            return False


# Global scheduler instance
compliance_scheduler = ComplianceScheduler()
