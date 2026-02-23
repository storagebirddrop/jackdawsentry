"""
Compliance Analytics API Router

This module provides API endpoints for compliance analytics and reporting including:
- Report generation and management
- Dashboard data retrieval
- Analytics metrics collection
- Performance monitoring
"""

import logging
import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import HTTPException

from src.analytics.compliance_analytics import AnalyticsReport
from src.analytics.compliance_analytics import ComplianceAnalyticsEngine
from src.analytics.compliance_analytics import ReportType
from src.api.auth import User
from src.api.auth import check_permissions
from src.api.auth import get_current_user
from src.api.models.analytics import AnalyticsMetricsResponse
from src.api.models.analytics import AnalyticsReportRequest
from src.api.models.analytics import AnalyticsReportResponse
from src.api.models.analytics import DashboardResponse

logger = logging.getLogger(__name__)

router = APIRouter()
analytics_engine = ComplianceAnalyticsEngine()


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard_data(
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"])),
):
    """Get analytics dashboard data"""
    try:
        dashboard_data = await analytics_engine.get_dashboard_data()

        return DashboardResponse(
            success=True, data=dashboard_data, timestamp=datetime.now(timezone.utc)
        )

    except Exception as e:
        logger.error(f"Failed to get dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/report", response_model=AnalyticsReportResponse)
async def generate_analytics_report(
    request: AnalyticsReportRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"])),
):
    """Generate analytics report"""
    try:
        # Parse dates
        period_start = None
        period_end = None

        if request.period_start:
            period_start = datetime.fromisoformat(request.period_start)
            if period_start.tzinfo is None:
                period_start = period_start.replace(tzinfo=timezone.utc)
        if request.period_end:
            period_end = datetime.fromisoformat(request.period_end)
            if period_end.tzinfo is None:
                period_end = period_end.replace(tzinfo=timezone.utc)

        # Generate report
        report = await analytics_engine.generate_analytics_report(
            report_type=ReportType(request.report_type),
            period_start=period_start,
            period_end=period_end,
            custom_config=request.custom_config,
        )

        return AnalyticsReportResponse(
            success=True,
            report_id=report.report_id,
            report_type=report.report_type.value,
            title=report.title,
            description=report.description,
            generated_at=report.generated_at,
            period_start=report.period_start,
            period_end=report.period_end,
            metrics_count=len(report.metrics),
            charts_count=len(report.charts),
            insights_count=len(report.insights),
            recommendations_count=len(report.recommendations),
        )

    except Exception as e:
        logger.error(f"Failed to generate analytics report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/{report_id}")
async def get_analytics_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"])),
):
    """Get analytics report details"""
    try:
        # Find report in analytics engine
        report = None
        for r in analytics_engine.reports:
            if r.report_id == report_id:
                report = r
                break

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        return {
            "success": True,
            "report": {
                "report_id": report.report_id,
                "report_type": report.report_type.value,
                "title": report.title,
                "description": report.description,
                "generated_at": report.generated_at,
                "period_start": report.period_start,
                "period_end": report.period_end,
                "metrics": [
                    {
                        "name": metric.name,
                        "value": metric.value,
                        "unit": metric.unit,
                        "metric_type": metric.metric_type.value,
                        "timestamp": metric.timestamp,
                        "metadata": metric.metadata,
                    }
                    for metric in report.metrics
                ],
                "charts": report.charts,
                "insights": report.insights,
                "recommendations": report.recommendations,
                "metadata": report.metadata,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analytics report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports")
async def list_analytics_reports(
    limit: int = 50,
    offset: int = 0,
    report_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"])),
):
    """List analytics reports"""
    try:
        # Get all reports
        all_reports = analytics_engine.reports

        # Apply filters
        filtered_reports = all_reports
        if report_type:
            filtered_reports = [
                r for r in filtered_reports if r.report_type.value == report_type
            ]

        # Sort by generated date (newest first)
        filtered_reports.sort(key=lambda x: x.generated_at, reverse=True)

        # Apply pagination
        total_count = len(filtered_reports)
        paginated_reports = filtered_reports[offset : offset + limit]

        # Convert to response format
        report_list = []
        for report in paginated_reports:
            report_list.append(
                {
                    "report_id": report.report_id,
                    "report_type": report.report_type.value,
                    "title": report.title,
                    "generated_at": report.generated_at,
                    "period_start": report.period_start,
                    "period_end": report.period_end,
                    "metrics_count": len(report.metrics),
                    "charts_count": len(report.charts),
                    "insights_count": len(report.insights),
                    "recommendations_count": len(report.recommendations),
                }
            )

        return {
            "success": True,
            "reports": report_list,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"Failed to list analytics reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_analytics_metrics(
    metric_type: Optional[str] = None,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"])),
):
    """Get analytics metrics"""
    try:
        # Parse dates
        start_date = None
        end_date = None

        if period_start:
            start_date = datetime.fromisoformat(period_start)
        if period_end:
            end_date = datetime.fromisoformat(period_end)

        # Set default period if not provided
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=7)
        if not end_date:
            end_date = datetime.now(timezone.utc)

        # Collect metrics
        if metric_type:
            # Collect specific metric type
            metrics = await analytics_engine.collect_metrics(
                ReportType.CUSTOM_REPORT,
                start_date,
                end_date,
                {"metrics": [{"name": metric_type, "type": "counter"}]},
            )
        else:
            # Collect all metrics
            metrics = await analytics_engine.collect_metrics(
                ReportType.WEEKLY_ANALYSIS, start_date, end_date
            )

        return AnalyticsMetricsResponse(
            success=True,
            metrics=[
                {
                    "name": metric.name,
                    "value": metric.value,
                    "unit": metric.unit,
                    "metric_type": metric.metric_type.value,
                    "timestamp": metric.timestamp,
                    "metadata": metric.metadata,
                }
                for metric in metrics
            ],
            period_start=start_date,
            period_end=end_date,
            total_metrics=len(metrics),
        )

    except Exception as e:
        logger.error(f"Failed to get analytics metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/charts")
async def get_analytics_charts(
    chart_type: Optional[str] = None,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"])),
):
    """Get analytics charts"""
    try:
        # Parse dates
        start_date = None
        end_date = None

        if period_start:
            start_date = datetime.fromisoformat(period_start)
        if period_end:
            end_date = datetime.fromisoformat(period_end)

        # Set default period if not provided
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=7)
        if not end_date:
            end_date = datetime.now(timezone.utc)

        # Generate charts
        charts = await analytics_engine._generate_charts(
            ReportType.WEEKLY_ANALYSIS, [], start_date, end_date
        )

        # Filter by chart type if specified
        if chart_type:
            charts = [c for c in charts if c.get("type") == chart_type]

        return {
            "success": True,
            "charts": charts,
            "period_start": start_date,
            "period_end": end_date,
            "total_charts": len(charts),
        }

    except Exception as e:
        logger.error(f"Failed to get analytics charts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights")
async def get_analytics_insights(
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"])),
):
    """Get analytics insights"""
    try:
        # Parse dates
        start_date = None
        end_date = None

        if period_start:
            start_date = datetime.fromisoformat(period_start)
        if period_end:
            end_date = datetime.fromisoformat(period_end)

        # Set default period if not provided
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=7)
        if not end_date:
            end_date = datetime.now(timezone.utc)

        # Generate insights
        insights = await analytics_engine._generate_insights(
            ReportType.WEEKLY_ANALYSIS, [], start_date, end_date
        )

        return {
            "success": True,
            "insights": insights,
            "period_start": start_date,
            "period_end": end_date,
            "total_insights": len(insights),
        }

    except Exception as e:
        logger.error(f"Failed to get analytics insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/report/{report_id}")
async def delete_analytics_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["admin:full"])),
):
    """Delete analytics report"""
    try:
        # Find and remove report
        report_found = False
        for i, report in enumerate(analytics_engine.reports):
            if report.report_id == report_id:
                analytics_engine.reports.pop(i)
                report_found = True
                break

        if not report_found:
            raise HTTPException(status_code=404, detail="Report not found")

        return {"success": True, "message": f"Report {report_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete analytics report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_analytics_statistics(
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:read"])),
):
    """Get analytics statistics"""
    try:
        total_reports = len(analytics_engine.reports)

        # Calculate statistics by report type
        type_stats = {}
        for report in analytics_engine.reports:
            report_type = report.report_type.value
            if report_type not in type_stats:
                type_stats[report_type] = 0
            type_stats[report_type] += 1

        # Recent reports (last 7 days)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
        recent_reports = len(
            [r for r in analytics_engine.reports if r.generated_at > cutoff_date]
        )

        return {
            "success": True,
            "statistics": {
                "total_reports": total_reports,
                "recent_reports_7_days": recent_reports,
                "by_report_type": type_stats,
                "cache_status": "active",
                "last_updated": datetime.now(timezone.utc),
            },
        }

    except Exception as e:
        logger.error(f"Failed to get analytics statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
async def refresh_analytics_data(
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_permissions(["compliance:write"])),
):
    """Refresh analytics data"""
    try:
        # Clear cache
        analytics_engine.dashboard_cache.clear()

        # Reload data
        dashboard_data = await analytics_engine.get_dashboard_data()

        return {
            "success": True,
            "message": "Analytics data refreshed successfully",
            "timestamp": datetime.now(timezone.utc),
        }

    except Exception as e:
        logger.error(f"Failed to refresh analytics data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
