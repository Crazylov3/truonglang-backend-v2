# Configuration Management System

The Learnify LMS uses a flexible configuration management system that separates sensitive and non-sensitive configuration data, provides environment-specific overrides, and supports safe dot notation access.

## 🏗️ Architecture

```
┌─────────────────────┐    ┌─────────────────────┐
│   YAML Files        │    │   Environment       │
│   (Non-sensitive)   │    │   Variables         │
│                     │    │   (Sensitive)       │
│   • cfg/base.yaml   │    │   • DB_PASSWORD     │
│   • cfg/dev.yaml    │────│   • SECRET_KEY      │
│   • cfg/prod.yaml   │    │   • API_KEYS        │
│   • cfg/test.yaml   │    │   • etc.            │
└─────────────────────┘    └─────────────────────┘
           │                          │
           └────────────┬─────────────┘
                        ▼
              ┌─────────────────────┐
              │  ConfigManager      │
              │  Merges & Provides  │
              │  Cfg.section.key    │
              └─────────────────────┘
```

## 📁 File Structure

```
project/
├── cfg/                     # Configuration directory
│   ├── base.yaml           # Base configuration (non-sensitive)
│   ├── development.yaml    # Development overrides
│   ├── production.yaml     # Production overrides
│   └── testing.yaml        # Testing overrides
├── .env                    # Sensitive data (local)
├── env.template           # Template for .env
└── app/
    ├── cfg_manager.py     # Configuration management class
    └── config.py          # Backward compatibility wrapper
```

## 🚀 Quick Start

### 1. Basic Usage

```python
from app.config import Cfg, settings

# New dot notation interface (recommended)
database_host = Cfg.database.host
app_name = Cfg.app.name
jwt_algorithm = Cfg.jwt.algorithm

# Legacy interface (backward compatibility)
database_url = settings.database_url
debug_mode = settings.debug
```

### 2. Safe Attribute Access

```python
# Returns None instead of raising errors
missing_value = Cfg.nonexistent.deep.nested.key  # Returns None
if Cfg.optional.feature.enabled:  # Safe boolean check
    print("Feature enabled")
```

### 3. Environment Variable Overrides

```bash
# Set sensitive data via environment variables
export DB_PASSWORD="secure-password"
export SECRET_KEY="super-secret-key"
export ENVIRONMENT="production"
```

## 📋 Configuration Categories

### Non-Sensitive (YAML Files)

Stored in `cfg/*.yaml` files and version controlled:

- **Application settings** (name, version, debug mode)
- **Database configuration** (driver, port, pool settings)
- **Redis settings** (port, timeouts, connection limits)
- **Security policies** (password rules, rate limits)
- **File upload limits** and allowed types
- **Pagination settings**
- **CORS configuration**
- **Logging configuration**

### Sensitive (Environment Variables)

Stored in `.env` files (not version controlled):

- **Database credentials** (password, username)
- **API keys** (SendGrid, external services)
- **Secret keys** (JWT, CSRF tokens)
- **SSL certificates** and private keys
- **Production hostnames** and URLs

## ⚙️ Environment-Specific Configuration

### Development (`cfg/development.yaml`)

```yaml
app:
  debug: true

database:
  host: "localhost"
  echo: true  # SQL logging enabled

rate_limiting:
  enabled: false  # Disabled for development
```

### Production (`cfg/production.yaml`)

```yaml
app:
  debug: false

database:
  host: "db"  # Docker service name
  pool_size: 50

rate_limiting:
  enabled: true
  requests_per_minute: 30  # More restrictive
```

### Testing (`cfg/testing.yaml`)

```yaml
database:
  name: "learnify_test_db"
  echo: false

redis:
  db: 1  # Separate Redis database

jwt:
  access_token_expire_minutes: 5  # Shorter for tests
```

## 🔧 Usage Examples

### Basic Configuration Access

```python
from app.config import Cfg

# Application settings
print(f"App: {Cfg.app.name} v{Cfg.app.version}")
print(f"Debug mode: {Cfg.app.debug}")

# Database configuration
print(f"Database: {Cfg.database.driver}://{Cfg.database.host}:{Cfg.database.port}")
print(f"Pool size: {Cfg.database.pool_size}")

# Security settings
print(f"Max login attempts: {Cfg.security.max_login_attempts}")
print(f"OTP expires in: {Cfg.security.otp_expire_minutes} minutes")
```

### Environment Variable Mapping

```python
# Environment variables automatically override YAML values
# DB_HOST=custom.host.com -> Cfg.database.host
# SECRET_KEY=my-secret -> Cfg.jwt.secret_key
# SENDGRID_API_KEY=key -> Cfg.email.sendgrid_api_key
```

### Backward Compatibility

```python
from app.config import settings

# Old interface still works
database_url = settings.database_url
redis_url = settings.redis_url
debug = settings.debug
app_name = settings.app_name
```

### Advanced Usage

```python
from app.cfg_manager import get_config_manager

# Get configuration manager instance
manager = get_config_manager()

# Access using paths
value = manager.get('database.host', default='localhost')

# Set values programmatically
manager.set('custom.setting', 'value')

# Reload configuration
manager.reload()

# Export entire config
config_dict = manager.dump()
```

## 🌍 Environment Setup

### 1. Copy Environment Template

```bash
cp env.template .env
```

### 2. Configure Sensitive Data

```bash
# .env file
ENVIRONMENT=development
DB_PASSWORD=your-secure-password
SECRET_KEY=your-secret-key
SENDGRID_API_KEY=your-api-key
```

### 3. Set Environment

```bash
# Development
export ENVIRONMENT=development

# Production
export ENVIRONMENT=production

# Testing
export ENVIRONMENT=testing
```

## 🔍 Environment Variable Reference

| Variable | YAML Path | Description |
|----------|-----------|-------------|
| `ENVIRONMENT` | - | Environment to load (development/production/testing) |
| `DB_HOST` | `database.host` | Database hostname |
| `DB_USER` | `database.user` | Database username |
| `DB_PASSWORD` | `database.password` | Database password |
| `REDIS_HOST` | `redis.host` | Redis hostname |
| `REDIS_PASSWORD` | `redis.password` | Redis password |
| `SECRET_KEY` | `jwt.secret_key` | JWT secret key |
| `SENDGRID_API_KEY` | `email.sendgrid_api_key` | SendGrid API key |
| `FROM_EMAIL` | `email.from_email` | Default from email |
| `CSRF_SECRET_KEY` | `security.csrf_secret_key` | CSRF token secret |
| `CORS_ORIGINS` | `cors.origins` | Allowed CORS origins (comma-separated) |

## 🛡️ Security Best Practices

### 1. Environment Files

```bash
# Secure environment files
chmod 600 .env .env.prod

# Add to .gitignore
echo ".env*" >> .gitignore
```

### 2. Production Secrets

```bash
# Use strong, unique secrets in production
SECRET_KEY=$(openssl rand -hex 32)
CSRF_SECRET_KEY=$(openssl rand -hex 32)
DB_PASSWORD=$(openssl rand -base64 32)
```

### 3. Docker Secrets (Advanced)

```bash
# Use Docker secrets for sensitive data
echo "my-secret" | docker secret create db_password -
```

## 🧪 Testing Configuration

```python
# Test configuration loading
python demo_config.py

# Test specific environment
ENVIRONMENT=production python demo_config.py

# Test with custom variables
DB_HOST=custom.host SECRET_KEY=test-key python demo_config.py
```

## 🔄 Migration from Old System

### Before (Pydantic Settings)

```python
from app.config import settings

database_url = settings.DATABASE_URL
debug = settings.DEBUG
```

### After (New System)

```python
from app.config import Cfg, settings

# New way (recommended)
database_url = Cfg.database.url or f"{Cfg.database.driver}://{Cfg.database.user}:..."
debug = Cfg.app.debug

# Old way (still works)
database_url = settings.database_url
debug = settings.debug
```

## 🐛 Troubleshooting

### Configuration Not Loading

```bash
# Check environment file exists
ls -la .env

# Check YAML files exist
ls -la cfg/

# Check environment variable
echo $ENVIRONMENT
```

### Missing Configuration Values

```python
# Debug configuration
from app.cfg_manager import get_config_manager

manager = get_config_manager()
print(manager.dump())  # Print all loaded config
```

### Environment Variables Not Working

```python
# Check environment variable mapping
import os
print(f"DB_HOST env var: {os.getenv('DB_HOST')}")
print(f"Config value: {Cfg.database.host}")
```

## 📚 API Reference

### ConfigDict Class

- `Cfg.section.key` - Dot notation access
- `Cfg.get_nested('section.key', default)` - Get with default
- `Cfg.set_nested('section.key', value)` - Set value

### ConfigManager Class

- `manager.get(path, default)` - Get configuration value
- `manager.set(path, value)` - Set configuration value  
- `manager.reload()` - Reload from files
- `manager.dump()` - Export as dictionary

### Settings Class (Legacy)

- `settings.database_url` - Built database URL
- `settings.redis_url` - Built Redis URL
- All legacy properties maintained for compatibility 