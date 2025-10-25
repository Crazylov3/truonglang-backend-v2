"""Branch schemas."""

from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, validator
from app.schemas.common import BaseUUIDModel, PaginatedResponse


class BranchCreate(BaseModel):
    """Schema for creating a branch."""
    name: str = Field(..., min_length=3, max_length=255, description="Branch name, e.g., 'Cơ sở Cầu Giấy'")
    address: str = Field(..., min_length=5, max_length=500, description="Branch address")
    contact_info: Optional[str] = Field(None, max_length=255, description="Contact information (phone, email, etc.)")
    
    @validator('name', 'address')
    def strip_whitespace(cls, v):
        return v.strip() if v else v


class BranchUpdate(BaseModel):
    """Schema for updating a branch."""
    name: Optional[str] = Field(None, min_length=3, max_length=255, description="Branch name")
    address: Optional[str] = Field(None, min_length=5, max_length=500, description="Branch address")
    contact_info: Optional[str] = Field(None, max_length=255, description="Contact information")
    
    @validator('name', 'address', 'contact_info')
    def strip_whitespace(cls, v):
        return v.strip() if v else v


class BranchResponse(BaseUUIDModel):
    """Branch response with basic info."""
    name: str
    address: str
    contact_info: Optional[str] = None


class BranchDetailResponse(BranchResponse):
    """Branch response with detailed info."""
    room_count: int = Field(0, description="Number of rooms in this branch")
    course_count: int = Field(0, description="Number of active courses in this branch")


class BranchListResponse(BaseModel):
    """Branch list response."""
    items: List[BranchResponse]
    total: int