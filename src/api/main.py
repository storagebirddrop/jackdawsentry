"""
Jackdaw Sentry - Main API Application
Enterprise-grade blockchain onchain analysis platform for crypto compliance
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import asyncio
from typing import Optional

from src.api.config import settings
from src.api.database import init_databases, close_databases
from src.api.auth import get_current_user, require_admin, User
from src.api.routers import (
    analysis,
    analytics,
    compliance,
    export,
    investigations,
    blockchain,
    intelligence,
    reports,
    admin,
    workflows,
    monitoring,
    rate_limit,
    visualization,
    scheduler,
    mobile,
    graph,
    sanctions,
)
from src.api.routers import auth as auth_router
from src.api.routers import setup as setup_router
from src.api.middleware import (
    SecurityMiddleware,
    AuditMiddleware,
    RateLimitMiddleware
)
from src.api.exceptions import (
    JackdawException,
    ComplianceException,
    BlockchainException
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
        
        # Start background tasks
        asyncio.create_task(start_background_tasks())
        logger.info("Background tasks started")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Jackdaw Sentry API...")
    await stop_background_tasks()
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
    from src.collectors.manager import CollectorManager
    from src.analysis.manager import AnalysisManager
    
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
    
    # Start sanctions sync background loop
    try:
        from src.services.sanctions import sync_all as _sanctions_sync
        _sanctions_task = asyncio.create_task(_sanctions_sync_loop(_sanctions_sync))
        tasks.append(_sanctions_task)
        logger.info("✅ Sanctions sync scheduler started (every 6h)")
    except Exception as e:
        logger.error(f"❌ Failed to start sanctions sync scheduler: {e}")

    # Store task references for monitoring and cleanup
    if hasattr(start_background_tasks, '_tasks'):
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


async def stop_background_tasks():
    """Stop all background tasks gracefully"""
    if not hasattr(start_background_tasks, '_tasks'):
        return
    
    logger.info("Stopping background tasks...")

    async_tasks = []
    for task in start_background_tasks._tasks:
        try:
            if isinstance(task, asyncio.Task):
                task.cancel()
                async_tasks.append(task)
            elif hasattr(task, 'stop_all'):
                await task.stop_all()
            elif hasattr(task, 'stop'):
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
                logger.error(f"❌ Async task {task.get_name()} error on cancel: {result}")
    
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
    lifespan=lifespan
)

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
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=allowed_hosts
)

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
            "timestamp": exc.timestamp
        }
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
            "timestamp": exc.timestamp
        }
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
            "timestamp": exc.timestamp
        }
    )


# Health check endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "service": "Jackdaw Sentry API",
        "version": "1.0.0",
        "timestamp": "2024-01-01T00:00:00Z"
    }


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Basic application metrics"""
    import time
    import os

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
        "timestamp": "2024-01-01T00:00:00Z"
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
            "gdpr_compliant": True
        }
    }


# Include routers
app.include_router(
    setup_router.router,
    prefix="/api/v1/setup",
    tags=["Setup"]
)

app.include_router(
    auth_router.router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

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
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    investigations.router,
    prefix="/api/v1/investigations",
    tags=["Investigations"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    blockchain.router,
    prefix="/api/v1/blockchain",
    tags=["Blockchain"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    graph.router,
    prefix="/api/v1/graph",
    tags=["Graph"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    sanctions.router,
    prefix="/api/v1/sanctions",
    tags=["Sanctions"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    intelligence.router,
    prefix="/api/v1/intelligence",
    tags=["Intelligence"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    reports.router,
    prefix="/api/v1/reports",
    tags=["Reports"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    admin.router,
    prefix="/api/v1/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    analytics.router,
    prefix="/api/v1/compliance/analytics",
    tags=["Analytics"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    export.router,
    prefix="/api/v1/compliance/export",
    tags=["Export"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    workflows.router,
    prefix="/api/v1/compliance/workflows",
    tags=["Workflows"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    monitoring.router,
    prefix="/api/v1/compliance/monitoring",
    tags=["Monitoring"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    rate_limit.router,
    prefix="/api/v1/compliance/rate-limit",
    tags=["Rate Limiting"],
    dependencies=[Depends(require_admin)]
)

app.include_router(
    visualization.router,
    prefix="/api/v1/compliance/visualization",
    tags=["Visualization"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    scheduler.router,
    prefix="/api/v1/compliance/scheduler",
    tags=["Scheduler"],
    dependencies=[Depends(require_admin)]
)

app.include_router(
    mobile.router,
    prefix="/api/v1/compliance/mobile",
    tags=["Mobile"],
    dependencies=[Depends(get_current_user)]
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
        "status": "/api/v1/status"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
