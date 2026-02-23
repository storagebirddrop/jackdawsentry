"""
Jackdaw Sentry - Competitive Dashboard
Real-time competitive monitoring and visualization dashboard
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
import aiofiles
import aiohttp

logger = logging.getLogger(__name__)


class CompetitiveDashboard:
    """
    Real-time competitive monitoring dashboard
    
    Provides live visualization of competitive metrics, trends,
    and market positioning data for Jackdaw Sentry.
    """
    
    def __init__(self, base_url: str, data_dir: str):
        self.base_url = base_url.rstrip('/')
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_running = False
        
        # Dashboard state
        self.current_metrics: Dict[str, Any] = {}
        self.historical_data: List[Dict[str, Any]] = []
        self.last_update: Optional[datetime] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def start_monitoring(self):
        """Start the competitive monitoring dashboard"""
        logger.info(f"Starting competitive dashboard for {self.base_url}")
        logger.info(f"Data directory: {self.data_dir}")
        
        self.is_running = True
        
        try:
            # Load existing historical data
            await self._load_historical_data()
            
            # Start monitoring loop
            await self._monitoring_loop()
            
        except KeyboardInterrupt:
            logger.info("Dashboard monitoring stopped by user")
        except Exception as e:
            logger.error(f"Dashboard monitoring failed: {e}")
            raise
        finally:
            self.is_running = False
    
    async def _monitoring_loop(self):
        """Main monitoring loop for real-time data collection"""
        logger.info("Starting competitive monitoring loop")
        
        while self.is_running:
            try:
                # Collect current metrics
                await self._collect_current_metrics()
                
                # Update dashboard display
                await self._update_dashboard_display()
                
                # Save historical data
                await self._save_historical_data()
                
                # Wait for next update (30 seconds)
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Short delay before retry
    
    async def _collect_current_metrics(self):
        """Collect current competitive metrics"""
        logger.debug("Collecting current competitive metrics")
        
        # Simulate metric collection - in real implementation would fetch from APIs
        current_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "base_url": self.base_url,
            "metrics": {
                "performance": {
                    "response_time": {"value": 180, "target": 200, "competitor_avg": 250, "parity": 138.9},
                    "throughput": {"value": 1200, "target": 1000, "competitor_avg": 800, "parity": 150.0},
                    "availability": {"value": 99.95, "target": 99.9, "competitor_avg": 99.5, "parity": 100.5},
                    "memory_usage": {"value": 450, "target": 512, "competitor_avg": 600, "parity": 133.3}
                },
                "security": {
                    "security_score": {"value": 92, "target": 95, "competitor_avg": 85, "parity": 108.2},
                    "vulnerability_response": {"value": 18, "target": 24, "competitor_avg": 48, "parity": 266.7},
                    "compliance_coverage": {"value": 98, "target": 100, "competitor_avg": 90, "parity": 108.9},
                    "encryption_coverage": {"value": 100, "target": 100, "competitor_avg": 85, "parity": 117.6}
                },
                "features": {
                    "feature_coverage": {"value": 88, "target": 90, "competitor_avg": 75, "parity": 117.3},
                    "api_endpoints": {"value": 48, "target": 50, "competitor_avg": 35, "parity": 137.1},
                    "integration_support": {"value": 16, "target": 15, "competitor_avg": 10, "parity": 160.0},
                    "customization_options": {"value": 82, "target": 80, "competitor_avg": 60, "parity": 136.7}
                },
                "user_experience": {
                    "ui_responsiveness": {"value": 93, "target": 95, "competitor_avg": 85, "parity": 109.4},
                    "mobile_experience": {"value": 91, "target": 90, "competitor_avg": 80, "parity": 113.8},
                    "documentation_quality": {"value": 87, "target": 85, "competitor_avg": 70, "parity": 124.3},
                    "support_quality": {"value": 92, "target": 90, "competitor_avg": 75, "parity": 122.7}
                }
            },
            "summary": {
                "overall_parity": 125.4,
                "market_position": "Leader",
                "strengths": [
                    "Integration Support: 160.0% parity",
                    "Vulnerability Response: 266.7% parity",
                    "API Endpoints: 137.1% parity"
                ],
                "improvements": [
                    "Security Score: 92.0% (target: 95.0)",
                    "Feature Coverage: 88.0% (target: 90.0)",
                    "UI Responsiveness: 93.0% (target: 95.0)"
                ],
                "recommendations": [
                    "Maintain competitive leadership through continuous innovation",
                    "Focus on security enhancements to reach target scores",
                    "Expand feature set to strengthen market position"
                ]
            }
        }
        
        self.current_metrics = current_data
        self.last_update = datetime.now(timezone.utc)
        
        # Add to historical data
        self.historical_data.append(current_data)
        
        # Keep only last 100 entries to prevent memory issues
        if len(self.historical_data) > 100:
            self.historical_data = self.historical_data[-100:]
    
    async def _update_dashboard_display(self):
        """Update the dashboard display with current metrics"""
        logger.debug("Updating dashboard display")
        
        # Create dashboard output
        dashboard_output = self._generate_dashboard_output()
        
        # Save to dashboard file
        dashboard_file = self.data_dir / "dashboard_current.json"
        async with aiofiles.open(dashboard_file, 'w') as f:
            await f.write(json.dumps(self.current_metrics, indent=2, default=str))
        
        # Generate HTML dashboard
        html_content = self._generate_html_dashboard()
        html_file = self.data_dir / "dashboard.html"
        async with aiofiles.open(html_file, 'w') as f:
            await f.write(html_content)
        
        # Print summary to console
        print(dashboard_output)
    
    def _generate_dashboard_output(self) -> str:
        """Generate formatted dashboard output for console display"""
        if not self.current_metrics:
            return "No data available"
        
        summary = self.current_metrics.get("summary", {})
        metrics = self.current_metrics.get("metrics", {})
        
        output = []
        output.append("\n" + "="*80)
        output.append("JACKDAW SENTRY - COMPETITIVE DASHBOARD")
        output.append("="*80)
        output.append(f"Last Update: {self.last_update.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        output.append(f"Base URL: {self.base_url}")
        output.append("")
        
        # Overall status
        output.append("OVERALL STATUS:")
        output.append(f"  Competitive Parity: {summary.get('overall_parity', 0):.1f}%")
        output.append(f"  Market Position: {summary.get('market_position', 'Unknown')}")
        output.append("")
        
        # Category breakdowns
        for category, category_metrics in metrics.items():
            output.append(f"{category.upper()}:")
            for metric_name, metric_data in category_metrics.items():
                parity = metric_data.get('parity', 0)
                value = metric_data.get('value', 0)
                target = metric_data.get('target', 0)
                
                status_icon = "✓" if parity >= 100 else "○"
                output.append(f"  {status_icon} {metric_name.replace('_', ' ').title()}: {parity:.1f}% parity ({value}/{target})")
            output.append("")
        
        # Strengths
        strengths = summary.get('strengths', [])
        if strengths:
            output.append("KEY STRENGTHS:")
            for strength in strengths[:3]:
                output.append(f"  ✓ {strength}")
            output.append("")
        
        # Improvements
        improvements = summary.get('improvements', [])
        if improvements:
            output.append("IMPROVEMENT AREAS:")
            for improvement in improvements[:3]:
                output.append(f"  ○ {improvement}")
            output.append("")
        
        output.append("="*80)
        
        return "\n".join(output)
    
    def _generate_html_dashboard(self) -> str:
        """Generate HTML dashboard for web viewing"""
        if not self.current_metrics:
            return "<html><body>No data available</body></html>"
        
        summary = self.current_metrics.get("summary", {})
        metrics = self.current_metrics.get("metrics", {})
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jackdaw Sentry - Competitive Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .status {{ display: flex; justify-content: space-around; margin-bottom: 30px; }}
        .status-item {{ text-align: center; padding: 20px; border-radius: 8px; background-color: #e8f4fd; }}
        .category {{ margin-bottom: 30px; }}
        .category h3 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        .metric {{ display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid #eee; }}
        .metric-name {{ font-weight: bold; }}
        .metric-value {{ display: flex; align-items: center; gap: 10px; }}
        .parity {{ padding: 4px 8px; border-radius: 4px; color: white; font-size: 0.9em; }}
        .parity.good {{ background-color: #28a745; }}
        .parity.warning {{ background-color: #ffc107; color: #333; }}
        .parity.danger {{ background-color: #dc3545; }}
        .strengths, .improvements {{ display: flex; gap: 20px; margin-bottom: 20px; }}
        .strengths h4, .improvements h4 {{ margin-bottom: 10px; }}
        .list-item {{ padding: 5px 0; }}
        .footer {{ text-align: center; margin-top: 30px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Jackdaw Sentry - Competitive Dashboard</h1>
            <p>Real-time competitive monitoring and analysis</p>
            <p><strong>Last Update:</strong> {self.last_update.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        </div>
        
        <div class="status">
            <div class="status-item">
                <h3>Competitive Parity</h3>
                <h2>{summary.get('overall_parity', 0):.1f}%</h2>
            </div>
            <div class="status-item">
                <h3>Market Position</h3>
                <h2>{summary.get('market_position', 'Unknown')}</h2>
            </div>
        </div>
        
        <div class="strengths">
            <div>
                <h4>Key Strengths</h4>
                <div class="list-item">{'<br>'.join([f"✓ {s}" for s in summary.get('strengths', [])[:3]])}</div>
            </div>
            <div>
                <h4>Improvement Areas</h4>
                <div class="list-item">{'<br>'.join([f"○ {i}" for i in summary.get('improvements', [])[:3]])}</div>
            </div>
        </div>
"""
        
        # Add categories
        for category, category_metrics in metrics.items():
            html += f'<div class="category"><h3>{category.title()}</h3>'
            
            for metric_name, metric_data in category_metrics.items():
                parity = metric_data.get('parity', 0)
                value = metric_data.get('value', 0)
                target = metric_data.get('target', 0)
                
                parity_class = "good" if parity >= 100 else "warning" if parity >= 80 else "danger"
                
                html += f"""
                <div class="metric">
                    <span class="metric-name">{metric_name.replace('_', ' ').title()}</span>
                    <div class="metric-value">
                        <span>{value}/{target}</span>
                        <span class="parity {parity_class}">{parity:.1f}%</span>
                    </div>
                </div>
"""
            
            html += '</div>'
        
        html += f"""
        <div class="footer">
            <p>Dashboard data saved to: {self.data_dir}</p>
        </div>
    </div>
</body>
</html>
"""
        
        return html
    
    async def _save_historical_data(self):
        """Save historical data to file"""
        if not self.historical_data:
            return
        
        historical_file = self.data_dir / "historical_data.json"
        async with aiofiles.open(historical_file, 'w') as f:
            await f.write(json.dumps(self.historical_data, indent=2, default=str))
    
    async def _load_historical_data(self):
        """Load historical data from file"""
        historical_file = self.data_dir / "historical_data.json"
        
        if historical_file.exists():
            try:
                async with aiofiles.open(historical_file, 'r') as f:
                    content = await f.read()
                    self.historical_data = json.loads(content)
                logger.info(f"Loaded {len(self.historical_data)} historical data points")
            except Exception as e:
                logger.warning(f"Could not load historical data: {e}")
                self.historical_data = []
        else:
            self.historical_data = []
    
    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current competitive metrics"""
        return self.current_metrics.copy() if self.current_metrics else {}
    
    async def get_historical_data(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get historical data with optional limit"""
        return self.historical_data[-limit:] if self.historical_data else []
    
    async def export_report(self, output_file: Optional[str] = None) -> str:
        """Export comprehensive competitive report"""
        if not output_file:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_file = self.data_dir / f"competitive_report_{timestamp}.json"
        
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "base_url": self.base_url,
            "current_metrics": self.current_metrics,
            "historical_summary": {
                "total_data_points": len(self.historical_data),
                "date_range": {
                    "start": self.historical_data[0]["timestamp"] if self.historical_data else None,
                    "end": self.historical_data[-1]["timestamp"] if self.historical_data else None
                }
            },
            "trends": self._calculate_trends()
        }
        
        async with aiofiles.open(output_file, 'w') as f:
            await f.write(json.dumps(report, indent=2, default=str))
        
        logger.info(f"Competitive report exported to {output_file}")
        return str(output_file)
    
    def _calculate_trends(self) -> Dict[str, Any]:
        """Calculate trends from historical data"""
        if len(self.historical_data) < 2:
            return {"message": "Insufficient data for trend analysis"}
        
        # Simple trend calculation - compare last 10 data points with previous 10
        recent_data = self.historical_data[-10:] if len(self.historical_data) >= 10 else self.historical_data[-len(self.historical_data)//2:]
        previous_data = self.historical_data[-20:-10] if len(self.historical_data) >= 20 else self.historical_data[:len(self.historical_data)//2]
        
        if not recent_data or not previous_data:
            return {"message": "Insufficient data for trend analysis"}
        
        # Calculate average parity changes
        recent_avg_parity = sum(d.get("summary", {}).get("overall_parity", 0) for d in recent_data) / len(recent_data)
        previous_avg_parity = sum(d.get("summary", {}).get("overall_parity", 0) for d in previous_data) / len(previous_data)
        
        trend_direction = "improving" if recent_avg_parity > previous_avg_parity else "declining" if recent_avg_parity < previous_avg_parity else "stable"
        trend_magnitude = abs(recent_avg_parity - previous_avg_parity)
        
        return {
            "direction": trend_direction,
            "magnitude": round(trend_magnitude, 2),
            "recent_average": round(recent_avg_parity, 1),
            "previous_average": round(previous_avg_parity, 1),
            "data_points_analyzed": len(recent_data) + len(previous_data)
        }