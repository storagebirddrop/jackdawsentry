"""
Jackdaw Sentry - Main API Application
Enterprise-grade blockchain onchain analysis platform for crypto compliance
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from .webhooks.competitive_webhooks import startup as webhook_startup, shutdown as webhook_shutdown
from .schedulers.competitive_scheduler import startup as scheduler_startup, shutdown as scheduler_shutdown


# Custom JSON encoder for datetime serialization
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# Custom JSONResponse class that uses our encoder
class CustomJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(
            content, cls=DateTimeEncoder, ensure_ascii=False, allow_nan=False
        ).encode("utf-8")


# Custom middleware to handle datetime serialization
class DateTimeMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Let the app handle the request first
            async def receive_wrapper():
                return await receive()

            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    # Modify the response to use our custom JSON response
                    pass
                elif message["type"] == "http.response.body":
                    # Try to serialize the body with our encoder
                    try:
                        if message.get("body"):
                            body = message["body"]
                            if isinstance(body, bytes):
                                # Try to decode and re-encode with datetime handling
                                try:
                                    content = json.loads(body.decode())
                                    serialized = json.dumps(
                                        content,
                                        cls=DateTimeEncoder,
                                        ensure_ascii=False,
                                        allow_nan=False,
                                    ).encode("utf-8")
                                    message["body"] = serialized
                                except:
                                    pass  # If it fails, use original body
                    except:
                        pass  # If anything fails, use original message
                await send(message)

            await self.app(scope, receive_wrapper, send_wrapper)
        else:
            await self.app(scope, receive, send)


from src.api.auth import User
from src.api.auth import get_current_user
from src.api.auth import require_admin
from src.api.config import settings
from src.api.database import close_databases
from src.api.database import init_databases
from src.api.exceptions import BlockchainException
from src.api.exceptions import ComplianceException
from src.api.exceptions import JackdawException
from src.api.middleware import AuditMiddleware
from src.api.middleware import RateLimitMiddleware
from src.api.middleware import SecurityMiddleware
from src.api.routers import (
    admin, analysis,  # Re-enabled for testing, analytics,  # Temporarily disabled due to dependency issues; advanced_analytics,  # Temporarily disabled due to dependency issues
)
from src.api.routers import alerts
from src.api.routers import attribution
from src.api.routers import auth as auth_router
from src.api.routers import blockchain
from src.api.routers import bulk
from src.api.routers import compliance
from src.api.routers import cross_platform
from src.api.routers import entities
from src.api.routers import export
from src.api.routers import forensics
from src.api.routers import graph
from src.api.routers import intelligence
from src.api.routers import investigations
from src.api.routers import mobile
from src.api.routers import monitoring
from src.api.routers import patterns
from src.api.routers import professional_services
from src.api.routers import rate_limit
from src.api.routers import reports
from src.api.routers import risk_config
from src.api.routers import sanctions
from src.api.routers import scheduler
from src.api.routers import setup
from src.api.routers import setup as setup_router
from src.api.routers import teams
from src.api.routers import threat_feeds
from src.api.routers import tracing
from src.api.routers import travel_rule
from src.api.routers import victim_reports
from src.api.routers import visualization
from src.api.routers import webhooks
from src.api.routers import workflows
from src.api.routers import competitive

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Jackdaw Sentry API...")

    try:
        # Initialize databases
        await init_databases()
        logger.info("Databases initialized successfully")

        # Ensure monitoring tables exist (alert_rules, alert_events)
        from src.monitoring.alert_rules import ensure_tables as ensure_alert_tables

        await ensure_alert_tables()
        logger.info("Alert tables ready")

        # Start background tasks
        asyncio.create_task(start_background_tasks())
        logger.info("Background tasks started")

        # Initialize competitive assessment systems
        await webhook_startup()
        await scheduler_startup()
        logger.info("Competitive assessment systems initialized")

    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Jackdaw Sentry API...")
    await stop_background_tasks()
    
    # Shutdown competitive assessment systems
    await webhook_shutdown()
    await scheduler_shutdown()
    logger.info("Competitive assessment systems shutdown")
    
    from src.collectors.rpc.factory import close_all_clients

    errors = []
    try:
        await close_all_clients()
    except Exception as exc:
        logger.error(f"Error closing RPC clients: {exc}", exc_info=True)
        errors.append(exc)
    try:
        await close_databases()
    except Exception as exc:
        logger.error(f"Error closing databases: {exc}", exc_info=True)
        errors.append(exc)
    if errors:
        logger.warning(f"Shutdown completed with {len(errors)} error(s)")
    else:
        logger.info("Application shutdown complete")


async def start_background_tasks():
    """Start background collection and analysis tasks with error handling"""
    from src.analysis.manager import AnalysisManager
    from src.analytics import get_analytics_engine
    from src.attribution import get_attribution_engine
    from src.collectors.manager import CollectorManager
    from src.forensics.court_defensible import get_court_defensible_evidence
    from src.forensics.evidence_manager import get_evidence_manager
    from src.forensics.forensic_engine import get_forensic_engine
    from src.forensics.report_generator import get_report_generator
    from src.intelligence.cross_platform import get_cross_platform_attribution_engine
    from src.intelligence.professional_services import get_professional_services_manager
    from src.intelligence.threat_feeds import get_threat_intelligence_manager
    from src.intelligence.victim_reports import get_victim_reports_db
    from src.patterns import get_pattern_detector

    tasks = []

    try:
        # Start blockchain collectors
        logger.info("Starting blockchain collectors...")
        collector_manager = CollectorManager()
        await collector_manager.start_all()
        tasks.append(collector_manager)
        logger.info("✅ Blockchain collectors started")

    except Exception as e:
        logger.error(f"❌ Failed to start blockchain collectors: {e}")
        # Continue with other tasks even if collectors fail

    try:
        # Start analysis engine
        logger.info("Starting analysis engine...")
        analysis_manager = AnalysisManager()
        await analysis_manager.start()
        tasks.append(analysis_manager)
        logger.info("✅ Analysis engine started")

    except Exception as e:
        logger.error(f"❌ Failed to start analysis engine: {e}")
        # Continue with other tasks even if analysis fails

    try:
        # Initialize attribution engine
        logger.info("Initializing attribution engine...")
        attribution_engine = get_attribution_engine()
        await attribution_engine.initialize()
        logger.info("✅ Attribution engine initialized")

    except Exception as e:
        logger.error(f"❌ Failed to initialize attribution engine: {e}")
        # Continue with other tasks even if attribution fails

    try:
        # Initialize pattern detector
        logger.info("Initializing pattern detector...")
        pattern_detector = get_pattern_detector()
        await pattern_detector.initialize()
        logger.info("✅ Pattern detector initialized")

    except Exception as e:
        logger.error(f"❌ Failed to initialize pattern detector: {e}")
        # Continue with other tasks even if patterns fail

    try:
        # Initialize advanced analytics engine
        logger.info("Initializing advanced analytics engine...")
        analytics_engine = get_analytics_engine()
        await analytics_engine.initialize()
        logger.info("✅ Advanced analytics engine initialized")

    except Exception as e:
        logger.error(f"❌ Failed to initialize advanced analytics engine: {e}")
        # Continue with other tasks even if analytics fails

    # Start sanctions sync background loop
    try:
        from src.services.sanctions import sync_all as _sanctions_sync

        _sanctions_task = asyncio.create_task(_sanctions_sync_loop(_sanctions_sync))
        tasks.append(_sanctions_task)
        logger.info("✅ Sanctions sync scheduler started (every 6h)")
    except Exception as e:
        logger.error(f"❌ Failed to start sanctions sync scheduler: {e}")

    # Start entity labels sync background loop
    try:
        from src.services.entity_attribution import sync_all_labels as _labels_sync

        _labels_task = asyncio.create_task(_labels_sync_loop(_labels_sync))
        tasks.append(_labels_task)
        logger.info("Entity labels sync scheduler started (every 24h)")
    except Exception as e:
        logger.error(f"Failed to start labels sync scheduler: {e}")

    # Start transaction monitoring pipeline (M12)
    try:
        from src.monitoring.tx_monitor import start_monitor

        start_monitor(chains=["ethereum", "bitcoin"])
        logger.info("Transaction monitor started (ethereum, bitcoin)")
    except Exception as e:
        logger.error(f"Failed to start transaction monitor: {e}")

    # Initialize Phase 4 Intelligence Integration Hub components
    try:
        # Initialize victim reports database
        logger.info("Initializing victim reports database...")
        victim_reports_db = await get_victim_reports_db()
        await victim_reports_db.initialize()
        logger.info("✅ Victim reports database initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize victim reports database: {e}")

    try:
        # Initialize threat intelligence manager
        logger.info("Initializing threat intelligence manager...")
        threat_manager = await get_threat_intelligence_manager()
        await threat_manager.initialize()
        logger.info("✅ Threat intelligence manager initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize threat intelligence manager: {e}")

    try:
        # Initialize cross-platform attribution engine
        logger.info("Initializing cross-platform attribution engine...")
        attribution_engine = await get_cross_platform_attribution_engine()
        await attribution_engine.initialize()
        logger.info("✅ Cross-platform attribution engine initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize cross-platform attribution engine: {e}")

    try:
        # Initialize professional services manager
        logger.info("Initializing professional services manager...")
        services_manager = await get_professional_services_manager()
        await services_manager.initialize()
        logger.info("✅ Professional services manager initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize professional services manager: {e}")

    try:
        # Initialize forensic engine
        logger.info("Initializing forensic engine...")
        forensic_engine = await get_forensic_engine()
        await forensic_engine.initialize()
        logger.info("✅ Forensic engine initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize forensic engine: {e}")

    try:
        # Initialize evidence manager
        logger.info("Initializing evidence manager...")
        evidence_manager = await get_evidence_manager()
        await evidence_manager.initialize()
        logger.info("✅ Evidence manager initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize evidence manager: {e}")

    try:
        # Initialize report generator
        logger.info("Initializing report generator...")
        report_generator = await get_report_generator()
        await report_generator.initialize()
        logger.info("✅ Report generator initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize report generator: {e}")

    try:
        # Initialize court defensible evidence system
        logger.info("Initializing court defensible evidence system...")
        court_defensible = await get_court_defensible_evidence()
        await court_defensible.initialize()
        logger.info("✅ Court defensible evidence system initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize court defensible evidence system: {e}")

    # Store task references for monitoring and cleanup
    if hasattr(start_background_tasks, "_tasks"):
        start_background_tasks._tasks.extend(tasks)
    else:
        start_background_tasks._tasks = tasks

    logger.info(f"✅ Background tasks started: {len(tasks)} managers running")


async def _sanctions_sync_loop(sync_fn, interval_seconds: int = 21600):
    """Run sanctions sync every *interval_seconds* (default 6 hours).

    First sync fires 60 s after startup to let DB connections settle.
    """
    await asyncio.sleep(60)
    while True:
        try:
            logger.info("Sanctions sync: starting scheduled run")
            result = await sync_fn(requested_by="scheduler")
            logger.info(f"Sanctions sync complete: {result}")
        except Exception as exc:
            logger.error(f"Sanctions sync failed: {exc}")
        await asyncio.sleep(interval_seconds)


async def _labels_sync_loop(sync_fn, interval_seconds: int = 86400):
    """Run entity label sync every *interval_seconds* (default 24 hours).

    First sync fires 120 s after startup to let DB connections settle.
    """
    await asyncio.sleep(120)
    while True:
        try:
            logger.info("Entity labels sync: starting scheduled run")
            result = await sync_fn(requested_by="scheduler")
            logger.info(f"Entity labels sync complete: {result}")
        except Exception as exc:
            logger.error(f"Entity labels sync failed: {exc}")
        await asyncio.sleep(interval_seconds)


async def stop_background_tasks():
    """Stop all background tasks gracefully"""
    if not hasattr(start_background_tasks, "_tasks"):
        return

    logger.info("Stopping background tasks...")

    async_tasks = []
    for task in start_background_tasks._tasks:
        try:
            if isinstance(task, asyncio.Task):
                task.cancel()
                async_tasks.append(task)
            elif hasattr(task, "stop_all"):
                await task.stop_all()
            elif hasattr(task, "stop"):
                await task.stop()
            logger.info(f"✅ Stopped task: {type(task).__name__}")
        except Exception as e:
            logger.error(f"❌ Failed to stop task {type(task).__name__}: {e}")

    if async_tasks:
        results = await asyncio.gather(*async_tasks, return_exceptions=True)
        for task, result in zip(async_tasks, results):
            if isinstance(result, asyncio.CancelledError):
                logger.info(f"✅ Cancelled async task: {task.get_name()}")
            elif isinstance(result, Exception):
                logger.error(
                    f"❌ Async task {task.get_name()} error on cancel: {result}"
                )

    start_background_tasks._tasks.clear()
    logger.info("✅ All background tasks stopped")


# Create FastAPI application
app = FastAPI(
    title="Jackdaw Sentry API",
    description="Enterprise-grade blockchain onchain analysis platform for crypto compliance",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    default_response_class=CustomJSONResponse,
)

import json as _json

# Override the default JSON response class
from fastapi.responses import JSONResponse

# Monkey patch the JSONResponse.render method to use our encoder
original_render = JSONResponse.render


def patched_render(self, content) -> bytes:
    try:
        return _json.dumps(
            content, cls=DateTimeEncoder, ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError):
        # Fallback to original render if our encoder fails
        return original_render(self, content)


JSONResponse.render = patched_render

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

allowed_hosts = ["localhost", "127.0.0.1", "*.jackdawsentry.local"]
if settings.DEBUG or settings.TESTING:
    allowed_hosts.append("testclient")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

app.add_middleware(SecurityMiddleware)
app.add_middleware(AuditMiddleware)
app.add_middleware(RateLimitMiddleware)


# Exception handlers
@app.exception_handler(JackdawException)
async def jackdaw_exception_handler(request, exc: JackdawException):
    """Handle Jackdaw-specific exceptions"""
    logger.error(f"JackdawException: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "JackdawError",
            "message": exc.message,
            "code": exc.error_code,
            "timestamp": exc.timestamp,
        },
    )


@app.exception_handler(ComplianceException)
async def compliance_exception_handler(request, exc: ComplianceException):
    """Handle compliance-related exceptions"""
    logger.error(f"ComplianceException: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "ComplianceError",
            "message": exc.message,
            "regulation": exc.regulation,
            "timestamp": exc.timestamp,
        },
    )


@app.exception_handler(BlockchainException)
async def blockchain_exception_handler(request, exc: BlockchainException):
    """Handle blockchain-related exceptions"""
    logger.error(f"BlockchainException: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "BlockchainError",
            "message": exc.message,
            "blockchain": exc.blockchain,
            "timestamp": exc.timestamp,
        },
    )


# Health check endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "service": "Jackdaw Sentry API",
        "version": "1.0.0",
        "timestamp": "2024-01-01T00:00:00Z",
    }


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Basic application metrics"""
    import os
    import time

    process = None
    try:
        import psutil

        process = psutil.Process(os.getpid())
    except Exception:
        pass

    mem_mb = process.memory_info().rss / 1024 / 1024 if process else None
    cpu_pct = process.cpu_percent() if process else None

    return {
        "uptime_seconds": time.monotonic(),
        "memory_usage_mb": round(mem_mb, 1) if mem_mb is not None else None,
        "cpu_percent": cpu_pct,
        "version": "1.0.0",
    }


@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check():
    """Detailed health check with database status"""
    from src.api.database import check_database_health

    db_health = await check_database_health()

    return {
        "status": "healthy" if all(db_health.values()) else "degraded",
        "service": "Jackdaw Sentry API",
        "version": "1.0.0",
        "databases": db_health,
        "timestamp": "2024-01-01T00:00:00Z",
    }


@app.get("/api/v1/status", tags=["Status"])
async def api_status(current_user: User = Depends(get_current_user)):
    """API status for authenticated users"""
    return {
        "status": "operational",
        "user": current_user.username,
        "permissions": current_user.permissions,
        "features": {
            "multi_chain": True,
            "lightning_network": True,
            "stablecoin_tracking": True,
            "compliance_reporting": True,
            "gdpr_compliant": True,
        },
    }


# Include routers
app.include_router(setup_router.router, prefix="/api/v1/setup", tags=["Setup"])

app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["Authentication"])

app.include_router(
    analysis.router,
    prefix="/api/v1/analysis",
    tags=["Analysis"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    compliance.router,
    prefix="/api/v1/compliance",
    tags=["Compliance"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    investigations.router,
    prefix="/api/v1/investigations",
    tags=["Investigations"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    blockchain.router,
    prefix="/api/v1/blockchain",
    tags=["Blockchain"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    graph.router,
    prefix="/api/v1/graph",
    tags=["Graph"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    sanctions.router,
    prefix="/api/v1/sanctions",
    tags=["Sanctions"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    entities.router,
    prefix="/api/v1/entities",
    tags=["Entities"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    alerts.router,
    prefix="/api/v1/alerts",
    tags=["Alerts"],
)

app.include_router(
    attribution.router,
    prefix="/api/v1/attribution",
    tags=["Attribution"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    patterns.router,
    prefix="/api/v1/patterns",
    tags=["Patterns"],
    dependencies=[Depends(get_current_user)],
)

# app.include_router(
#     advanced_analytics.router,
#     prefix="/api/v1/analytics",
#     tags=["Advanced Analytics"],
#     dependencies=[Depends(get_current_user)]
# )

app.include_router(
    tracing.router,
    prefix="/api/v1/tracing",
    tags=["Tracing"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    risk_config.router,
    prefix="/api/v1",
    tags=["Risk Config"],
)

app.include_router(
    intelligence.router,
    prefix="/api/v1/intelligence",
    tags=["Intelligence"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    victim_reports.router,
    prefix="/api/v1/intelligence/victim-reports",
    tags=["Victim Reports"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    threat_feeds.router,
    prefix="/api/v1/intelligence/threat-feeds",
    tags=["Threat Feeds"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    cross_platform.router,
    prefix="/api/v1/intelligence/attribution",
    tags=["Cross-Platform Attribution"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    professional_services.router,
    prefix="/api/v1/intelligence/professional-services",
    tags=["Professional Services"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    forensics.router,
    prefix="/api/v1/forensics",
    tags=["Forensics"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    reports.router,
    prefix="/api/v1/reports",
    tags=["Reports"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    admin.router,
    prefix="/api/v1/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_user)],
)

# app.include_router(
#     analytics.router,
#     prefix="/api/v1/compliance/analytics",
#     tags=["Analytics"],
#     dependencies=[Depends(get_current_user)]
# )

app.include_router(
    export.router,
    prefix="/api/v1/compliance/export",
    tags=["Export"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    workflows.router,
    prefix="/api/v1/compliance/workflows",
    tags=["Workflows"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    monitoring.router,
    prefix="/api/v1/compliance/monitoring",
    tags=["Monitoring"],
    dependencies=[Depends(get_current_user)],
)

# Add competitive assessment router
app.include_router(
    competitive.router,
    prefix="/api/competitive",
    tags=["Competitive Assessment"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    rate_limit.router,
    prefix="/api/v1/compliance/rate-limit",
    tags=["Rate Limiting"],
    dependencies=[Depends(require_admin)],
)

app.include_router(
    visualization.router,
    prefix="/api/v1/compliance/visualization",
    tags=["Visualization"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    scheduler.router,
    prefix="/api/v1/compliance/scheduler",
    tags=["Scheduler"],
    dependencies=[Depends(require_admin)],
)

app.include_router(
    mobile.router,
    prefix="/api/v1/compliance/mobile",
    tags=["Mobile"],
    dependencies=[Depends(get_current_user)],
)

app.include_router(
    teams.router,
    prefix="/api/v1/teams",
    tags=["Teams"],
)

app.include_router(
    webhooks.router,
    prefix="/api/v1/webhooks",
    tags=["Webhooks"],
)

app.include_router(
    travel_rule.router,
    prefix="/api/v1/travel-rule",
    tags=["Travel Rule"],
)

app.include_router(
    bulk.router,
    prefix="/api/v1/bulk",
    tags=["Bulk"],
)


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Jackdaw Sentry API",
        "description": "Enterprise-grade blockchain onchain analysis platform",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "status": "/api/v1/status",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
