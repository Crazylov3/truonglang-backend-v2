from pydantic import BaseModel
from typing import List, Optional, Generic, TypeVar
from datetime import datetime

T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response schema."""
    items: List[T]
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool
    
    @classmethod
    def create(cls, items: List[T], total: int, page: int, per_page: int):
        """Create a paginated response."""
        pages = (total + per_page - 1) // per_page if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )


class MessageResponse(BaseModel):
    """Standard message response schema."""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Standard error response schema."""
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = datetime.utcnow()


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str
    app_name: str
    version: str
    timestamp: datetime = datetime.utcnow()


class BaseTimestampedModel(BaseModel):
    """Base model with timestamps."""
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


__all__ = [
    "PaginatedResponse",
    "MessageResponse", 
    "ErrorResponse",
    "HealthResponse",
    "BaseTimestampedModel"
] 