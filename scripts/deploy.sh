#!/bin/bash

# CloudArb Deployment Script
# This script deploys the complete CloudArb platform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-development}
COMPOSE_FILE="docker-compose.yml"
PROJECT_NAME="cloudarb"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
    fi

    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running. Please start Docker first."
    fi

    log "Prerequisites check passed"
}

# Create environment file
create_env_file() {
    log "Creating environment file..."

    if [ ! -f .env ]; then
        cat > .env << EOF
# CloudArb Environment Configuration
ENVIRONMENT=${ENVIRONMENT}

# Database Configuration
DB_HOST=postgres
DB_PORT=5432
DB_NAME=cloudarb
DB_USER=cloudarb
DB_PASSWORD=cloudarb_password

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379

# Security
SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# Cloud Provider API Keys (Add your actual keys)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1

GCP_PROJECT_ID=your_gcp_project_id
GCP_CREDENTIALS_FILE=/path/to/credentials.json

AZURE_SUBSCRIPTION_ID=your_azure_subscription_id
AZURE_TENANT_ID=your_azure_tenant_id
AZURE_CLIENT_ID=your_azure_client_id
AZURE_CLIENT_SECRET=your_azure_client_secret

LAMBDA_API_KEY=your_lambda_api_key
RUNPOD_API_KEY=your_runpod_api_key

# Optimization Configuration
SOLVER_TIMEOUT_SECONDS=30
MAX_ITERATIONS=10000
RISK_TOLERANCE=0.1

# Monitoring
PROMETHEUS_PORT=9090
LOG_LEVEL=INFO
ENABLE_METRICS=true
ENABLE_TRACING=true

# Application Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=4
DEBUG=true
EOF
        log "Environment file created: .env"
        warn "Please update the .env file with your actual API keys and configuration"
    else
        log "Environment file already exists: .env"
    fi
}

# Build Docker images
build_images() {
    log "Building Docker images..."

    docker-compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} build --no-cache

    log "Docker images built successfully"
}

# Start services
start_services() {
    log "Starting CloudArb services..."

    # Start core services first
    docker-compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} up -d postgres redis

    # Wait for database to be ready
    log "Waiting for database to be ready..."
    sleep 30

    # Start remaining services
    docker-compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} up -d

    log "Services started successfully"
}

# Wait for services to be healthy
wait_for_services() {
    log "Waiting for services to be healthy..."

    # Wait for API
    log "Waiting for API service..."
    timeout=300
    while [ $timeout -gt 0 ]; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            log "API service is healthy"
            break
        fi
        sleep 5
        timeout=$((timeout - 5))
    done

    if [ $timeout -le 0 ]; then
        error "API service failed to become healthy"
    fi

    # Wait for frontend
    log "Waiting for frontend service..."
    timeout=120
    while [ $timeout -gt 0 ]; do
        if curl -f http://localhost:3000 &> /dev/null; then
            log "Frontend service is healthy"
            break
        fi
        sleep 5
        timeout=$((timeout - 5))
    done

    if [ $timeout -le 0 ]; then
        warn "Frontend service may not be ready yet"
    fi

    log "All services are healthy"
}

# Initialize database
init_database() {
    log "Initializing database..."

    # Run database migrations
    docker-compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} exec -T api alembic upgrade head

    # Seed initial data
    docker-compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} exec -T api python -m cloudarb.scripts.seed_data

    log "Database initialized successfully"
}

# Setup monitoring
setup_monitoring() {
    log "Setting up monitoring..."

    # Wait for Prometheus
    log "Waiting for Prometheus..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if curl -f http://localhost:9090/-/healthy &> /dev/null; then
            log "Prometheus is ready"
            break
        fi
        sleep 5
        timeout=$((timeout - 5))
    done

    # Wait for Grafana
    log "Waiting for Grafana..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if curl -f http://localhost:3001/api/health &> /dev/null; then
            log "Grafana is ready"
            break
        fi
        sleep 5
        timeout=$((timeout - 5))
    done

    log "Monitoring setup completed"
}

# Display deployment information
show_deployment_info() {
    log "Deployment completed successfully!"
    echo
    echo -e "${BLUE}CloudArb Platform is now running:${NC}"
    echo
    echo -e "${GREEN}Frontend Dashboard:${NC} http://localhost:3000"
    echo -e "${GREEN}API Documentation:${NC} http://localhost:8000/docs"
    echo -e "${GREEN}API Health Check:${NC} http://localhost:8000/health"
    echo -e "${GREEN}Grafana Dashboards:${NC} http://localhost:3001 (admin/admin)"
    echo -e "${GREEN}Prometheus Metrics:${NC} http://localhost:9090"
    echo
    echo -e "${YELLOW}Default credentials:${NC}"
    echo -e "  Username: admin@cloudarb.com"
    echo -e "  Password: admin123"
    echo
    echo -e "${YELLOW}Next steps:${NC}"
    echo -e "  1. Update the .env file with your actual cloud provider API keys"
    echo -e "  2. Configure your cloud provider credentials"
    echo -e "  3. Start the data ingestion service to collect pricing data"
    echo -e "  4. Create your first optimization"
    echo
}

# Stop services
stop_services() {
    log "Stopping CloudArb services..."
    docker-compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} down
    log "Services stopped"
}

# Remove services and volumes
cleanup() {
    log "Cleaning up CloudArb deployment..."
    docker-compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} down -v
    docker system prune -f
    log "Cleanup completed"
}

# Show logs
show_logs() {
    log "Showing service logs..."
    docker-compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} logs -f
}

# Show service status
show_status() {
    log "Service status:"
    docker-compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} ps
}

# Main deployment function
deploy() {
    log "Starting CloudArb deployment for environment: ${ENVIRONMENT}"

    check_prerequisites
    create_env_file
    build_images
    start_services
    wait_for_services
    init_database
    setup_monitoring
    show_deployment_info
}

# Command line interface
case "${2:-deploy}" in
    "deploy")
        deploy
        ;;
    "stop")
        stop_services
        ;;
    "start")
        start_services
        wait_for_services
        ;;
    "restart")
        stop_services
        start_services
        wait_for_services
        ;;
    "cleanup")
        cleanup
        ;;
    "logs")
        show_logs
        ;;
    "status")
        show_status
        ;;
    "build")
        build_images
        ;;
    "init-db")
        init_database
        ;;
    *)
        echo "Usage: $0 [environment] [command]"
        echo
        echo "Environments:"
        echo "  development (default)"
        echo "  staging"
        echo "  production"
        echo
        echo "Commands:"
        echo "  deploy     - Full deployment (default)"
        echo "  start      - Start services"
        echo "  stop       - Stop services"
        echo "  restart    - Restart services"
        echo "  cleanup    - Remove all containers and volumes"
        echo "  logs       - Show service logs"
        echo "  status     - Show service status"
        echo "  build      - Build Docker images"
        echo "  init-db    - Initialize database"
        echo
        echo "Examples:"
        echo "  $0                    # Deploy to development"
        echo "  $0 production deploy  # Deploy to production"
        echo "  $0 development logs   # Show logs for development"
        ;;
esac