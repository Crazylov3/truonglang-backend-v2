from pydantic import BaseModel, validator, Field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from app.schemas.users import UserResponse
from app.schemas.common import PaginatedResponse


class CourseBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255, description="Course title")
    description: Optional[str] = Field(None, description="Course description")

    @validator('title')
    def validate_title(cls, v):
        return v.strip()


class CourseCreate(CourseBase):
    price: Optional[Decimal] = Field(None, ge=0, description="One-time price for the course")


class CourseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)

    @validator('title')
    def validate_title(cls, v):
        return v.strip() if v else v


class CourseResponse(CourseBase):
    id: int
    creator_id: int
    price: Optional[Decimal] = None
    created_at: datetime
    enrolled_students_count: int

    class Config:
        from_attributes = True


class CourseDetailResponse(CourseResponse):
    creator: UserResponse


class CourseListResponse(PaginatedResponse[CourseResponse]):
    pass

class StudentViewCourseResponse(CourseBase):
    id: int
    creator_name: str
    price: Optional[Decimal] = None
    created_at: datetime


class EnrollmentResponse(BaseModel):
    id: int
    student_id: int
    course_id: int
    enrolled_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class UnenrollmentResponse(BaseModel):
    message: str


class DeleteCourseResponse(BaseModel):
    message: str


class CourseStudent(BaseModel):
    id: int
    email: str
    full_name: str
    enrolled_at: datetime
    is_active: bool


# Removed CourseStudentsResponse class as it's replaced by PaginatedResponse[CourseStudent] 