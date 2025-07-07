from pydantic import BaseModel, validator, Field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from app.schemas.users import UserResponse
from app.schemas.common import PaginatedResponse


class PublicViewCourseDetail(BaseModel):
    id: int = Field(..., description="Course ID")
    title: str = Field(..., min_length=3, max_length=255,
                       description="Course title")
    description: Optional[str] = Field(None, description="Course description")
    location: Optional[str] = Field(None, description="Course location")
    start_date: Optional[datetime] = Field(
        None, description="Course start date")
    teacher_name: Optional[str] = Field(
        None, description="Course teacher name")
    price: Optional[Decimal] = Field(None, description="Course price")


class InstructorViewCourseDetail(PublicViewCourseDetail):
    created_at: datetime = Field(..., description="Course creation date")
    updated_at: datetime = Field(..., description="Course update date")
    enrolled_students_count: int = Field(...,
                                         description="Number of enrolled students")


class AdminViewCourseDetail(InstructorViewCourseDetail):
    creator_id: int = Field(..., description="Creator ID")
    creator_name: str = Field(..., description="Creator name")


class PublicViewCoursesDetail(PaginatedResponse[PublicViewCourseDetail]):
    pass


class InstructorViewCoursesDetail(PaginatedResponse[InstructorViewCourseDetail]):
    pass


class AdminViewCoursesDetail(PaginatedResponse[AdminViewCourseDetail]):
    pass


class CourseCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255,
                       description="Course title")
    description: Optional[str] = Field(None, description="Course description")
    price: Optional[Decimal] = Field(
        None, ge=0, description="One-time price for the course")
    location: Optional[str] = Field(None, description="Course location")
    start_date: Optional[datetime] = Field(
        None, description="Course start date")
    teacher_name: Optional[str] = Field(
        None, description="Course teacher name")
    
    @validator('title')
    def validate_title(cls, v):
        return v.strip() if v else v


class CourseUpdate(CourseCreate):
    pass


class CourseStudent(BaseModel):
    id: int 
    email: str
    full_name: str 
    enrolled_at: datetime

class CourseStudents(PaginatedResponse[CourseStudent]):
    pass


class CourseResponse(CourseCreate):
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


class StudentViewCourseResponse(CourseCreate):
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
