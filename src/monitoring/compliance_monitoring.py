"""
Compliance Monitoring and Alerting System

This module provides comprehensive monitoring for compliance operations including:
- Real-time metrics collection
- Health checks and status monitoring
- Alert generation and notification
- Performance monitoring
- Compliance rule violations detection
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import prometheus_client as prometheus
from prometheus_client import CollectorRegistry, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status"""
    FIRING = "firing"
    RESOLVED = "resolved"
    SILENCED = "silenced"


class MetricType(Enum):
    """Metric types"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class ComplianceMetric:
    """Compliance metric definition"""
    name: str
    type: MetricType
    description: str
    labels: List[str]
    value: Union[int, float]
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ComplianceAlert:
    """Compliance alert definition"""
    alert_id: str
    name: str
    description: str
    severity: AlertSeverity
    status: AlertStatus
    metric_name: str
    threshold: float
    current_value: float
    labels: Dict[str, str]
    timestamp: datetime
    resolved_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class HealthCheck:
    """Health check definition"""
    name: str
    status: str
    message: str
    timestamp: datetime
    duration_ms: float
    metadata: Optional[Dict[str, Any]] = None


class ComplianceMonitoringEngine:
    """Compliance monitoring and alerting engine"""

    def __init__(self):
        self.metrics_registry = CollectorRegistry()
        self.metrics = {}
        self.alerts = {}
        self.health_checks = {}
        self.alert_webhook_url = None
        self.metrics_enabled = True
        self.alerting_enabled = True
        
        # Initialize Prometheus metrics
        self._setup_prometheus_metrics()
        
        # Alert rules
        self.alert_rules = []
        self._setup_default_alert_rules()

    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics collection"""
        def _get_or_create(metric_cls, name, *args, **kwargs):
            """Get existing metric or create new one, avoiding duplicate registration."""
            try:
                return metric_cls(name, *args, **kwargs)
            except ValueError:
                return prometheus.REGISTRY._names_to_collectors.get(name)

        # Compliance operation metrics
        self.metrics['regulatory_reports_total'] = _get_or_create(
            prometheus.Counter,
            'compliance_regulatory_reports_total',
            'Total number of regulatory reports',
            ['jurisdiction', 'report_type', 'status']
        )
        
        self.metrics['cases_total'] = _get_or_create(
            prometheus.Counter,
            'compliance_cases_total',
            'Total number of compliance cases',
            ['case_type', 'status', 'priority']
        )
        
        self.metrics['risk_assessments_total'] = _get_or_create(
            prometheus.Counter,
            'compliance_risk_assessments_total',
            'Total number of risk assessments',
            ['entity_type', 'risk_level', 'trigger_type']
        )
        
        self.metrics['audit_events_total'] = _get_or_create(
            prometheus.Counter,
            'compliance_audit_events_total',
            'Total number of audit events',
            ['event_type', 'severity', 'user_id']
        )
        
        # Performance metrics
        self.metrics['operation_duration'] = _get_or_create(
            prometheus.Histogram,
            'compliance_operation_duration_seconds',
            'Duration of compliance operations',
            ['operation_type'],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0]
        )
        
        self.metrics['active_cases'] = _get_or_create(
            prometheus.Gauge,
            'compliance_active_cases',
            'Number of active compliance cases',
            ['case_type', 'priority']
        )
        
        self.metrics['pending_deadlines'] = _get_or_create(
            prometheus.Gauge,
            'compliance_pending_deadlines',
            'Number of pending regulatory deadlines',
            ['jurisdiction', 'hours_until']
        )
        
        # Error metrics
        self.metrics['errors_total'] = _get_or_create(
            prometheus.Counter,
            'compliance_errors_total',
            'Total number of compliance errors',
            ['error_type', 'component', 'severity']
        )
        
        # Cache metrics
        self.metrics['cache_hits'] = _get_or_create(
            prometheus.Counter,
            'compliance_cache_hits_total',
            'Total number of cache hits',
            ['cache_type']
        )
        
        self.metrics['cache_misses'] = _get_or_create(
            prometheus.Counter,
            'compliance_cache_misses_total',
            'Total number of cache misses',
            ['cache_type']
        )

    def _setup_default_alert_rules(self):
        """Setup default alerting rules"""
        self.alert_rules = [
            {
                'name': 'High Risk Assessment Volume',
                'description': 'High number of risk assessments detected',
                'metric': 'compliance_risk_assessments_total',
                'threshold': 100,
                'severity': AlertSeverity.HIGH,
                'window': '5m',
                'comparison': 'greater_than'
            },
            {
                'name': 'Critical Cases Pending',
                'description': 'Critical priority cases not resolved',
                'metric': 'compliance_active_cases',
                'threshold': 10,
                'severity': AlertSeverity.CRITICAL,
                'window': '1m',
                'comparison': 'greater_than',
                'labels': {'priority': 'critical'}
            },
            {
                'name': 'Regulatory Deadlines Approaching',
                'description': 'Regulatory deadlines within 24 hours',
                'metric': 'compliance_pending_deadlines',
                'threshold': 5,
                'severity': AlertSeverity.HIGH,
                'window': '1m',
                'comparison': 'greater_than',
                'labels': {'hours_until': '24'}
            },
            {
                'name': 'High Error Rate',
                'description': 'High error rate in compliance operations',
                'metric': 'compliance_errors_total',
                'threshold': 10,
                'severity': AlertSeverity.MEDIUM,
                'window': '5m',
                'comparison': 'rate'
            },
            {
                'name': 'Cache Hit Rate Low',
                'description': 'Cache hit rate below threshold',
                'metric': 'compliance_cache_hits_total',
                'threshold': 0.8,
                'severity': AlertSeverity.LOW,
                'window': '5m',
                'comparison': 'ratio'
            }
        ]

    async def record_metric(self, metric: ComplianceMetric) -> bool:
        """Record a compliance metric"""
        try:
            if not self.metrics_enabled:
                return True
            
            # Update Prometheus metric
            prometheus_metric = self.metrics.get(metric.name)
            if prometheus_metric:
                if metric.type == MetricType.COUNTER:
                    prometheus_metric.labels(**metric.labels).inc(metric.value)
                elif metric.type == MetricType.GAUGE:
                    prometheus_metric.labels(**metric.labels).set(metric.value)
                elif metric.type == MetricType.HISTOGRAM:
                    prometheus_metric.labels(**metric.labels).observe(metric.value)
            
            # Store in internal metrics
            self.metrics[metric.name] = metric
            
            # Check alert rules
            await self._check_alert_rules(metric)
            
            logger.debug(f"Recorded metric: {metric.name} = {metric.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record metric {metric.name}: {e}")
            return False

    async def create_alert(self, alert: ComplianceAlert) -> bool:
        """Create a compliance alert"""
        try:
            if not self.alerting_enabled:
                return True
            
            self.alerts[alert.alert_id] = alert
            
            # Send alert notification
            await self._send_alert_notification(alert)
            
            # Store alert in metrics
            alert_metric = self.metrics.get('compliance_alerts_total')
            if alert_metric:
                alert_metric.labels(
                    severity=alert.severity.value,
                    status=alert.status.value
                ).inc()
            
            logger.warning(f"Alert created: {alert.name} - {alert.description}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create alert {alert.alert_id}: {e}")
            return False

    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve a compliance alert"""
        try:
            alert = self.alerts.get(alert_id)
            if not alert:
                logger.warning(f"Alert not found: {alert_id}")
                return False
            
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now(timezone.utc)
            
            # Send resolution notification
            await self._send_alert_notification(alert)
            
            logger.info(f"Alert resolved: {alert.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve alert {alert_id}: {e}")
            return False

    async def perform_health_check(self, check_name: str, check_func) -> HealthCheck:
        """Perform a health check"""
        start_time = datetime.now(timezone.utc)
        
        try:
            result = await check_func()
            duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            health_check = HealthCheck(
                name=check_name,
                status="healthy" if result else "unhealthy",
                message="Health check passed" if result else "Health check failed",
                timestamp=start_time,
                duration_ms=duration
            )
            
            self.health_checks[check_name] = health_check
            return health_check
            
        except Exception as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            health_check = HealthCheck(
                name=check_name,
                status="error",
                message=str(e),
                timestamp=start_time,
                duration_ms=duration
            )
            
            self.health_checks[check_name] = health_check
            logger.error(f"Health check {check_name} failed: {e}")
            return health_check

    async def _check_alert_rules(self, metric: ComplianceMetric):
        """Check alert rules against metric"""
        for rule in self.alert_rules:
            if rule['metric'] == metric.name:
                # Check if alert should be triggered
                should_alert = await self._evaluate_alert_rule(rule, metric)
                
                if should_alert:
                    alert_id = f"{rule['name']}_{metric.name}_{int(datetime.now(timezone.utc).timestamp())}"
                    
                    alert = ComplianceAlert(
                        alert_id=alert_id,
                        name=rule['name'],
                        description=rule['description'],
                        severity=rule['severity'],
                        status=AlertStatus.FIRING,
                        metric_name=metric.name,
                        threshold=rule['threshold'],
                        current_value=metric.value,
                        labels=rule.get('labels', {}),
                        timestamp=datetime.now(timezone.utc)
                    )
                    
                    await self.create_alert(alert)

    async def _evaluate_alert_rule(self, rule: Dict[str, Any], metric: ComplianceMetric) -> bool:
        """Evaluate if alert rule should trigger"""
        threshold = rule['threshold']
        comparison = rule['comparison']
        
        if comparison == 'greater_than':
            return metric.value > threshold
        elif comparison == 'less_than':
            return metric.value < threshold
        elif comparison == 'equal':
            return metric.value == threshold
        elif comparison == 'rate':
            # For rate-based alerts, check rate over time window
            return await self._check_rate_threshold(rule, metric)
        elif comparison == 'ratio':
            # For ratio-based alerts, check cache hit rate
            return await self._check_ratio_threshold(rule, metric)
        
        return False

    async def _check_rate_threshold(self, rule: Dict[str, Any], metric: ComplianceMetric) -> bool:
        """Check rate-based threshold"""
        try:
            # Get metric value over time window (simplified)
            # In production, this would query time-series database
            window_seconds = self._parse_time_window(rule.get('window', '5m'))
            
            # For now, use current value as rate (simplified)
            rate = metric.value / window_seconds if window_seconds > 0 else 0
            
            return rate > rule['threshold']
            
        except Exception as e:
            logger.error(f"Failed to check rate threshold: {e}")
            return False

    async def _check_ratio_threshold(self, rule: Dict[str, Any], metric: ComplianceMetric) -> bool:
        """Check ratio-based threshold (e.g., cache hit rate)"""
        try:
            if 'cache_hits' in metric.name:
                hits_metric = self.metrics.get('compliance_cache_hits_total')
                misses_metric = self.metrics.get('compliance_cache_misses_total')
                
                if hits_metric and misses_metric:
                    hits = hits_metric._value._value.get()
                    misses = misses_metric._value._value.get()
                    
                    if hits + misses > 0:
                        hit_rate = hits / (hits + misses)
                        return hit_rate < rule['threshold']
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check ratio threshold: {e}")
            return False

    def _parse_time_window(self, window_str: str) -> int:
        """Parse time window string to seconds"""
        if window_str.endswith('s'):
            return int(window_str[:-1])
        elif window_str.endswith('m'):
            return int(window_str[:-1]) * 60
        elif window_str.endswith('h'):
            return int(window_str[:-1]) * 3600
        elif window_str.endswith('d'):
            return int(window_str[:-1]) * 86400
        else:
            return 300  # Default 5 minutes

    async def _send_alert_notification(self, alert: ComplianceAlert):
        """Send alert notification via webhook"""
        if not self.alert_webhook_url:
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    'alert_id': alert.alert_id,
                    'name': alert.name,
                    'description': alert.description,
                    'severity': alert.severity.value,
                    'status': alert.status.value,
                    'metric_name': alert.metric_name,
                    'threshold': alert.threshold,
                    'current_value': alert.current_value,
                    'labels': alert.labels,
                    'timestamp': alert.timestamp.isoformat(),
                    'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                    'metadata': alert.metadata or {}
                }
                
                async with session.post(
                    self.alert_webhook_url,
                    json=payload,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        logger.info(f"Alert notification sent: {alert.alert_id}")
                    else:
                        logger.warning(f"Failed to send alert notification: {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to send alert notification: {e}")

    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        try:
            summary = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'metrics_count': len(self.metrics),
                'alerts_count': len(self.alerts),
                'active_alerts': len([a for a in self.alerts.values() if a.status == AlertStatus.FIRING]),
                'health_checks': len(self.health_checks),
                'healthy_services': len([h for h in self.health_checks.values() if h.status == 'healthy']),
                'prometheus_metrics': {}
            }
            
            # Get Prometheus metrics
            for name, metric in self.metrics.items():
                if hasattr(metric, '_value'):
                    summary['prometheus_metrics'][name] = {
                        'type': metric._type._name,
                        'value': metric._value._value,
                        'labels': dict(metric._value._labels)
                    }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {'error': str(e)}

    async def get_alerts(self, severity: Optional[AlertSeverity] = None, status: Optional[AlertStatus] = None) -> List[ComplianceAlert]:
        """Get alerts with optional filtering"""
        alerts = list(self.alerts.values())
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if status:
            alerts = [a for a in alerts if a.status == status]
        
        # Sort by timestamp (newest first)
        alerts.sort(key=lambda a: a.timestamp, reverse=True)
        
        return alerts

    async def get_health_checks(self) -> List[HealthCheck]:
        """Get all health checks"""
        return list(self.health_checks.values())

    async def get_prometheus_metrics(self) -> str:
        """Get Prometheus metrics in text format"""
        try:
            from prometheus_client import generate_latest
            return generate_latest(self.metrics_registry)
        except Exception as e:
            logger.error(f"Failed to get Prometheus metrics: {e}")
            return ""

    def set_alert_webhook(self, webhook_url: str):
        """Set alert webhook URL"""
        self.alert_webhook_url = webhook_url
        logger.info(f"Alert webhook URL set: {webhook_url}")

    def enable_metrics(self, enabled: bool = True):
        """Enable or disable metrics collection"""
        self.metrics_enabled = enabled
        logger.info(f"Metrics collection {'enabled' if enabled else 'disabled'}")

    def enable_alerting(self, enabled: bool = True):
        """Enable or disable alerting"""
        self.alerting_enabled = enabled
        logger.info(f"Alerting {'enabled' if enabled else 'disabled'}")

    async def start_monitoring_loop(self, interval: int = 60):
        """Start continuous monitoring loop"""
        logger.info(f"Starting compliance monitoring loop (interval: {interval}s)")
        
        while True:
            try:
                # Perform health checks
                await self._perform_scheduled_health_checks()
                
                # Check alert rules
                await self._check_all_alert_rules()
                
                # Clean up old data
                await self._cleanup_old_data()
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval)

    async def _perform_scheduled_health_checks(self):
        """Perform scheduled health checks"""
        health_checks = [
            ('database_connectivity', self._check_database_connectivity),
            ('cache_connectivity', self._check_cache_connectivity),
            ('api_responsiveness', self._check_api_responsiveness),
            ('compliance_engine_status', self._check_compliance_engine_status)
        ]
        
        for check_name, check_func in health_checks:
            await self.perform_health_check(check_name, check_func)

    async def _check_database_connectivity(self) -> bool:
        """Check database connectivity"""
        try:
            # This would check Neo4j and PostgreSQL connectivity
            # Implementation depends on your database client setup
            return True
        except Exception:
            return False

    async def _check_cache_connectivity(self) -> bool:
        """Check cache connectivity"""
        try:
            # This would check Redis connectivity
            # Implementation depends on your Redis client setup
            return True
        except Exception:
            return False

    async def _check_api_responsiveness(self) -> bool:
        """Check API responsiveness"""
        try:
            # This would check if API endpoints are responding
            return True
        except Exception:
            return False

    async def _check_compliance_engine_status(self) -> bool:
        """Check compliance engine status"""
        try:
            # This would check if compliance engines are running
            return True
        except Exception:
            return False

    async def _check_all_alert_rules(self):
        """Check all alert rules"""
        # This would evaluate all alert rules against current metrics
        # Implementation depends on your metrics storage
        pass

    async def _cleanup_old_data(self):
        """Clean up old monitoring data"""
        try:
            # Clean up old alerts (older than 7 days)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
            old_alerts = [
                alert_id for alert_id, alert in self.alerts.items()
                if alert.timestamp < cutoff_date and alert.status == AlertStatus.RESOLVED
            ]
            
            for alert_id in old_alerts:
                del self.alerts[alert_id]
            
            if old_alerts:
                logger.info(f"Cleaned up {len(old_alerts)} old alerts")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")


# Global monitoring instance
compliance_monitor = ComplianceMonitoringEngine()
