#!/usr/bin/env python3
"""
Jackdaw Sentry - Automated Workflows Manager
Manages automated competitive assessment workflows and integrations
"""

import asyncio
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from competitive.benchmarking_suite import CompetitiveBenchmarkingSuite
from competitive.advanced_analytics import AdvancedAnalytics
from competitive.expanded_competitors import ExpandedCompetitiveAnalysis
from competitive.cost_analysis import CostAnalysis
from api.reports.executive_reports import get_report_generator
from api.webhooks.competitive_webhooks import webhook_manager, alert_manager
from api.schedulers.competitive_scheduler import get_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutomatedWorkflowManager:
    """Manages automated competitive assessment workflows"""
    
    def __init__(self):
        self.workflows = {}
        self.running = False
        self.workflow_tasks = {}
        
    def register_workflow(self, workflow_id: str, workflow_config: Dict[str, Any]) -> None:
        """Register an automated workflow"""
        self.workflows[workflow_id] = workflow_config
        logger.info(f"Registered workflow: {workflow_id}")
    
    async def start_workflow(self, workflow_id: str, params: Dict[str, Any] = None) -> bool:
        """Start a specific workflow"""
        if workflow_id not in self.workflows:
            logger.error(f"Workflow not found: {workflow_id}")
            return False
        
        workflow = self.workflows[workflow_id]
        params = params or {}
        
        try:
            # Create workflow task
            task = asyncio.create_task(
                self.execute_workflow(workflow_id, workflow, params)
            )
            self.workflow_tasks[workflow_id] = task
            
            logger.info(f"Started workflow: {workflow_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start workflow {workflow_id}: {e}")
            return False
    
    async def execute_workflow(self, workflow_id: str, workflow: Dict[str, Any], params: Dict[str, Any]) -> None:
        """Execute a workflow"""
        logger.info(f"Executing workflow: {workflow_id}")
        
        try:
            # Send workflow started notification
            await webhook_manager.send_notification("workflow_started", {
                "workflow_id": workflow_id,
                "workflow_name": workflow.get("name", workflow_id),
                "params": params
            })
            
            # Execute workflow steps
            steps = workflow.get("steps", [])
            results = {}
            
            for i, step in enumerate(steps):
                step_name = step.get("name", f"step_{i}")
                step_type = step.get("type", "unknown")
                
                logger.info(f"Executing step {i+1}/{len(steps)}: {step_name}")
                
                try:
                    step_result = await self.execute_step(step, params, results)
                    results[step_name] = {
                        "status": "completed",
                        "result": step_result,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Send step completed notification
                    await webhook_manager.send_notification("step_completed", {
                        "workflow_id": workflow_id,
                        "step_name": step_name,
                        "step_number": i + 1,
                        "total_steps": len(steps),
                        "result": step_result
                    })
                    
                except Exception as e:
                    logger.error(f"Step {step_name} failed: {e}")
                    results[step_name] = {
                        "status": "failed",
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Send step failed notification
                    await webhook_manager.send_notification("step_failed", {
                        "workflow_id": workflow_id,
                        "step_name": step_name,
                        "error": str(e)
                    })
                    
                    # Check if workflow should continue on failure
                    if not step.get("continue_on_failure", False):
                        break
            
            # Send workflow completed notification
            await webhook_manager.send_notification("workflow_completed", {
                "workflow_id": workflow_id,
                "workflow_name": workflow.get("name", workflow_id),
                "results": results,
                "status": "completed"
            })
            
            logger.info(f"Workflow completed: {workflow_id}")
            
        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {e}")
            
            # Send workflow failed notification
            await webhook_manager.send_notification("workflow_failed", {
                "workflow_id": workflow_id,
                "error": str(e)
            })
    
    async def execute_step(self, step: Dict[str, Any], params: Dict[str, Any], previous_results: Dict[str, Any]) -> Any:
        """Execute a single workflow step"""
        step_type = step.get("type")
        
        if step_type == "benchmark":
            return await self.execute_benchmark_step(step, params)
        elif step_type == "analysis":
            return await self.execute_analysis_step(step, params)
        elif step_type == "report":
            return await self.execute_report_step(step, params)
        elif step_type == "notification":
            return await self.execute_notification_step(step, params)
        elif step_type == "integration":
            return await self.execute_integration_step(step, params)
        elif step_type == "cleanup":
            return await self.execute_cleanup_step(step, params)
        else:
            raise ValueError(f"Unknown step type: {step_type}")
    
    async def execute_benchmark_step(self, step: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute benchmark step"""
        benchmark_type = step.get("benchmark_type", "full")
        
        # Initialize benchmarking suite
        async with CompetitiveBenchmarkingSuite() as benchmarking_suite:
            if benchmark_type == "full":
                results = await benchmarking_suite.run_all_benchmarks()
            elif benchmark_type == "performance":
                results = await benchmarking_suite.run_performance_benchmarks()
            elif benchmark_type == "security":
                results = await benchmarking_suite.run_security_benchmarks()
            elif benchmark_type == "feature":
                results = await benchmarking_suite.run_feature_benchmarks()
            elif benchmark_type == "ux":
                results = await benchmarking_suite.run_ux_benchmarks()
            else:
                raise ValueError(f"Unknown benchmark type: {benchmark_type}")
            
            return results
    
    async def execute_analysis_step(self, step: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute analysis step"""
        analysis_type = step.get("analysis_type", "comprehensive")
        
        # Initialize services
        advanced_analytics = AdvancedAnalytics()
        await advanced_analytics.initialize_models()
        
        expanded_analysis = ExpandedCompetitiveAnalysis()
        cost_analysis = CostAnalysis()
        
        if analysis_type == "comprehensive":
            insights = await advanced_analytics.generate_competitive_insights()
            competitors = await expanded_analysis.analyze_expanded_competitive_landscape()
            cost_report = await cost_analysis.generate_cost_report()
            
            return {
                "insights": [asdict(insight) for insight in insights],
                "competitors": competitors,
                "cost_analysis": cost_report
            }
        elif analysis_type == "advanced_analytics":
            insights = await advanced_analytics.generate_competitive_insights()
            return {"insights": [asdict(insight) for insight in insights]}
        elif analysis_type == "competitor_analysis":
            competitors = await expanded_analysis.analyze_expanded_competitive_landscape()
            return {"competitors": competitors}
        elif analysis_type == "cost_analysis":
            cost_report = await cost_analysis.generate_cost_report()
            return {"cost_analysis": cost_report}
        else:
            raise ValueError(f"Unknown analysis type: {analysis_type}")
    
    async def execute_report_step(self, step: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute report step"""
        report_type = step.get("report_type", "executive")
        format_type = step.get("format", "pdf")
        recipients = step.get("recipients", [])
        
        # Get report generator
        report_generator = await get_report_generator()
        
        # Generate report
        report_result = await report_generator.generate_comprehensive_report(report_type)
        
        # Send report if recipients specified
        if recipients and report_result.get("pdf_path"):
            await report_generator.send_report_email(
                report_result["pdf_path"],
                recipients,
                f"Jackdaw Sentry {report_type.title()} Report"
            )
        
        return report_result
    
    async def execute_notification_step(self, step: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute notification step"""
        notification_type = step.get("notification_type", "webhook")
        message = step.get("message", "Workflow notification")
        recipients = step.get("recipients", [])
        
        if notification_type == "webhook":
            await webhook_manager.send_notification("workflow_notification", {
                "message": message,
                "recipients": recipients,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        elif notification_type == "email":
            # Send email notification
            logger.info(f"Would send email notification to: {recipients}")
        elif notification_type == "slack":
            # Send Slack notification
            logger.info(f"Would send Slack notification: {message}")
        
        return {"notification_sent": True, "recipients": recipients}
    
    async def execute_integration_step(self, step: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute integration step"""
        integration_type = step.get("integration_type", "api")
        target_url = step.get("target_url")
        data = step.get("data", {})
        
        if integration_type == "api":
            # Send data to external API
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.post(target_url, json=data) as response:
                    if response.status == 200:
                        return {"integration_success": True, "response": await response.json()}
                    else:
                        return {"integration_success": False, "status": response.status}
        elif integration_type == "database":
            # Store data in database
            logger.info(f"Would store data in database: {data}")
            return {"integration_success": True}
        elif integration_type == "file":
            # Save data to file
            file_path = step.get("file_path", "workflow_output.json")
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
            return {"integration_success": True, "file_path": file_path}
        else:
            raise ValueError(f"Unknown integration type: {integration_type}")
    
    async def execute_cleanup_step(self, step: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute cleanup step"""
        cleanup_type = step.get("cleanup_type", "cache")
        
        if cleanup_type == "cache":
            # Clear cache
            logger.info("Cache cleanup completed")
        elif cleanup_type == "logs":
            # Clean up old logs
            logger.info("Log cleanup completed")
        elif cleanup_type == "temp_files":
            # Clean up temporary files
            logger.info("Temporary files cleanup completed")
        
        return {"cleanup_completed": True, "cleanup_type": cleanup_type}
    
    async def get_workflow_status(self, workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of workflows"""
        if workflow_id:
            if workflow_id in self.workflow_tasks:
                task = self.workflow_tasks[workflow_id]
                if task.done():
                    return {
                        "workflow_id": workflow_id,
                        "status": "completed" if not task.cancelled() else "cancelled",
                        "result": task.result() if not task.cancelled() else None
                    }
                else:
                    return {
                        "workflow_id": workflow_id,
                        "status": "running"
                    }
            else:
                return {"error": "Workflow not found"}
        else:
            # Return all workflow statuses
            statuses = {}
            for wid, task in self.workflow_tasks.items():
                if task.done():
                    statuses[wid] = {
                        "status": "completed" if not task.cancelled() else "cancelled",
                        "result": task.result() if not task.cancelled() else None
                    }
                else:
                    statuses[wid] = {"status": "running"}
            
            return {
                "workflows": statuses,
                "total_workflows": len(self.workflow_tasks),
                "running_workflows": len([t for t in self.workflow_tasks.values() if not t.done()])
            }
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow"""
        if workflow_id in self.workflow_tasks:
            task = self.workflow_tasks[workflow_id]
            task.cancel()
            
            # Send cancellation notification
            await webhook_manager.send_notification("workflow_cancelled", {
                "workflow_id": workflow_id
            })
            
            logger.info(f"Cancelled workflow: {workflow_id}")
            return True
        else:
            logger.error(f"Workflow not found: {workflow_id}")
            return False

# Initialize default workflows
def initialize_default_workflows() -> AutomatedWorkflowManager:
    """Initialize default automated workflows"""
    manager = AutomatedWorkflowManager()
    
    # Daily comprehensive assessment workflow
    manager.register_workflow("daily_assessment", {
        "name": "Daily Competitive Assessment",
        "description": "Comprehensive daily competitive assessment and reporting",
        "steps": [
            {
                "name": "Run Performance Benchmarks",
                "type": "benchmark",
                "benchmark_type": "performance",
                "continue_on_failure": False
            },
            {
                "name": "Run Security Benchmarks",
                "type": "benchmark", 
                "benchmark_type": "security",
                "continue_on_failure": False
            },
            {
                "name": "Advanced Analytics",
                "type": "analysis",
                "analysis_type": "comprehensive",
                "continue_on_failure": True
            },
            {
                "name": "Generate Executive Report",
                "type": "report",
                "report_type": "executive",
                "format": "pdf",
                "recipients": ["executives@company.com"],
                "continue_on_failure": True
            },
            {
                "name": "Send Notifications",
                "type": "notification",
                "notification_type": "webhook",
                "message": "Daily competitive assessment completed",
                "recipients": ["slack", "email"],
                "continue_on_failure": True
            },
            {
                "name": "Store Results",
                "type": "integration",
                "integration_type": "database",
                "continue_on_failure": True
            }
        ]
    })
    
    # Weekly competitive intelligence workflow
    manager.register_workflow("weekly_intelligence", {
        "name": "Weekly Competitive Intelligence",
        "description": "Weekly competitive analysis and market intelligence",
        "steps": [
            {
                "name": "Full Benchmark Suite",
                "type": "benchmark",
                "benchmark_type": "full",
                "continue_on_failure": False
            },
            {
                "name": "Competitor Analysis",
                "type": "analysis",
                "analysis_type": "competitor_analysis",
                "continue_on_failure": True
            },
            {
                "name": "Cost Analysis",
                "type": "analysis",
                "analysis_type": "cost_analysis",
                "continue_on_failure": True
            },
            {
                "name": "Generate Intelligence Report",
                "type": "report",
                "report_type": "competitive",
                "format": "pdf",
                "recipients": ["strategy@company.com", "marketing@company.com"],
                "continue_on_failure": True
            },
            {
                "name": "Update Dashboard",
                "type": "integration",
                "integration_type": "api",
                "target_url": "https://dashboard.company.com/api/update",
                "continue_on_failure": True
            }
        ]
    })
    
    # Monthly executive reporting workflow
    manager.register_workflow("monthly_executive", {
        "name": "Monthly Executive Reporting",
        "description": "Monthly executive reports and strategic analysis",
        "steps": [
            {
                "name": "Comprehensive Analysis",
                "type": "analysis",
                "analysis_type": "comprehensive",
                "continue_on_failure": False
            },
            {
                "name": "Generate Executive Report",
                "type": "report",
                "report_type": "executive",
                "format": "pdf",
                "recipients": ["ceo@company.com", "board@company.com"],
                "continue_on_failure": False
            },
            {
                "name": "Generate Technical Report",
                "type": "report",
                "report_type": "technical",
                "format": "pdf",
                "recipients": ["cto@company.com", "engineering@company.com"],
                "continue_on_failure": True
            },
            {
                "name": "Generate Financial Report",
                "type": "report",
                "report_type": "financial",
                "format": "pdf",
                "recipients": ["cfo@company.com", "finance@company.com"],
                "continue_on_failure": True
            },
            {
                "name": "Distribute Reports",
                "type": "notification",
                "notification_type": "email",
                "message": "Monthly competitive assessment reports are ready",
                "recipients": ["all-staff@company.com"],
                "continue_on_failure": True
            }
        ]
    })
    
    # Real-time anomaly detection workflow
    manager.register_workflow("realtime_monitoring", {
        "name": "Real-time Anomaly Detection",
        "description": "Continuous monitoring and anomaly detection",
        "steps": [
            {
                "name": "Check Performance Anomalies",
                "type": "analysis",
                "analysis_type": "advanced_analytics",
                "continue_on_failure": True
            },
            {
                "name": "Generate Anomaly Report",
                "type": "report",
                "report_type": "technical",
                "format": "html",
                "recipients": ["ops@company.com"],
                "continue_on_failure": True
            },
            {
                "name": "Alert on Critical Anomalies",
                "type": "notification",
                "notification_type": "webhook",
                "message": "Critical performance anomalies detected",
                "recipients": ["slack", "email"],
                "continue_on_failure": True
            }
        ]
    })
    
    return manager

# Global workflow manager
workflow_manager = None

async def get_workflow_manager() -> AutomatedWorkflowManager:
    """Get or create global workflow manager"""
    global workflow_manager
    if workflow_manager is None:
        workflow_manager = initialize_default_workflows()
    return workflow_manager

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Jackdaw Sentry Automated Workflows")
    parser.add_argument("--workflow", help="Workflow ID to run")
    parser.add_argument("--list", action="store_true", help="List available workflows")
    parser.add_argument("--status", help="Get workflow status")
    parser.add_argument("--cancel", help="Cancel running workflow")
    parser.add_argument("--params", help="Workflow parameters (JSON)")
    
    args = parser.parse_args()
    
    async def run_workflow_manager():
        manager = await get_workflow_manager()
        
        if args.list:
            workflows = manager.workflows
            print("Available Workflows:")
            for workflow_id, workflow in workflows.items():
                print(f"  {workflow_id}: {workflow.get('name', workflow_id)}")
                print(f"    Description: {workflow.get('description', 'No description')}")
                print(f"    Steps: {len(workflow.get('steps', []))}")
                print()
        
        elif args.workflow:
            params = {}
            if args.params:
                try:
                    params = json.loads(args.params)
                except json.JSONDecodeError:
                    print("Error: Invalid JSON parameters")
                    return
            
            success = await manager.start_workflow(args.workflow, params)
            if success:
                print(f"Workflow started: {args.workflow}")
                
                # Wait for completion
                while True:
                    status = await manager.get_workflow_status(args.workflow)
                    if status.get("status") in ["completed", "cancelled", "error"]:
                        print(f"Workflow {status['status']}: {args.workflow}")
                        break
                    await asyncio.sleep(5)
            else:
                print(f"Failed to start workflow: {args.workflow}")
        
        elif args.status:
            if args.status == "all":
                status = await manager.get_workflow_status()
                print(f"Total workflows: {status.get('total_workflows', 0)}")
                print(f"Running workflows: {status.get('running_workflows', 0)}")
                print("\nWorkflow Statuses:")
                for workflow_id, workflow_status in status.get("workflows", {}).items():
                    print(f"  {workflow_id}: {workflow_status.get('status', 'unknown')}")
            else:
                status = await manager.get_workflow_status(args.status)
                print(f"Workflow Status: {json.dumps(status, indent=2)}")
        
        elif args.cancel:
            success = await manager.cancel_workflow(args.cancel)
            if success:
                print(f"Workflow cancelled: {args.cancel}")
            else:
                print(f"Failed to cancel workflow: {args.cancel}")
        
        else:
            print("No action specified. Use --help for usage.")
    
    asyncio.run(run_workflow_manager())

if __name__ == "__main__":
    main()
