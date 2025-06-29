#!/bin/bash
# Giao Duc Thang Long Development Script

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

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Function to check if docker-compose is available
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi
    
    # Use docker compose if available, otherwise use docker-compose
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    else
        DOCKER_COMPOSE="docker-compose"
    fi
}

# Function to start services
start() {
    print_status "Starting Giao Duc Thang Long development environment..."
    
    check_docker
    check_docker_compose
    
    # Create logs directory if it doesn't exist
    mkdir -p logs
    
    # Start services
    $DOCKER_COMPOSE up -d
    
    print_success "Services started successfully!"
    print_status "API: http://localhost:8000"
    print_status "API Docs: http://localhost:8000/docs"
    print_status "PostgreSQL: localhost:5432"
    print_status "Redis: localhost:6379"
    print_status ""
    print_status "To start development tools:"
    print_status "$DOCKER_COMPOSE --profile dev up -d"
    print_status "Then visit:"
    print_status "  - pgAdmin: http://localhost:8080"
    print_status "  - Redis Commander: http://localhost:8081"
}

# Function to start with dev tools
start_dev() {
    print_status "Starting Giao Duc Thang Long with development tools..."
    
    check_docker
    check_docker_compose
    
    # Create logs directory if it doesn't exist
    mkdir -p logs
    
    # Start services with dev profile
    $DOCKER_COMPOSE --profile dev up -d
    
    print_success "Services with dev tools started successfully!"
    print_status "API: http://localhost:8000"
    print_status "API Docs: http://localhost:8000/docs"
    print_status "pgAdmin: http://localhost:8080"
    print_status "Redis Commander: http://localhost:8081"
}

# Function to stop services
stop() {
    print_status "Stopping Giao Duc Thang Long services..."
    
    check_docker_compose
    
    $DOCKER_COMPOSE down
    
    print_success "Services stopped successfully!"
}

# Function to restart services
restart() {
    print_status "Restarting Giao Duc Thang Long services..."
    stop
    start
}

# Function to view logs
logs() {
    check_docker_compose
    
    if [ -n "$2" ]; then
        $DOCKER_COMPOSE logs -f "$2"
    else
        $DOCKER_COMPOSE logs -f
    fi
}

# Function to run database migrations
migrate() {
    print_status "Running database migrations..."
    
    check_docker_compose
    
    # Run migrations inside the app container
    $DOCKER_COMPOSE exec app uv run alembic upgrade head
    
    print_success "Database migrations completed!"
}

# Function to create a new migration
makemigration() {
    print_status "Creating new migration..."
    
    check_docker_compose
    
    if [ -n "$2" ]; then
        $DOCKER_COMPOSE exec app uv run alembic revision --autogenerate -m "$2"
    else
        print_error "Please provide a migration message: ./scripts/dev.sh makemigration 'Your migration message'"
        exit 1
    fi
    
    print_success "Migration created successfully!"
}

# Function to run tests
test() {
    print_status "Running tests..."
    
    check_docker_compose
    
    $DOCKER_COMPOSE exec app uv run pytest
    
    print_success "Tests completed!"
}

# Function to enter shell
shell() {
    print_status "Entering app container shell..."
    
    check_docker_compose
    
    $DOCKER_COMPOSE exec app bash
}

# Function to show status
status() {
    check_docker_compose
    
    print_status "Service Status:"
    $DOCKER_COMPOSE ps
}

# Function to cleanup
cleanup() {
    print_warning "This will remove all containers, volumes, and networks!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Cleaning up..."
        $DOCKER_COMPOSE down -v --remove-orphans
        docker system prune -f
        print_success "Cleanup completed!"
    else
        print_status "Cleanup cancelled."
    fi
}

# Function to show help
help() {
    echo "Giao Duc Thang Long Development Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start         Start all services"
    echo "  start-dev     Start all services with development tools"
    echo "  stop          Stop all services"
    echo "  restart       Restart all services"
    echo "  logs [service] Show logs (optionally for specific service)"
    echo "  migrate       Run database migrations"
    echo "  makemigration Create new migration"
    echo "  test          Run tests"
    echo "  shell         Enter app container shell"
    echo "  status        Show service status"
    echo "  cleanup       Remove all containers and volumes"
    echo "  help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 logs app"
    echo "  $0 makemigration 'Add user table'"
}

# Main script logic
case "$1" in
    start)
        start
        ;;
    start-dev)
        start_dev
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs "$@"
        ;;
    migrate)
        migrate
        ;;
    makemigration)
        makemigration "$@"
        ;;
    test)
        test
        ;;
    shell)
        shell
        ;;
    status)
        status
        ;;
    cleanup)
        cleanup
        ;;
    help|--help|-h)
        help
        ;;
    "")
        help
        ;;
    *)
        print_error "Unknown command: $1"
        help
        exit 1
        ;;
esac 