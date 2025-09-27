# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Running the Application
```bash
# Development mode with auto-reload
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using Python module
uv run python -m app.main
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_auth.py

# Run with coverage
uv run pytest --cov=app
```

### Code Quality Tools
```bash
# Format code with Black
uv run black app/

# Sort imports with isort
uv run isort app/

# Lint with flake8
uv run flake8 app/

# Type checking with mypy
uv run mypy app/
```

### Database Migrations
```bash
# Create new migration
uv run alembic revision --autogenerate -m "Description of changes"

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1
```

## Architecture Overview

This is a FastAPI-based Learning Management System (LMS) with a modular, layered architecture:

### Core Components

1. **app/main.py**: FastAPI application entry point
   - Configures middleware (CORS, TrustedHost, Audit)
   - Sets up lifespan events
   - Registers all routers

2. **Configuration System** (app/config.py, app/cfg_manager.py):
   - Hierarchical config loading: base.yaml → environment-specific YAML → .env
   - Supports dot notation access (Cfg.database.host)
   - Environment variables override YAML configs
   - Backward compatibility with Settings class

3. **Database Layer** (app/database.py):
   - SQLAlchemy with async support (asyncpg)
   - Session management with dependency injection
   - Base model definitions in app/models/base.py

4. **Authentication & Security**:
   - JWT-based authentication with Redis session storage
   - Role-based access control (Student, Instructor, Staff, Admin)
   - CSRF protection with custom middleware
   - Password hashing with bcrypt
   - Email verification with OTP

5. **API Structure** (app/routers/):
   - auth/: Authentication endpoints (login, register, password reset)
   - users/: User management
   - courses/: Course CRUD and management
   - enrollments/: Student enrollment handling
   - payments/: Payment processing
   - attendance/: Attendance tracking
   - audit/: Audit log access

6. **Business Logic** (app/core/operations/):
   - Centralized business logic separated from routes
   - Operations for each domain entity
   - Database transaction handling

7. **Data Validation** (app/schemas/):
   - Pydantic models for request/response validation
   - Organized by domain (auth/, courses/, users/, etc.)

### Key Design Patterns

1. **Dependency Injection**: Database sessions, current user, and other dependencies injected via FastAPI's DI system

2. **Repository Pattern**: Operations files act as repositories, abstracting database operations from routes

3. **Middleware Pipeline**: 
   - CORS for cross-origin requests
   - TrustedHost for security
   - Custom audit middleware for API call logging

4. **Role-Based Permissions**: Decorators in app/core/decorators/auth.py enforce role requirements

### Database Schema

The application uses PostgreSQL with these main entities:
- Users (with roles: student, instructor, staff, admin)
- Courses (with status: draft, published, archived)
- Enrollments (linking users to courses)
- Payments
- Attendance records
- Audit logs

### Environment Configuration

The app uses a three-tier configuration system:
1. YAML files in cfg/ directory (base.yaml + environment-specific)
2. .env file for sensitive data
3. Environment variables (highest priority)

Key configuration areas:
- Database connection (supports component-based or URL)
- Redis connection
- JWT settings
- Email (SendGrid)
- CORS origins
- Security settings