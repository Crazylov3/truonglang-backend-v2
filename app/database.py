from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings
import redis.asyncio as redis

# Use PostgreSQL URL directly (no conversion needed for asyncpg)
async_database_url = settings.database_url

# Async SQLAlchemy setup
async_engine = create_async_engine(
    async_database_url,
    echo=settings.debug,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Sync SQLAlchemy setup (for Alembic migrations) - convert to sync PostgreSQL URL
sync_database_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
sync_engine = create_engine(
    sync_database_url,
    echo=settings.debug
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

Base = declarative_base()

# Redis setup
redis_client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)


# Dependency to get database session
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Dependency to get Redis client
async def get_redis():
    return redis_client 