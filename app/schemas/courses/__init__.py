from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
from app.models.course import CourseStatus
from app.schemas.users import UserResponse
from app.schemas.common import PaginatedResponse


class CourseBase(BaseModel):
    title: str
    description: Optional[str] = None

    @validator('title')
    def validate_title(cls, v):
        if len(v.strip()) < 3:
            raise ValueError('Course title must be at least 3 characters long')
        return v.strip()


class CourseCreate(CourseBase):
    status: CourseStatus = CourseStatus.DRAFT


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CourseStatus] = None

    @validator('title')
    def validate_title(cls, v):
        if v and len(v.strip()) < 3:
            raise ValueError('Course title must be at least 3 characters long')
        return v.strip() if v else v


class CourseResponse(CourseBase):
    id: int
    instructor_id: int
    status: CourseStatus
    created_at: datetime
    updated_at: datetime
    enrolled_students_count: int

    class Config:
        from_attributes = True


class CourseDetailResponse(CourseResponse):
    instructor: UserResponse


# Use the common PaginatedResponse instead of custom CourseListResponse
CourseListResponse = PaginatedResponse[CourseResponse]

__all__ = [
    "CourseBase",
    "CourseCreate", 
    "CourseUpdate",
    "CourseResponse",
    "CourseDetailResponse",
    "CourseListResponse"
] 