"""
Jackdaw Sentry - Competitive Assessment Webhooks
Webhook handlers for real-time notifications and integrations
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from dataclasses import asdict
import aiohttp
import aiofiles
from pathlib import Path

logger = logging.getLogger(__name__)

class CompetitiveWebhookManager:
    """Manages webhooks for competitive assessment notifications"""
    
    def __init__(self):
        self.webhook_configs = {}
        self.active_sessions = {}
        self.notification_queue = asyncio.Queue()
        self.webhook_processor_task = None
        
    async def initialize(self):
        """Initialize webhook manager"""
        # Start webhook processor
        self.webhook_processor_task = asyncio.create_task(self.process_webhooks())
        logger.info("Webhook manager initialized")
    
    async def shutdown(self):
        """Shutdown webhook manager"""
        if self.webhook_processor_task:
            self.webhook_processor_task.cancel()
            try:
                await self.webhook_processor_task
            except asyncio.CancelledError:
                pass
        logger.info("Webhook manager shutdown")
    
    def register_webhook(self, webhook_id: str, config: Dict[str, Any]) -> None:
        """Register a webhook configuration"""
        self.webhook_configs[webhook_id] = config
        logger.info(f"Registered webhook: {webhook_id}")
    
    def unregister_webhook(self, webhook_id: str) -> None:
        """Unregister a webhook"""
        if webhook_id in self.webhook_configs:
            del self.webhook_configs[webhook_id]
            logger.info(f"Unregistered webhook: {webhook_id}")
    
    async def send_notification(self, event_type: str, data: Dict[str, Any]) -> None:
        """Send notification to all registered webhooks"""
        notification = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        
        await self.notification_queue.put(notification)
        logger.info(f"Queued notification: {event_type}")
    
    async def process_webhooks(self) -> None:
        """Process webhook notifications"""
        while True:
            try:
                notification = await self.notification_queue.get()
                await self.deliver_webhooks(notification)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing webhooks: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def deliver_webhooks(self, notification: Dict[str, Any]) -> None:
        """Deliver notification to all registered webhooks"""
        tasks = []
        
        for webhook_id, config in self.webhook_configs.items():
            if self.should_deliver_webhook(webhook_id, config, notification):
                task = asyncio.create_task(
                    self.deliver_single_webhook(webhook_id, config, notification)
                )
                tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def should_deliver_webhook(self, webhook_id: str, config: Dict[str, Any], notification: Dict[str, Any]) -> bool:
        """Check if webhook should receive this notification"""
        # Check event type filters
        event_filters = config.get("event_filters", [])
        if event_filters and notification["event_type"] not in event_filters:
            return False
        
        # Check severity filters
        severity_filters = config.get("severity_filters", [])
        if severity_filters:
            severity = notification["data"].get("severity", "info")
            if severity not in severity_filters:
                return False
        
        # Check rate limiting
        rate_limit = config.get("rate_limit", 0)
        if rate_limit > 0:
            last_sent = self.active_sessions.get(webhook_id, {}).get("last_sent", 0)
            time_diff = datetime.now(timezone.utc).timestamp() - last_sent
            if time_diff < rate_limit:
                return False
        
        return True
    
    async def deliver_single_webhook(self, webhook_id: str, config: Dict[str, Any], notification: Dict[str, Any]) -> None:
        """Deliver notification to a single webhook"""
        try:
            url = config["url"]
            method = config.get("method", "POST")
            headers = config.get("headers", {})
            payload = self.format_webhook_payload(config, notification)
            
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Webhook delivered successfully: {webhook_id}")
                        # Update rate limiting
                        self.active_sessions[webhook_id] = {
                            "last_sent": datetime.now(timezone.utc).timestamp()
                        }
                    else:
                        logger.error(f"Webhook delivery failed: {webhook_id}, status: {response.status}")
        
        except Exception as e:
            logger.error(f"Error delivering webhook {webhook_id}: {e}")
    
    def format_webhook_payload(self, config: Dict[str, Any], notification: Dict[str, Any]) -> Dict[str, Any]:
        """Format webhook payload based on configuration"""
        payload_format = config.get("payload_format", "default")
        
        if payload_format == "slack":
            return self.format_slack_payload(notification)
        elif payload_format == "teams":
            return self.format_teams_payload(notification)
        elif payload_format == "discord":
            return self.format_discord_payload(notification)
        elif payload_format == "email":
            return self.format_email_payload(notification)
        else:
            return notification
    
    def format_slack_payload(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Format payload for Slack webhook"""
        event_type = notification["event_type"]
        data = notification["data"]
        
        # Determine color based on severity
        severity_colors = {
            "critical": "danger",
            "high": "danger", 
            "medium": "warning",
            "low": "good",
            "info": "good"
        }
        
        color = severity_colors.get(data.get("severity", "info"), "good")
        
        return {
            "text": f"Jackdaw Sentry Competitive Alert: {event_type}",
            "attachments": [
                {
                    "color": color,
                    "fields": [
                        {
                            "title": "Event Type",
                            "value": event_type,
                            "short": True
                        },
                        {
                            "title": "Severity",
                            "value": data.get("severity", "info").title(),
                            "short": True
                        },
                        {
                            "title": "Message",
                            "value": data.get("message", "No message provided"),
                            "short": False
                        }
                    ],
                    "footer": "Jackdaw Sentry",
                    "ts": datetime.now(timezone.utc).timestamp()
                }
            ]
        }
    
    def format_teams_payload(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Format payload for Microsoft Teams webhook"""
        event_type = notification["event_type"]
        data = notification["data"]
        
        # Determine theme color based on severity
        severity_colors = {
            "critical": "FF0000",
            "high": "FF0000",
            "medium": "FFA500", 
            "low": "00FF00",
            "info": "00FF00"
        }
        
        theme_color = severity_colors.get(data.get("severity", "info"), "00FF00")
        
        return {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": theme_color,
            "summary": f"Jackdaw Sentry Competitive Alert: {event_type}",
            "sections": [
                {
                    "activityTitle": f"Competitive Assessment Alert",
                    "activitySubtitle": event_type.title(),
                    "facts": [
                        {
                            "name": "Severity",
                            "value": data.get("severity", "info").title()
                        },
                        {
                            "name": "Message", 
                            "value": data.get("message", "No message provided")
                        },
                        {
                            "name": "Timestamp",
                            "value": notification["timestamp"]
                        }
                    ],
                    "markdown": True
                }
            ]
        }
    
    def format_discord_payload(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Format payload for Discord webhook"""
        event_type = notification["event_type"]
        data = notification["data"]
        
        # Determine color based on severity
        severity_colors = {
            "critical": 0xFF0000,
            "high": 0xFF0000,
            "medium": 0xFFA500,
            "low": 0x00FF00,
            "info": 0x00FF00
        }
        
        color = severity_colors.get(data.get("severity", "info"), 0x00FF00)
        
        return {
            "embeds": [
                {
                    "title": f"Jackdaw Sentry Competitive Alert",
                    "description": f"**Event:** {event_type}\n**Message:** {data.get('message', 'No message provided')}",
                    "color": color,
                    "timestamp": notification["timestamp"],
                    "footer": {
                        "text": "Jackdaw Sentry Competitive Assessment"
                    }
                }
            ]
        }
    
    def format_email_payload(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Format payload for email webhook"""
        event_type = notification["event_type"]
        data = notification["data"]
        
        return {
            "to": notification["data"].get("recipients", []),
            "subject": f"Jackdaw Sentry Competitive Alert: {event_type}",
            "body": f"""
                <h2>Competitive Assessment Alert</h2>
                <p><strong>Event Type:</strong> {event_type}</p>
                <p><strong>Severity:</strong> {data.get('severity', 'info').title()}</p>
                <p><strong>Message:</strong> {data.get('message', 'No message provided')}</p>
                <p><strong>Timestamp:</strong> {notification['timestamp']}</p>
                
                {self.generate_email_details(data)}
                
                <hr>
                <p><em>This alert was generated by Jackdaw Sentry Competitive Assessment System</em></p>
            """,
            "html": True
        }
    
    def generate_email_details(self, data: Dict[str, Any]) -> str:
        """Generate detailed email content based on data type"""
        if "feature" in data:
            return f"""
                <h3>Feature Details</h3>
                <p><strong>Feature:</strong> {data['feature']}</p>
                <p><strong>Current Value:</strong> {data.get('current_value', 'N/A')}</p>
                <p><strong>Expected Range:</strong> {data.get('expected_range', 'N/A')}</p>
            """
        
        elif "competitor" in data:
            return f"""
                <h3>Competitor Analysis</h3>
                <p><strong>Competitor:</strong> {data['competitor']}</p>
                <p><strong>Impact:</strong> {data.get('impact', 'N/A')}</p>
                <p><strong>Recommendation:</strong> {data.get('recommendation', 'N/A')}</p>
            """
        
        elif "parity" in data:
            return f"""
                <h3>Performance Metrics</h3>
                <p><strong>Overall Parity:</strong> {data['parity']}%</p>
                <p><strong>Market Position:</strong> {data.get('market_position', 'N/A')}</p>
                <p><strong>Trend:</strong> {data.get('trend', 'N/A')}</p>
            """
        
        return ""

class CompetitiveAlertManager:
    """Manages competitive assessment alerts and notifications"""
    
    def __init__(self, webhook_manager: CompetitiveWebhookManager):
        self.webhook_manager = webhook_manager
        self.alert_rules = {}
        self.alert_history = []
        
    def register_alert_rule(self, rule_id: str, rule_config: Dict[str, Any]) -> None:
        """Register an alert rule"""
        self.alert_rules[rule_id] = rule_config
        logger.info(f"Registered alert rule: {rule_id}")
    
    async def check_alert_conditions(self, metrics_data: Dict[str, Any]) -> None:
        """Check alert conditions and trigger notifications"""
        for rule_id, rule in self.alert_rules.items():
            if self.evaluate_alert_rule(rule, metrics_data):
                await self.trigger_alert(rule_id, rule, metrics_data)
    
    def evaluate_alert_rule(self, rule: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Evaluate if alert rule conditions are met"""
        conditions = rule.get("conditions", [])
        
        for condition in conditions:
            field = condition["field"]
            operator = condition["operator"]
            threshold = condition["threshold"]
            
            value = self.get_nested_value(data, field)
            if value is None:
                continue
            
            if not self.evaluate_condition(value, operator, threshold):
                return False
        
        return True
    
    def get_nested_value(self, data: Dict[str, Any], field: str) -> Any:
        """Get nested value from data using dot notation"""
        keys = field.split(".")
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    def evaluate_condition(self, value: Any, operator: str, threshold: Any) -> bool:
        """Evaluate a single condition"""
        try:
            if operator == "gt":
                return float(value) > float(threshold)
            elif operator == "lt":
                return float(value) < float(threshold)
            elif operator == "eq":
                return value == threshold
            elif operator == "ne":
                return value != threshold
            elif operator == "gte":
                return float(value) >= float(threshold)
            elif operator == "lte":
                return float(value) <= float(threshold)
            elif operator == "contains":
                return threshold in str(value)
            elif operator == "not_contains":
                return threshold not in str(value)
            else:
                return False
        except (ValueError, TypeError):
            return False
    
    async def trigger_alert(self, rule_id: str, rule: Dict[str, Any], data: Dict[str, Any]) -> None:
        """Trigger an alert"""
        alert_data = {
            "rule_id": rule_id,
            "rule_name": rule.get("name", rule_id),
            "severity": rule.get("severity", "info"),
            "message": self.generate_alert_message(rule, data),
            "data": data
        }
        
        # Add to alert history
        self.alert_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rule_id": rule_id,
            "alert_data": alert_data
        })
        
        # Send webhook notification
        await self.webhook_manager.send_notification("alert_triggered", alert_data)
        
        logger.warning(f"Alert triggered: {rule_id} - {alert_data['message']}")
    
    def generate_alert_message(self, rule: Dict[str, Any], data: Dict[str, Any]) -> str:
        """Generate alert message"""
        template = rule.get("message_template", "Alert triggered for rule {rule_name}")
        
        # Simple template substitution
        message = template.format(
            rule_name=rule.get("name", "Unknown"),
            value=self.get_nested_value(data, rule.get("value_field", "value")),
            threshold=rule.get("conditions", [{}])[0].get("threshold", "N/A")
        )
        
        return message

# Global instances
webhook_manager = CompetitiveWebhookManager()
alert_manager = CompetitiveAlertManager(webhook_manager)

# Initialize default webhooks
async def initialize_default_webhooks():
    """Initialize default webhook configurations"""
    
    # Slack webhook
    webhook_manager.register_webhook("slack", {
        "url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
        "method": "POST",
        "payload_format": "slack",
        "event_filters": ["alert_triggered", "benchmark_completed", "anomaly_detected"],
        "severity_filters": ["high", "critical"],
        "rate_limit": 300  # 5 minutes
    })
    
    # Teams webhook
    webhook_manager.register_webhook("teams", {
        "url": "https://outlook.office.com/webhook/YOUR/TEAMS/WEBHOOK",
        "method": "POST", 
        "payload_format": "teams",
        "event_filters": ["alert_triggered", "benchmark_completed"],
        "severity_filters": ["medium", "high", "critical"],
        "rate_limit": 600  # 10 minutes
    })
    
    # Email webhook
    webhook_manager.register_webhook("email", {
        "url": "https://your-email-service.com/send",
        "method": "POST",
        "payload_format": "email",
        "event_filters": ["alert_triggered"],
        "severity_filters": ["high", "critical"],
        "rate_limit": 1800  # 30 minutes
    })

# Initialize default alert rules
def initialize_default_alert_rules():
    """Initialize default alert rules"""
    
    # Low competitive parity alert
    alert_manager.register_alert_rule("low_parity", {
        "name": "Low Competitive Parity",
        "severity": "high",
        "conditions": [
            {
                "field": "overall_parity",
                "operator": "lt",
                "threshold": 80
            }
        ],
        "message_template": "Competitive parity dropped to {value}% (threshold: {threshold}%)"
    })
    
    # Critical parity alert
    alert_manager.register_alert_rule("critical_parity", {
        "name": "Critical Competitive Parity",
        "severity": "critical",
        "conditions": [
            {
                "field": "overall_parity", 
                "operator": "lt",
                "threshold": 70
            }
        ],
        "message_template": "CRITICAL: Competitive parity dropped to {value}% (threshold: {threshold}%)"
    })
    
    # Anomaly detection alert
    alert_manager.register_alert_rule("anomaly_detected", {
        "name": "Performance Anomaly Detected",
        "severity": "medium",
        "conditions": [
            {
                "field": "anomaly_count",
                "operator": "gt", 
                "threshold": 0
            }
        ],
        "message_template": "Performance anomaly detected: {value} anomalies"
    })
    
    # High anomaly count alert
    alert_manager.register_alert_rule("high_anomaly_count", {
        "name": "High Anomaly Count",
        "severity": "high",
        "conditions": [
            {
                "field": "anomaly_count",
                "operator": "gt",
                "threshold": 5
            }
        ],
        "message_template": "High number of anomalies detected: {value} (threshold: {threshold})"
    })
    
    # Performance degradation alert
    alert_manager.register_alert_rule("performance_degradation", {
        "name": "Performance Degradation",
        "severity": "medium",
        "conditions": [
            {
                "field": "performance_trend",
                "operator": "lt",
                "threshold": -0.1
            }
        ],
        "message_template": "Performance degradation detected: trend {value}"
    })
    
    # Competitor advantage alert
    alert_manager.register_alert_rule("competitor_advantage", {
        "name": "Competitor Advantage Detected",
        "severity": "info",
        "conditions": [
            {
                "field": "competitor_advantage",
                "operator": "gt",
                "threshold": 20
            }
        ],
        "message_template": "Competitor advantage detected: {value}% above market"
    })

# Initialize on module import
async def startup():
    """Initialize webhook and alert systems"""
    await webhook_manager.initialize()
    await initialize_default_webhooks()
    initialize_default_alert_rules()
    logger.info("Competitive webhook and alert systems initialized")

async def shutdown():
    """Shutdown webhook and alert systems"""
    await webhook_manager.shutdown()
    logger.info("Competitive webhook and alert systems shutdown")
