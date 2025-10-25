"""Room schemas."""

from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, validator
from app.schemas.common import BaseUUIDModel, PaginatedResponse


class RoomCreate(BaseModel):
    """Schema for creating a room."""
    branch_id: UUID = Field(..., description="Branch ID where the room is located")
    room_number: str = Field(..., min_length=1, max_length=50, description="Room number or name, e.g., 'P101'")
    capacity: Optional[int] = Field(None, ge=1, description="Room capacity")
    
    @validator('room_number')
    def strip_whitespace(cls, v):
        return v.strip() if v else v


class RoomUpdate(BaseModel):
    """Schema for updating a room."""
    room_number: Optional[str] = Field(None, min_length=1, max_length=50, description="Room number or name")
    capacity: Optional[int] = Field(None, ge=1, description="Room capacity")
    
    @validator('room_number')
    def strip_whitespace(cls, v):
        return v.strip() if v else v


class RoomResponse(BaseUUIDModel):
    """Room response with basic info."""
    branch_id: UUID
    room_number: str
    capacity: Optional[int] = None


class RoomDetailResponse(RoomResponse):
    """Room response with detailed info including branch."""
    branch_name: str = Field(..., description="Name of the branch where room is located")
    schedule_count: int = Field(0, description="Number of scheduled courses in this room")


class RoomListResponse(BaseModel):
    """Room list response."""
    items: List[RoomResponse]
    total: int


class RoomWithBranchResponse(BaseUUIDModel):
    """Room response with branch details."""
    room_number: str
    capacity: Optional[int] = None
    branch: dict = Field(..., description="Branch information")


class CreateRoomResponse(BaseModel):
    """Response after creating a room."""
    message: str
    room_id: UUID


class UpdateRoomResponse(BaseModel):
    """Response after updating a room."""
    message: str