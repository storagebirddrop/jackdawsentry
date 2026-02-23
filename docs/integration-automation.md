# Integration & Automation Guide

This guide covers the integration and automation capabilities of Jackdaw Sentry's Competitive Assessment framework.

## Overview

The integration and automation system provides:
- **REST API**: Comprehensive API for competitive assessment
- **Webhook Integration**: Real-time notifications and integrations
- **Automated Workflows**: Scheduled tasks and automated processes
- **Executive Reporting**: Automated report generation and distribution
- **Third-party Integrations**: Slack, Teams, Email, and custom integrations

## REST API

### Base URL
```
https://jackdaw-sentry.com/api/competitive
```

### Authentication
All API endpoints require JWT authentication:
```bash
# Get JWT token
curl -X POST "https://jackdaw-sentry.com/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'

# Use token in subsequent requests
curl -X GET "https://jackdaw-sentry.com/api/competitive/summary" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Key Endpoints

#### Competitive Summary
```bash
GET /api/competitive/summary
```
Returns overall competitive assessment summary including parity, market position, and key metrics.

#### Performance Metrics
```bash
GET /api/competitive/metrics?timeframe=24h
```
Get competitive metrics for specified timeframe (1h, 6h, 24h, 7d, 30d).

#### Competitive Insights
```bash
GET /api/competitive/insights?insight_type=opportunity
```
Get AI-powered competitive insights filtered by type (opportunity, threat, trend, prediction).

#### Competitor Analysis
```bash
GET /api/competitive/competitors
```
Comprehensive competitor analysis including market positioning and feature comparison.

#### Cost Analysis
```bash
GET /api/competitive/cost-analysis
```
Detailed cost analysis, ROI calculations, and pricing intelligence.

#### Performance Predictions
```bash
GET /api/competitive/predictions?metric=graph_expansion&horizon=24h
```
ML-powered performance predictions for specific metrics and time horizons.

#### Anomaly Detection
```bash
GET /api/competitive/anomalies?severity=high
```
Get detected performance anomalies filtered by severity.

#### Run Benchmark
```bash
POST /api/competitive/benchmark/run?benchmark_type=full
```
Trigger competitive benchmark execution (full, performance, security, feature, ux).

#### Generate Report
```bash
POST /api/competitive/reports/generate?report_type=executive
```
Generate competitive assessment reports (executive, technical, financial).

### API Response Format
```json
{
  "data": {...},
  "timestamp": "2024-01-01T00:00:00Z",
  "status": "success"
}
```

### Error Handling
```json
{
  "error": "ValidationError",
  "message": "Invalid parameters",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Webhook Integration

### Webhook Types

#### Slack Integration
```json
{
  "url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
  "method": "POST",
  "payload_format": "slack",
  "event_filters": ["alert_triggered", "benchmark_completed"],
  "severity_filters": ["high", "critical"],
  "rate_limit": 300
}
```

#### Microsoft Teams Integration
```json
{
  "url": "https://outlook.office.com/webhook/YOUR/TEAMS/WEBHOOK",
  "method": "POST",
  "payload_format": "teams",
  "event_filters": ["alert_triggered", "benchmark_completed"],
  "severity_filters": ["medium", "high", "critical"],
  "rate_limit": 600
}
```

#### Email Integration
```json
{
  "url": "https://your-email-service.com/send",
  "method": "POST",
  "payload_format": "email",
  "event_filters": ["alert_triggered"],
  "severity_filters": ["high", "critical"],
  "rate_limit": 1800
}
```

### Webhook Events

#### Alert Triggered
```json
{
  "event_type": "alert_triggered",
  "timestamp": "2024-01-01T00:00:00Z",
  "data": {
    "rule_id": "low_parity",
    "rule_name": "Low Competitive Parity",
    "severity": "high",
    "message": "Competitive parity dropped to 75% (threshold: 80%)",
    "feature": "overall_parity",
    "current_value": 75,
    "threshold": 80
  }
}
```

#### Benchmark Completed
```json
{
  "event_type": "benchmark_completed",
  "timestamp": "2024-01-01T00:00:00Z",
  "data": {
    "task_id": "benchmark_20240101_000000",
    "task_name": "Hourly Competitive Benchmark",
    "status": "success",
    "benchmark_type": "performance",
    "results": {...}
  }
}
```

#### Anomaly Detected
```json
{
  "event_type": "anomaly_detected",
  "timestamp": "2024-01-01T00:00:00Z",
  "data": {
    "anomaly_count": 3,
    "anomalies": [
      {
        "feature": "api_response",
        "severity": "medium",
        "description": "API response time 25% above expected",
        "recommendations": ["Check server load", "Optimize database queries"]
      }
    ]
  }
}
```

### Registering Webhooks

#### Programmatically
```python
from src.api.webhooks.competitive_webhooks import webhook_manager

# Register Slack webhook
webhook_manager.register_webhook("slack", {
    "url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
    "method": "POST",
    "payload_format": "slack",
    "event_filters": ["alert_triggered", "benchmark_completed"],
    "severity_filters": ["high", "critical"],
    "rate_limit": 300
})
```

#### Via API
```bash
curl -X POST "https://jackdaw-sentry.com/api/competitive/webhooks" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_id": "slack",
    "url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
    "payload_format": "slack",
    "event_filters": ["alert_triggered"]
  }'
```

## Automated Workflows

### Workflow Definition
```json
{
  "name": "Daily Competitive Assessment",
  "description": "Comprehensive daily competitive assessment and reporting",
  "steps": [
    {
      "name": "Run Performance Benchmarks",
      "type": "benchmark",
      "benchmark_type": "performance",
      "continue_on_failure": false
    },
    {
      "name": "Advanced Analytics",
      "type": "analysis",
      "analysis_type": "comprehensive",
      "continue_on_failure": true
    },
    {
      "name": "Generate Executive Report",
      "type": "report",
      "report_type": "executive",
      "format": "pdf",
      "recipients": ["executives@company.com"],
      "continue_on_failure": true
    },
    {
      "name": "Send Notifications",
      "type": "notification",
      "notification_type": "webhook",
      "message": "Daily competitive assessment completed",
      "recipients": ["slack", "email"],
      "continue_on_failure": true
    }
  ]
}
```

### Workflow Types

#### Benchmark Steps
```json
{
  "type": "benchmark",
  "benchmark_type": "full|performance|security|feature|ux"
}
```

#### Analysis Steps
```json
{
  "type": "analysis",
  "analysis_type": "comprehensive|advanced_analytics|competitor_analysis|cost_analysis"
}
```

#### Report Steps
```json
{
  "type": "report",
  "report_type": "executive|technical|financial|competitive",
  "format": "pdf|html",
  "recipients": ["email@company.com"]
}
```

#### Notification Steps
```json
{
  "type": "notification",
  "notification_type": "webhook|email|slack",
  "message": "Notification message",
  "recipients": ["slack", "email"]
}
```

#### Integration Steps
```json
{
  "type": "integration",
  "integration_type": "api|database|file",
  "target_url": "https://api.example.com/webhook",
  "data": {"key": "value"}
}
```

### Running Workflows

#### CLI
```bash
# List available workflows
python scripts/automated_workflows.py --list

# Run specific workflow
python scripts/automated_workflows.py --workflow daily_assessment

# Run workflow with parameters
python scripts/automated_workflows.py --workflow weekly_intelligence --params '{"benchmark_type": "full"}'

# Check workflow status
python scripts/automated_workflows.py --status all

# Cancel running workflow
python scripts/automated_workflows.py --cancel workflow_id
```

#### Programmatically
```python
from scripts.automated_workflows import get_workflow_manager

manager = await get_workflow_manager()

# Start workflow
success = await manager.start_workflow("daily_assessment", {
    "benchmark_type": "performance"
})

# Check status
status = await manager.get_workflow_status("daily_assessment")
```

#### Via API
```bash
curl -X POST "https://jackdaw-sentry.com/api/competitive/workflows/daily_assessment/run" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"benchmark_type": "performance"}'
```

### Default Workflows

#### Daily Assessment
- **ID**: `daily_assessment`
- **Description**: Comprehensive daily competitive assessment
- **Schedule**: Every hour
- **Steps**: Performance benchmarks → Security benchmarks → Advanced analytics → Executive report → Notifications

#### Weekly Intelligence
- **ID**: `weekly_intelligence`
- **Description**: Weekly competitive intelligence and market analysis
- **Schedule**: Every Monday at 9 AM
- **Steps**: Full benchmark suite → Competitor analysis → Cost analysis → Intelligence report → Dashboard update

#### Monthly Executive
- **ID**: `monthly_executive`
- **Description**: Monthly executive reporting and strategic analysis
- **Schedule**: First of each month at 8 AM
- **Steps**: Comprehensive analysis → Executive report → Technical report → Financial report → Distribution

#### Real-time Monitoring
- **ID**: `realtime_monitoring`
- **Description**: Continuous monitoring and anomaly detection
- **Schedule**: Every 30 minutes
- **Steps**: Anomaly check → Anomaly report → Critical alerts

## Executive Reporting

### Report Types

#### Executive Summary
- **Audience**: Executives, Board Members, Stakeholders
- **Frequency**: Weekly/Monthly
- **Content**: Overall parity, market position, key insights, strategic recommendations
- **Format**: PDF, HTML

#### Technical Performance
- **Audience**: Technical Teams, Engineers, DevOps
- **Frequency**: Daily/Weekly
- **Content**: Performance benchmarks, anomalies, predictions, technical metrics
- **Format**: PDF, HTML

#### Financial Analysis
- **Audience**: Finance Teams, Management
- **Frequency**: Monthly/Quarterly
- **Content**: Cost analysis, ROI calculations, financial impact, cost positioning
- **Format**: PDF, HTML

#### Competitive Intelligence
- **Audience**: Strategy Teams, Marketing, Sales
- **Frequency**: Weekly/Monthly
- **Content**: Competitor analysis, market positioning, opportunities, threats
- **Format**: PDF, HTML

### Report Generation

#### CLI
```bash
# Generate executive report
python scripts/automated_workflows.py --workflow monthly_executive
```

#### Programmatically
```python
from src.api.reports.executive_reports import get_report_generator

generator = await get_report_generator()
report = await generator.generate_comprehensive_report("executive")
```

#### Via API
```bash
curl -X POST "https://jackdaw-sentry.com/api/competitive/reports/generate?report_type=executive" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Report Distribution

#### Email Distribution
```json
{
  "recipients": ["ceo@company.com", "board@company.com"],
  "subject": "Jackdaw Sentry Executive Report",
  "format": "pdf"
}
```

#### Webhook Distribution
```json
{
  "webhook_url": "https://your-system.com/reports",
  "report_type": "executive",
  "format": "json"
}
```

### Custom Templates

#### Template Structure
```html
<!DOCTYPE html>
<html>
<head>
    <title>{{ report_title }}</title>
    <style>
        /* Custom CSS styles */
    </style>
</head>
<body>
    <h1>{{ company_name }} Competitive Assessment</h1>
    
    <!-- Report sections -->
    <div class="section">
        <h2>Executive Summary</h2>
        <div class="metric">
            <div class="metric-value">{{ overall_parity }}%</div>
            <div class="metric-label">Overall Parity</div>
        </div>
    </div>
    
    <!-- Dynamic content -->
    {% for section in sections %}
    <div class="section">
        <h2>{{ section.title }}</h2>
        {{ section.content }}
    </div>
    {% endfor %}
    
    <div class="footer">
        Generated on {{ generation_time }}
    </div>
</body>
</html>
```

#### Custom Template Usage
```python
from src.api.reports.executive_reports import ExecutiveReportGenerator

generator = ExecutiveReportGenerator(template_dir="custom_templates")
html_content = await generator.generate_executive_report(report_data)
```

## Third-party Integrations

### Slack Integration

#### Setup
1. Create Slack app at https://api.slack.com/apps
2. Enable Incoming Webhooks
3. Create webhook URL
4. Register webhook with competitive system

#### Message Format
```json
{
  "text": "Jackdaw Sentry Competitive Alert",
  "attachments": [
    {
      "color": "danger",
      "fields": [
        {"title": "Event", "value": "Low Competitive Parity"},
        {"title": "Severity", "value": "High"},
        {"title": "Message", "value": "Parity dropped to 75%"}
      ]
    }
  ]
}
```

### Microsoft Teams Integration

#### Setup
1. Create Teams channel
2. Add Incoming Webhook connector
3. Create webhook URL
4. Register webhook with competitive system

#### Message Format
```json
{
  "@type": "MessageCard",
  "@context": "http://schema.org/extensions",
  "themeColor": "FF0000",
  "summary": "Competitive Alert",
  "sections": [
    {
      "activityTitle": "Jackdaw Sentry Alert",
      "facts": [
        {"name": "Event", "value": "Low Competitive Parity"},
        {"name": "Severity", "value": "High"}
      ]
    }
  ]
}
```

### Email Integration

#### SMTP Configuration
```python
# Configure email service
EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "username": "your_email@gmail.com",
    "password": "your_app_password",
    "from_address": "alerts@jackdaw-sentry.com"
}
```

#### Email Template
```html
<!DOCTYPE html>
<html>
<head>
    <title>Competitive Assessment Alert</title>
</head>
<body>
    <h2>Jackdaw Sentry Competitive Alert</h2>
    <p><strong>Event:</strong> {{ event_type }}</p>
    <p><strong>Severity:</strong> {{ severity }}</p>
    <p><strong>Message:</strong> {{ message }}</p>
    
    <hr>
    <p><em>This alert was generated by Jackdaw Sentry</em></p>
</body>
</html>
```

### Custom API Integration

#### Webhook Endpoint
```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook/competitive', methods=['POST'])
def competitive_webhook():
    data = request.json
    
    # Process competitive data
    event_type = data.get('event_type')
    timestamp = data.get('timestamp')
    payload = data.get('data')
    
    # Your custom logic here
    process_competitive_data(event_type, timestamp, payload)
    
    return jsonify({"status": "received"})
```

#### Data Processing
```python
def process_competitive_data(event_type, timestamp, data):
    """Process competitive assessment data"""
    
    if event_type == "alert_triggered":
        # Handle alert
        severity = data.get('severity')
        message = data.get('message')
        
        # Your custom alert handling
        handle_alert(severity, message)
    
    elif event_type == "benchmark_completed":
        # Handle benchmark results
        results = data.get('results')
        
        # Your custom benchmark processing
        process_benchmark_results(results)
```

## Scheduling and Automation

### Cron-like Scheduling
```yaml
# Hourly benchmarks
0 * * * *  # Every hour at minute 0

# Daily analysis
0 2 * * *  # Every day at 2 AM

# Weekly reports
0 9 * * 1  # Every Monday at 9 AM

# Monthly cost analysis
0 3 1 * *  # Every month on 1st at 3 AM

# Anomaly checks
*/30 * * * *  # Every 30 minutes
```

### Task Configuration
```python
# Configure scheduled tasks
TASKS = {
    "hourly_benchmark": {
        "schedule": "0 * * * *",
        "function": "run_hourly_benchmark",
        "enabled": True,
        "retry_count": 3,
        "timeout": 300
    },
    "daily_analysis": {
        "schedule": "0 2 * * *",
        "function": "run_daily_analysis",
        "enabled": True,
        "retry_count": 3,
        "timeout": 600
    }
}
```

### Monitoring and Alerting

#### Task Status Monitoring
```python
# Monitor task execution
async def monitor_task_status():
    scheduler = await get_scheduler()
    status = await scheduler.get_task_status()
    
    for task_id, task_status in status["tasks"].items():
        if task_status["status"] == "failed":
            # Send alert for failed task
            await send_task_failure_alert(task_id, task_status)
```

#### Performance Monitoring
```python
# Monitor workflow performance
async def monitor_workflow_performance():
    metrics = {
        "task_execution_time": [],
        "success_rate": [],
        "error_count": []
    }
    
    # Collect metrics and send to monitoring system
    await send_metrics_to_monitoring_system(metrics)
```

## Best Practices

### API Usage
1. **Authentication**: Always use JWT tokens
2. **Rate Limiting**: Respect API rate limits
3. **Error Handling**: Implement proper error handling
4. **Timezones**: Use UTC timestamps
5. **Pagination**: Use pagination for large datasets

### Webhook Integration
1. **Retry Logic**: Implement retry mechanisms
2. **Timeout Handling**: Set appropriate timeouts
3. **Validation**: Validate webhook payloads
4. **Security**: Verify webhook signatures
5. **Logging**: Log all webhook activities

### Workflow Design
1. **Idempotency**: Design workflows to be idempotent
2. **Error Recovery**: Implement error recovery mechanisms
3. **Monitoring**: Monitor workflow execution
4. **Testing**: Test workflows thoroughly
5. **Documentation**: Document workflow logic

### Report Generation
1. **Templates**: Use consistent report templates
2. **Caching**: Cache report data when appropriate
3. **Performance**: Optimize report generation performance
4. **Distribution**: Use multiple distribution channels
5. **Archiving**: Archive historical reports

## Troubleshooting

### Common Issues

#### API Authentication Failures
```bash
# Check JWT token validity
curl -X GET "https://jackdaw-sentry.com/api/competitive/summary" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -v
```

#### Webhook Delivery Failures
```python
# Check webhook configuration
webhook_config = webhook_manager.webhook_configs.get("webhook_id")
if not webhook_config:
    print("Webhook not found")

# Test webhook delivery
await webhook_manager.deliver_single_webhook("webhook_id", webhook_config, test_notification)
```

#### Workflow Execution Failures
```bash
# Check workflow status
python scripts/automated_workflows.py --status workflow_id

# Check logs
docker logs jackdaw-competitive-monitoring-prod
```

#### Report Generation Issues
```python
# Check template rendering
template = report_generator.template_env.get_template("executive_report.html")
html_content = template.render(test_data)

# Check PDF generation
success = await report_generator.generate_pdf_report(html_content, "test.pdf")
```

### Debugging Tools

#### API Testing
```bash
# Test API endpoints
curl -X GET "https://jackdaw-sentry.com/api/competitive/health" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Webhook Testing
```python
# Test webhook delivery
test_notification = {
    "event_type": "test",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "data": {"message": "Test notification"}
}

await webhook_manager.send_notification("test", test_notification)
```

#### Workflow Testing
```bash
# Test workflow execution
python scripts/automated_workflows.py --workflow test_workflow --params '{"test": true}'
```

## Support

For integration and automation support:
1. Check API documentation at `/docs`
2. Review webhook and workflow logs
3. Monitor system health at `/health`
4. Contact support team for complex issues

## Security Considerations

### API Security
- Use HTTPS for all API calls
- Validate JWT tokens
- Implement rate limiting
- Monitor API usage
- Secure webhook endpoints

### Data Protection
- Encrypt sensitive data
- Use secure connections
- Implement access controls
- Monitor data access
- Regular security audits

### Compliance
- GDPR compliance for data handling
- SOC 2 controls for security
- Audit logging for all activities
- Data retention policies
- Regular compliance reviews
