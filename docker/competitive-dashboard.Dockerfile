# Competitive Dashboard Docker Image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-competitive.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-competitive.txt

# Copy competitive assessment code
COPY src/competitive/ ./src/competitive/
COPY scripts/run_competitive_benchmarking.py ./scripts/
COPY frontend/competitive-dashboard.html ./frontend/

# Create data directories
RUN mkdir -p /app/data /app/logs /app/reports

# Set environment variables
ENV PYTHONPATH=/app/src
ENV COMPETITIVE_DB_URL=postgresql://jackdaw:password@db:5432/jackdaw
ENV COMPETITIVE_REDIS_URL=redis://redis:6379
ENV COMPETITIVE_BASE_URL=http://api:8000

# Expose dashboard port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import aiohttp; asyncio.run(aiohttp.ClientSession().get('http://localhost:8080/api/summary'))" || exit 1

# Default command - start dashboard
CMD ["python", "scripts/run_competitive_benchmarking.py", "dashboard", "--data-dir", "/app/data"]
