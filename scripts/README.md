# Scripts Directory

This directory contains utility scripts for the Learnify LMS system.

## Database Schema Tool (`show_db_schema.py`)

A comprehensive tool for displaying database schema information.

### Usage

```bash
# Show help
python scripts/show_db_schema.py --help

# Or from Docker container
docker compose exec app uv run python scripts/show_db_schema.py --help
```

### Available Commands

#### `list-tables`
Shows a summary of all tables with row counts and metadata:
```bash
python scripts/show_db_schema.py list-tables
```

#### `show-table`
Shows detailed information about a specific table including columns, types, constraints, indexes, and relationships:
```bash
python scripts/show_db_schema.py show-table --table users
```

#### `show-all`
Shows comprehensive schema information for all tables:
```bash
python scripts/show_db_schema.py show-all
```

#### `show-relationships`
Shows all foreign key relationships in the database:
```bash
python scripts/show_db_schema.py show-relationships
```

#### `show-constraints`
Shows all constraints (primary keys, foreign keys, unique constraints, etc.):
```bash
python scripts/show_db_schema.py show-constraints
```

### Example Output

The script provides rich, emoji-enhanced output showing:
- 📊 Table summaries with row counts
- 📝 Column definitions with types and constraints
- 🔍 Indexes and their definitions
- 🔗 Foreign key relationships
- 🔙 Tables that reference the current table
- 📦 Table sizes and storage information

## Admin CLI Tool (`admin_cli.py`)

Administrative operations for the Learnify LMS system.

### Usage

```bash
# Show help
python scripts/admin_cli.py --help

# Create admin user
python scripts/admin_cli.py create-admin --email admin@example.com

# List all users
python scripts/admin_cli.py list-users

# Show database information
python scripts/admin_cli.py database-info
```

## Setup Script (`setup_data_dirs.sh`)

Shell script for setting up data directories.

### Usage

```bash
bash scripts/setup_data_dirs.sh
```

## Notes

- All scripts should be run from the project root directory
- When using Docker, prefix commands with `docker compose exec app uv run`
- Scripts require proper database connectivity as configured in your environment
- The schema tool requires PostgreSQL (uses PostgreSQL-specific queries) 