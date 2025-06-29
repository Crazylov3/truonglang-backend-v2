from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
import logging
import time
from contextlib import asynccontextmanager

from app.config import settings
from app.database import async_engine, Base
from app.db.utils import check_system_health
from app.schemas.common import HealthResponse
from app.routers import auth, users, courses, enrollments

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async context manager for FastAPI lifespan events."""
    # Startup
    logger.info("Starting up Learnify LMS...")
    
    # Create database tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created successfully")
    
    # Check system health
    health_status = await check_system_health()
    if health_status["status"] == "healthy":
        logger.info("All system components are healthy")
    else:
        logger.warning(f"System health issues detected: {health_status}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Learnify LMS...")


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


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors()
        }
    )


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


# Health check endpoint with comprehensive system health
@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Comprehensive health check endpoint."""
    system_health = await check_system_health()
    
    return HealthResponse(
        status=system_health["status"],
        app_name=settings.app_name,
        version=settings.version
    )


# Detailed health check for monitoring
@app.get("/health/detailed", tags=["health"])
async def detailed_health_check():
    """Detailed health check with component status."""
    return await check_system_health()


# API Info endpoint
@app.get("/", tags=["info"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": f"Welcome to {settings.app_name} API",
        "version": settings.version,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "detailed_health": "/health/detailed",
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


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    ) 