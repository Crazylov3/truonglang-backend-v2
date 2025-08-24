from fastapi import FastAPI, Request, status, Response
from fastapi.middleware.cors import CORSMiddleware
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
from app.routers.auth import auth
from app.routers.users import users
from app.routers.courses import courses
from app.routers.enrollments import enrollments
from app.routers.payments import payments
from app.routers.attendance import attendance
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Silence SQLAlchemy's noisy query logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.dialects').setLevel(logging.WARNING)

csrf_token_header = APIKeyHeader(name="X-Csrftoken", auto_error=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async context manager for FastAPI lifespan events."""
    # Startup
    logger.info("Starting up Giao Duc Thang Long...")
    
    # Note: Database tables should be created using Alembic migrations
    # Run: alembic upgrade head
    logger.info("Note: Ensure database migrations are up to date with: alembic upgrade head")
  
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# # Global exception handlers
# @app.exception_handler(RequestValidationError)
# async def validation_exception_handler(request: Request, exc: RequestValidationError):
#     """Handle validation errors."""
#     return JSONResponse(
#         status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#         content={
#             "detail": "Validation error",
#             "errors": exc.errors()
#         }
#     )


@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError):
    """Handle database integrity errors."""
    logger.error(f"Database integrity error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": "Database constraint violation. This may indicate duplicate data or invalid relationships."
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unexpected error: {exc}")
    if settings.debug:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": f"Internal server error: {str(exc)}"
            }
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error"
            }
        )

# API Info endpoint
@app.get("/", tags=["info"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": f"Welcome to {settings.app_name} API",
        "version": settings.version,
        "docs": "/docs",
        "redoc": "/redoc",
        "architecture": {
            "database": "PostgreSQL with async SQLAlchemy",
            "cache": "Redis",
            "authentication": "JWT tokens",
            "email": "SendGrid",
            "patterns": "Repository & Service Layer"
        }
    }


# Include routers with consistent API versioning
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(courses.router, prefix="/api/v1")
app.include_router(enrollments.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(attendance.router, prefix="/api/v1")

# Middleware for request logging and monitoring
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing and basic metrics."""
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log response with metrics
    logger.info(
        f"Response: {request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.4f}s"
    )
    
    # Add custom headers for monitoring
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-API-Version"] = settings.version
    
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