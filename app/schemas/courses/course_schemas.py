from pydantic import BaseModel, validator, Field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from app.schemas.users import UserResponse
from app.schemas.common import PaginatedResponse
from app.schemas.payments.payment_schemas import PaymentPeriodResponse

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
    preview_picture_path: Optional[str] = Field(None, description="Path to course preview picture for lazy loading")


class InstructorViewCourseDetail(PublicViewCourseDetail):
    created_at: datetime = Field(..., description="Course creation date")
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
    preview_image: Optional[str] = Field(
        None, description="Preview image in base64 format")
    
    @validator('title')
    def validate_title(cls, v):
        return v.strip() if v else v

class CourseCreateResponse(BaseModel):
    message: str

class CourseUpdate(CourseCreate):
    pass


class CourseStudent(BaseModel):
    id: int 
    email: str
    full_name: str 
    enrolled_at: datetime
    owe_money: bool

class CourseStudents(PaginatedResponse[CourseStudent]):
    pass

class _Invoice(BaseModel):
    amount_due: float
    created_at: datetime

class CourseStudentPaymentDetail(BaseModel):
    invoices: dict[int, _Invoice]
    payments: dict[int, float]

class EnrollmentResponse(BaseModel):
    message: str


class UnEnrollmentResponse(BaseModel):
    message: str


class DeleteCourseResponse(BaseModel):
    message: str


# Removed CourseStudentsResponse class as it's replaced by PaginatedResponse[CourseStudent]
