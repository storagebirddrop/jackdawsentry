"""
Jackdaw Sentry - Minimal API Application
Basic FastAPI app for testing infrastructure
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Jackdaw Sentry API",
    description="Enterprise-grade blockchain onchain analysis platform",
    version="1.6.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic health check endpoint
@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "jackdawsentry-api",
        "version": "1.6.0",
        "timestamp": "2024-01-21T00:00:00Z"
    }

# Basic info endpoint
@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    """Root endpoint"""
    return {
        "message": "Jackdaw Sentry API",
        "version": "1.6.0",
        "status": "running",
        "docs": "/docs"
    }

# Basic status endpoint
@app.get("/status", status_code=status.HTTP_200_OK)
async def api_status():
    """API status endpoint"""
    return {
        "api": "operational",
        "infrastructure": "healthy",
        "databases": "connected",
        "compliance": "enabled"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
