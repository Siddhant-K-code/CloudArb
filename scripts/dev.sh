#!/bin/bash

# CloudArb Development Environment Script
# This script starts all required services for local development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for a service to be ready
wait_for_service() {
    local service_name=$1
    local host=$2
    local port=$3
    local max_attempts=30
    local attempt=1

    print_status "Waiting for $service_name to be ready..."

    while [ $attempt -le $max_attempts ]; do
        # Try different methods to check if service is ready
        if command -v nc >/dev/null 2>&1 && nc -z "$host" "$port" 2>/dev/null; then
            print_success "$service_name is ready!"
            return 0
        elif command -v curl >/dev/null 2>&1 && curl -s "http://$host:$port" >/dev/null 2>&1; then
            print_success "$service_name is ready!"
            return 0
        elif [ "$service_name" = "PostgreSQL" ] && docker exec cloudarb-postgres pg_isready -U cloudarb -d cloudarb >/dev/null 2>&1; then
            print_success "$service_name is ready!"
            return 0
        elif [ "$service_name" = "Redis" ] && docker exec cloudarb-redis redis-cli ping >/dev/null 2>&1; then
            print_success "$service_name is ready!"
            return 0
        fi

        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    print_error "$service_name failed to start within $((max_attempts * 2)) seconds"
    return 1
}

# Function to start PostgreSQL
start_postgres() {
    print_status "Starting PostgreSQL with TimescaleDB..."

    # Check if PostgreSQL container is already running
    if docker ps --format "table {{.Names}}" | grep -q "cloudarb-postgres"; then
        print_warning "PostgreSQL container is already running"
        return 0
    fi

    # Check if PostgreSQL container exists but is stopped
    if docker ps -a --format "table {{.Names}}" | grep -q "cloudarb-postgres"; then
        print_status "Starting existing PostgreSQL container..."
        docker start cloudarb-postgres
    else
        # Start new PostgreSQL container
        docker run -d \
            --name cloudarb-postgres \
            --network host \
            -e POSTGRES_DB=cloudarb \
            -e POSTGRES_USER=cloudarb \
            -e POSTGRES_PASSWORD=cloudarb_password \
            -e POSTGRES_HOST_AUTH_METHOD=trust \
            -v postgres_data:/var/lib/postgresql/data \
            timescale/timescaledb:latest-pg14
    fi

    wait_for_service "PostgreSQL" "localhost" "5432"
}

# Function to start Redis
start_redis() {
    print_status "Starting Redis..."

    # Check if Redis container is already running
    if docker ps --format "table {{.Names}}" | grep -q "cloudarb-redis"; then
        print_warning "Redis container is already running"
        return 0
    fi

    # Check if Redis container exists but is stopped
    if docker ps -a --format "table {{.Names}}" | grep -q "cloudarb-redis"; then
        print_status "Starting existing Redis container..."
        docker start cloudarb-redis
    else
        # Start new Redis container
        docker run -d \
            --name cloudarb-redis \
            --network host \
            -v redis_data:/data \
            redis:7-alpine redis-server --appendonly yes
    fi

    wait_for_service "Redis" "localhost" "6379"
}

# Function to start API backend
start_api() {
    print_status "Starting CloudArb API..."

    # Check if API is already running
    if pgrep -f "uvicorn cloudarb.main:app" > /dev/null; then
        print_warning "API is already running"
        return 0
    fi

    # Set up Python environment
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Install dependencies
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt

    # Set environment variables
    export DB_HOST=localhost
    export DB_PORT=5432
    export DB_NAME=cloudarb
    export DB_USER=cloudarb
    export DB_PASSWORD=cloudarb_password
    export REDIS_HOST=localhost
    export REDIS_PORT=6379
    export SECRET_KEY=dev-secret-key-change-in-production
    export ENVIRONMENT=development
    export DEBUG=true
    export LOG_LEVEL=INFO

    # Start API server in background
    cd src
    nohup python -m uvicorn cloudarb.main:app --host 0.0.0.0 --port 8000 --reload > ../logs/api.log 2>&1 &
    cd ..

    wait_for_service "API" "localhost" "8000"
}

# Function to start frontend
start_frontend() {
    print_status "Starting CloudArb Frontend..."

    # Check if frontend is already running
    if pgrep -f "react-scripts start\|serve -s build" > /dev/null; then
        print_warning "Frontend is already running"
        return 0
    fi

    # Set up Node.js 18 if available
    if command -v nvm >/dev/null 2>&1; then
        print_status "Setting up Node.js 18..."
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
        nvm use 18 2>/dev/null || nvm install 18 && nvm use 18
    fi

    # Install frontend dependencies
    cd frontend
    if [ ! -d "node_modules" ]; then
        print_status "Installing frontend dependencies..."
        npm install
    fi

    # Try development server first, fallback to production build
    print_status "Building frontend for development..."
    if npm run build; then
        print_status "Starting frontend with production build (hot reload disabled)"
        # Set environment variables for development
        export REACT_APP_API_URL=http://localhost:8000
        export REACT_APP_WS_URL=ws://localhost:8000

        # Start production build server in background with client-side routing support
        nohup npx serve -s build -l 3000 --config serve.json > ../logs/frontend.log 2>&1 &
        cd ..

        wait_for_service "Frontend" "localhost" "3000"
    else
        print_error "Failed to build frontend"
        cd ..
        return 1
    fi
}

# Function to start monitoring services
start_monitoring() {
    print_status "Starting monitoring services..."

    # Create monitoring directory
    mkdir -p monitoring

    # Create Prometheus config
    cat > monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: 'cloudarb-api'
    static_configs:
      - targets: ['localhost:8000']
EOF

    # Start Prometheus
    if ! docker ps --format "table {{.Names}}" | grep -q "cloudarb-prometheus"; then
        docker run -d \
            --name cloudarb-prometheus \
            --network host \
            -v $(pwd)/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml \
            -v prometheus_data:/prometheus \
            prom/prometheus:latest \
            --config.file=/etc/prometheus/prometheus.yml \
            --storage.tsdb.path=/prometheus \
            --web.enable-lifecycle
    fi

    # Start Grafana
    if ! docker ps --format "table {{.Names}}" | grep -q "cloudarb-grafana"; then
        docker run -d \
            --name cloudarb-grafana \
            --network host \
            -e GF_SECURITY_ADMIN_PASSWORD=admin \
            -e GF_USERS_ALLOW_SIGN_UP=false \
            -e GF_SERVER_HTTP_PORT=3001 \
            -v grafana_data:/var/lib/grafana \
            grafana/grafana:latest
    fi

    wait_for_service "Prometheus" "localhost" "9090"
    wait_for_service "Grafana" "localhost" "3001"
}

# Function to initialize database
init_database() {
    print_status "Initializing database..."

    # Wait for PostgreSQL to be ready
    wait_for_service "PostgreSQL" "localhost" "5432"

    # Activate virtual environment
    source venv/bin/activate

    # Set environment variables
    export DB_HOST=localhost
    export DB_PORT=5432
    export DB_NAME=cloudarb
    export DB_USER=cloudarb
    export DB_PASSWORD=cloudarb_password

    # Run database migrations
    cd src
    python -c "
from cloudarb.database import engine
from cloudarb.models import Base
Base.metadata.create_all(bind=engine)
print('Database schema created successfully!')
"

    # Insert initial data
    python -c "
from cloudarb.database import SessionLocal
from cloudarb.models.user import User
from cloudarb.models.role import Role
from cloudarb.services.auth_service import get_password_hash

db = SessionLocal()
try:
    # Create admin role if it doesn't exist
    admin_role = db.query(Role).filter(Role.name == 'admin').first()
    if not admin_role:
        admin_role = Role(name='admin', description='Administrator')
        db.add(admin_role)
        db.commit()
        print('Admin role created')

    # Create admin user if it doesn't exist
    admin_user = db.query(User).filter(User.email == 'admin@cloudarb.com').first()
    if not admin_user:
        admin_user = User(
            email='admin@cloudarb.com',
            hashed_password=get_password_hash('admin123'),
            full_name='Admin User',
            role_id=admin_role.id
        )
        db.add(admin_user)
        db.commit()
        print('Admin user created')
except Exception as e:
    print(f'Error initializing database: {e}')
finally:
    db.close()
"
    cd ..
}

# Function to show status
show_status() {
    print_status "Development Environment Status:"
    echo

    # Check PostgreSQL
    if docker ps --format "table {{.Names}}" | grep -q "cloudarb-postgres"; then
        print_success "PostgreSQL: Running"
    else
        print_error "PostgreSQL: Not running"
    fi

    # Check Redis
    if docker ps --format "table {{.Names}}" | grep -q "cloudarb-redis"; then
        print_success "Redis: Running"
    else
        print_error "Redis: Not running"
    fi

    # Check API
    if pgrep -f "uvicorn cloudarb.main:app" > /dev/null; then
        print_success "API: Running"
    else
        print_error "API: Not running"
    fi

    # Check Frontend
    if pgrep -f "react-scripts start\|serve -s build" > /dev/null; then
        print_success "Frontend: Running"
    else
        print_error "Frontend: Not running"
    fi

    # Check Prometheus
    if docker ps --format "table {{.Names}}" | grep -q "cloudarb-prometheus"; then
        print_success "Prometheus: Running"
    else
        print_error "Prometheus: Not running"
    fi

    # Check Grafana
    if docker ps --format "table {{.Names}}" | grep -q "cloudarb-grafana"; then
        print_success "Grafana: Running"
    else
        print_error "Grafana: Not running"
    fi

    echo
    print_status "Access URLs:"
    echo "  Frontend: http://localhost:3000"
    echo "  API: http://localhost:8000"
    echo "  API Docs: http://localhost:8000/docs"
    echo "  Prometheus: http://localhost:9090"
    echo "  Grafana: http://localhost:3001 (admin/admin)"
}

# Function to stop all services
stop_all() {
    print_status "Stopping all development services..."

    # Stop frontend
    pkill -f "react-scripts start" 2>/dev/null || true
    pkill -f "serve -s build" 2>/dev/null || true

    # Stop API
    pkill -f "uvicorn cloudarb.main:app" 2>/dev/null || true

    # Stop containers
    docker stop cloudarb-postgres cloudarb-redis cloudarb-prometheus cloudarb-grafana 2>/dev/null || true
    docker rm cloudarb-postgres cloudarb-redis cloudarb-prometheus cloudarb-grafana 2>/dev/null || true

    print_success "All services stopped"
}

# Function to clean up
cleanup() {
    print_status "Cleaning up development environment..."

    # Stop all services
    stop_all

    # Remove volumes
    docker volume rm cloudarb_postgres_data cloudarb_redis_data prometheus_data grafana_data 2>/dev/null || true

    # Remove virtual environment
    rm -rf venv

    # Remove node_modules
    rm -rf frontend/node_modules

    # Remove logs
    rm -rf logs

    print_success "Development environment cleaned up"
}

# Function to clean up Docker Compose containers
cleanup_docker_compose() {
    print_status "Cleaning up Docker Compose containers..."

    # Stop and remove Docker Compose containers
    docker-compose down 2>/dev/null || true

    # Remove any remaining containers with cloudarb names
    docker stop $(docker ps -q --filter "name=cloudarb") 2>/dev/null || true
    docker rm $(docker ps -aq --filter "name=cloudarb") 2>/dev/null || true

    print_success "Docker Compose containers cleaned up"
}

# Main script logic
case "${1:-start}" in
    "start")
        print_status "Starting CloudArb development environment..."

        # Create logs directory
        mkdir -p logs

        # Start services
        start_postgres
        start_redis
        start_api
        start_frontend
        start_monitoring

        # Initialize database
        init_database

        print_success "Development environment started successfully!"
        echo
        show_status
        ;;

    "stop")
        stop_all
        ;;

    "restart")
        stop_all
        sleep 2
        $0 start
        ;;

    "status")
        show_status
        ;;

        "cleanup")
        cleanup
        ;;

    "cleanup-docker")
        cleanup_docker_compose
        ;;

    "logs")
        print_status "Showing logs..."
        echo "API logs:"
        tail -f logs/api.log &
        echo "Frontend logs:"
        tail -f logs/frontend.log &
        ;;

    *)
        echo "Usage: $0 {start|stop|restart|status|cleanup|cleanup-docker|logs}"
        echo
        echo "Commands:"
        echo "  start         - Start all development services"
        echo "  stop          - Stop all development services"
        echo "  restart       - Restart all development services"
        echo "  status        - Show status of all services"
        echo "  cleanup       - Stop services and clean up environment"
        echo "  cleanup-docker - Clean up Docker Compose containers"
        echo "  logs          - Show live logs from API and frontend"
        exit 1
        ;;
esac