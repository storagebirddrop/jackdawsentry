#!/usr/bin/env python3
"""
Jackdaw Sentry - Production Health Check Script
Comprehensive health monitoring for production deployment
"""

import asyncio
import sys
import json
import requests
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProductionHealthChecker:
    """Production health monitoring system"""
    
    def __init__(self):
        self.services = {
            'api': {
                'url': 'http://localhost:8000/health',
                'timeout': 10,
                'expected_status': 200
            },
            'competitive-dashboard': {
                'url': 'http://localhost:8080/health',
                'timeout': 10,
                'expected_status': 200
            },
            'grafana': {
                'url': 'http://localhost:3000/api/health',
                'timeout': 10,
                'expected_status': 200
            },
            'prometheus': {
                'url': 'http://localhost:9090/-/healthy',
                'timeout': 10,
                'expected_status': 200
            }
        }
        
        self.database_checks = {
            'postgres': {
                'command': ['docker-compose', '-f', 'docker/production-compose.yml', 'exec', '-T', 'postgres', 'pg_isready', '-U', 'jackdaw', '-d', 'jackdaw'],
                'timeout': 10
            },
            'redis': {
                'command': ['docker-compose', '-f', 'docker/production-compose.yml', 'exec', '-T', 'redis', 'redis-cli', 'ping'],
                'timeout': 10
            }
        }
    
    async def run_comprehensive_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check"""
        logger.info("Running comprehensive production health check...")
        
        health_report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_status': 'healthy',
            'services': {},
            'databases': {},
            'system_resources': {},
            'alerts': [],
            'performance_metrics': {}
        }
        
        # Check HTTP services
        await self.check_http_services(health_report)
        
        # Check databases
        await self.check_databases(health_report)
        
        # Check system resources
        await self.check_system_resources(health_report)
        
        # Check performance metrics
        await self.check_performance_metrics(health_report)
        
        # Determine overall status
        health_report['overall_status'] = self.determine_overall_status(health_report)
        
        return health_report
    
    async def check_http_services(self, health_report: Dict[str, Any]) -> None:
        """Check HTTP service health"""
        logger.info("Checking HTTP services...")
        
        for service_name, config in self.services.items():
            try:
                response = requests.get(
                    config['url'],
                    timeout=config['timeout']
                )
                
                service_health = {
                    'status': 'healthy' if response.status_code == config['expected_status'] else 'unhealthy',
                    'response_time': response.elapsed.total_seconds(),
                    'status_code': response.status_code,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                # Check response time
                if service_health['response_time'] > 5:
                    service_health['performance_warning'] = 'Slow response time'
                
                health_report['services'][service_name] = service_health
                
            except requests.exceptions.Timeout:
                health_report['services'][service_name] = {
                    'status': 'timeout',
                    'error': 'Request timeout',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                health_report['alerts'].append(f"Service {service_name} timeout")
                
            except requests.exceptions.ConnectionError:
                health_report['services'][service_name] = {
                    'status': 'connection_error',
                    'error': 'Connection refused',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                health_report['alerts'].append(f"Service {service_name} connection error")
                
            except Exception as e:
                health_report['services'][service_name] = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                health_report['alerts'].append(f"Service {service_name} error: {e}")
    
    async def check_databases(self, health_report: Dict[str, Any]) -> None:
        """Check database health"""
        logger.info("Checking databases...")
        
        for db_name, config in self.database_checks.items():
            try:
                result = subprocess.run(
                    config['command'],
                    capture_output=True,
                    text=True,
                    timeout=config['timeout']
                )
                
                if result.returncode == 0:
                    health_report['databases'][db_name] = {
                        'status': 'healthy',
                        'response': result.stdout.strip(),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                else:
                    health_report['databases'][db_name] = {
                        'status': 'unhealthy',
                        'error': result.stderr.strip(),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    health_report['alerts'].append(f"Database {db_name} unhealthy")
                    
            except subprocess.TimeoutExpired:
                health_report['databases'][db_name] = {
                    'status': 'timeout',
                    'error': 'Command timeout',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                health_report['alerts'].append(f"Database {db_name} timeout")
                
            except Exception as e:
                health_report['databases'][db_name] = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                health_report['alerts'].append(f"Database {db_name} error: {e}")
    
    async def check_system_resources(self, health_report: Dict[str, Any]) -> None:
        """Check system resources"""
        logger.info("Checking system resources...")
        
        try:
            # Get Docker container stats
            result = subprocess.run(
                ['docker', 'stats', '--no-stream', '--format', 'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                container_stats = {}
                
                for line in lines:
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 4:
                            container_name = parts[0]
                            cpu_percent = float(parts[1].rstrip('%'))
                            mem_usage = parts[2]
                            mem_percent = float(parts[3].rstrip('%'))
                            
                            container_stats[container_name] = {
                                'cpu_percent': cpu_percent,
                                'memory_usage': mem_usage,
                                'memory_percent': mem_percent,
                                'timestamp': datetime.now(timezone.utc).isoformat()
                            }
                            
                            # Check for resource warnings
                            if cpu_percent > 80:
                                health_report['alerts'].append(f"High CPU usage on {container_name}: {cpu_percent}%")
                            
                            if mem_percent > 85:
                                health_report['alerts'].append(f"High memory usage on {container_name}: {mem_percent}%")
                
                health_report['system_resources']['containers'] = container_stats
            
            # Check disk space
            disk_result = subprocess.run(
                ['df', '-h', '/'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if disk_result.returncode == 0:
                lines = disk_result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    disk_info = lines[1].split()
                    if len(disk_info) >= 5:
                        used_percent = int(disk_info[4].rstrip('%'))
                        
                        health_report['system_resources']['disk'] = {
                            'total': disk_info[1],
                            'used': disk_info[2],
                            'available': disk_info[3],
                            'used_percent': used_percent,
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
                        
                        if used_percent > 90:
                            health_report['alerts'].append(f"High disk usage: {used_percent}%")
            
        except Exception as e:
            health_report['system_resources']['error'] = str(e)
            health_report['alerts'].append(f"System resource check failed: {e}")
    
    async def check_performance_metrics(self, health_report: Dict[str, Any]) -> None:
        """Check performance metrics"""
        logger.info("Checking performance metrics...")
        
        try:
            # Get competitive dashboard metrics
            if 'competitive-dashboard' in health_report['services'] and health_report['services']['competitive-dashboard']['status'] == 'healthy':
                try:
                    response = requests.get(
                        'http://localhost:8080/api/metrics',
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        metrics = response.json()
                        health_report['performance_metrics']['competitive'] = {
                            'parity': metrics.get('overall_parity', 0),
                            'market_position': metrics.get('market_position', 'Unknown'),
                            'active_alerts': metrics.get('active_alerts', 0),
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
                        
                        # Check for performance issues
                        if metrics.get('overall_parity', 0) < 80:
                            health_report['alerts'].append(f"Low competitive parity: {metrics.get('overall_parity', 0)}%")
                        
                        if metrics.get('active_alerts', 0) > 10:
                            health_report['alerts'].append(f"High number of active alerts: {metrics.get('active_alerts', 0)}")
                
                except Exception as e:
                    health_report['performance_metrics']['competitive'] = {
                        'error': str(e),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
            
            # Get API performance metrics
            if 'api' in health_report['services'] and health_report['services']['api']['status'] == 'healthy':
                try:
                    response = requests.get(
                        'http://localhost:8000/metrics',
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        # Parse Prometheus metrics
                        metrics_text = response.text
                        api_metrics = self.parse_prometheus_metrics(metrics_text)
                        
                        health_report['performance_metrics']['api'] = {
                            'metrics': api_metrics,
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
                
                except Exception as e:
                    health_report['performance_metrics']['api'] = {
                        'error': str(e),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
        
        except Exception as e:
            health_report['performance_metrics']['error'] = str(e)
            health_report['alerts'].append(f"Performance metrics check failed: {e}")
    
    def parse_prometheus_metrics(self, metrics_text: str) -> Dict[str, Any]:
        """Parse Prometheus metrics text"""
        metrics = {}
        
        for line in metrics_text.split('\n'):
            if line and not line.startswith('#'):
                parts = line.split()
                if len(parts) >= 2:
                    metric_name = parts[0]
                    metric_value = float(parts[1])
                    
                    # Extract key metrics
                    if 'http_requests_total' in metric_name:
                        metrics['total_requests'] = metric_value
                    elif 'http_request_duration_seconds' in metric_name:
                        metrics['avg_response_time'] = metric_value
                    elif 'process_cpu_seconds_total' in metric_name:
                        metrics['cpu_time'] = metric_value
                    elif 'process_resident_memory_bytes' in metric_name:
                        metrics['memory_bytes'] = metric_value
        
        return metrics
    
    def determine_overall_status(self, health_report: Dict[str, Any]) -> str:
        """Determine overall system status"""
        critical_services = ['api', 'competitive-dashboard']
        
        # Check if any critical service is down
        for service in critical_services:
            if service in health_report['services']:
                service_status = health_report['services'][service]['status']
                if service_status != 'healthy':
                    return 'critical'
        
        # Check if any database is down
        for db_name, db_status in health_report['databases'].items():
            if db_status['status'] != 'healthy':
                return 'critical'
        
        # Check for high alert count
        if len(health_report['alerts']) > 5:
            return 'degraded'
        
        # Check for resource issues
        if 'containers' in health_report['system_resources']:
            for container, stats in health_report['system_resources']['containers'].items():
                if stats['cpu_percent'] > 90 or stats['memory_percent'] > 95:
                    return 'degraded'
        
        # Check disk space
        if 'disk' in health_report['system_resources']:
            if health_report['system_resources']['disk']['used_percent'] > 85:
                return 'degraded'
        
        return 'healthy'
    
    async def send_alerts(self, health_report: Dict[str, Any]) -> None:
        """Send alerts for critical issues"""
        if health_report['overall_status'] == 'critical':
            # Send critical alert
            await self.send_slack_alert(health_report, "CRITICAL")
        elif len(health_report['alerts']) > 0:
            # Send warning alert
            await self.send_slack_alert(health_report, "WARNING")
    
    async def send_slack_alert(self, health_report: Dict[str, Any], severity: str) -> None:
        """Send Slack alert (placeholder implementation)"""
        logger.warning(f"Would send {severity} alert to Slack:")
        logger.warning(f"Overall Status: {health_report['overall_status']}")
        logger.warning(f"Alerts: {health_report['alerts']}")
        
        # In production, this would integrate with Slack webhook
        # webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        # payload = {
        #     "text": f"Jackdaw Sentry {severity} Alert",
        #     "attachments": [
        #         {
        #             "color": "danger" if severity == "CRITICAL" else "warning",
        #             "fields": [
        #             {"title": "Overall Status", "value": health_report['overall_status']},
        #             {"title": "Alerts", "value": "\n".join(health_report['alerts'])}
        #             ]
        #         }
        #     ]
        # }
        # requests.post(webhook_url, json=payload)

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Jackdaw Sentry Production Health Check")
    parser.add_argument('--output', help='Output file for health report')
    parser.add_argument('--alerts', action='store_true', help='Send alerts for issues')
    parser.add_argument('--json', action='store_true', help='Output JSON format')
    
    args = parser.parse_args()
    
    async def run_health_check():
        checker = ProductionHealthChecker()
        health_report = await checker.run_comprehensive_health_check()
        
        if args.alerts:
            await checker.send_alerts(health_report)
        
        if args.json:
            output = json.dumps(health_report, indent=2)
        else:
            output = format_health_report(health_report)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Health report saved to {args.output}")
        else:
            print(output)
        
        # Exit with appropriate code
        if health_report['overall_status'] == 'critical':
            sys.exit(2)
        elif health_report['overall_status'] == 'degraded':
            sys.exit(1)
        else:
            sys.exit(0)
    
    asyncio.run(run_health_check())

def format_health_report(health_report: Dict[str, Any]) -> str:
    """Format health report for console output"""
    output = []
    output.append("=" * 60)
    output.append("JACKDAW SENTRY - PRODUCTION HEALTH REPORT")
    output.append("=" * 60)
    output.append(f"Timestamp: {health_report['timestamp']}")
    output.append(f"Overall Status: {health_report['overall_status'].upper()}")
    output.append("")
    
    # Services
    output.append("SERVICES:")
    for service, status in health_report['services'].items():
        status_icon = "✅" if status['status'] == 'healthy' else "❌"
        output.append(f"  {status_icon} {service}: {status['status']}")
        if 'response_time' in status:
            output.append(f"    Response Time: {status['response_time']:.3f}s")
        if 'error' in status:
            output.append(f"    Error: {status['error']}")
    output.append("")
    
    # Databases
    output.append("DATABASES:")
    for db, status in health_report['databases'].items():
        status_icon = "✅" if status['status'] == 'healthy' else "❌"
        output.append(f"  {status_icon} {db}: {status['status']}")
        if 'error' in status:
            output.append(f"    Error: {status['error']}")
    output.append("")
    
    # System Resources
    if 'containers' in health_report['system_resources']:
        output.append("SYSTEM RESOURCES:")
        for container, stats in health_report['system_resources']['containers'].items():
            cpu_icon = "⚠️" if stats['cpu_percent'] > 80 else "✅"
            mem_icon = "⚠️" if stats['memory_percent'] > 85 else "✅"
            output.append(f"  {container}:")
            output.append(f"    {cpu_icon} CPU: {stats['cpu_percent']}%")
            output.append(f"    {mem_icon} Memory: {stats['memory_percent']}% ({stats['memory_usage']})")
        output.append("")
    
    # Alerts
    if health_report['alerts']:
        output.append("ALERTS:")
        for alert in health_report['alerts']:
            output.append(f"  ⚠️  {alert}")
        output.append("")
    
    # Performance Metrics
    if health_report['performance_metrics']:
        output.append("PERFORMANCE METRICS:")
        for category, metrics in health_report['performance_metrics'].items():
            output.append(f"  {category.title()}:")
            if 'error' in metrics:
                output.append(f"    Error: {metrics['error']}")
            else:
                for key, value in metrics.items():
                    if key != 'timestamp':
                        output.append(f"    {key}: {value}")
        output.append("")
    
    output.append("=" * 60)
    return "\n".join(output)

if __name__ == "__main__":
    main()
