# Jackdaw Sentry Deployment Guide

## Overview

This guide covers deploying Jackdaw Sentry in production environments, including Docker deployment, Kubernetes configuration, monitoring setup, and security best practices.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Environment Configuration](#environment-configuration)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Database Setup](#database-setup)
6. [Monitoring & Logging](#monitoring--logging)
7. [Security Configuration](#security-configuration)
8. [Performance Tuning](#performance-tuning)
9. [Backup & Recovery](#backup--recovery)
10. [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements

- **CPU**: 8 cores
- **Memory**: 32GB RAM
- **Storage**: 500GB SSD
- **Network**: 1Gbps
- **OS**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+

### Recommended Requirements

- **CPU**: 16 cores
- **Memory**: 64GB RAM
- **Storage**: 1TB NVMe SSD
- **Network**: 10Gbps
- **OS**: Ubuntu 22.04 LTS

### External Dependencies

- **Neo4j 5.x**: Graph database
- **PostgreSQL 14+**: Compliance database
- **Redis 7.x**: Caching and message queue
- **Prometheus**: Metrics collection
- **Grafana**: Visualization dashboard

## Environment Configuration

### Environment Variables

Create a `.env` file with the following configuration:

```bash
# =============================================================================
# API Configuration
# =============================================================================
API_HOST=0.0.0.0
API_PORT=8000
API_SECRET_KEY=your-super-secret-jwt-key-here-min-32-chars
API_ALGORITHM=HS256
API_ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS Settings
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# =============================================================================
# Database Configuration
# =============================================================================

# Neo4j Graph Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password
NEO4J_DATABASE=neo4j

# PostgreSQL Compliance Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=jackdawsentry_compliance
POSTGRES_USER=jackdawsentry_user
POSTGRES_PASSWORD=your-postgres-password

# Redis Cache & Message Queue
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password
REDIS_DB=0

# =============================================================================
# Blockchain RPC Configuration
# =============================================================================

# Bitcoin
BITCOIN_RPC_URL=http://localhost:8332
BITCOIN_RPC_USER=your-bitcoin-rpc-user
BITCOIN_RPC_PASSWORD=your-bitcoin-rpc-password

# Ethereum
ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/your-project-id
ETHEREUM_WS_URL=wss://mainnet.infura.io/ws/v3/your-project-id

# Solana
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com

# Add other blockchain RPCs as needed...

# =============================================================================
# External Services
# =============================================================================

# Claude AI (for narrative generation)
CLAUDE_API_KEY=your-claude-api-key

# Notification Services
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=your-email@gmail.com
EMAIL_SMTP_PASSWORD=your-email-password

# =============================================================================
# Monitoring & Logging
# =============================================================================

# Prometheus
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/jackdawsentry/app.log

# Sentry (error tracking)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# =============================================================================
# Security & Compliance
# =============================================================================

# GDPR Settings
DATA_RETENTION_DAYS=2557  # 7 years, including leap years
GDPR_ENABLED=true

# Encryption
ENCRYPTION_KEY=your-32-character-encryption-key-here

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=1000
RATE_LIMIT_BURST=100

# =============================================================================
# Performance Settings
# =============================================================================

# Connection Pools
POSTGRES_POOL_SIZE=20
POSTGRES_MAX_OVERFLOW=30
NEO4J_MAX_CONNECTION_POOL_SIZE=50
REDIS_CONNECTION_POOL_SIZE=20

# Cache Settings
CACHE_TTL_SECONDS=3600
CACHE_MAX_SIZE=10000

# Async Settings
MAX_CONCURRENT_REQUESTS=1000
REQUEST_TIMEOUT_SECONDS=300
```

### Configuration Validation

```bash
# Validate environment variables
python scripts/validate_config.py

# Check database connectivity
python scripts/check_databases.py
```

## Docker Deployment

### Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/jackdawsentry.git
cd jackdawsentry

# Copy environment template
cp .env.example .env
# Edit .env with your configuration

# Start services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f api
```

### Docker Compose Configuration

```yaml
version: '3.8'

services:
  # Main API Service
  api:
    build:
      context: .
      dockerfile: docker/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - PYTHONPATH=/app
      - NEO4J_URI=bolt://neo4j:7687
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
    env_file:
      - .env
    depends_on:
      - postgres
      - neo4j
      - redis
    volumes:
      - ./logs:/var/log/jackdawsentry
      - ./uploads:/app/uploads
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # PostgreSQL Database
  postgres:
    image: postgres:14-alpine
    environment:
      POSTGRES_DB: jackdawsentry_compliance
      POSTGRES_USER: jackdawsentry_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U jackdawsentry_user -d jackdawsentry_compliance"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Neo4j Graph Database
  neo4j:
    image: neo4j:5.15-community
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
      NEO4J_dbms_memory_heap_initial__size: 2G
      NEO4J_dbms_memory_heap_max__size: 4G
      NEO4J_dbms_memory_pagecache_size: 2G
      NEO4J_dbms_security_procedures_unrestricted: gds.*,apoc.*
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - neo4j_import:/var/lib/neo4j/import
      - neo4j_plugins:/plugins
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "/docker/neo4j/healthcheck.sh"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    command: redis-server /usr/local/etc/redis/redis.conf
    volumes:
      - redis_data:/data
      - ./docker/redis/redis.conf:/usr/local/etc/redis/redis.conf
    ports:
      - "6379:6379"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./docker/nginx/ssl:/etc/nginx/ssl
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - api
    restart: unless-stopped

  # Prometheus Monitoring
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./docker/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    restart: unless-stopped

  # Grafana Dashboard
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./docker/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./docker/grafana/datasources:/etc/grafana/provisioning/datasources
    depends_on:
      - prometheus
    restart: unless-stopped

volumes:
  postgres_data:
  neo4j_data:
  neo4j_logs:
  neo4j_import:
  neo4j_plugins:
  redis_data:
  prometheus_data:
  grafana_data:

networks:
  default:
    driver: bridge
```

### Production Dockerfile

```dockerfile
# Multi-stage build for production
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim as production

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash jackdawsentry

# Copy Python packages from builder
COPY --from=builder /root/.local /home/jackdawsentry/.local

# Copy application code
COPY --chown=jackdawsentry:jackdawsentry . .

# Set permissions
RUN chown -R jackdawsentry:jackdawsentry /app

# Switch to non-root user
USER jackdawsentry

# Set PATH
ENV PATH=/home/jackdawsentry/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Expose port
EXPOSE 8000

# Start application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Kubernetes Deployment

### Namespace Configuration

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: jackdawsentry
  labels:
    name: jackdawsentry
```

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: jackdawsentry-config
  namespace: jackdawsentry
data:
  API_HOST: "0.0.0.0"
  API_PORT: "8000"
  LOG_LEVEL: "INFO"
  PROMETHEUS_ENABLED: "true"
  RATE_LIMIT_REQUESTS_PER_MINUTE: "1000"
```

### Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: jackdawsentry-secrets
  namespace: jackdawsentry
type: Opaque
data:
  API_SECRET_KEY: <base64-encoded-secret>
  POSTGRES_PASSWORD: <base64-encoded-password>
  NEO4J_PASSWORD: <base64-encoded-password>
  REDIS_PASSWORD: <base64-encoded-password>
  CLAUDE_API_KEY: <base64-encoded-key>
```

### API Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jackdawsentry-api
  namespace: jackdawsentry
  labels:
    app: jackdawsentry-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: jackdawsentry-api
  template:
    metadata:
      labels:
        app: jackdawsentry-api
    spec:
      containers:
      - name: api
        image: jackdawsentry/api:v1.0.0
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: jackdawsentry-config
        - secretRef:
            name: jackdawsentry-secrets
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: jackdawsentry-api-service
  namespace: jackdawsentry
spec:
  selector:
    app: jackdawsentry-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
```

### Ingress Configuration

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: jackdawsentry-ingress
  namespace: jackdawsentry
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "1000"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
spec:
  tls:
  - hosts:
    - api.jackdawsentry.com
    secretName: jackdawsentry-tls
  rules:
  - host: api.jackdawsentry.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: jackdawsentry-api-service
            port:
              number: 80
```

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: jackdawsentry-api-hpa
  namespace: jackdawsentry
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: jackdawsentry-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Database Setup

### PostgreSQL Configuration

```sql
-- Create database and user
CREATE DATABASE jackdawsentry_compliance;
CREATE USER jackdawsentry_user WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE jackdawsentry_compliance TO jackdawsentry_user;

-- Enable required extensions
\c jackdawsentry_compliance;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Performance settings
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET work_mem = '256MB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET max_connections = 200;

SELECT pg_reload_conf();
```

### Neo4j Configuration

```conf
# conf/neo4j.conf
dbms.memory.heap.initial_size=2G
dbms.memory.heap.max_size=4G
dbms.memory.pagecache.size=2G
dbms.security.procedures.unrestricted=gds.*,apoc.*
dbms.security.auth_enabled=true
dbms.connector.bolt.listen_address=0.0.0.0:7687
dbms.connector.http.listen_address=0.0.0.0:7474
dbms.logs.query.enabled=true
dbms.logs.query.threshold=1000ms
dbms.track_query_cpu_time=true
```

### Redis Configuration

```conf
# redis.conf
requirepass your_redis_password
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec
```

## Monitoring & Logging

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'jackdawsentry-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'neo4j'
    static_configs:
      - targets: ['neo4j:2004']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Jackdaw Sentry Overview",
    "panels": [
      {
        "title": "API Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Database Connections",
        "type": "graph",
        "targets": [
          {
            "expr": "pg_stat_database_numbackends",
            "legendFormat": "PostgreSQL Connections"
          }
        ]
      }
    ]
  }
}
```

### Log Aggregation

```yaml
# docker-compose.logging.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    volumes:
      - ./docker/logstash/pipeline:/usr/share/logstash/pipeline
      - ./logs:/var/log/jackdawsentry
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch

volumes:
  elasticsearch_data:
```

## Security Configuration

### SSL/TLS Setup

```bash
# Generate SSL certificates (Let's Encrypt)
certbot certonly --standalone -d api.jackdawsentry.com

# Configure Nginx with SSL
server {
    listen 443 ssl http2;
    server_name api.jackdawsentry.com;

    ssl_certificate /etc/letsencrypt/live/api.jackdawsentry.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.jackdawsentry.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    location / {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Firewall Configuration

```bash
# UFW firewall rules
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# IPTables for additional security
iptables -A INPUT -p tcp --dport 8000 -s 10.0.0.0/8 -j ACCEPT
iptables -A INPUT -p tcp --dport 8000 -j DROP
```

### Security Headers

```python
# src/api/middleware.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI()

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["api.jackdawsentry.com", "*.jackdawsentry.com"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.jackdawsentry.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"]
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

## Performance Tuning

### Application Performance

```python
# src/api/performance.py
import asyncio
from functools import lru_cache
from typing import List

# Connection pooling
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 30

# Caching configuration
@lru_cache(maxsize=1000)
def get_address_analysis(address: str):
    """Cache address analysis results"""
    return analyze_address_internal(address)

# Async batch processing
async def batch_analyze_addresses(addresses: List[str], batch_size: int = 50):
    """Process addresses in batches for better performance"""
    results = []
    
    for i in range(0, len(addresses), batch_size):
        batch = addresses[i:i + batch_size]
        batch_results = await asyncio.gather(
            *[analyze_address(addr) for addr in batch]
        )
        results.extend(batch_results)
    
    return results
```

### Database Optimization

```sql
-- PostgreSQL performance indexes
CREATE INDEX CONCURRENTLY idx_investigations_created_at 
ON investigations(created_at DESC);

CREATE INDEX CONCURRENTLY idx_entity_addresses_address_blockchain 
ON entity_addresses(address, blockchain) 
WHERE removed_at IS NULL;

CREATE INDEX CONCURRENTLY idx_transactions_timestamp_address 
ON transactions(timestamp DESC, from_address);

-- Partitioning for large tables
CREATE TABLE transactions_2024 PARTITION OF transactions
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

### Redis Caching Strategy

```python
# src/api/cache.py
import redis.asyncio as redis
import json
from typing import Any, Optional

class CacheManager:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def get_cached_result(self, key: str) -> Optional[Any]:
        """Get cached result"""
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None
    
    async def cache_result(self, key: str, data: Any, ttl: int = 3600):
        """Cache result with TTL"""
        await self.redis.setex(key, ttl, json.dumps(data))
    
    async def invalidate_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern"""
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
```

## Backup & Recovery

### Database Backup Scripts

```bash
#!/bin/bash
# scripts/backup_databases.sh

set -e

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# PostgreSQL backup (non-interactive password handling)
PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -h localhost -U jackdawsentry_user -d jackdawsentry_compliance \
    | gzip > "$BACKUP_DIR/postgres_$DATE.sql.gz"

# Alternative: Configure .pgpass file for jackdawsentry_user
# echo "localhost:5432:jackdawsentry_compliance:jackdawsentry_user:$POSTGRES_PASSWORD" > ~/.pgpass
# chmod 600 ~/.pgpass

# Neo4j backup
neo4j-admin dump --database=neo4j --to="$BACKUP_DIR/neo4j_$DATE.dump"

# Redis backup (option 1: trigger BGSAVE and copy dump file)
redis-cli BGSAVE
sleep 2  # wait for BGSAVE to complete
cp /var/lib/redis/dump.rdb "$BACKUP_DIR/redis_$DATE.rdb"

# Redis backup (option 2: remote export with auth)
# redis-cli -a "$REDIS_PASSWORD" --rdb "$BACKUP_DIR/redis_$DATE.rdb"

# Upload to cloud storage (AWS S3 example)
aws s3 cp "$BACKUP_DIR/postgres_$DATE.sql.gz" s3://jackdawsentry-backups/postgres/
aws s3 cp "$BACKUP_DIR/neo4j_$DATE.dump" s3://jackdawsentry-backups/neo4j/
aws s3 cp "$BACKUP_DIR/redis_$DATE.rdb" s3://jackdawsentry-backups/redis/

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.dump" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.rdb" -mtime +30 -delete

echo "Backup completed: $DATE"
```

### Recovery Procedures

```bash
#!/bin/bash
# scripts/restore_databases.sh

set -e

BACKUP_FILE=$1
BACKUP_DIR="/backups"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_date>"
    exit 1
fi

# Restore PostgreSQL
gunzip -c "$BACKUP_DIR/postgres_$BACKUP_FILE.sql.gz" | \
    psql -h localhost -U jackdawsentry_user -d jackdawsentry_compliance

# Restore Neo4j
neo4j-admin load --from="$BACKUP_DIR/neo4j_$BACKUP_FILE.dump" --database=neo4j

# Restore Redis (host approach)
systemctl stop redis-server
cp "$BACKUP_DIR/redis_$BACKUP_FILE.rdb" /var/lib/redis/dump.rdb
chown redis:redis /var/lib/redis/dump.rdb
systemctl start redis-server

# Restore Redis (Docker approach)
docker stop redis
docker cp "$BACKUP_DIR/redis_$BACKUP_FILE.rdb" redis:/data/dump.rdb
docker start redis

echo "Restore completed: $BACKUP_FILE"
```

### Automated Backup Cron Job

```bash
# Add to crontab (crontab -e)
# Daily backup at 2 AM
0 2 * * * /opt/jackdawsentry/scripts/backup_databases.sh

# Weekly backup verification (Sundays at 3 AM)
0 3 * * 0 /opt/jackdawsentry/scripts/verify_backups.sh
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors

```bash
# Check PostgreSQL status
docker-compose exec postgres pg_isready -U jackdawsentry_user

# Check Neo4j status
docker-compose exec neo4j cypher-shell -u neo4j -p password "RETURN 1"

# Check Redis status
docker-compose exec redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning ping
```

#### 2. High Memory Usage

```bash
# Check memory usage by container
docker stats

# Monitor application memory
python scripts/memory_profiler.py

# Clear Redis cache if needed
docker-compose exec redis redis-cli FLUSHDB
```

#### 3. Slow API Responses

```bash
# Check application logs
docker-compose logs api | tail -100

# Monitor database queries
docker-compose exec postgres psql -U jackdawsentry_user -d jackdawsentry_compliance \
    -c "SELECT query, calls, total_time, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Check Neo4j query performance
docker-compose exec neo4j cypher-shell -u neo4j -p password \
    "CALL dbms.queryJmx('org.neo4j:instance=kernel#0,name=Transactions') YIELD metrics RETURN metrics;"
```

#### 4. SSL Certificate Issues

```bash
# Check certificate expiration
openssl x509 -in /etc/letsencrypt/live/api.jackdawsentry.com/cert.pem -noout -dates

# Renew certificates
certbot renew

# Test SSL configuration
openssl s_client -connect api.jackdawsentry.com:443
```

### Health Check Script

```bash
#!/bin/bash
# scripts/health_check.sh

API_URL="https://api.jackdawsentry.com/api/v1/health"

# Check API health
response=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL")

if [ "$response" -eq 200 ]; then
    echo "✅ API is healthy"
else
    echo "❌ API is unhealthy (HTTP $response)"
    exit 1
fi

# Check database connectivity
docker-compose exec -T postgres pg_isready -U jackdawsentry_user > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ PostgreSQL is healthy"
else
    echo "❌ PostgreSQL is unhealthy"
    exit 1
fi

# Check Redis connectivity
docker-compose exec -T redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning ping > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Redis is healthy"
else
    echo "❌ Redis is unhealthy"
    exit 1
fi

echo "🎉 All systems healthy"
```

### Performance Monitoring

```python
# scripts/performance_monitor.py
import psutil
import requests
import time
from datetime import datetime

def check_system_health():
    """Monitor system health metrics"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Check API response time
    start_time = time.time()
    response = requests.get('https://api.jackdawsentry.com/api/v1/health')
    api_response_time = time.time() - start_time
    
    metrics = {
        'timestamp': datetime.now().isoformat(),
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'disk_percent': disk.percent,
        'api_response_time': api_response_time,
        'api_status': response.status_code
    }
    
    # Alert if thresholds exceeded
    if cpu_percent > 80:
        print(f"⚠️ High CPU usage: {cpu_percent}%")
    
    if memory.percent > 85:
        print(f"⚠️ High memory usage: {memory.percent}%")
    
    if api_response_time > 2.0:
        print(f"⚠️ Slow API response: {api_response_time:.2f}s")
    
    return metrics

if __name__ == "__main__":
    while True:
        metrics = check_system_health()
        print(f"Health check: {metrics['timestamp']} - CPU: {metrics['cpu_percent']}%, Memory: {metrics['memory_percent']}%, API: {metrics['api_response_time']:.2f}s")
        time.sleep(60)
```

## Support & Maintenance

### Regular Maintenance Tasks

1. **Daily**: Monitor system health and performance metrics
2. **Weekly**: Review logs for errors and unusual patterns
3. **Monthly**: Update dependencies and security patches
4. **Quarterly**: Performance optimization and capacity planning
5. **Annually**: Security audit and compliance review

### Emergency Procedures

1. **Service Outage**: Check health endpoints, restart services if needed
2. **Database Issues**: Switch to read-only mode, investigate logs
3. **Security Incident**: Enable audit logging, notify security team
4. **Performance Degradation**: Scale horizontally, investigate bottlenecks

### Contact Information

- **Technical Support**: support@jackdawsentry.com
- **Security Issues**: security@jackdawsentry.com
- **Emergency Hotline**: +1-555-JACKDAW

---

*This deployment guide covers the essential aspects of deploying and maintaining Jackdaw Sentry in production. For specific environment requirements or custom configurations, please contact our technical support team.*
