# Database Migration Guide

## Overview

This guide explains how to set up and manage database migrations for the Learnify LMS platform using Alembic.

## 🚀 Quick Start (Recommended)

We've created convenient scripts to manage your database. Choose your preferred method:

### Method 1: Database Management Script (Easiest)
```bash
# All-in-one database management tool
./scripts/db.sh reset      # Clear and setup database from scratch
./scripts/db.sh check      # Check database status
./scripts/db.sh migrate    # Apply migrations only
./scripts/db.sh help       # See all available commands
```

### Method 2: Individual Python Scripts
```bash
# Step-by-step approach
python scripts/clear_database.py    # Clear existing data
python scripts/setup_database.py    # Set up fresh database
python scripts/check_database.py    # Verify setup
```

### Method 3: Manual Alembic (Advanced)
```bash
# Traditional approach
alembic upgrade head        # Apply migrations
alembic current            # Check status
```

## Prerequisites

1. **PostgreSQL Database**: Ensure you have a PostgreSQL database running
2. **Environment Configuration**: Make sure your database connection is properly configured in your environment
3. **Dependencies**: Alembic should be installed (already included in requirements)

## Database Configuration

The application expects a PostgreSQL database. Update your configuration in one of these ways:

### Option 1: Environment Variables
```bash
export DATABASE_URL="postgresql+asyncpg://username:password@localhost:5432/learnify_db"
```

### Option 2: Configuration File
Update your `app/config.py` or environment-specific config files with your database credentials.

## 🛠️ Available Scripts

The `scripts/` folder contains several database management tools:

| Script | Purpose | Usage |
|--------|---------|-------|
| `db.sh` | All-in-one management tool | `./scripts/db.sh <command>` |
| `clear_database.py` | Clear all data | `python scripts/clear_database.py` |
| `setup_database.py` | Set up from scratch | `python scripts/setup_database.py` |
| `check_database.py` | Status and health check | `python scripts/check_database.py` |

## Migration Commands

### 1. Apply Migrations (Recommended)
```bash
# Using the management script
./scripts/db.sh migrate

# Or directly with Alembic
alembic upgrade head
```

### 2. Check Migration Status
```bash
# Using the management script
./scripts/db.sh status

# Or directly with Alembic
alembic current
alembic history --verbose
```

### 3. Create New Migrations (For Future Changes)
```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Create empty migration file for manual changes
alembic revision -m "Description of changes"
```

### 4. Rollback Migrations (If Needed)
```bash
# Rollback to previous migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>
```

## Initial Database Setup

### For New Installations:

**Option A: Using Management Script (Recommended)**
```bash
./scripts/db.sh setup
```

**Option B: Step by Step**
1. **Ensure Database Exists**:
   ```sql
   -- Connect to PostgreSQL as superuser and create database
   CREATE DATABASE learnify_db;
   CREATE USER learnify_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE learnify_db TO learnify_user;
   ```

2. **Apply Initial Migration**:
   ```bash
   alembic upgrade head
   ```

3. **Verify Setup**:
   ```bash
   ./scripts/db.sh check
   ```

### For Development with Docker:

If you're using Docker for development:

```bash
# Make sure your database service is running
docker-compose up -d db

# Then run the database setup
./scripts/db.sh setup

# Or individually with uv run
uv run python scripts/setup_database.py
```

## Database Schema

The initial migration creates the following tables:

- **users**: User accounts with roles (Student, Instructor, Staff, Admin)
- **user_avatars**: User profile pictures
- **courses**: Course information and metadata
- **enrollments**: Student-course relationships
- **transactions**: Payment transaction records
- **payments**: Payment status tracking

## Troubleshooting

### Common Issues:

1. **Database Connection Error**:
   ```bash
   # Check your connection
   ./scripts/db.sh check
   ```
   - Verify database is running
   - Check connection string in configuration
   - Ensure database user has proper permissions

2. **Enum Type Already Exists Error**:
   ```bash
   # Reset database to clean state
   ./scripts/db.sh reset
   ```
   - The migration now handles existing enums gracefully
   - If issues persist, clear and recreate

3. **Migration Conflicts**:
   ```bash
   # Check current state
   ./scripts/db.sh status
   
   # If needed, reset to known good state
   ./scripts/db.sh reset
   ```

4. **Manual Schema Fixes**:
   If you need to manually fix the database schema, create a new migration:
   ```bash
   alembic revision -m "Fix schema issue"
   # Edit the generated file with your fixes
   alembic upgrade head
   ```

## Best Practices

1. **Always backup before migrations** in production
2. **Test migrations** on a copy of production data first
3. **Review generated migrations** before applying them
4. **Use descriptive commit messages** for migrations
5. **Never edit applied migrations** - create new ones instead
6. **Use the management scripts** for routine operations

## Production Deployment

For production deployments:

1. **Backup Database**:
   ```bash
   pg_dump learnify_db > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Apply Migrations**:
   ```bash
   # Safest approach - migrations only
   alembic upgrade head
   
   # Or using management script
   ./scripts/db.sh migrate
   ```

3. **Verify Application**:
   ```bash
   ./scripts/db.sh check
   ```
   - Check that all services start correctly
   - Run health checks
   - Verify critical functionality

## Development Workflow

### Typical Development Cycle:
```bash
# Start development
./scripts/db.sh check          # Check current state

# Make model changes
# ... edit your models ...

# Create new migration
alembic revision --autogenerate -m "Add new feature"

# Apply migration
./scripts/db.sh migrate

# Verify changes
./scripts/db.sh check

# If issues arise
./scripts/db.sh reset          # Nuclear option - start fresh
```

### Team Development:
```bash
# Pull latest code
git pull

# Apply any new migrations
./scripts/db.sh migrate

# Check everything is working
./scripts/db.sh check
```

## Getting Help

If you encounter issues with database migrations:

1. **Check the logs**: Look for specific error messages in script output
2. **Verify configuration**: Ensure database settings are correct
3. **Check dependencies**: Make sure all requirements are installed
4. **Use the scripts**: The management scripts handle most common scenarios
5. **Reset if needed**: When in doubt, use `./scripts/db.sh reset`

For detailed script documentation, see `scripts/README.md`.

For development questions, refer to the main project documentation. 