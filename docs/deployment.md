# Jackdaw Sentry Deployment Guide

🚀 **Production Deployment Guide for Jackdaw Sentry**

Complete guide for deploying Jackdaw Sentry in production environments with Docker, monitoring, security, and scaling considerations.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Docker Deployment](#docker-deployment)
- [Database Configuration](#database-configuration)
- [Security Configuration](#security-configuration)
- [Monitoring Setup](#monitoring-setup)
- [Scaling Considerations](#scaling-considerations)
- [Troubleshooting](#troubleshooting)

## 🔧 Prerequisites

### System Requirements
- **CPU**: 8+ cores (16+ recommended for multi-chain production)
- **RAM**: 16GB+ (32GB+ recommended for full blockchain data)
- **Storage**: 500GB+ SSD (1TB+ for full blockchain data)
- **Network**: Stable internet connection for blockchain RPC calls
- **OS**: Linux (Ubuntu 20.04+, CentOS 8+, RHEL 8+)

### Software Requirements
- **Docker**: 20.10+ with Docker Compose 2.0+
- **Python**: 3.11+
- **Git**: For source code management
- **SSL Certificate**: For HTTPS (recommended)

### Blockchain RPC Requirements
- **Bitcoin**: Full node or RPC endpoint
- **Ethereum EVM**: Ethereum, BSC, Polygon, Arbitrum, Base, Avalanche RPC endpoints
- **Solana**: Solana RPC endpoint
- **Tron**: Tron RPC endpoint
- **Lightning Network**: LND node (optional, for Lightning Network analysis)

## 🌍 Environment Setup

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/jackdaw-sentry.git
cd jackdaw-sentry
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env
# Edit .env with your configuration
```

### 3. Multi-Chain Blockchain Configuration
```bash
# =============================================================================
# Multi-Chain Blockchain RPC Configuration
# =============================================================================

# Bitcoin Configuration
BITCOIN_RPC_URL=http://localhost:8332
BITCOIN_RPC_USER=your_bitcoin_rpc_user
BITCOIN_RPC_PASSWORD=your_bitcoin_rpc_password
BITCOIN_NETWORK=mainnet

# Lightning Network Configuration (Optional)
LND_RPC_URL=localhost:10009
LND_MACAROON_PATH=/path/to/lnd/admin.macaroon
LND_TLS_CERT_PATH=/path/to/lnd/tls.cert

# Ethereum EVM Configuration
ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/YOUR_INFURA_KEY
ETHEREUM_NETWORK=mainnet

BSC_RPC_URL=https://bsc-dataseed.binance.org
BSC_NETWORK=mainnet

POLYGON_RPC_URL=https://polygon-rpc.com
POLYGON_NETWORK=mainnet

ARBITRUM_RPC_URL=https://arb1.arbitrum.io/rpc
ARBITRUM_NETWORK=mainnet

BASE_RPC_URL=https://mainnet.base.org
BASE_NETWORK=mainnet

AVALANCHE_RPC_URL=https://api.avax.network/ext/bc/C/rpc
AVALANCHE_NETWORK=mainnet

# Alternative Blockchains
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_NETWORK=mainnet

TRON_RPC_URL=https://api.trongrid.io
TRON_NETWORK=mainnet

# Optional Additional Blockchains
XRPL_RPC_URL=https://xrplcluster.com
XRPL_NETWORK=mainnet

STELLAR_RPC_URL=https://horizon.stellar.org
STELLAR_NETWORK=public

SEI_RPC_URL=https://rpc.sei-apis.com
SEI_NETWORK=mainnet

HYPERLIQUID_RPC_URL=https://api.hyperliquid.xyz/info
HYPERLIQUID_NETWORK=mainnet

PLASMA_RPC_URL=https://rpc.plasma.network
PLASMA_NETWORK=mainnet
```

### 3. Required Environment Variables
```bash
# =============================================================================
# Database Configuration
# =============================================================================
POSTGRES_DB=jackdawsentry_compliance
POSTGRES_USER=jackdawsentry_user
POSTGRES_PASSWORD=your_secure_postgres_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

NEO4J_URI=bolt://neo4j:your_neo4j_password@localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_neo4j_password

REDIS_URL=redis://:your_redis_password@localhost:6379/0
REDIS_PASSWORD=your_secure_redis_password
REDIS_MAXMEMORY=1gb              # Max memory for Redis (default: 1gb). Examples: 512mb, 2gb, 4gb

# =============================================================================
# API Configuration
# =============================================================================
API_HOST=127.0.0.1
API_PORT=8000
API_SECRET_KEY=your_api_secret_key_min_32_chars

# =============================================================================
# Security Configuration
# =============================================================================
ENCRYPTION_KEY=your_32_character_encryption_key_here
JWT_SECRET_KEY=your_jwt_secret_key_min_32_chars
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# =============================================================================
# Logging Configuration
# =============================================================================
LOG_LEVEL=INFO
LOG_FILE_PATH=/app/logs

# =============================================================================
# Cache Configuration
# =============================================================================
CACHE_TTL_SECONDS=300
CACHE_MAX_SIZE=1000
```

## 🐳 Docker Deployment

### Production Docker Compose
```bash
# Deploy with production configuration
docker compose -f docker/docker-compose.prod.yml up -d

# Check service status
docker compose -f docker/docker-compose.prod.yml ps

# View logs
docker compose -f docker/docker-compose.prod.yml logs -f
```

### Service Health Checks
```bash
# Check API health
curl http://localhost/health

# Check database connectivity
curl http://localhost/health/detailed

# Check system metrics
curl http://localhost/metrics
```

### Automated Deployment Script
```bash
# Make deployment script executable
chmod +x scripts/deploy.sh

# Run deployment with health checks
./scripts/deploy.sh deploy

# Check deployment status
./scripts/deploy.sh health

# Rollback if needed
./scripts/deploy.sh rollback
```

## 🗄️ Database Configuration

### PostgreSQL Setup
```bash
# Initialize database
docker exec jackdawsentry_postgres_prod psql -U jackdawsentry_user -d jackdawsentry_compliance -c "\dt"

# Run migrations
python3 -c "
import sys
sys.path.append('.')
from src.api.migrations.migration_manager import run_database_migrations
import asyncio
asyncio.run(run_database_migrations())
"

# Verify tables
docker exec jackdawsentry_postgres_prod psql -U jackdawsentry_user -d jackdawsentry_compliance -c "\dt"
```

### Neo4j Setup
```bash
# Verify Neo4j connection
docker exec jackdawsentry_neo4j_prod cypher-shell -u neo4j -p your_neo4j_password "MATCH (n) RETURN count(n) as nodes"

# Create constraints (handled by migrations)
docker exec jackdawsentry_neo4j_prod cypher-shell -u neo4j -p your_neo4j_password "SHOW CONSTRAINTS"
```

### Redis Setup
```bash
# Verify Redis connection
docker exec jackdawsentry_redis_prod redis-cli -a ${REDIS_PASSWORD} ping

# Check Redis memory usage
docker exec jackdawsentry_redis_prod redis-cli -a ${REDIS_PASSWORD} info memory
```

## 🔒 Security Configuration

### SSL/TLS Setup
```bash
# Generate SSL certificates (Let's Encrypt recommended)
sudo certbot --nginx -d your-domain.com

# Or use self-signed certificates for testing
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout docker/nginx/ssl/jackdawsentry.key \
  -out docker/nginx/ssl/jackdawsentry.crt
```

### Firewall Configuration
```bash
# Configure UFW firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 8000/tcp  # Block direct API access
```

### Security Headers
The application includes comprehensive security headers:
- `X-Frame-Options: SAMEORIGIN`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000`
- `Content-Security-Policy: default-src 'self'`

## 📊 Monitoring Setup

### Application Monitoring
```bash
# Check application logs
docker logs jackdawsentry_api_prod

# Monitor system resources
docker stats jackdawsentry_api_prod

# Check health endpoints
curl -s http://localhost/health | jq .
```

### Log Management
```bash
# View application logs
tail -f /app/logs/jackdawsentry.log

# View audit logs
tail -f /app/logs/audit.log

# View error logs
tail -f /app/logs/errors.log
```

### Metrics Collection
```bash
# Get system metrics
curl http://localhost/metrics

# Get detailed health status
curl http://localhost/health/detailed

# Monitor database connections
curl http://localhost/api/v1/admin/system/status
```

### Alert Configuration
```bash
# Configure alerts in monitoring system
# (Integrate with your preferred monitoring tool)
# - Prometheus + Grafana
# - DataDog
# - New Relic
# - ELK Stack
```

## 📈 Scaling Considerations

### Horizontal Scaling
```yaml
# docker/docker-compose.prod.yml scaling example
services:
  api:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
```

### Database Scaling
```bash
# PostgreSQL read replicas
# Configure in docker/docker-compose.prod.yml
postgres_replica:
  image: postgres:16-alpine
  environment:
    POSTGRES_MASTER_SERVICE: postgres
    POSTGRES_REPLICATION_USER: replicator
    POSTGRES_REPLICATION_PASSWORD: replica_password

# Redis clustering
redis_cluster:
  image: redis:7.2-alpine
  command: redis-server --cluster-enabled yes
```

### Load Balancing
```nginx
# nginx.conf load balancing configuration
upstream jackdawsentry_backend {
    least_conn;
    server api:8000 max_fails=3 fail_timeout=30s;
    server api_1:8000 max_fails=3 fail_timeout=30s;
    server api_2:8000 max_fails=3 fail_timeout=30s;
}
```

## 🔧 Performance Optimization

### Caching Strategy
```bash
# Redis caching configuration
redis-cli CONFIG SET maxmemory 2gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Application cache settings
CACHE_TTL_SECONDS=300
CACHE_MAX_SIZE=1000
```

### Database Optimization
```sql
-- PostgreSQL performance tuning
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '2GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
```

### Connection Pooling
```python
# Database connection pool settings
POSTGRES_POOL_SIZE=20
POSTGRES_MAX_OVERFLOW=30
NEO4J_MAX_CONNECTION_POOL_SIZE=50
REDIS_CONNECTION_POOL_SIZE=10
```

## 🚨 Backup and Recovery

### Database Backups
```bash
# PostgreSQL backup
docker exec jackdawsentry_postgres_prod pg_dump -U jackdawsentry_user jackdawsentry_compliance > backup_$(date +%Y%m%d_%H%M%S).sql

# Neo4j backup
docker exec jackdawsentry_neo4j_prod neo4j-admin backup --backup-dir=/backups neo4j

# Redis backup
docker exec jackdawsentry_redis_prod redis-cli BGSAVE
```

### Automated Backup Script
```bash
#!/bin/bash
# scripts/backup.sh
BACKUP_DIR="/opt/jackdawsentry/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker exec jackdawsentry_postgres_prod pg_dump -U jackdawsentry_user jackdawsentry_compliance > $BACKUP_DIR/postgres_$DATE.sql

# Backup Neo4j
docker exec jackdawsentry_neo4j_prod neo4j-admin backup --backup-dir=/backups neo4j

# Backup Redis
docker exec jackdawsentry_redis_prod redis-cli BGSAVE

# Clean old backups (keep 7 days)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.backup" -mtime +7 -delete
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Database Connection Errors
```bash
# Check database status
docker compose -f docker/docker-compose.prod.yml ps postgres neo4j redis

# Check logs
docker compose -f docker/docker-compose.prod.yml logs postgres
docker compose -f docker/docker-compose.prod.yml logs neo4j
docker compose -f docker/docker-compose.prod.yml logs redis

# Verify network connectivity
docker network ls
docker network inspect jackdawsentry_jackdawsentry_network
```

#### 2. API Not Responding
```bash
# Check API container status
docker ps | grep jackdawsentry_api

# Check API logs
docker logs jackdawsentry_api_prod

# Restart API service
docker compose -f docker/docker-compose.prod.yml restart api

# Check port availability
netstat -tlnp | grep :80
```

#### 3. High Memory Usage
```bash
# Monitor memory usage
docker stats jackdawsentry_api_prod

# Check for memory leaks
docker exec jackdawsentry_api_prod ps aux

# Restart if needed
docker compose -f docker/docker-compose.prod.yml restart api
```

#### 4. Slow Database Queries
```bash
# Check PostgreSQL slow queries
docker exec jackdawsentry_postgres_prod psql -U jackdawsentry_user -d jackdawsentry_compliance -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Check Neo4j query performance
docker exec jackdawsentry_neo4j_prod cypher-shell -u neo4j -p your_neo4j_password "CALL dbms.listQueries() YIELD query, elapsedTimeMillis RETURN query, elapsedTimeMillis ORDER BY elapsedTimeMillis DESC LIMIT 10;"
```

### Health Check Script
```bash
#!/bin/bash
# scripts/health_check.sh

echo "=== Jackdaw Sentry Health Check ==="

# Check API health
echo "Checking API..."
API_HEALTH=$(curl -s http://localhost/health | jq -r .status)
echo "API Status: $API_HEALTH"

# Check databases
echo "Checking PostgreSQL..."
PG_STATUS=$(docker exec jackdawsentry_postgres_prod pg_isready -U jackdawsentry_user -d jackdawsentry_compliance)
echo "PostgreSQL: $PG_STATUS"

echo "Checking Neo4j..."
NEO4J_STATUS=$(docker exec jackdawsentry_neo4j_prod cypher-shell -u neo4j -p your_neo4j_password "RETURN 1" 2>/dev/null | grep "1" | wc -l)
if [ $NEO4J_STATUS -eq 1 ]; then
    echo "Neo4j: Healthy"
else
    echo "Neo4j: Unhealthy"
fi

echo "Checking Redis..."
REDIS_STATUS=$(docker exec jackdawsentry_redis_prod redis-cli -a ${REDIS_PASSWORD} ping)
echo "Redis: $REDIS_STATUS"

# Check system resources
echo "System Resources:"
docker stats --no-stream jackdawsentry_api_prod --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

echo "=== Health Check Complete ==="
```

## 📚 Additional Resources

### Documentation
- [API Documentation](docs/api/README.md)
- [Database Schema](docs/database/README.md)
- [Security Guide](docs/security.md)
- [Roadmap](docs/roadmap.md)

### Support
- [GitHub Issues](https://github.com/yourusername/jackdaw-sentry/issues)
- [Discord Community](https://discord.gg/jackdawsentry)
- [Email Support](support@jackdawsentry.com)

### Monitoring Tools
- [Prometheus](https://prometheus.io/) - Metrics collection
- [Grafana](https://grafana.com/) - Visualization
- [ELK Stack](https://www.elastic.co/) - Log management
- [DataDog](https://www.datadoghq.com/) - APM and monitoring

---

**Deployment Version**: v1.0.0  
**Last Updated**: January 2024  
**Production Status**: ✅ Fully Production Ready  
**Support**: deployment@jackdawsentry.com
