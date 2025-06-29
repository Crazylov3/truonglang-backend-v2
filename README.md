# Giao Duc Thang Long API

A modern, secure, and scalable Learning Management System (LMS) built with FastAPI, implementing role-based access control, course management, and student enrollment features.

## Features

- **User Authentication & Authorization**
  - JWT-based authentication
  - Role-based access control (Student, Instructor, Staff, Admin)
  - Email verification with OTP
  - Password reset functionality

- **Course Management**
  - Create, read, update, delete courses
  - Course status management (Draft, Published, Archived)
  - Instructor-specific course management

- **Student Enrollment**
  - Course enrollment/unenrollment
  - Student progress tracking
  - Enrollment management

- **Security & Performance**
  - Password hashing with bcrypt
  - Redis caching for session management
  - Async database operations
  - Input validation with Pydantic

## Technology Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL with SQLAlchemy (async)
- **Cache**: Redis
- **Email**: SendGrid
- **Package Manager**: UV
- **Authentication**: JWT tokens
- **Validation**: Pydantic

## Installation & Setup

### Prerequisites

- Python 3.11+
- UV package manager
- PostgreSQL 15+
- Redis 6.0+

### 1. Clone the Repository

```bash
git clone <repository-url>
cd learnify-lms
```

### 2. Install Dependencies with UV

```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

### 3. Environment Configuration

Copy the environment template and configure your settings:

```bash
cp env.template .env
```

Edit `.env` with your configuration:

```env
# Database Configuration - Individual Components (Recommended)
DB_HOST=localhost
DB_PORT=5432
DB_USER=learnify
DB_PASSWORD=your-secure-password
DB_NAME=learnify_db
DB_DRIVER=postgresql+asyncpg

# Alternative: Direct Database URL (Optional - overrides above components)
# DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/learnify_db

# Redis Configuration - Individual Components (Recommended)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
# REDIS_PASSWORD=your-redis-password-if-needed

# Alternative: Direct Redis URL (Optional - overrides above components)
# REDIS_URL=redis://localhost:6379/0

# JWT Configuration
SECRET_KEY=your-super-secret-key-here-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Email Configuration (SendGrid)
SENDGRID_API_KEY=your-sendgrid-api-key-here
FROM_EMAIL=noreply@learnify.com

# Application Configuration
DEBUG=True
```

### 4. Database Setup

You can configure the database in two ways:

#### Option 1: Individual Components (Recommended)
Configure each database component separately in your `.env` file:

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=learnify
DB_PASSWORD=your-secure-password
DB_NAME=learnify_db
DB_DRIVER=postgresql+asyncpg
```

#### Option 2: Direct URL (Legacy Support)
Use a complete database URL:

```env
DATABASE_URL=postgresql+asyncpg://learnify:your-secure-password@localhost:5432/learnify_db
```

Create your PostgreSQL database:

```sql
CREATE DATABASE learnify_db WITH ENCODING 'UTF8' LC_COLLATE='en_US.UTF-8' LC_CTYPE='en_US.UTF-8';
```

For PostgreSQL user setup:
```sql
CREATE USER learnify WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE learnify_db TO learnify;
```

### 5. Run the Application

```bash
# Development mode
uv run python -m app.main

# Or using uvicorn directly
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- Main API: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Authentication (`/api/v1/auth`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/register` | Register new user | No |
| POST | `/verify-email` | Verify email with OTP | No |
| POST | `/login` | User login | No |
| POST | `/logout` | User logout | Yes |
| POST | `/forgot-password` | Request password reset | No |
| POST | `/reset-password` | Reset password with token | No |
| POST | `/change-password` | Change current password | Yes |

### Users (`/api/v1/users`)

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/me` | Get current user profile | All |
| PUT | `/me` | Update current user profile | All |
| GET | `/` | Get all users | Staff, Admin |
| GET | `/{user_id}` | Get user by ID | Staff, Admin |
| PUT | `/{user_id}` | Update user | Staff, Admin |
| PUT | `/{user_id}/role` | Update user role | Admin |
| DELETE | `/{user_id}` | Delete user | Staff, Admin |
| POST | `/` | Create user | Admin |

### Courses (`/api/v1/courses`)

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/` | Get courses (paginated) | All |
| GET | `/{course_id}` | Get course details | All |
| POST | `/` | Create course | Instructor, Staff, Admin |
| PUT | `/{course_id}` | Update course | Owner, Staff, Admin |
| DELETE | `/{course_id}` | Delete course | Staff, Admin |
| POST | `/{course_id}/enroll` | Enroll in course | Student |
| DELETE | `/{course_id}/enroll` | Unenroll from course | Student |
| GET | `/{course_id}/students` | Get enrolled students | Owner, Staff, Admin |

### Enrollments (`/api/v1/enrollments`)

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/my-courses` | Get enrolled courses | Student |
| GET | `/` | Get all enrollments | Staff, Admin |
| DELETE | `/{enrollment_id}` | Delete enrollment | Owner, Staff, Admin |

## Usage Examples

### 1. User Registration & Login

```bash
# Register a new user
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@example.com",
    "password": "securepassword123",
    "first_name": "John",
    "last_name": "Doe"
  }'

# Verify email (check your email for OTP)
curl -X POST "http://localhost:8000/api/v1/auth/verify-email" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@example.com",
    "otp": "123456"
  }'

# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@example.com",
    "password": "securepassword123"
  }'
```

### 2. Course Management

```bash
# Create a course (as instructor/staff/admin)
curl -X POST "http://localhost:8000/api/v1/courses" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Introduction to Python",
    "description": "Learn Python programming from scratch",
    "status": "published"
  }'

# Get all courses
curl -X GET "http://localhost:8000/api/v1/courses?page=1&per_page=10"

# Enroll in a course (as student)
curl -X POST "http://localhost:8000/api/v1/courses/1/enroll" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Role-Based Permissions

### Student
- View published courses
- Enroll/unenroll in courses
- View their enrolled courses
- Manage their own profile

### Instructor
- All student permissions
- Create and manage their own courses
- View students enrolled in their courses

### Staff
- All instructor permissions
- Manage any course
- Manage user profiles
- View all users and enrollments

### Admin
- All staff permissions
- Manage user roles
- Create users directly
- Full system access

## Development

### Running Tests

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest
```

### Code Formatting

```bash
# Format code
uv run black app/
uv run isort app/

# Lint code
uv run flake8 app/
```

### Database Migrations (Optional)

For production deployments, you can set up Alembic:

```bash
# Initialize Alembic
uv run alembic init alembic

# Generate migration
uv run alembic revision --autogenerate -m "Initial migration"

# Apply migration
uv run alembic upgrade head
```

## Production Deployment

### Environment Variables

Ensure you set secure values for production:

```env
SECRET_KEY=your-super-secure-secret-key
ALGORITHM=HS256
DEBUG=False
SENDGRID_API_KEY=your-production-sendgrid-key
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/learnify_db
REDIS_URL=redis://prod-redis:6379/0
```

### Docker Deployment (Optional)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install uv && uv sync --frozen

COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Security Considerations

- Always use HTTPS in production
- Set strong SECRET_KEY values
- Configure proper CORS origins
- Use environment variables for sensitive data
- Regularly update dependencies
- Monitor API usage and implement rate limiting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

This project is licensed under the MIT License. 