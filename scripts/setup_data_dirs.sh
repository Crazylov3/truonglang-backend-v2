#!/bin/bash

# Setup script for Truong Lang Web Data Directories
# This script creates the necessary directories for Docker bind mounts

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Main data directory
DATA_DIR="$HOME/.truonglang_web_data"

echo "🚀 Setting up Truong Lang Web Data Directories"
echo "=============================================="
echo ""

print_info "Creating data directories in: $DATA_DIR"

# Create main directory
mkdir -p "$DATA_DIR"
print_success "Created main directory: $DATA_DIR"

# Create subdirectories for each service
mkdir -p "$DATA_DIR/postgres"
mkdir -p "$DATA_DIR/redis" 
mkdir -p "$DATA_DIR/uv_cache"

print_success "Created PostgreSQL data directory: $DATA_DIR/postgres"
print_success "Created Redis data directory: $DATA_DIR/redis"
print_success "Created UV cache directory: $DATA_DIR/uv_cache"

# Set proper permissions
# PostgreSQL needs specific ownership (UID 999 in the postgres:15-alpine container)
print_info "Setting up permissions..."

# For PostgreSQL (container runs as postgres user with UID 999)
sudo chown -R 999:999 "$DATA_DIR/postgres" 2>/dev/null || {
    print_warning "Could not set PostgreSQL permissions. You may need to run:"
    echo "  sudo chown -R 999:999 $DATA_DIR/postgres"
}

# For Redis (container runs as redis user with UID 999)
sudo chown -R 999:999 "$DATA_DIR/redis" 2>/dev/null || {
    print_warning "Could not set Redis permissions. You may need to run:"
    echo "  sudo chown -R 999:999 $DATA_DIR/redis"
}

# UV cache can be owned by current user
chown -R "$(id -u):$(id -g)" "$DATA_DIR/uv_cache"

print_success "Permissions configured"

# Show directory structure
echo ""
print_info "Directory structure created:"
echo "📁 $DATA_DIR/"
echo "├── 📁 postgres/     (PostgreSQL database files)"
echo "├── 📁 redis/        (Redis data files)"
echo "└── 📁 uv_cache/     (UV package cache)"

echo ""
print_success "Setup completed! Your Docker services will now store data in:"
print_info "$DATA_DIR"

echo ""
print_info "Next steps:"
echo "1. Run: docker-compose down (if running)"
echo "2. Run: docker-compose up -d"
echo "3. Your data will persist in the custom directory!"

echo ""
print_warning "Note: If you encounter permission issues, you may need to:"
echo "  sudo chown -R 999:999 $DATA_DIR/postgres"
echo "  sudo chown -R 999:999 $DATA_DIR/redis" 
