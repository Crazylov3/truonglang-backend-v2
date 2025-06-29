from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
import logging
from sqlalchemy import text

from app.database import AsyncSessionLocal, redis_client
from app.db.repositories import UserRepository, CourseRepository, EnrollmentRepository
from app.db.services import AuthService, UserService, CourseService, EnrollmentService

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database connection and session manager."""
    
    @staticmethod
    @asynccontextmanager
    async def get_session() -> AsyncGenerator[AsyncSession, None]:
        """Get a database session with automatic cleanup."""
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database transaction failed: {e}")
                raise
            finally:
                await session.close()
    
    @staticmethod
    @asynccontextmanager
    async def get_transaction() -> AsyncGenerator[AsyncSession, None]:
        """Get a database session with explicit transaction control."""
        async with AsyncSessionLocal() as session:
            async with session.begin():
                try:
                    yield session
                except Exception as e:
                    logger.error(f"Database transaction failed: {e}")
                    raise


class ServiceFactory:
    """Factory class for creating service instances."""
    
    def __init__(self, session: AsyncSession, redis_client: Optional[redis.Redis] = None):
        self.session = session
        self.redis_client = redis_client or get_redis_client()
    
    def get_auth_service(self) -> AuthService:
        """Get authentication service."""
        return AuthService(self.session, self.redis_client)
    
    def get_user_service(self) -> UserService:
        """Get user service."""
        return UserService(self.session)
    
    def get_course_service(self) -> CourseService:
        """Get course service."""
        return CourseService(self.session)
    
    def get_enrollment_service(self) -> EnrollmentService:
        """Get enrollment service."""
        return EnrollmentService(self.session)


class RepositoryFactory:
    """Factory class for creating repository instances."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def get_user_repository(self) -> UserRepository:
        """Get user repository."""
        return UserRepository(self.session)
    
    def get_course_repository(self) -> CourseRepository:
        """Get course repository."""
        return CourseRepository(self.session)
    
    def get_enrollment_repository(self) -> EnrollmentRepository:
        """Get enrollment repository."""
        return EnrollmentRepository(self.session)


async def get_db_session() -> AsyncSession:
    """Dependency to get database session."""
    async with DatabaseManager.get_session() as session:
        yield session


async def get_redis_client() -> redis.Redis:
    """Dependency to get Redis client."""
    return redis_client


async def get_service_factory(session: AsyncSession = None) -> ServiceFactory:
    """Dependency to get service factory."""
    if session is None:
        async with DatabaseManager.get_session() as session:
            yield ServiceFactory(session)
    else:
        yield ServiceFactory(session)


async def get_repository_factory(session: AsyncSession = None) -> RepositoryFactory:
    """Dependency to get repository factory."""
    if session is None:
        async with DatabaseManager.get_session() as session:
            yield RepositoryFactory(session)
    else:
        yield RepositoryFactory(session)


# Database health check
async def check_database_health() -> dict:
    """Check database connectivity and health."""
    try:
        async with DatabaseManager.get_session() as session:
            # Try a simple query with proper text() wrapper
            result = await session.execute(text("SELECT 1"))
            result.scalar()
            
        return {
            "status": "healthy"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# Redis health check
async def check_redis_health() -> dict:
    """Check Redis connectivity and health."""
    try:
        client = await get_redis_client()
        await client.ping()
        
        return {
            "status": "healthy"
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def check_system_health() -> dict:
    """Comprehensive system health check."""
    db_health = await check_database_health()
    redis_health = await check_redis_health()
    
    overall_status = "healthy" if (
        db_health.get("status") == "healthy" and 
        redis_health.get("status") == "healthy"
    ) else "unhealthy"
    
    return {
        "status": overall_status,
        "components": {
            "database": db_health,
            "redis": redis_health
        }
    }


__all__ = [
    "DatabaseManager",
    "ServiceFactory",
    "RepositoryFactory",
    "get_db_session",
    "get_redis_client", 
    "get_service_factory",
    "get_repository_factory",
    "check_database_health",
    "check_redis_health",
    "check_system_health"
] 