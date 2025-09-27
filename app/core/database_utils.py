"""Database utilities for transaction management and error handling."""

from typing import TypeVar, Optional, Callable, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, DataError, OperationalError
from fastapi import HTTPException, status
import logging
from functools import wraps
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

T = TypeVar("T")


@asynccontextmanager
async def db_transaction(session: AsyncSession):
    """
    Context manager for database transactions.
    Automatically commits on success and rollbacks on failure.
    
    Usage:
        async with db_transaction(session) as transaction:
            # Perform database operations
            await transaction.add(entity)
            # Transaction commits automatically on exit
    """
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise


def handle_db_errors(func: Callable) -> Callable:
    """
    Decorator to handle common database errors and convert them to HTTP exceptions.
    
    Usage:
        @handle_db_errors
        async def create_user(db: AsyncSession, user_data: dict):
            # Database operation
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except IntegrityError as e:
            logger.error(f"Database integrity error in {func.__name__}: {str(e)}")
            error_msg = str(e.orig)
            
            # Handle specific constraint violations
            if "unique constraint" in error_msg.lower() or "duplicate key" in error_msg.lower():
                if "email" in error_msg:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Email address already exists"
                    )
                elif "card_uid" in error_msg:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Card UID already exists"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Resource already exists"
                    )
            elif "foreign key constraint" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Referenced resource does not exist"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Database constraint violation"
                )
        
        except DataError as e:
            logger.error(f"Database data error in {func.__name__}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid data format"
            )
        
        except OperationalError as e:
            logger.error(f"Database operational error in {func.__name__}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection error. Please try again later."
            )
        
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred"
            )
    
    return wrapper


class DatabaseResult:
    """
    Wrapper for database operation results with success/error handling.
    
    Usage:
        result = await db_operation()
        if result.success:
            return result.data
        else:
            handle_error(result.error)
    """
    def __init__(self, success: bool, data: Optional[T] = None, error: Optional[str] = None):
        self.success = success
        self.data = data
        self.error = error
    
    @classmethod
    def ok(cls, data: T) -> "DatabaseResult[T]":
        """Create a successful result."""
        return cls(success=True, data=data)
    
    @classmethod
    def fail(cls, error: str) -> "DatabaseResult[T]":
        """Create a failed result."""
        return cls(success=False, error=error)


async def safe_db_operation(
    session: AsyncSession,
    operation: Callable,
    *args,
    commit: bool = True,
    **kwargs
) -> DatabaseResult:
    """
    Execute a database operation safely with proper error handling.
    
    Args:
        session: Database session
        operation: Async function to execute
        *args: Arguments for the operation
        commit: Whether to commit after successful operation
        **kwargs: Keyword arguments for the operation
    
    Returns:
        DatabaseResult with operation result or error
    """
    try:
        result = await operation(session, *args, **kwargs)
        
        if commit:
            await session.commit()
        
        return DatabaseResult.ok(result)
    
    except IntegrityError as e:
        await session.rollback()
        logger.error(f"Integrity error in safe_db_operation: {str(e)}")
        return DatabaseResult.fail(str(e))
    
    except Exception as e:
        await session.rollback()
        logger.error(f"Error in safe_db_operation: {str(e)}", exc_info=True)
        return DatabaseResult.fail(str(e))


def paginate_query(query, page: int = 1, per_page: int = 20):
    """
    Add pagination to a SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query object
        page: Page number (1-indexed)
        per_page: Items per page
    
    Returns:
        Query with limit and offset applied
    """
    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 20
    if per_page > 100:
        per_page = 100  # Maximum items per page
    
    offset = (page - 1) * per_page
    return query.limit(per_page).offset(offset)