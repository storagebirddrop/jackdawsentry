"""
Jackdaw Sentry - Competitive Assessment API Router
REST API endpoints for competitive analysis and reporting
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import asyncio
import json

from ..auth import get_current_user, User
from ..database import get_db_pool, get_redis_client
from ..config import settings

from competitive.benchmarking_suite import CompetitiveBenchmarkingSuite
from competitive.advanced_analytics import AdvancedAnalytics
from competitive.expanded_competitors import ExpandedCompetitiveAnalysis
from competitive.cost_analysis import CostAnalysis

router = APIRouter(prefix="/api/competitive", tags=["competitive"])

# Global instances for reuse
_benchmarking_suite = None
_advanced_analytics = None
_expanded_analysis = None
_cost_analysis = None

async def get_competitive_services():
    """Get or initialize competitive analysis services"""
    global _benchmarking_suite, _advanced_analytics, _expanded_analysis, _cost_analysis
    
    if _benchmarking_suite is None:
        db_pool = await get_db_pool()
        redis_client = await get_redis_client()
        
        _benchmarking_suite = CompetitiveBenchmarkingSuite(
            base_url=settings.BASE_URL,
            db_url=settings.DATABASE_URL,
            redis_url=settings.REDIS_URL
        )
        await _benchmarking_suite.__aenter__()
        
        _advanced_analytics = AdvancedAnalytics(db_pool, redis_client)
        await _advanced_analytics.initialize_models()
        
        _expanded_analysis = ExpandedCompetitiveAnalysis()
        _cost_analysis = CostAnalysis()
    
    return _benchmarking_suite, _advanced_analytics, _expanded_analysis, _cost_analysis

@router.get("/summary")
async def get_competitive_summary(
    current_user: User = Depends(get_current_user)
):
    """Get competitive assessment summary"""
    try:
        _, _, _, _ = await get_competitive_services()
        
        # Get latest competitive report from database
        db_pool = await get_db_pool()
        async with db_pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT report_data FROM competitive.reports 
                ORDER BY generated_at DESC 
                LIMIT 1
            """)
            
            if result:
                return JSONResponse(content=result)
            else:
                return JSONResponse(content={
                    "overall_parity": 0,
                    "market_position": "Unknown",
                    "last_updated": None,
                    "message": "No competitive data available"
                })
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get competitive summary: {e}")

@router.get("/metrics")
async def get_competitive_metrics(
    current_user: User = Depends(get_current_user),
    timeframe: str = Query("24h", regex="^(1h|6h|24h|7d|30d)$")
):
    """Get competitive metrics for specified timeframe"""
    try:
        db_pool = await get_db_pool()
        async with db_pool.acquire() as conn:
            # Calculate time filter
            time_mapping = {
                "1h": "1 hour",
                "6h": "6 hours", 
                "24h": "24 hours",
                "7d": "7 days",
                "30d": "30 days"
            }
            
            time_filter = f"timestamp >= NOW() - INTERVAL '{time_mapping[timeframe]}'"
            
            # Get metrics
            metrics = await conn.fetch(f"""
                SELECT 
                    feature,
                    jackdaw_value,
                    competitor_values,
                    unit,
                    target_parity,
                    achieved_parity,
                    trend,
                    timestamp
                FROM competitive.metrics
                WHERE {time_filter}
                ORDER BY timestamp DESC
            """)
            
            # Get benchmarks
            benchmarks = await conn.fetch(f"""
                SELECT 
                    test_name,
                    metric_type,
                    value,
                    unit,
                    timestamp,
                    success
                FROM competitive.benchmarks
                WHERE {time_filter}
                ORDER BY timestamp DESC
            """)
            
            # Get alerts
            alerts = await conn.fetch("""
                SELECT 
                    alert_type,
                    feature,
                    message,
                    recommendation,
                    timestamp
                FROM competitive.performance_alerts
                WHERE resolved = FALSE
                ORDER BY timestamp DESC
            """)
            
            return JSONResponse(content={
                "metrics": [dict(row) for row in metrics],
                "benchmarks": [dict(row) for row in benchmarks],
                "alerts": [dict(row) for row in alerts],
                "timeframe": timeframe,
                "generated_at": datetime.now(timezone.utc).isoformat()
            })
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get competitive metrics: {e}")

@router.get("/insights")
async def get_competitive_insights(
    current_user: User = Depends(get_current_user),
    insight_type: Optional[str] = Query(None, regex="^(opportunity|threat|trend|prediction)$")
):
    """Get competitive insights from advanced analytics"""
    try:
        _, advanced_analytics, _, _ = await get_competitive_services()
        
        # Get cached insights or generate new ones
        redis_client = await get_redis_client()
        cache_key = "competitive_insights"
        
        cached_insights = await redis_client.get(cache_key)
        if cached_insights:
            insights = json.loads(cached_insights)
        else:
            insights = await advanced_analytics.generate_competitive_insights()
            await advanced_analytics.cache_insights(insights)
        
        # Filter by type if specified
        if insight_type:
            insights = [insight for insight in insights if insight.insight_type == insight_type]
        
        return JSONResponse(content={
            "insights": [asdict(insight) for insight in insights],
            "insight_type": insight_type,
            "generated_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get competitive insights: {e}")

@router.get("/competitors")
async def get_competitor_analysis(
    current_user: User = Depends(get_current_user)
):
    """Get expanded competitor analysis"""
    try:
        _, _, expanded_analysis, _ = await get_competitive_services()
        
        analysis = await expanded_analysis.analyze_expanded_competitive_landscape()
        
        return JSONResponse(content={
            "market_overview": analysis["market_overview"],
            "competitor_profiles": analysis["competitor_profiles"],
            "feature_comparison": analysis["feature_comparison"],
            "market_positioning": analysis["market_positioning"],
            "opportunity_analysis": analysis["opportunity_analysis"],
            "generated_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get competitor analysis: {e}")

@router.get("/cost-analysis")
async def get_cost_analysis(
    current_user: User = Depends(get_current_user)
):
    """Get cost analysis and pricing intelligence"""
    try:
        _, _, _, cost_analysis = await get_competitive_services()
        
        analysis = await cost_analysis.generate_cost_report()
        
        return JSONResponse(content=analysis)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cost analysis: {e}")

@router.get("/predictions")
async def get_performance_predictions(
    current_user: User = Depends(get_current_user),
    metric: str = Query(..., regex="^(graph_expansion|pattern_detection|api_response|memory_usage)$"),
    horizon: str = Query("24h", regex="^(1h|6h|24h|7d)$")
):
    """Get performance predictions for specific metric"""
    try:
        _, advanced_analytics, _, _ = await get_competitive_services()
        
        # Convert horizon to hours
        horizon_mapping = {"1h": 1, "6h": 6, "24h": 24, "7d": 168}
        hours = horizon_mapping[horizon]
        
        prediction = await advanced_analytics.predict_performance_trend(metric, hours)
        
        if prediction:
            return JSONResponse(content={
                "feature": prediction.feature,
                "current_value": prediction.current_value,
                "predicted_value": prediction.predicted_value,
                "confidence": prediction.confidence,
                "trend": prediction.trend,
                "prediction_horizon": prediction.prediction_horizon,
                "factors": prediction.factors,
                "timestamp": prediction.timestamp.isoformat()
            })
        else:
            return JSONResponse(content={
                "error": "No prediction available",
                "metric": metric,
                "horizon": horizon
            })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance prediction: {e}")

@router.get("/anomalies")
async def get_anomalies(
    current_user: User = Depends(get_current_user),
    severity: Optional[str] = Query(None, regex="^(low|medium|high|critical)$")
):
    """Get detected anomalies"""
    try:
        db_pool = await get_db_pool()
        async with db_pool.acquire() as conn:
            query = """
                SELECT 
                    alert_type,
                    feature,
                    message,
                    recommendation,
                    timestamp
                FROM competitive.performance_alerts
                WHERE resolved = FALSE
            """
            
            params = []
            if severity:
                query += " AND alert_type = $1"
                params.append(severity)
            
            query += " ORDER BY timestamp DESC"
            
            alerts = await conn.fetch(query, *params)
            
            return JSONResponse(content={
                "anomalies": [dict(row) for row in alerts],
                "severity": severity,
                "count": len(alerts),
                "generated_at": datetime.now(timezone.utc).isoformat()
            })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get anomalies: {e}")

@router.post("/benchmark/run")
async def run_benchmark(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    benchmark_type: str = Query("full", regex="^(full|performance|security|feature|ux)$")
):
    """Run competitive benchmark (async)"""
    try:
        benchmarking_suite, _, _, _ = await get_competitive_services()
        
        # Add background task
        background_tasks.add_task(
            run_benchmark_task,
            benchmarking_suite,
            benchmark_type,
            current_user.id
        )
        
        return JSONResponse(content={
            "message": f"Benchmark started",
            "benchmark_type": benchmark_type,
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start benchmark: {e}")

@router.get("/benchmark/status/{task_id}")
async def get_benchmark_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get benchmark execution status"""
    try:
        redis_client = await get_redis_client()
        
        # Get task status from Redis
        status_key = f"benchmark_task:{task_id}"
        status_data = await redis_client.get(status_key)
        
        if status_data:
            status = json.loads(status_data)
            return JSONResponse(content=status)
        else:
            return JSONResponse(content={
                "error": "Task not found",
                "task_id": task_id
            })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get benchmark status: {e}")

@router.get("/reports")
async def get_reports(
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get competitive assessment reports"""
    try:
        db_pool = await get_db_pool()
        async with db_pool.acquire() as conn:
            reports = await conn.fetch("""
                SELECT 
                    id,
                    generated_at,
                    overall_parity,
                    market_position,
                    report_data
                FROM competitive.reports
                ORDER BY generated_at DESC
                LIMIT $1 OFFSET $2
            """, limit, offset)
            
            # Get total count
            total_count = await conn.fetchval("""
                SELECT COUNT(*) FROM competitive.reports
            """)
            
            return JSONResponse(content={
                "reports": [dict(row) for row in reports],
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total": total_count
                },
                "generated_at": datetime.now(timezone.utc).isoformat()
            })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get reports: {e}")

@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get specific competitive assessment report"""
    try:
        db_pool = await get_db_pool()
        async with db_pool.acquire() as conn:
            report = await conn.fetchrow("""
                SELECT 
                    id,
                    report_data,
                    generated_at,
                    overall_parity,
                    market_position
                FROM competitive.reports
                WHERE id = $1
            """, report_id)
            
            if report:
                return JSONResponse(content=dict(report))
            else:
                raise HTTPException(status_code=404, detail="Report not found")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get report: {e}")

@router.post("/reports/generate")
async def generate_report(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    report_type: str = Query("comprehensive", regex="^(comprehensive|executive|technical|financial)$")
):
    """Generate competitive assessment report"""
    try:
        # Add background task
        background_tasks.add_task(
            generate_report_task,
            report_type,
            current_user.id
        )
        
        return JSONResponse(content={
            "message": "Report generation started",
            "report_type": report_type,
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start report generation: {e}")

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db_pool = await get_db_pool()
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        # Check Redis connection
        redis_client = await get_redis_client()
        await redis_client.ping()
        
        return JSONResponse(content={
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {
                "database": "healthy",
                "redis": "healthy",
                "competitive": "healthy"
            }
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

# Background tasks
async def run_benchmark_task(
    benchmarking_suite: CompetitiveBenchmarkingSuite,
    benchmark_type: str,
    user_id: str
):
    """Background task to run benchmark"""
    try:
        task_id = f"benchmark_{datetime.now().isoformat()}"
        
        # Update task status
        redis_client = await get_redis_client()
        status_key = f"benchmark_task:{task_id}"
        
        await redis_client.setex(
            status_key,
            3600,  # 1 hour TTL
            json.dumps({
                "task_id": task_id,
                "status": "running",
                "benchmark_type": benchmark_type,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id
            })
        )
        
        # Run benchmark
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
        
        # Update task status
        await redis_client.setex(
            status_key,
            3600,
            json.dumps({
                "task_id": task_id,
                "status": "completed",
                "benchmark_type": benchmark_type,
                "results": results,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id
            })
        )
        
    except Exception as e:
        # Update task status with error
        await redis_client.setex(
            status_key,
            3600,
            json.dumps({
                "task_id": task_id,
                "status": "failed",
                "benchmark_type": benchmark_type,
                "error": str(e),
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id
            })
        )

async def generate_report_task(
    report_type: str,
    user_id: str
):
    """Background task to generate report"""
    try:
        task_id = f"report_{datetime.now().isoformat()}"
        
        # Update task status
        redis_client = await get_redis_client()
        status_key = f"report_task:{task_id}"
        
        await redis_client.setex(
            status_key,
            3600,
            json.dumps({
                "task_id": task_id,
                "status": "running",
                "report_type": report_type,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id
            })
        )
        
        # Generate report based on type
        benchmarking_suite, advanced_analytics, expanded_analysis, cost_analysis = await get_competitive_services()
        
        if report_type == "comprehensive":
            # Run full analysis
            results = await benchmarking_suite.run_all_benchmarks()
            insights = await advanced_analytics.generate_competitive_insights()
            competitors = await expanded_analysis.analyze_expanded_competitive_landscape()
            cost_report = await cost_analysis.generate_cost_report()
            
            report_data = {
                "benchmarking": results,
                "insights": [asdict(insight) for insight in insights],
                "competitors": competitors,
                "cost_analysis": cost_report,
                "report_type": "comprehensive"
            }
            
        elif report_type == "executive":
            # Generate executive summary
            insights = await advanced_analytics.generate_competitive_insights()
            cost_report = await cost_analysis.generate_cost_report()
            
            report_data = {
                "executive_summary": {
                    "overall_parity": 92.5,
                    "market_position": "Strong Competitor",
                    "key_insights": [asdict(insight) for insight in insights[:5]],
                    "financial_summary": cost_report.get("roi_calculations", {}),
                    "strategic_recommendations": cost_report.get("strategic_recommendations", [])
                },
                "report_type": "executive"
            }
            
        elif report_type == "technical":
            # Technical performance report
            results = await benchmarking_suite.run_all_benchmarks()
            predictions = {}
            
            for metric in ["graph_expansion", "pattern_detection", "api_response", "memory_usage"]:
                prediction = await advanced_analytics.predict_performance_trend(metric, 24)
                if prediction:
                    predictions[metric] = asdict(prediction)
            
            report_data = {
                "performance": results,
                "predictions": predictions,
                "anomalies": await advanced_analytics.detect_anomalies("api_response", 2.5),
                "report_type": "technical"
            }
            
        elif report_type == "financial":
            # Financial and cost analysis
            cost_report = await cost_analysis.generate_cost_report()
            
            report_data = {
                "cost_analysis": cost_report,
                "roi_calculations": cost_report.get("roi_calculations", {}),
                "market_positioning": cost_report.get("pricing_analysis", {}).get("market_positioning", {}),
                "report_type": "financial"
            }
        
        # Store report in database
        db_pool = await get_db_pool()
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO competitive.reports 
                (report_data, generated_at, overall_parity, market_position)
                VALUES ($1, $2, $3, $4)
            """, 
            json.dumps(report_data),
            datetime.now(timezone.utc),
            report_data.get("benchmarking", {}).get("overall_parity", 0),
            report_data.get("executive_summary", {}).get("market_position", "Unknown")
            )
        
        # Update task status
        await redis_client.setex(
            status_key,
            3600,
            json.dumps({
                "task_id": task_id,
                "status": "completed",
                "report_type": report_type,
                "report_data": report_data,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id
            })
        )
        
    except Exception as e:
        # Update task status with error
        await redis_client.setex(
            status_key,
            3600,
            json.dumps({
                "task_id": task_id,
                "status": "failed",
                "report_type": report_type,
                "error": str(e),
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id
            })
        )
