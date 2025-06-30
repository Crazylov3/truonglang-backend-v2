# Database Management Scripts

This folder contains utility scripts for managing the Learnify LMS database.

## 🛠️ Available Scripts

### 1. `clear_database.py` - Database Reset
**Purpose**: Completely clears the database and resets it to a clean state.

```bash
# Local development
python scripts/clear_database.py

# Docker container
uv run python scripts/clear_database.py
```

**What it does**:
- ⚠️ **PERMANENTLY DELETES ALL DATA**
- Drops all tables and schemas
- Removes enum types
- Clears Alembic version tracking
- Verifies the database is empty

**Use when**:
- Starting fresh development
- Resolving migration conflicts
- Cleaning up after testing

---

### 2. `setup_database.py` - Database Setup
**Purpose**: Sets up the database from scratch with all tables and initial data.

```bash
# Local development
python scripts/setup_database.py

# Docker container  
uv run python scripts/setup_database.py
```

**What it does**:
- ✅ Checks database connection
- 🔄 Runs Alembic migrations
- 🔍 Verifies all tables are created
- 👤 Optionally creates admin user
- 📊 Shows setup summary

**Use when**:
- Initial project setup
- After clearing the database
- Setting up new environments

---

### 3. `check_database.py` - Database Status
**Purpose**: Provides comprehensive database health and status information.

```bash
# Local development
python scripts/check_database.py

# Docker container
uv run python scripts/check_database.py
```

**What it shows**:
- 🔍 Connection status and database info
- 🔄 Migration status (current vs latest)
- 📋 Table list with row counts
- 🔢 Enum types and values
- 🗂️ Database indexes
- 👥 User and data summaries

**Use when**:
- Debugging database issues
- Checking migration status
- Monitoring database health
- Understanding current data state

---

## 🚀 Quick Start Guide

### For New Projects:
```bash
# 1. Clear any existing data (optional)
python scripts/clear_database.py

# 2. Set up fresh database
python scripts/setup_database.py

# 3. Verify everything is working
python scripts/check_database.py
```

### For Docker Development:
```bash
# Make sure your database service is running
docker-compose up -d db

# Then run the scripts with uv
uv run python scripts/clear_database.py
uv run python scripts/setup_database.py
uv run python scripts/check_database.py
```

---

## 📋 Prerequisites

1. **PostgreSQL Database**: Must be running and accessible
2. **Environment Configuration**: Database connection properly configured
3. **Dependencies**: All Python dependencies installed
4. **Alembic**: Migration tool available in your environment

---

## 🔧 Configuration

The scripts use your existing database configuration from `app/config.py`:
- Database host, port, name
- Username and password
- Connection settings

Make sure your environment variables or config files are properly set up before running the scripts.

---

## 🆘 Troubleshooting

### Common Issues:

**"Could not connect to database"**
- ✅ Check PostgreSQL is running
- ✅ Verify database credentials
- ✅ Ensure database exists
- ✅ Check firewall/network settings

**"Alembic command not found"**
- ✅ Run with `uv run` prefix in Docker
- ✅ Ensure Alembic is installed
- ✅ Check your Python environment

**"Permission denied"**
- ✅ Check database user permissions
- ✅ Ensure user can create/drop tables
- ✅ Verify schema permissions

**"Migration conflicts"**
- ✅ Run `clear_database.py` to reset
- ✅ Then run `setup_database.py`
- ✅ Check for manual schema changes

---

## ⚠️ Safety Notes

1. **Backup Before Clearing**: Always backup production data before using `clear_database.py`
2. **Test First**: Test scripts on development data before production
3. **Review Output**: Check script output for any errors or warnings
4. **Confirm Operations**: Scripts will ask for confirmation before destructive operations

---

## 🔄 Typical Workflow

```bash
# Development cycle
python scripts/check_database.py      # Check current state
python scripts/clear_database.py     # Reset if needed
python scripts/setup_database.py     # Set up fresh
python scripts/check_database.py     # Verify success

# Production deployment
python scripts/check_database.py     # Check before deploy
alembic upgrade head                  # Apply migrations only
python scripts/check_database.py     # Verify deployment
```

---

## 📞 Support

If you encounter issues with these scripts:
1. Check the detailed error messages in the output
2. Verify your database configuration
3. Ensure all prerequisites are met
4. Review the troubleshooting section above

For more help, refer to the main project documentation. 