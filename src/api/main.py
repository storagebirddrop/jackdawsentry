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
from src.api.auth import get_current_user, User
from src.api.routers import (
    analysis,
    compliance,
    investigations,
    blockchain,
    intelligence,
    reports,
    admin
)
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
    await close_databases()
    logger.info("Application shutdown complete")


async def start_background_tasks():
    """Start background collection and analysis tasks"""
    from src.collectors.manager import CollectorManager
    from src.analysis.manager import AnalysisManager
    
    # Start blockchain collectors
    collector_manager = CollectorManager()
    await collector_manager.start_all()
    
    # Start analysis engine
    analysis_manager = AnalysisManager()
    await analysis_manager.start()


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

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.jackdawsentry.local"]
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
