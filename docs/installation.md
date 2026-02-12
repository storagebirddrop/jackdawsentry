# Installation Guide

Complete installation instructions for Jackdaw Sentry on your local development environment.

## 📋 Prerequisites

### System Requirements
- **Operating System**: Linux, macOS, or Windows (with WSL2)
- **RAM**: Minimum 8GB, recommended 16GB+
- **Storage**: Minimum 100GB free space, recommended 500GB+
- **CPU**: 4+ cores recommended for optimal performance

### Software Dependencies
- **Docker**: 20.10+ and Docker Compose 2.0+
- **Python**: 3.11+ (for local development)
- **Git**: For version control
- **Node.js**: 18+ (for frontend development)

## 🚀 Quick Installation

### 1. Clone Repository
```bash
git clone https://github.com/storagebirddrop/jackdaw-sentry.git
cd jackdaw-sentry
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit configuration (required)
nano .env
```

**Critical Settings to Update:**
- `API_SECRET_KEY`: Generate a secure random key
- `ENCRYPTION_KEY`: At least 32-character encryption key
- `JWT_SECRET_KEY`: JWT signing secret
- Blockchain RPC URLs (if using custom nodes)

### 3. Start Services
```bash
# Start all services
docker compose up -d

# Check service status
docker compose ps
```

### 4. Verify Services
```bash
# Check all containers are healthy
docker compose ps

# Verify the API is responding
curl http://localhost/health

# Verify Neo4j is initialized and accepting queries
docker compose exec neo4j cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" "RETURN 1 AS ok"

# Verify Redis is responding
docker compose exec redis redis-cli -a "${REDIS_PASSWORD}" PING
```

PostgreSQL is automatically initialized via `docker/postgres/init.sql` on first start.
The Neo4j and Redis checks above confirm that their respective initialization scripts
(`docker/neo4j/init.cypher` and `docker/redis/redis.conf`) ran successfully.

### 5. Access Applications
- **Web Dashboard (Nginx)**: http://localhost/
- **API Documentation (via Nginx)**: http://localhost/docs
- **Neo4j Browser**: http://localhost:7474
- **API Health (via Nginx)**: http://localhost/health

### Optional: Compliance Microservices

If you want to run the dedicated compliance microservice stack (separate containers), start it explicitly:

```bash
docker compose -f docker/compliance-compose.yml up -d
```

## 🔧 Detailed Installation

### Docker Setup

#### Install Docker (Ubuntu/Debian)
```bash
# Update package index
sudo apt-get update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt-get install docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

#### Install Docker (macOS)
```bash
# Using Homebrew
brew install --cask docker

# Or download from https://www.docker.com/products/docker-desktop
```

#### Install Docker (Windows)
1. Download Docker Desktop from https://www.docker.com/products/docker-desktop
2. Enable WSL2 integration
3. Restart your computer

### Environment Configuration

#### Generate Secure Keys
```bash
# Generate all required secrets at once:
for var in API_SECRET_KEY NEO4J_PASSWORD POSTGRES_PASSWORD REDIS_PASSWORD ENCRYPTION_KEY JWT_SECRET_KEY; do
  echo "$var=$(openssl rand -hex 32)"
done
```

The loop above prints `KEY=VALUE` lines for `API_SECRET_KEY`, `NEO4J_PASSWORD`,
`POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `ENCRYPTION_KEY`, and `JWT_SECRET_KEY`.
Append them to your `.env` file (or copy-paste the output), for example:

```bash
# Append generated secrets directly to .env
for var in API_SECRET_KEY NEO4J_PASSWORD POSTGRES_PASSWORD REDIS_PASSWORD ENCRYPTION_KEY JWT_SECRET_KEY; do
  echo "$var=$(openssl rand -hex 32)" >> .env
done

# Restrict file permissions so only the owner can read it
chmod 600 .env
```

See [security.md](security.md#-secrets-management) for details.

#### Blockchain RPC Configuration

**Option 1: Public RPC Endpoints (Free)**
```bash
# Ethereum (Infura - requires free account)
ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/YOUR_INFURA_KEY

# Solana (Public)
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com

# Bitcoin (Public)
BITCOIN_RPC_URL=https://blockstream.info/api
```

**Option 2: Self-Hosted Nodes (Advanced)**
```bash
# Bitcoin Core
BITCOIN_RPC_URL=http://localhost:8332
BITCOIN_RPC_USER=your_bitcoin_user
BITCOIN_RPC_PASSWORD=your_bitcoin_password

# Ethereum (Geth)
ETHEREUM_RPC_URL=http://localhost:8545
```

### Database Initialization

#### Neo4j Setup
```bash
# Access Neo4j Browser
open http://localhost:7474

# Login with credentials from your .env file
Username: neo4j
Password: <your NEO4J_PASSWORD from .env>

# Run initialization script
:play init-graph
```

#### PostgreSQL Setup
```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U jackdawsentry_user -d jackdawsentry_compliance

# Verify tables
\dt

# Check compliance schema
\d compliance_*
```

#### Redis Setup
```bash
# Test Redis connection
docker compose exec redis redis-cli -a ${REDIS_PASSWORD} ping

# Check memory usage
docker compose exec redis redis-cli -a ${REDIS_PASSWORD} info memory
```

## 🧪 Verification

### Health Checks
```bash
# Check API health (via Nginx)
curl -f http://localhost/health

# Verify API status endpoint
curl -f http://localhost/api/v1/status

# Verify data in Neo4j
docker compose exec neo4j cypher-shell -u neo4j -p ${NEO4J_PASSWORD} "MATCH (n) RETURN count(n) as node_count"
```

## 🔧 Troubleshooting

### Common Issues

#### Port Conflicts
```bash
# Check port usage
netstat -tulpn | grep :7474
netstat -tulpn | grep :5432

# Kill conflicting processes
sudo kill -9 <PID>
```

#### Memory Issues
```bash
# Check Docker memory limits
docker system df

# Increase Docker memory allocation
# In Docker Desktop: Settings > Resources > Memory
```

#### Permission Issues
```bash
# Fix Docker permissions
sudo chown -R $USER:$USER ./data
sudo chown -R $USER:$USER ./logs

# Reset Docker permissions
sudo chmod 666 /var/run/docker.sock
```

### Service-Specific Issues

#### Neo4j Won't Start
```bash
# Check Neo4j logs
docker compose logs neo4j

# Reset Neo4j data
docker compose down -v
docker compose up -d neo4j
```

#### PostgreSQL Connection Issues
```bash
# Check PostgreSQL logs
docker compose logs postgres

# Reset PostgreSQL
docker compose down -v postgres
docker compose up -d postgres
```

#### API Won't Start
```bash
# Check API logs
docker compose logs api

# Verify environment variables
docker compose exec api env | grep -E "(NEO4J|POSTGRES|REDIS)"
```

## 📊 Performance Optimization

### Resource Allocation
```yaml
# In the docker-compose.yml file, adjust memory limits:
services:
  neo4j:
    environment:
      NEO4J_dbms_memory_heap_max__size: 8G  # Increase for large datasets
      NEO4J_dbms_memory_pagecache_size: 4G   # Increase for better performance
```

### Storage Optimization
```bash
# Use SSD for better performance
# Mount external drives for large datasets
sudo mount /dev/sdb1 ./data/blockchain
```

## 🔄 Updates and Maintenance

### Update Jackdaw Sentry
```bash
# Pull latest changes
git pull origin main

# Rebuild containers
docker compose build --no-cache

# Restart services
docker compose up -d
```

### Backup Data
```bash
# Backup Neo4j
docker compose exec neo4j neo4j-admin dump --database=neo4j --to=/backup/neo4j.dump

# Backup PostgreSQL
docker compose exec postgres pg_dump -U jackdawsentry_user jackdawsentry_compliance > backup/postgres.sql

# Backup Redis
docker compose exec redis redis-cli --rdb /backup/redis.rdb
```

## 📞 Support

If you encounter issues during installation:

1. **Check Logs**: `docker compose logs [service_name]`
2. **Review FAQ**: See the Troubleshooting section above
3. **Community Support**: [Discord Server](https://discord.gg/jackdawsentry)
4. **Report Issues**: [GitHub Issues](https://github.com/storagebirddrop/jackdaw-sentry/issues)

---

**Next Steps**: After successful installation, visit http://localhost/docs for API documentation, or see the [Roadmap](roadmap.md) for the project status.
