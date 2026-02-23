# Production Deployment Guide

This guide covers the production deployment of Jackdaw Sentry with Competitive Assessment framework.

## Overview

The production deployment includes:
- Multi-container Docker setup with load balancing
- High availability PostgreSQL and Redis
- Comprehensive monitoring with Prometheus and Grafana
- Log aggregation with Loki and Promtail
- SSL termination with Nginx
- Automated deployment and health checks

## Prerequisites

### System Requirements
- **CPU**: 8 cores minimum, 16 cores recommended
- **Memory**: 16GB minimum, 32GB recommended
- **Storage**: 100GB SSD minimum, 500GB recommended
- **Network**: 1Gbps connection recommended
- **OS**: Ubuntu 20.04+ or CentOS 8+

### Software Requirements
- Docker 20.10+
- Docker Compose 2.0+
- Git
- SSL certificates (for HTTPS)

### Environment Variables
Create a `.env.production` file based on `config/production.env.example`:

```bash
# Database Configuration
POSTGRES_PASSWORD=your_secure_postgres_password_here
DATABASE_URL=postgresql://jackdaw:your_secure_postgres_password_here@postgres:5432/jackdaw

# JWT Configuration
JWT_SECRET=your_super_secure_jwt_secret_key_change_in_production

# Grafana Configuration
GRAFANA_PASSWORD=your_secure_grafana_password
GRAFANA_SMTP_USER=your_smtp_username@gmail.com
GRAFANA_SMTP_PASSWORD=your_smtp_app_password
GRAFANA_FROM_ADDRESS=alerts@jackdaw-sentry.com
```

## Deployment Steps

### 1. Prepare Environment

```bash
# Clone repository
git clone https://github.com/your-org/jackdaw-sentry.git
cd jackdaw-sentry

# Create environment file
cp config/production.env.example .env.production
# Edit .env.production with your values

# Create SSL certificates
mkdir -p docker/nginx/ssl
# Copy your SSL certificates to docker/nginx/ssl/
# jackdaw-sentry.crt and jackdaw-sentry.key
```

### 2. Automated Deployment

```bash
# Run automated deployment
python scripts/deploy_production.py

# Check deployment status
python scripts/deploy_production.py --status

# Run health checks
python scripts/production_health_check.py
```

### 3. Manual Deployment (Alternative)

```bash
# Build production images
docker build -t jackdaw-sentry:production -f docker/competitive-production.Dockerfile .
docker build -t jackdaw-competitive-dashboard:production -f docker/competitive-production.Dockerfile .

# Deploy services
docker-compose -f docker/production-compose.yml up -d

# Wait for services to start
sleep 60

# Run health checks
python scripts/production_health_check.py
```

## Service Architecture

### Core Services
- **API**: Main application (3 replicas)
- **Competitive Dashboard**: Competitive assessment UI (2 replicas)
- **Competitive Monitoring**: Scheduled benchmark runner (1 replica)

### Infrastructure Services
- **PostgreSQL**: Primary database with backup
- **Redis**: Caching and session storage
- **Nginx**: Load balancer and SSL termination

### Monitoring Services
- **Prometheus**: Metrics collection
- **Grafana**: Visualization and alerting
- **Loki**: Log aggregation
- **Promtail**: Log collection

## Access URLs

After deployment, services are available at:

- **Main API**: https://jackdaw-sentry.com/api/
- **Competitive Dashboard**: https://jackdaw-sentry.com/competitive/
- **Grafana**: https://jackdaw-sentry.com:3000/
- **Prometheus**: https://jackdaw-sentry.com:9090/

## Monitoring and Alerting

### Health Checks
Run comprehensive health checks:

```bash
# Basic health check
python scripts/production_health_check.py

# JSON output
python scripts/production_health_check.py --json

# Save to file
python scripts/production_health_check.py --output health_report.json

# Send alerts
python scripts/production_health_check.py --alerts
```

### Grafana Dashboards
Access production dashboards at http://localhost:3000:
- **Jackdaw Sentry - Production Competitive Dashboard**
- **System Health Dashboard**
- **Performance Metrics Dashboard**

### Alert Rules
Critical alerts are configured for:
- Competitive parity below 80%
- Service downtime
- High resource usage
- Database connection issues
- Performance degradation

## Backup and Recovery

### Automated Backups
Backups are automatically created during deployment and can be scheduled:

```bash
# Manual backup
docker-compose -f docker/production-compose.yml exec postgres pg_dump -U jackdaw jackdaw > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
docker-compose -f docker/production-compose.yml exec -T postgres psql -U jackdaw jackdaw < backup_file.sql
```

### Disaster Recovery
1. **Rollback deployment**:
   ```bash
   python scripts/deploy_production.py --rollback
   ```

2. **Restore database**:
   ```bash
   # Stop services
   docker-compose -f docker/production-compose.yml down
   
   # Start database only
   docker-compose -f docker/production-compose.yml up -d postgres
   
   # Wait for database
   sleep 30
   
   # Restore backup
   docker-compose -f docker/production-compose.yml exec -T postgres psql -U jackdaw jackdaw < latest_backup.sql
   
   # Restart services
   docker-compose -f docker/production-compose.yml up -d
   ```

## Performance Optimization

### Database Optimization
- Connection pooling configured for 100 connections
- Indexes optimized for competitive assessment queries
- Automatic vacuum and analyze configured

### Caching Strategy
- Redis configured with 2GB memory limit
- LRU eviction policy for cache management
- Competitive metrics cached for 1 hour

### Load Balancing
- Nginx configured for round-robin load balancing
- Health checks for upstream servers
- SSL termination at load balancer

## Security Configuration

### SSL/TLS
- SSL certificates required for production
- TLS 1.2 and 1.3 supported
- HSTS headers configured
- Security headers added

### Network Security
- Internal network isolation
- Only required ports exposed
- Rate limiting configured
- Firewall rules recommended

### Application Security
- JWT secrets configured
- Environment variables for sensitive data
- Database access restricted
- Regular security updates

## Troubleshooting

### Common Issues

#### Service Not Starting
```bash
# Check logs
docker-compose -f docker/production-compose.yml logs [service_name]

# Check container status
docker-compose -f docker/production-compose.yml ps

# Restart service
docker-compose -f docker/production-compose.yml restart [service_name]
```

#### Database Connection Issues
```bash
# Check database health
docker-compose -f docker/production-compose.yml exec postgres pg_isready -U jackdaw

# Check connections
docker-compose -f docker/production-compose.yml exec postgres psql -U jackdaw -c "SELECT count(*) FROM pg_stat_activity;"

# Reset database
docker-compose -f docker/production-compose.yml down
docker volume rm jackdaw_postgres_data
docker-compose -f docker/production-compose.yml up -d postgres
```

#### Performance Issues
```bash
# Check resource usage
docker stats

# Check system resources
df -h
free -h

# Check application logs
docker-compose -f docker/production-compose.yml logs api
```

### Log Locations
- **Application logs**: `/var/log/app/`
- **Nginx logs**: `/var/log/nginx/`
- **Docker logs**: `docker-compose logs`
- **Grafana logs**: Available in Grafana UI

## Maintenance

### Regular Tasks
1. **Monitor system health**: Daily health checks
2. **Update dependencies**: Monthly security updates
3. **Backup verification**: Weekly backup testing
4. **Performance tuning**: Quarterly optimization
5. **Security audit**: Annual security review

### Scaling
To scale services, modify `docker/production-compose.yml`:

```yaml
# Scale API service
api:
  deploy:
    replicas: 5  # Increase from 3 to 5

# Scale dashboard service
competitive-dashboard:
  deploy:
    replicas: 3  # Increase from 2 to 3
```

### Updates
To update the application:

```bash
# Pull latest code
git pull origin main

# Rebuild and redeploy
python scripts/deploy_production.py
```

## Support

For production issues:
1. Check health reports
2. Review logs
3. Consult troubleshooting guide
4. Contact support team

## Compliance

The production deployment meets:
- **GDPR**: Data protection and privacy
- **SOC 2**: Security controls
- **ISO 27001**: Information security management
- **PCI DSS**: Payment card security (if applicable)
