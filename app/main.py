from fastapi import FastAPI, Request, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
import logging
import time
import uuid
from contextlib import asynccontextmanager
from fastapi.security.api_key import APIKeyHeader
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html

from app.config import settings
from app.routers.auth.auth import router as auth_router
from app.routers.auth.login import router as login_router
from app.routers.auth.register import router as register_router
from app.routers.auth.password_reset import router as password_reset_router
from app.routers.users import users
from app.routers.courses import courses
from app.routers.enrollments import enrollments
from app.routers.payments import payments
from app.routers.attendance import attendance
from app.routers.audit import audit
from app.core.middleware.audit_middleware import AuditMiddleware
from app.core.middleware.security_headers import SecurityHeadersMiddleware
from app.core.middleware.request_validation import RequestValidationMiddleware
from app.core.middleware.rate_limit import RateLimitMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Silence SQLAlchemy's noisy query logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.dialects').setLevel(logging.WARNING)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async context manager for FastAPI lifespan events."""
    # Startup
    logger.info("Starting up Giao Duc Thang Long...")
    
    # Note: Database tables should be created using Alembic migrations
    # Run: alembic upgrade head
    logger.info("Note: Ensure database migrations are up to date with: alembic upgrade head")
    
    # Ensure media directories exist with proper permissions
    import os
    media_dirs = [
        settings.media_root,
        os.path.join(settings.media_root, "avatars"),
        os.path.join(settings.media_root, "documents"),
        os.path.join(settings.media_root, "course_materials")
    ]
    
    for directory in media_dirs:
        try:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Ensured directory exists: {directory}")
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Giao Duc Thang Long...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="A modern Learning Management System API built with FastAPI",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add security headers middleware (should be first)
app.add_middleware(
    SecurityHeadersMiddleware,
    enable_hsts=not settings.debug,  # Only enable HSTS in production
)

# Add request validation middleware
app.add_middleware(
    RequestValidationMiddleware,
    max_request_size=10 * 1024 * 1024,  # 10MB for general requests
    max_upload_size=50 * 1024 * 1024,   # 50MB for file uploads
)

# Add rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=60,
    requests_per_hour=1000,
    burst_size=10,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Accept", "Authorization", "Content-Type", "X-CSRF-Token", "X-Csrftoken"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts
)

# Add audit middleware for automatic API call logging
app.add_middleware(
    AuditMiddleware,
    exclude_paths=[
        "/docs", "/redoc", "/openapi.json", "/favicon.ico",
        "/health", "/metrics"
    ]
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with sanitized output."""
    # Sanitize error messages to avoid exposing sensitive data
    errors = []
    for error in exc.errors():
        # Remove any sensitive field values from error messages
        sanitized_error = {
            "type": error.get("type"),
            "loc": error.get("loc"),
            "msg": error.get("msg")
        }
        errors.append(sanitized_error)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": errors
        }
    )


@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError):
    """Handle database integrity errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": "Database integrity error",
            "message": str(exc)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with basic information."""
    return HTMLResponse(
        f"""
        <html>
            <head>
                <title>{settings.app_name}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    .container {{ max-width: 800px; margin: 0 auto; }}
                    .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
                    .content {{ margin-top: 20px; }}
                    .link {{ color: #007bff; text-decoration: none; }}
                    .link:hover {{ text-decoration: underline; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🚀 {settings.app_name}</h1>
                        <p>Version: {settings.version}</p>
                        <p>A modern Learning Management System API built with FastAPI</p>
                    </div>
                    <div class="content">
                        <h2>📚 Available Endpoints</h2>
                        <ul>
                            <li><a href="/docs" class="link">📖 Interactive API Documentation (Swagger UI)</a></li>
                            <li><a href="/redoc" class="link">📚 Alternative API Documentation (ReDoc)</a></li>
                            <li><a href="/openapi.json" class="link">🔧 OpenAPI Schema (JSON)</a></li>
                        </ul>
                        
                        <h2>🛠️ Development</h2>
                        <p>This API provides comprehensive endpoints for:</p>
                        <ul>
                            <li>👥 User Management & Authentication</li>
                            <li>📚 Course Management</li>
                            <li>🎓 Enrollment Management</li>
                            <li>💳 Payment Processing</li>
                            <li>📊 Attendance Tracking</li>
                            <li>📝 Audit Logging</li>
                        </ul>
                        
                        <h2>🚀 Getting Started</h2>
                        <p>Check out the <a href="/docs" class="link">API documentation</a> to explore all available endpoints and start building!</p>
                    </div>
                </div>
            </body>
        </html>
        """
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": settings.app_name,
        "version": settings.version
    }


@app.get("/metrics")
async def metrics():
    """Basic metrics endpoint."""
    return {
        "uptime": time.time(),
        "service": settings.app_name,
        "version": settings.version
    }


# Include routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(login_router, prefix="/api/v1")
app.include_router(register_router, prefix="/api/v1")
app.include_router(password_reset_router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(courses.router, prefix="/api/v1")
app.include_router(enrollments.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(attendance.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")

# Middleware for request logging and monitoring
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    start_time = time.time()
    
    # Generate request ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Log request
    logger.info(f"Request {request_id}: {request.method} {request.url.path}")
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log response
    logger.info(f"Request {request_id}: {response.status_code} - {process_time:.3f}s")
    
    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id
    
    return response

# Custom Swagger UI
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    swagger_html = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="LMS API - Swagger UI",
        swagger_favicon_url=None,
        swagger_ui_parameters={
            "requestInterceptor": """
                function(request) {
                    // Get CSRF token from cookie
                    var csrfCookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
                    if (csrfCookie) {
                        var csrfToken = csrfCookie.split('=')[1];
                        request.headers['X-Csrftoken'] = csrfToken;
                        console.log('✅ Added CSRF token to request:', csrfToken.substring(0, 8) + '...');
                    } else {
                        console.log('⚠️ No CSRF token found in cookies. Call /csrf-token first.');
                    }
                    return request;
                }
            """
        },
    )
    return HTMLResponse(swagger_html.body)


# Custom OpenAPI Schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="LMS API",
        version="1.0.0",
        description="Learning Management System API with CSRF Protection",
        routes=app.routes,
    )
    # Add CSRF Token Security
    # Ensure components exists
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}
    
    openapi_schema["components"]["securitySchemes"]["csrf-token"] = {
        "type": "apiKey",
        "name": "X-Csrftoken",
        "in": "header"
    }
    openapi_schema["security"] = [{"csrf-token": []}]
    app.openapi_schema = openapi_schema
    return openapi_schema

app.openapi = custom_openapi


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    ) 