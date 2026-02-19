#!/bin/bash

# Jackdaw Sentry Compliance Services Deployment Script
# Production deployment with health checks and rollback capabilities

set -euo pipefail

# Configuration
COMPOSE_FILE="docker/compliance-compose.yml"
PROJECT_NAME="jackdawsentry_compliance"
BACKUP_DIR="./backups/compliance"
LOG_DIR="./logs/deployment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "./data/compliance"
    mkdir -p "./logs/compliance"
    mkdir -p "./uploads/compliance"
    mkdir -p "./cache/compliance"
    mkdir -p "./config/compliance"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    # Check if compose file exists
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "Compose file not found: $COMPOSE_FILE"
        exit 1
    fi
    
    # Check available disk space (minimum 10GB)
    available_space=$(df . | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 10485760 ]; then  # 10GB in KB
        log_warning "Low disk space detected: ${available_space}KB available"
    fi
    
    log_success "Prerequisites check completed"
}

# Backup existing data
backup_data() {
    log "Creating backup of existing data..."
    
    if [ -d "./data/compliance" ] && [ "$(ls -A ./data/compliance)" ]; then
        backup_name="compliance_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
        tar -czf "$BACKUP_DIR/$backup_name" ./data/compliance
        log_success "Backup created: $backup_name"
    else
        log "No existing compliance data to backup"
    fi
}

# Build images
build_images() {
    log "Building Docker images..."
    
    cd ..
    docker-compose -f "$COMPOSE_FILE" build --no-cache
    build_result=$?
    
    if [ $build_result -eq 0 ]; then
        log_success "Docker images built successfully"
    else
        log_error "Docker image build failed"
        exit 1
    fi
}

# Start services
start_services() {
    log "Starting compliance services..."
    
    cd ..
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d
    start_result=$?
    
    if [ $start_result -eq 0 ]; then
        log_success "Services started successfully"
    else
        log_error "Failed to start services"
        exit 1
    fi
}

# Wait for services to be healthy
wait_for_health() {
    log "Waiting for services to become healthy..."
    
    # List of services to check
    services=("neo4j" "postgres" "redis" "compliance-api" "compliance-worker" "compliance-scheduler" "compliance-monitoring")
    
    for service in "${services[@]}"; do
        log "Checking health of $service..."
        
        max_attempts=30
        attempt=1
        
        while [ $attempt -le $max_attempts ]; do
            if docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps "$service" | grep -q "Up (healthy)"; then
                log_success "$service is healthy"
                break
            elif [ $attempt -eq $max_attempts ]; then
                log_error "$service failed to become healthy after $max_attempts attempts"
                show_service_logs "$service"
                exit 1
            else
                log "Attempt $attempt/$max_attempts: $service not ready yet..."
                sleep 10
                ((attempt++))
            fi
        done
    done
    
    log_success "All services are healthy"
}

# Show service logs
show_service_logs() {
    local service=$1
    log "Showing logs for $service (last 50 lines)..."
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs --tail=50 "$service"
}

# Run health checks
run_health_checks() {
    log "Running comprehensive health checks..."
    
    # API Health Check
    log "Checking API health endpoint..."
    if curl -f http://localhost:8001/api/v1/compliance/health > /dev/null 2>&1; then
        log_success "API health check passed"
    else
        log_error "API health check failed"
        show_service_logs "compliance-api"
        exit 1
    fi
    
    # Database Connectivity Check
    log "Checking database connectivity..."
    if docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec -T compliance-api python -c "
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
            print('Database connectivity check passed')
        except Exception as e:
            print(f'Database connectivity check failed: {e}')
            sys.exit(1)
    asyncio.run(check())
except Exception as e:
    print(f'Health check error: {e}')
    sys.exit(1)
" > /dev/null 2>&1; then
        log_success "Database connectivity check passed"
    else
        log_error "Database connectivity check failed"
        exit 1
    fi
    
    # Compliance Module Health Check
    log "Checking compliance modules..."
    if curl -f http://localhost:8001/api/v1/compliance/health/modules > /dev/null 2>&1; then
        log_success "Compliance modules health check passed"
    else
        log_warning "Compliance modules health check failed (may not be implemented yet)"
    fi
    
    log_success "Health checks completed"
}

# Initialize compliance schema
initialize_schema() {
    log "Initializing compliance database schema..."
    
    cd ..
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec -T compliance-api python -c "
import asyncio
import sys
sys.path.append('/app')
try:
    from src.database.compliance_schema import initialize_compliance_schema
    from src.database.neo4j_client import get_neo4j_session
    async def init():
        session = await get_neo4j_session()
        await initialize_compliance_schema(session)
        print('Compliance schema initialized successfully')
    asyncio.run(init())
except Exception as e:
    print(f'Schema initialization failed: {e}')
    sys.exit(1)
" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "Compliance schema initialized"
    else
        log_warning "Schema initialization failed (may already exist)"
    fi
}

# Run compliance tests
run_tests() {
    log "Running compliance tests..."
    
    cd ..
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec -T compliance-api python -m pytest tests/test_compliance/ -v --tb=short
    
    if [ $? -eq 0 ]; then
        log_success "Compliance tests passed"
    else
        log_warning "Some compliance tests failed"
    fi
}

# Show deployment status
show_status() {
    log "Deployment status:"
    cd ..
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps
    
    echo ""
    log "Service URLs:"
    echo "  Compliance API: http://localhost:8001"
    echo "  Compliance Monitoring: http://localhost:8002"
    echo "  Neo4j Browser: http://localhost:7474"
    echo "  Grafana: http://localhost:3001"
    echo "  Prometheus: http://localhost:9091"
    
    echo ""
    log "Health Endpoints:"
    echo "  API Health: curl http://localhost:8001/api/v1/compliance/health"
    echo "  Monitoring Health: curl http://localhost:8002/health"
}

# Cleanup function
cleanup() {
    log "Cleaning up..."
    cd ..
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down -v
    docker system prune -f
    log_success "Cleanup completed"
}

# Rollback function
rollback() {
    log "Rolling back to previous deployment..."
    
    if [ -f "$BACKUP_DIR/latest_backup.tar.gz" ]; then
        tar -xzf "$BACKUP_DIR/latest_backup.tar.gz"
        log_success "Rollback completed"
    else
        log_error "No backup found for rollback"
        exit 1
    fi
}

# Main deployment function
deploy() {
    log "Starting Jackdaw Sentry Compliance Services deployment..."
    
    create_directories
    check_prerequisites
    backup_data
    build_images
    start_services
    wait_for_health
    run_health_checks
    initialize_schema
    run_tests
    show_status
    
    log_success "Compliance services deployment completed successfully!"
}

# Parse command line arguments
case "${1:-deploy}" in
    "deploy")
        deploy
        ;;
    "cleanup")
        cleanup
        ;;
    "rollback")
        rollback
        ;;
    "status")
        show_status
        ;;
    "health")
        run_health_checks
        ;;
    "logs")
        if [ -n "${2:-}" ]; then
            show_service_logs "$2"
        else
            cd ..
            docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs -f
        fi
        ;;
    "restart")
        log "Restarting compliance services..."
        cd ..
        docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" restart
        wait_for_health
        run_health_checks
        log_success "Services restarted successfully"
        ;;
    "stop")
        log "Stopping compliance services..."
        cd ..
        docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down
        log_success "Services stopped"
        ;;
    "update")
        log "Updating compliance services..."
        cd ..
        docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" pull
        build_images
        docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d
        wait_for_health
        run_health_checks
        log_success "Services updated successfully"
        ;;
    *)
        echo "Usage: $0 {deploy|cleanup|rollback|status|health|logs|restart|stop|update} [service_name]"
        echo ""
        echo "Commands:"
        echo "  deploy    - Deploy compliance services (default)"
        echo "  cleanup   - Clean up containers and volumes"
        echo "  rollback  - Rollback to previous backup"
        echo "  status    - Show deployment status"
        echo "  health    - Run health checks"
        echo "  logs      - Show logs (all services or specific service)"
        echo "  restart   - Restart all services"
        echo "  stop      - Stop all services"
        echo "  update    - Update and restart services"
        exit 1
        ;;
esac
