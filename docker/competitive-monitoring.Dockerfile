# Dockerfile for Competitive Monitoring Service
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN groupadd -r competitive && useradd -r -g competitive competitive

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/reports

# Set permissions
RUN chown -R competitive:competitive /app
USER competitive

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV COMPETITIVE_ENV=production
ENV LOG_LEVEL=INFO
ENV COMPETITIVE_BASE_URL=http://api:8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import src.competitive.benchmarking_suite; print('ok')" || exit 1

# Start command - run scheduled benchmarks
CMD ["python", "scripts/run_competitive_benchmarking.py", "benchmark", "--output-dir", "/app/reports"]
