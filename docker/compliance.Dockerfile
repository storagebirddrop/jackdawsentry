# Jackdaw Sentry Compliance Service Docker Image
# Multi-stage build for compliance microservice

FROM python:3.14-slim AS builder

# Set environment variables for build
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Compliance-specific dependencies
RUN pip install --no-cache-dir \
    neo4j-driver \
    redis \
    aiohttp \
    pydantic \
    fastapi \
    uvicorn

# Production stage
FROM python:3.14-slim

# Create non-root user for security
RUN groupadd -r compliance && useradd -r -g compliance compliance

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV COMPLIANCE_SERVICE_PORT=8001
ENV COMPLIANCE_LOG_LEVEL=INFO

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy application code
COPY --chown=compliance:compliance . .

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create compliance-specific directories
RUN mkdir -p /app/logs /app/data/compliance /app/uploads/compliance /app/cache/compliance && \
    chown -R compliance:compliance /app/logs /app/data /app/uploads /app/cache

# Create compliance configuration
RUN mkdir -p /app/config/compliance && \
    echo '{"service": "compliance", "version": "1.5.0", "environment": "production"}' > /app/config/compliance/service.json && \
    chown -R compliance:compliance /app/config

# Health check script
COPY --chown=compliance:compliance <<EOF /app/healthcheck.sh
#!/bin/bash
# Health check for compliance service
curl -f http://localhost:8001/health || exit 1
curl -f http://localhost:8001/api/v1/compliance/health || exit 1
# Check database connectivity
python -c "
import asyncio
import sys
sys.path.append('/app')
try:
    from src.database.neo4j_client import get_neo4j_session
    from src.cache.redis_client import get_redis_client
    async def check():
        try:
            neo4j = await get_neo4j_session()
            await neo4j.run('RETURN 1')
            redis = await get_redis_client()
            await redis.ping()
            print('Health check passed')
        except Exception as e:
            print(f'Health check failed: {e}')
            sys.exit(1)
    asyncio.run(check())
except Exception as e:
    print(f'Health check error: {e}')
    sys.exit(1)
"
EOF

RUN chmod +x /app/healthcheck.sh

# Switch to compliance user
USER compliance

# Expose compliance service port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /app/healthcheck.sh

# Start compliance service
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4", "--log-level", "info"]
