# 🐳 Learnify LMS Docker Setup

This document explains how to run the Learnify LMS application using Docker for both development and production environments.

## 📋 Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (v20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2.0+)

## 🚀 Quick Start

### 1. Clone Repository and Setup Environment

```bash
git clone <repository-url>
cd learnify-lms

# Copy and configure environment file
cp env.template .env
# Edit .env with your settings
```

### 2. Start Development Environment

```bash
# Make scripts executable
chmod +x scripts/dev.sh

# Initialize project (creates directories and environment)
./scripts/dev.sh init

# Start all services with development tools
./scripts/dev.sh start
```

### 3. Access Services

- **FastAPI Application**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **pgAdmin (PostgreSQL UI)**: http://localhost:8080
  - Email: `admin@learnify.com`
  - Password: `admin_password`
- **Redis Commander**: http://localhost:8081

## 📁 File Structure

```
├── Dockerfile                    # Main application Dockerfile
├── docker-compose.yml           # Development environment
├── docker-compose.prod.yml      # Production environment
├── .dockerignore               # Files to exclude from Docker build
├── env.prod.template           # Production environment template
├── scripts/
│   └── dev.sh                  # Development helper script
└── docker/
    ├── postgres/
    │   ├── postgresql.conf     # PostgreSQL configuration
    │   └── pg_hba.conf        # PostgreSQL authentication config
    └── redis/
        └── redis.conf          # Redis configuration
```

## 🛠️ Development Commands

The `scripts/dev.sh` script provides convenient commands for development:

| Command | Description |
|---------|-------------|
| `start` | Start all services |
| `start-dev` | Start all services with development tools |
| `stop` | Stop all services |
| `restart` | Restart all services |
| `logs [service]` | Show logs (optionally for specific service) |
| `migrate` | Run database migrations |
| `makemigration 'message'` | Create new migration |
| `test` | Run tests |
| `shell` | Enter app container shell |
| `status` | Show service status |
| `cleanup` | Remove all containers and volumes |
| `help` | Show help message |

### Examples:

```bash
# Start development environment
./scripts/dev.sh start

# View logs for the app service
./scripts/dev.sh logs app

# Run database migrations
./scripts/dev.sh migrate

# Create a new migration
./scripts/dev.sh makemigration "Add user profile fields"

# Run tests
./scripts/dev.sh test

# Enter the app container shell
./scripts/dev.sh shell

# Clean up everything
./scripts/dev.sh cleanup
```

## 🔧 Service Configuration

### FastAPI Application
- **Port**: 8000
- **Health Check**: http://localhost:8000/health
- **API Documentation**: http://localhost:8000/docs

### PostgreSQL Database
- **Port**: 5432
- **Database**: learnify_db
- **Username**: learnify
- **Password**: learnify_password (development)

### Redis Cache
- **Port**: 6379
- **Configuration**: `docker/redis/redis.conf`

### Development Tools (with `--profile dev`)
- **pgAdmin**: http://localhost:8080
- **Redis Commander**: http://localhost:8081

## 🔐 Security Considerations

### Development
- Uses default passwords (acceptable for local development)
- Exposes database ports for debugging
- Includes development tools

### Production
- **MUST** change all default passwords
- Database ports are not exposed externally
- No development tools included
- Uses environment variables for sensitive data

## 🔍 Debugging

### View Container Logs
```bash
# All services
./scripts/dev.sh logs

# Specific service
./scripts/dev.sh logs app
./scripts/dev.sh logs db
./scripts/dev.sh logs redis
```

### Enter Container Shell
```bash
# Enter app container
./scripts/dev.sh shell

# Enter database container
docker compose exec db bash

# Enter Redis container
docker compose exec redis sh
```

### Check Service Status
```bash
./scripts/dev.sh status
```

## 🗄️ Database Management

### Run Migrations
```bash
./scripts/dev.sh migrate
```

### Create New Migration
```bash
./scripts/dev.sh makemigration "Your migration description"
```

### Access Database Directly
```bash
# Via pgAdmin (with dev tools)
# http://localhost:8080

# Via command line
docker compose exec db psql -U learnify -d learnify_db
```

## 📊 Monitoring

### Health Checks
All services include health checks:
- **App**: Checks `/health` endpoint
- **PostgreSQL**: Checks database connectivity with pg_isready
- **Redis**: Checks Redis ping

### View Health Status
```bash
docker compose ps
```

## 🔄 Data Persistence

Data is persisted using Docker volumes:
- **postgres_data**: PostgreSQL database files
- **redis_data**: Redis persistence files

### Backup Data
```bash
# Backup PostgreSQL
docker compose exec db pg_dump -U learnify learnify_db > backup.sql

# Backup Redis
docker compose exec redis redis-cli BGSAVE
```

## 🚀 Production Deployment

1. **Prepare environment:**
   ```bash
   cp env.prod.template .env.prod
   # Edit .env.prod with production values
   ```

2. **Important production settings:**
   - Set strong `SECRET_KEY`
   - Use secure database passwords
   - Configure proper CORS origins
   - Set DEBUG=false
   - Configure SendGrid API key
   - Set up SSL certificates (if using Nginx)

3. **Deploy:**
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
   ```

4. **Run initial migrations:**
   ```bash
   docker compose -f docker-compose.prod.yml exec app uv run alembic upgrade head
   ```

## 🔧 Troubleshooting

### Common Issues

1. **Port already in use:**
   ```bash
   # Stop conflicting services
   sudo systemctl stop postgresql
   sudo systemctl stop redis
   ```

2. **Permission issues:**
   ```bash
   # Fix script permissions
   chmod +x scripts/dev.sh
   ```

3. **Database connection issues:**
   ```bash
   # Check if database is ready
   ./scripts/dev.sh logs db
   ```

4. **Clean start:**
   ```bash
   # Remove everything and start fresh
   ./scripts/dev.sh cleanup
   ./scripts/dev.sh start
   ```

### Getting Help

1. Check service logs: `./scripts/dev.sh logs`
2. Check service status: `./scripts/dev.sh status`
3. Enter container shell: `./scripts/dev.sh shell`
4. Review this documentation
5. Check the main application logs in the `logs/` directory

## 📝 Notes

- The development environment mounts your source code as a volume, so changes are reflected immediately
- For production, remove the volume mount in `docker-compose.prod.yml`
- Database and Redis data are persisted in Docker volumes
- Always use environment variables for sensitive data in production
- pgAdmin default credentials: admin@learnify.com / admin_password (development only)

## Configuration

### Database Configuration

You can configure the database using individual components (recommended) or a direct URL:

#### Individual Components (Recommended)
```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=learnify
DB_PASSWORD=your-secure-password
DB_NAME=learnify_db
DB_DRIVER=postgresql+asyncpg
```

#### Direct URL (Legacy Support)
```env
DATABASE_URL=postgresql+asyncpg://learnify:your-secure-password@localhost:5432/learnify_db
```

### Redis Configuration

Similar to database, Redis can be configured with components or direct URL:

#### Individual Components (Recommended)
```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your-redis-password  # Optional
```

#### Direct URL (Legacy Support)
```env
REDIS_URL=redis://localhost:6379/0
# Or with password: redis://:password@localhost:6379/0
```

### Docker Environment Variables

The Docker services automatically use the following mappings:

**Development (docker-compose.yml):**
- `DB_HOST=db` (PostgreSQL container)
- `REDIS_HOST=redis` (Redis container)

**Production (docker-compose.prod.yml):**
- Uses `.env.prod` file
- Overrides host names for container networking

## Development Environment

### Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   PostgreSQL    │
│   (Port 8000)   │────│   (Port 5432)   │
└─────────────────┘    └─────────────────┘
         │                        │
         │              ┌─────────────────┐
         └──────────────│      Redis      │
                        │   (Port 6379)   │
                        └─────────────────┘
```

### Services

1. **app**: FastAPI application container
2. **db**: PostgreSQL 15 database
3. **redis**: Redis 7 cache
4. **pgadmin**: PostgreSQL web interface (dev profile)
5. **redis-commander**: Redis web interface (dev profile)

### Development Scripts

The `scripts/dev.sh` script provides convenient commands:

```bash
# Start services
./scripts/dev.sh start

# View logs
./scripts/dev.sh logs
./scripts/dev.sh logs app

# Access containers
./scripts/dev.sh shell        # App container
./scripts/dev.sh db-shell     # PostgreSQL shell
./scripts/dev.sh redis-shell  # Redis CLI

# Database operations
./scripts/dev.sh backup-db     # Create backup
./scripts/dev.sh restore-db backup.sql
./scripts/dev.sh reset-db      # WARNING: Destroys data

# Service management
./scripts/dev.sh stop
./scripts/dev.sh restart
./scripts/dev.sh status

# Cleanup
./scripts/dev.sh clean
```

### Environment Files

**Development (.env)**:
```env
# Database - Individual Components
DB_HOST=localhost
DB_PORT=5432
DB_USER=learnify
DB_PASSWORD=password
DB_NAME=learnify_db

# Redis - Individual Components  
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Application
DEBUG=true
SECRET_KEY=dev-secret-key
SENDGRID_API_KEY=your-dev-key
```

## Production Environment

### Architecture

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Nginx    │    │   FastAPI App   │    │   PostgreSQL    │
│  (80/443)   │────│   (Port 8000)   │────│   (Port 5432)   │
└─────────────┘    └─────────────────┘    └─────────────────┘
                            │                        │
                            │              ┌─────────────────┐
                            └──────────────│      Redis      │
                                          │   (Port 6379)   │
                                          └─────────────────┘
```

### Production Setup

1. **Copy and configure production environment**:
```bash
cp env.prod.template .env.prod
# Edit .env.prod with production values
```

2. **Configure security settings**:
```env
# Strong secret keys
SECRET_KEY=your-super-secure-secret-key-at-least-32-chars
CSRF_SECRET_KEY=your-csrf-secret-key

# Database credentials
DB_USER=learnify
DB_PASSWORD=very-secure-production-password
DB_NAME=learnify_db

# Redis with password
REDIS_PASSWORD=secure-redis-password

# Email configuration
SENDGRID_API_KEY=your-production-sendgrid-key
FROM_EMAIL=noreply@yourdomain.com

# CORS for your domain
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

3. **Create production data directories**:
```bash
sudo mkdir -p /var/lib/learnify/{postgres,redis}
sudo chown -R 1000:1000 /var/lib/learnify
```

4. **Start production services**:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Production Features

- **SSL/TLS**: Nginx handles HTTPS termination
- **Security**: Non-root containers, read-only filesystems
- **Performance**: Resource limits and health checks
- **Monitoring**: Comprehensive logging and metrics
- **Backups**: Persistent volumes with backup capabilities

### SSL Certificate Setup

Place your SSL certificates in `docker/nginx/ssl/`:
```bash
docker/nginx/ssl/
├── cert.pem      # SSL certificate
└── private.key   # Private key
```

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| **Database** | | |
| `DB_HOST` | `localhost` | Database host |
| `DB_PORT` | `5432` | Database port |
| `DB_USER` | `learnify` | Database username |
| `DB_PASSWORD` | `password` | Database password |
| `DB_NAME` | `learnify_db` | Database name |
| `DB_DRIVER` | `postgresql+asyncpg` | SQLAlchemy driver |
| **Redis** | | |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_DB` | `0` | Redis database number |
| `REDIS_PASSWORD` | | Redis password (optional) |
| **Application** | | |
| `SECRET_KEY` | | JWT secret key |
| `DEBUG` | `true` | Debug mode |
| `CORS_ORIGINS` | | Allowed CORS origins |
| **Email** | | |
| `SENDGRID_API_KEY` | | SendGrid API key |
| `FROM_EMAIL` | `noreply@learnify.com` | From email address |

### Docker Compose Profiles

- **Default**: Core services (app, db, redis)
- **dev**: Includes pgAdmin and Redis Commander
- **nginx**: Includes Nginx reverse proxy

```bash
# Start with development tools
docker-compose --profile dev up -d

# Start with Nginx
docker-compose --profile nginx up -d
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check database container
   docker-compose logs db
   
   # Test connection
   ./scripts/dev.sh db-shell
   ```

2. **Redis Connection Failed**
   ```bash
   # Check Redis container
   docker-compose logs redis
   
   # Test connection
   ./scripts/dev.sh redis-shell
   ```

3. **Port Already in Use**
   ```bash
   # Check what's using the port
   sudo lsof -i :8000
   
   # Stop conflicting services
   sudo systemctl stop postgresql
   sudo systemctl stop redis-server
   ```

4. **Permission Issues**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   chmod +x scripts/dev.sh
   ```

### Health Checks

Check service health:
```bash
# Application health
curl http://localhost:8000/health

# Detailed health check
curl http://localhost:8000/health/detailed

# Docker service status
docker-compose ps
```

### Logs

View logs for debugging:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f app
docker-compose logs -f db
docker-compose logs -f redis

# With timestamps
docker-compose logs -f -t app
```

## Backup and Recovery

### Database Backups

```bash
# Create backup
./scripts/dev.sh backup-db

# Restore from backup
./scripts/dev.sh restore-db backups/backup_file.sql

# Reset database (WARNING: destroys all data)
./scripts/dev.sh reset-db
```

### Manual Backup

```bash
# Backup database
docker-compose exec -T db pg_dump -U learnify -d learnify_db > backup.sql

# Restore database
docker-compose exec -T db psql -U learnify -d learnify_db < backup.sql
```

## Monitoring

### Metrics and Logs

- Application logs: `./logs/`
- Nginx logs: `./logs/nginx/` (production)
- Database logs: Available via `docker-compose logs db`

### Health Endpoints

- `/health` - Basic health check
- `/health/detailed` - Detailed component status

## Security Considerations

### Production Security

1. **Change Default Passwords**: Update all default passwords
2. **Use Strong Secret Keys**: Generate secure JWT and CSRF keys
3. **Enable HTTPS**: Configure SSL certificates in Nginx
4. **Network Security**: Use Docker networks and firewalls
5. **Regular Updates**: Keep Docker images updated
6. **Backup Encryption**: Encrypt database backups
7. **Log Monitoring**: Monitor logs for suspicious activity

### Environment Security

```bash
# Secure environment files
chmod 600 .env .env.prod

# Use Docker secrets for sensitive data (advanced)
echo "my-secret-password" | docker secret create db_password -
``` 