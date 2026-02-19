"""
Jackdaw Sentry - Monitoring and Error Handling
Comprehensive monitoring, error tracking, and alerting system
"""

import asyncio
import functools
import logging
import time
import traceback
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum
import json
import psutil
import aiohttp
from collections import defaultdict, deque

from src.api.config import settings
from src.api.logging_config import get_logger, log_error_with_traceback

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Alert:
    """Alert data structure"""
    id: str
    severity: AlertSeverity
    title: str
    message: str
    source: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class Metric:
    """Metric data structure"""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class ErrorEvent:
    """Error event data structure"""
    id: str
    error_type: str
    message: str
    stack_trace: str
    context: Dict[str, Any]
    timestamp: datetime
    severity: AlertSeverity
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class MetricsCollector:
    """Collects and manages application metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.timers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._lock = asyncio.Lock()
    
    async def increment_counter(self, name: str, value: int = 1, labels: Dict[str, str] = None):
        """Increment a counter metric"""
        async with self._lock:
            key = self._make_key(name, labels)
            self.counters[key] += value
            self.metrics[key].append(Metric(
                name=name,
                value=self.counters[key],
                metric_type=MetricType.COUNTER,
                timestamp=datetime.now(timezone.utc),
                labels=labels or {}
            ))
    
    async def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric"""
        async with self._lock:
            key = self._make_key(name, labels)
            self.gauges[key] = value
            self.metrics[key].append(Metric(
                name=name,
                value=value,
                metric_type=MetricType.GAUGE,
                timestamp=datetime.now(timezone.utc),
                labels=labels or {}
            ))
    
    async def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram metric"""
        async with self._lock:
            key = self._make_key(name, labels)
            self.histograms[key].append(value)
            self.metrics[key].append(Metric(
                name=name,
                value=value,
                metric_type=MetricType.HISTOGRAM,
                timestamp=datetime.now(timezone.utc),
                labels=labels or {}
            ))
    
    async def record_timer(self, name: str, duration: float, labels: Dict[str, str] = None):
        """Record a timer metric"""
        async with self._lock:
            key = self._make_key(name, labels)
            self.timers[key].append(duration)
            self.metrics[key].append(Metric(
                name=name,
                value=duration,
                metric_type=MetricType.TIMER,
                timestamp=datetime.now(timezone.utc),
                labels=labels or {}
            ))
    
    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Create a metric key with labels"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}[{label_str}]"
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics"""
        async with self._lock:
            return {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {
                    key: {
                        "count": len(values),
                        "sum": sum(values),
                        "avg": sum(values) / len(values) if values else 0,
                        "min": min(values) if values else 0,
                        "max": max(values) if values else 0
                    }
                    for key, values in self.histograms.items()
                },
                "timers": {
                    key: {
                        "count": len(values),
                        "sum": sum(values),
                        "avg": sum(values) / len(values) if values else 0,
                        "min": min(values) if values else 0,
                        "max": max(values) if values else 0
                    }
                    for key, values in self.timers.items()
                }
            }


class AlertManager:
    """Manages alerts and notifications"""
    
    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.alert_rules: List[Callable] = []
        self.notification_handlers: List[Callable] = []
        self._lock = asyncio.Lock()
    
    def add_alert_rule(self, rule_func: Callable):
        """Add an alert rule function"""
        self.alert_rules.append(rule_func)
    
    def add_notification_handler(self, handler_func: Callable):
        """Add a notification handler"""
        self.notification_handlers.append(handler_func)
    
    async def create_alert(self, severity: AlertSeverity, title: str, message: str,
                         source: str, metadata: Dict[str, Any] = None) -> Alert:
        """Create a new alert"""
        alert_id = f"alert_{int(time.time())}_{hash(title)}"
        alert = Alert(
            id=alert_id,
            severity=severity,
            title=title,
            message=message,
            source=source,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {}
        )
        
        async with self._lock:
            self.alerts[alert_id] = alert
        
        # Send notifications
        await self._send_notifications(alert)
        
        logger.warning(f"Alert created: {title} - {message}")
        return alert
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        async with self._lock:
            if alert_id in self.alerts:
                self.alerts[alert_id].resolved = True
                self.alerts[alert_id].resolved_at = datetime.now(timezone.utc)
                logger.info(f"Alert resolved: {alert_id}")
                return True
        return False
    
    async def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        async with self._lock:
            return [alert for alert in self.alerts.values() if not alert.resolved]
    
    async def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history"""
        async with self._lock:
            return sorted(
                self.alerts.values(),
                key=lambda a: a.timestamp,
                reverse=True
            )[:limit]
    
    async def _send_notifications(self, alert: Alert):
        """Send notifications for an alert"""
        for handler in self.notification_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")


class ErrorHandler:
    """Handles error tracking and reporting"""
    
    def __init__(self, alert_manager: AlertManager):
        self.alert_manager = alert_manager
        self.error_events: Dict[str, ErrorEvent] = {}
        self.error_patterns: Dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()
    
    async def capture_exception(self, exception: Exception, context: Dict[str, Any] = None,
                               severity: AlertSeverity = AlertSeverity.MEDIUM) -> ErrorEvent:
        """Capture and track an exception"""
        error_id = f"error_{int(time.time())}_{hash(str(exception))}"
        error_event = ErrorEvent(
            id=error_id,
            error_type=type(exception).__name__,
            message=str(exception),
            stack_trace=traceback.format_exc(),
            context=context or {},
            timestamp=datetime.now(timezone.utc),
            severity=severity
        )
        
        async with self._lock:
            self.error_events[error_id] = error_event
            self.error_patterns[error_event.error_type] += 1
        
        # Create alert for critical errors
        if severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
            await self.alert_manager.create_alert(
                severity=severity,
                title=f"Error: {error_event.error_type}",
                message=error_event.message,
                source="error_handler",
                metadata={
                    "error_id": error_id,
                    "error_type": error_event.error_type,
                    "context": context
                }
            )
        
        log_error_with_traceback(logger, f"Error captured: {error_event.error_type}", exception)
        return error_event
    
    async def get_error_summary(self) -> Dict[str, Any]:
        """Get error statistics summary"""
        async with self._lock:
            total_errors = len(self.error_events)
            recent_errors = [
                e for e in self.error_events.values()
                if e.timestamp > datetime.now(timezone.utc) - timedelta(hours=24)
            ]
            
            return {
                "total_errors": total_errors,
                "recent_errors_24h": len(recent_errors),
                "error_patterns": dict(self.error_patterns),
                "most_common_errors": sorted(
                    self.error_patterns.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
            }


class HealthChecker:
    """Monitors system health and components"""
    
    def __init__(self, metrics_collector: MetricsCollector, alert_manager: AlertManager):
        self.metrics_collector = metrics_collector
        self.alert_manager = alert_manager
        self.health_checks: Dict[str, Callable] = {}
        self._running = False
        self._task = None
    
    def add_health_check(self, name: str, check_func: Callable):
        """Add a health check function"""
        self.health_checks[name] = check_func
    
    async def start_monitoring(self, interval: int = 30):
        """Start continuous health monitoring"""
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop(interval))
    
    async def stop_monitoring(self):
        """Stop health monitoring"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_loop(self, interval: int):
        """Main monitoring loop"""
        while self._running:
            try:
                await self._run_health_checks()
                await self._collect_system_metrics()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(interval)
    
    async def _run_health_checks(self):
        """Run all registered health checks"""
        for name, check_func in self.health_checks.items():
            try:
                start_time = time.time()
                result = await check_func()
                duration = time.time() - start_time
                
                await self.metrics_collector.record_timer(
                    f"health_check_duration",
                    duration,
                    {"check": name}
                )
                
                if result:
                    await self.metrics_collector.increment_counter(
                        "health_check_success",
                        labels={"check": name}
                    )
                else:
                    await self.metrics_collector.increment_counter(
                        "health_check_failure",
                        labels={"check": name}
                    )
                    
                    await self.alert_manager.create_alert(
                        severity=AlertSeverity.HIGH,
                        title=f"Health Check Failed: {name}",
                        message=f"Health check '{name}' failed",
                        source="health_checker",
                        metadata={"check_name": name}
                    )
                    
            except Exception as e:
                await self.metrics_collector.increment_counter(
                    "health_check_error",
                    labels={"check": name}
                )
                
                await self.alert_manager.create_alert(
                    severity=AlertSeverity.HIGH,
                    title=f"Health Check Error: {name}",
                    message=f"Health check '{name}' error: {str(e)}",
                    source="health_checker",
                    metadata={"check_name": name, "error": str(e)}
                )
    
    async def _collect_system_metrics(self):
        """Collect system-level metrics"""
        try:
            # CPU metrics (run in executor to avoid blocking the event loop)
            loop = asyncio.get_event_loop()
            cpu_percent = await loop.run_in_executor(None, psutil.cpu_percent, 1)
            await self.metrics_collector.set_gauge("system_cpu_percent", cpu_percent)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            await self.metrics_collector.set_gauge("system_memory_percent", memory.percent)
            await self.metrics_collector.set_gauge("system_memory_used_mb", memory.used / 1024 / 1024)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            await self.metrics_collector.set_gauge("system_disk_percent", disk.percent)
            await self.metrics_collector.set_gauge("system_disk_used_gb", disk.used / 1024 / 1024 / 1024)
            
            # Network metrics
            network = psutil.net_io_counters()
            await self.metrics_collector.increment_counter("system_network_bytes_sent", network.bytes_sent)
            await self.metrics_collector.increment_counter("system_network_bytes_recv", network.bytes_recv)
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")


class MonitoringSystem:
    """Main monitoring system that coordinates all components"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.error_handler = ErrorHandler(self.alert_manager)
        self.health_checker = HealthChecker(self.metrics_collector, self.alert_manager)
        self._started = False
    
    async def start(self):
        """Start the monitoring system"""
        if self._started:
            return
        
        logger.info("Starting monitoring system...")
        
        # Start health monitoring
        await self.health_checker.start_monitoring()
        
        # Setup default notification handlers
        self._setup_default_handlers()
        
        # Setup default health checks
        self._setup_default_health_checks()
        
        self._started = True
        logger.info("Monitoring system started")
    
    async def stop(self):
        """Stop the monitoring system"""
        if not self._started:
            return
        
        logger.info("Stopping monitoring system...")
        
        await self.health_checker.stop_monitoring()
        
        self._started = False
        logger.info("Monitoring system stopped")
    
    def _setup_default_handlers(self):
        """Setup default notification handlers"""
        async def log_notification(alert: Alert):
            logger.warning(f"ALERT: [{alert.severity.value.upper()}] {alert.title}: {alert.message}")
        
        self.alert_manager.add_notification_handler(log_notification)
    
    def _setup_default_health_checks(self):
        """Setup default health checks"""
        async def check_api_health():
            # Check if API is responsive
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://{settings.API_HOST}:{settings.API_PORT}/health", timeout=5) as response:
                        return response.status == 200
            except Exception:
                return False
        
        async def check_database_health():
            # Check database connectivity
            try:
                from src.api.database import get_postgres_connection
                async with get_postgres_connection() as conn:
                    await conn.fetchval("SELECT 1")
                return True
            except Exception:
                return False
        
        self.health_checker.add_health_check("api", check_api_health)
        self.health_checker.add_health_check("database", check_database_health)
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "monitoring_active": self._started,
            "metrics": await self.metrics_collector.get_metrics_summary(),
            "active_alerts": await self.alert_manager.get_active_alerts(),
            "error_summary": await self.error_handler.get_error_summary(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Global monitoring instance
monitoring_system = MonitoringSystem()


# Decorators for easy monitoring
def monitor_performance(metric_name: str = None):
    """Decorator to monitor function performance"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            name = metric_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                await monitoring_system.metrics_collector.record_timer(
                    f"{name}_duration",
                    time.time() - start_time
                )
                await monitoring_system.metrics_collector.increment_counter(
                    f"{name}_success"
                )
                return result
            except Exception as e:
                await monitoring_system.metrics_collector.record_timer(
                    f"{name}_duration",
                    time.time() - start_time
                )
                await monitoring_system.metrics_collector.increment_counter(
                    f"{name}_error"
                )
                await monitoring_system.error_handler.capture_exception(e, {
                    "function": name,
                    "args": str(args)[:100],
                    "kwargs": str(kwargs)[:100]
                })
                raise
        
        return wrapper
    return decorator


def track_errors(severity: AlertSeverity = AlertSeverity.MEDIUM):
    """Decorator to automatically track function errors"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                await monitoring_system.error_handler.capture_exception(e, {
                    "function": f"{func.__module__}.{func.__name__}",
                    "args": str(args)[:100],
                    "kwargs": str(kwargs)[:100]
                }, severity)
                raise
        
        return wrapper
    return decorator
