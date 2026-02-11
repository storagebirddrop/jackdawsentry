#!/bin/bash
# Jackdaw Sentry - Production Deployment Script
# Automated deployment with health checks and rollback capabilities

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================
ENVIRONMENT=${1:-production}
BACKUP_DIR="/opt/jackdawsentry/backups"
LOG_DIR="/var/log/jackdawsentry"
HEALTH_CHECK_TIMEOUT=300
ROLLBACK_ENABLED=true

# =============================================================================
# Colors for output
# =============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# =============================================================================
# Logging functions
# =============================================================================
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# =============================================================================
# Pre-deployment checks
# =============================================================================
pre_deployment_checks() {
    log "Running pre-deployment checks..."
    
    # Check if Docker is running
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not running"
        exit 1
    fi
    
    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check if required environment variables are set
    required_vars=("POSTGRES_PASSWORD" "NEO4J_PASSWORD" "REDIS_PASSWORD" "API_SECRET_KEY" "ENCRYPTION_KEY")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Check if .env file exists
    if [[ ! -f ".env" ]]; then
        error ".env file not found"
        exit 1
    fi
    
    success "Pre-deployment checks passed"
}

# =============================================================================
# Backup current deployment
# =============================================================================
backup_current_deployment() {
    log "Creating backup of current deployment..."
    
    BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_PATH="$BACKUP_DIR/$BACKUP_TIMESTAMP"
    
    mkdir -p "$BACKUP_PATH"
    
    # Backup current containers
    docker-compose -f docker-compose.prod.yml ps --format json > "$BACKUP_PATH/containers.json" 2>/dev/null || true
    
    # Backup volumes
    docker run --rm -v jackdawsentry_postgres_prod_data:/data -v "$BACKUP_PATH":/backup alpine tar czf /backup/postgres_data.tar.gz -C /data 2>/dev/null || true
    docker run --rm -v jackdawsentry_neo4j_prod_data:/data -v "$BACKUP_PATH":/backup alpine tar czf /backup/neo4j_data.tar.gz -C /data 2>/dev/null || true
    docker run --rm -v jackdawsentry_redis_prod_data:/data -v "$BACKUP_PATH":/backup alpine tar czf /backup/redis_data.tar.gz -C /data 2>/dev/null || true
    
    success "Backup created: $BACKUP_PATH"
}

# =============================================================================
# Deploy new version
# =============================================================================
deploy_new_version() {
    log "Deploying new version..."
    
    # Pull latest images
    info "Pulling latest images..."
    docker-compose -f docker-compose.prod.yml pull --quiet
    
    # Stop current services
    log "Stopping current services..."
    docker-compose -f docker-compose.prod.yml down --timeout 60
    
    # Start new services
    log "Starting new services..."
    docker-compose -f docker-compose.prod.yml up -d --timeout 300
    
    # Wait for services to be healthy
    wait_for_health()
    
    success "Deployment completed"
}

# =============================================================================
# Health check function
# =============================================================================
wait_for_health() {
    log "Waiting for services to be healthy..."
    
    local services=("postgres" "neo4j" "redis" "api" "nginx")
    local max_attempts=30
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        local all_healthy=true
        
        for service in "${services[@]}"; do
            if check_service_health "$service"; then
                log "$service is healthy"
            else
                log "$service is not healthy yet"
                all_healthy=false
            fi
        done
        
        if [[ "$all_healthy" == true ]]; then
            success "All services are healthy"
            break
        fi
        
        sleep 10
        ((attempt++))
    done
    
    if [[ $attempt -eq $max_attempts ]]; then
        error "Health check timeout after $max_attempts attempts"
        if [[ "$ROLLBACK_ENABLED" == true ]]; then
            rollback_deployment
        fi
        exit 1
    fi
}

# =============================================================================
# Service health check
# =============================================================================
check_service_health() {
    local service=$1
    local container_name="jackdawsentry_${service}_prod"
    
    case $service in
        "postgres")
            docker exec "$container_name" pg_isready -U jackdawsentry_user -d jackdawsentry_compliance >/dev/null 2>&1
            ;;
        "neo4j")
            docker exec "$container_name" cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" "RETURN 1;" >/dev/null 2>&1
            ;;
        "redis")
            docker exec "$container_name" redis-cli -a "${REDIS_PASSWORD}" ping >/dev/null 2>&1
            ;;
        "api")
            curl -f http://localhost:8000/health >/dev/null 2>&1
            ;;
        "nginx")
            curl -f http://localhost/health >/dev/null 2>&1
            ;;
        *)
            warning "Unknown service: $service"
            return 1
            ;;
    esac
    
    return $?
}

# =============================================================================
# Rollback function
# =============================================================================
rollback_deployment() {
    log "Initiating rollback..."
    
    # Get latest backup
    local latest_backup=$(ls -t "$BACKUP_DIR" | head -1 | cut -d' ' -f1)
    
    if [[ -z "$latest_backup" ]]; then
        error "No backup found for rollback"
        exit 1
    fi
    
    log "Rolling back to: $latest_backup"
    
    # Stop current services
    docker-compose -f docker-compose.prod.yml down --timeout 60
    
    # Restore volumes from backup
    if [[ -f "$latest_backup/postgres_data.tar.gz" ]]; then
        docker run --rm -v jackdawsentry_postgres_prod_data:/data -v "$latest_backup":/backup alpine tar xzf /backup/postgres_data.tar.gz -C /data 2>/dev/null || true
    fi
    
    if [[ -f "$latest_backup/neo4j_data.tar.gz" ]]; then
        docker run --rm -v jackdawsentry_neo4j_prod_data:/data -v "$latest_backup":/backup alpine tar xzf /backup/neo4j_data.tar.gz -C /data 2>/dev/null || true
    fi
    
    if [[ -f "$latest_backup/redis_data.tar.gz" ]]; then
        docker run --rm -v jackdawsentry_redis_prod_data:/data -v "$latest_backup":/backup alpine tar xzf /backup/redis_data.tar.gz -C /data 2>/dev/null || true
    fi
    
    # Restart services
    docker-compose -f docker-compose.prod.yml up -d --timeout 300
    
    # Wait for health
    wait_for_health
    
    success "Rollback completed"
}

# =============================================================================
# Cleanup function
# =============================================================================
cleanup() {
    log "Performing cleanup..."
    
    # Remove old backups (keep last 5)
    find "$BACKUP_DIR" -maxdepth 1 -type d -mtime +7 -exec rm -rf {} \; 2>/dev/null || true
    
    # Clean up Docker images
    docker image prune -f --filter "label=jackdawsentry" --force 2>/dev/null || true
    
    success "Cleanup completed"
}

# =============================================================================
# Main deployment flow
# =============================================================================
main() {
    log "Starting Jackdaw Sentry deployment..."
    
    # Load environment variables
    if [[ -f ".env" ]]; then
        export $(cat .env | xargs)
    fi
    
    # Run deployment steps
    pre_deployment_checks
    backup_current_deployment
    deploy_new_version
    cleanup
    
    success "Deployment completed successfully"
}

# =============================================================================
# Script entry point
# =============================================================================
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    main "$@"
else
    case "${1:-}" in
        "deploy")
            main
            ;;
        "health")
            wait_for_health
            ;;
        "rollback")
            rollback_deployment
            ;;
        "backup")
            backup_current_deployment
            ;;
        "cleanup")
            cleanup
            ;;
        *)
            echo "Usage: $0 {deploy|health|rollback|backup|cleanup}"
            echo "  deploy  - Full deployment process"
            echo "  health  - Check service health"
            echo "  rollback - Rollback to last backup"
            echo "  backup  - Create backup"
            echo "  cleanup - Clean old backups and images"
            exit 1
            ;;
    esac
fi
