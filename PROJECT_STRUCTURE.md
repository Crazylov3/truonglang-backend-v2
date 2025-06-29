# Learnify LMS - Organized Project Structure

## 📁 Project Overview

The Learnify LMS API has been reorganized into a scalable, domain-driven architecture with proper separation of concerns. This structure follows modern Python/FastAPI best practices and is designed for maintainability and scalability.

## 🏗️ Architecture Pattern

The project implements a **Clean Architecture** approach with:
- **Repository Pattern** for data access
- **Service Layer** for business logic
- **Domain-Driven Design** for organization
- **Dependency Injection** for loose coupling
- **Configuration Management** with YAML + Environment Variables

## 📂 Directory Structure

```
app/
├── __init__.py
├── main.py                    # FastAPI application entry point
├── config.py                  # Configuration management (backward compatible)
├── cfg_manager.py             # New configuration management system
├── database.py                # Database connection setup
│
├── core/                      # Core functionality
│   ├── __init__.py
│   ├── deps.py               # Dependency injection
│   ├── email.py              # Email service
│   └── security.py           # Authentication & security
│
├── db/                       # Database management layer
│   ├── __init__.py
│   ├── repositories/         # Data access layer
│   │   └── __init__.py      # Base & domain repositories
│   ├── services/            # Business logic layer
│   │   └── __init__.py      # Domain services
│   ├── utils/               # Database utilities
│   │   └── __init__.py      # Session management, health checks
│   └── migrations/          # Database migrations (future)
│
├── models/                   # SQLAlchemy models
│   ├── __init__.py
│   ├── user.py              # User model
│   ├── course.py            # Course model
│   └── enrollment.py        # Enrollment model
│
├── routers/                  # API routes (domain-organized)
│   ├── __init__.py
│   ├── auth/                # Authentication endpoints
│   │   └── __init__.py
│   ├── users/               # User management endpoints
│   │   └── __init__.py
│   ├── courses/             # Course management endpoints
│   │   └── __init__.py
│   └── enrollments/         # Enrollment endpoints
│       └── __init__.py
│
└── schemas/                  # Pydantic schemas (domain-organized)
    ├── __init__.py
    ├── common/              # Shared schemas
    │   └── __init__.py      # PaginatedResponse, MessageResponse, etc.
    ├── auth/                # Authentication schemas
    │   └── __init__.py
    ├── users/               # User schemas
    │   └── __init__.py
    ├── courses/             # Course schemas
    │   └── __init__.py
    └── enrollments/         # Enrollment schemas
        └── __init__.py

cfg/                          # Configuration management (NEW)
├── base.yaml                 # Base configuration (non-sensitive)
├── development.yaml          # Development environment overrides
├── production.yaml           # Production environment overrides
└── testing.yaml             # Testing environment overrides

# Configuration files
env.template                  # Environment template (sensitive data only)
env.prod.template            # Production environment template
demo_config.py               # Configuration system demonstration
CONFIG.md                    # Configuration system documentation

# Project files
pyproject.toml               # Project dependencies (includes PyYAML)
README.md                    # Main project documentation
PROJECT_STRUCTURE.md         # This file
DOCKER.md                    # Docker setup documentation
```

## 🔧 Key Components

### 1. **Configuration Management System (NEW)**

#### YAML Configuration (`cfg/`)
- **`base.yaml`**: Common settings (ports, timeouts, limits, features)
- **`development.yaml`**: Dev overrides (debug mode, local hosts, relaxed limits)
- **`production.yaml`**: Production settings (security, performance, monitoring)
- **`testing.yaml`**: Test-specific config (test DB, shorter timeouts)

#### Configuration Manager (`app/cfg_manager.py`)
- **ConfigDict**: Enables `Cfg.database.host` dot notation access
- **NullConfigDict**: Safe chaining that returns None for missing keys
- **ConfigManager**: Loads, merges YAML + environment variables
- **Environment-specific loading**: Based on `ENVIRONMENT` variable

#### Environment Variables (Sensitive Data)
- **Database credentials**: `DB_HOST`, `DB_PASSWORD`, `DB_USER`
- **API keys**: `SENDGRID_API_KEY`, external service keys
- **Secret keys**: `SECRET_KEY`, `CSRF_SECRET_KEY`
- **SSL certificates**: Paths and credentials

#### Usage Examples
```python
# New dot notation interface (recommended)
from app.config import Cfg
host = Cfg.database.host
debug = Cfg.app.debug
max_attempts = Cfg.security.max_login_attempts

# Safe chaining (returns None for missing keys)
optional_feature = Cfg.feature.that.might.not.exist

# Legacy interface (backward compatibility)
from app.config import settings
database_url = settings.database_url
```

### 2. **Database Layer (`app/db/`)**

#### Repositories (`app/db/repositories/`)
- `BaseRepository`: Generic CRUD operations
- `UserRepository`: User-specific database operations
- `CourseRepository`: Course-specific database operations
- `EnrollmentRepository`: Enrollment-specific database operations

#### Services (`app/db/services/`)
- `AuthService`: Authentication & authorization logic
- `UserService`: User management business logic
- `CourseService`: Course management business logic
- `EnrollmentService`: Enrollment business logic

#### Utils (`app/db/utils/`)
- `DatabaseManager`: Session & transaction management
- `ServiceFactory`: Service instance creation
- `RepositoryFactory`: Repository instance creation
- Health check utilities

### 3. **API Layer (`app/routers/`)**

Each domain has its own router module:
- **Auth Router**: Registration, login, password reset
- **Users Router**: Profile management, admin operations
- **Courses Router**: Course CRUD, enrollment
- **Enrollments Router**: Student course management

### 4. **Schema Layer (`app/schemas/`)**

Domain-organized Pydantic models:
- **Common Schemas**: Shared response models
- **Auth Schemas**: Authentication requests/responses
- **User Schemas**: User data models
- **Course Schemas**: Course data models
- **Enrollment Schemas**: Enrollment data models

### 5. **Core Layer (`app/core/`)**

Cross-cutting concerns:
- **Security**: JWT, password hashing, auth dependencies
- **Email**: SendGrid integration, OTP generation
- **Dependencies**: Role-based access control

## 🚀 Benefits of This Structure

### 1. **Scalability**
- Easy to add new domains (payments, notifications, etc.)
- Clear separation of concerns
- Modular architecture
- **Environment-specific configurations**

### 2. **Maintainability**
- Domain-driven organization
- Single responsibility principle
- Easy to locate and modify code
- **Clear separation of sensitive/non-sensitive config**

### 3. **Testability**
- Dependency injection supports mocking
- Service layer isolates business logic
- Repository pattern abstracts data access
- **Test-specific configuration overrides**

### 4. **Developer Experience**
- Clear folder structure
- Consistent naming conventions
- Self-documenting code organization
- **Safe configuration access with dot notation**

### 5. **Security**
- **Sensitive data in environment variables only**
- **Non-sensitive config version controlled**
- **Environment-specific security policies**

## 🔄 Data Flow

```
Request → Router → Service → Repository → Database
         ↓
    Response ← Schema ← Service ← Repository ← Database

Configuration Flow:
YAML Files + Environment Variables → ConfigManager → Cfg.section.key
```

1. **Router** receives HTTP request
2. **Service** handles business logic
3. **Repository** manages data access
4. **Schema** validates and serializes data
5. **Configuration** provides settings via `Cfg` object

## 📋 Configuration Architecture

### Non-Sensitive Data (YAML Files)
```yaml
# cfg/base.yaml
database:
  driver: "postgresql+asyncpg"
  port: 5432
  pool_size: 20

security:
  max_login_attempts: 5
  otp_expire_minutes: 10

file_upload:
  max_size_mb: 10
  allowed_types: ["jpg", "jpeg", "png", "pdf"]
```

### Sensitive Data (Environment Variables)
```bash
# .env file
DB_HOST=localhost
DB_PASSWORD=secure-password
SECRET_KEY=super-secret-jwt-key
SENDGRID_API_KEY=api-key-here
```

### Environment-Specific Overrides
```yaml
# cfg/production.yaml
app:
  debug: false
  
database:
  pool_size: 50  # Higher for production
  
security:
  max_login_attempts: 3  # Stricter in production
```

## 📋 Usage Examples

### Adding a New Domain (e.g., Payments)

1. Create `app/models/payment.py`
2. Create `app/schemas/payments/__init__.py`
3. Create `app/routers/payments/__init__.py`
4. Add `PaymentRepository` to `app/db/repositories/`
5. Add `PaymentService` to `app/db/services/`
6. Add payment config to `cfg/base.yaml`
7. Register router in `app/main.py`

### Database Operations

```python
# Using Repository Pattern
from app.db.repositories import UserRepository

async def get_user_by_email(db: AsyncSession, email: str):
    user_repo = UserRepository(db)
    return await user_repo.get_by_email(email)

# Using Service Layer
from app.db.services import UserService

async def get_user_profile(db: AsyncSession, user_id: int):
    user_service = UserService(db)
    return await user_service.get_user_profile(user_id)
```

### Configuration Usage

```python
# Access configuration
from app.config import Cfg

# Database connection
pool_size = Cfg.database.pool_size
timeout = Cfg.database.socket_timeout

# Security settings
max_attempts = Cfg.security.max_login_attempts
otp_expires = Cfg.security.otp_expire_minutes

# File upload limits
max_size = Cfg.file_upload.max_size_mb
allowed_types = Cfg.file_upload.allowed_types
```

## 🔧 Environment Setup

### 1. Copy Configuration Template
```bash
cp env.template .env
```

### 2. Set Environment
```bash
export ENVIRONMENT=development  # or production, testing
```

### 3. Configure Sensitive Data
```bash
# Edit .env with your sensitive data
DB_PASSWORD=your-secure-password
SECRET_KEY=your-jwt-secret
SENDGRID_API_KEY=your-api-key
```

## 📊 Health Monitoring

Built-in health checks:
- `/health` - Basic health status
- `/health/detailed` - Component-level health
- Database connectivity
- Redis connectivity
- **Configuration validation**

## 🧪 Testing

### Configuration Testing
```bash
# Test configuration system
python demo_config.py

# Test different environments
ENVIRONMENT=production python demo_config.py
ENVIRONMENT=testing python demo_config.py
```

### Application Testing
```bash
# Run tests with test configuration
ENVIRONMENT=testing pytest
```

## 📚 Documentation

- **`CONFIG.md`**: Comprehensive configuration system documentation
- **`PROJECT_STRUCTURE.md`**: This file - project architecture
- **`DOCKER.md`**: Docker setup and deployment
- **`README.md`**: Main project documentation

## 🎯 Next Steps

1. **Add Database Migrations** using Alembic
2. **Implement Caching** with Redis decorators
3. **Add API Testing** with pytest
4. **Add Background Tasks** with Celery
5. **Add API Documentation** with custom OpenAPI
6. **Environment-specific Docker configs**
7. **Configuration validation and type checking**

## 🔗 File Dependencies

```
Configuration System:
cfg/*.yaml → app/cfg_manager.py → app/config.py → Application

Database Layer:
app/models/ → app/db/repositories/ → app/db/services/ → app/routers/

Schema Layer:
app/schemas/ ↔ app/routers/ ↔ app/db/services/
```

This organized structure provides a solid foundation for scaling the Learnify LMS platform while maintaining code quality, security, and developer productivity. The new configuration management system ensures secure, maintainable, and environment-specific configuration handling. 