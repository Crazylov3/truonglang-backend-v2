#!/bin/bash

# Database Management Script for Learnify LMS
# This script provides convenient shortcuts for database operations

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Detect if we're in a Docker container
if [ -f /.dockerenv ]; then
    PYTHON_CMD="uv run python"
    ALEMBIC_CMD="uv run alembic"
    print_info "Detected Docker environment"
else
    PYTHON_CMD="python"
    ALEMBIC_CMD="alembic"
    print_info "Detected local environment"
fi

# Function to show usage
show_usage() {
    echo "🚀 Learnify Database Management Tool"
    echo "======================================"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Available commands:"
    echo "  check     - Check database status and health"
    echo "  setup     - Set up database from scratch"
    echo "  clear     - Clear all database data (⚠️ DESTRUCTIVE)"
    echo "  migrate   - Run database migrations"
    echo "  reset     - Clear database and set up fresh (clear + setup)"
    echo "  status    - Show migration status"
    echo "  help      - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 check          # Check current database state"
    echo "  $0 setup          # Set up database for first time"
    echo "  $0 reset          # Complete reset and setup"
    echo "  $0 migrate        # Apply pending migrations"
    echo ""
}

# Function to check if database scripts exist
check_scripts() {
    local script_dir="$(dirname "$0")"
    if [ ! -f "$script_dir/check_database.py" ] || [ ! -f "$script_dir/setup_database.py" ] || [ ! -f "$script_dir/clear_database.py" ]; then
        print_error "Database scripts not found in $script_dir"
        print_info "Make sure you're running this from the correct directory"
        exit 1
    fi
}

# Function to run database check
cmd_check() {
    print_info "Running database status check..."
    $PYTHON_CMD scripts/check_database.py
}

# Function to run database setup
cmd_setup() {
    print_info "Setting up database..."
    $PYTHON_CMD scripts/setup_database.py
}

# Function to clear database
cmd_clear() {
    print_warning "This will PERMANENTLY DELETE all data!"
    read -p "Are you sure you want to continue? (yes/no): " -r
    if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        print_info "Clearing database..."
        $PYTHON_CMD scripts/clear_database.py
    else
        print_info "Operation cancelled"
        exit 0
    fi
}

# Function to run migrations only
cmd_migrate() {
    print_info "Running database migrations..."
    $ALEMBIC_CMD upgrade head
    if [ $? -eq 0 ]; then
        print_success "Migrations completed successfully!"
    else
        print_error "Migration failed!"
        exit 1
    fi
}

# Function to reset database (clear + setup)
cmd_reset() {
    print_warning "This will PERMANENTLY DELETE all data and recreate the database!"
    read -p "Are you sure you want to continue? (yes/no): " -r
    if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        print_info "Resetting database..."
        echo "yes" | $PYTHON_CMD scripts/clear_database.py
        $PYTHON_CMD scripts/setup_database.py
        print_success "Database reset completed!"
    else
        print_info "Operation cancelled"
        exit 0
    fi
}

# Function to show migration status
cmd_status() {
    print_info "Checking migration status..."
    echo "Current migration:"
    $ALEMBIC_CMD current
    echo ""
    echo "Available migrations:"
    $ALEMBIC_CMD history --verbose
}

# Main command processing
main() {
    # Check if scripts exist
    check_scripts
    
    # Process command
    case "${1:-help}" in
        "check")
            cmd_check
            ;;
        "setup")
            cmd_setup
            ;;
        "clear")
            cmd_clear
            ;;
        "migrate")
            cmd_migrate
            ;;
        "reset")
            cmd_reset
            ;;
        "status")
            cmd_status
            ;;
        "help"|"--help"|"-h")
            show_usage
            ;;
        *)
            print_error "Unknown command: $1"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@" 