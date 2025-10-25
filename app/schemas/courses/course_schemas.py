from pydantic import BaseModel, validator, Field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from uuid import UUID
from app.schemas.users import UserResponse
from app.schemas.common import PaginatedResponse, BaseUUIDModel
from app.schemas.payments.payment_schemas import PaymentPeriodResponse

class PublicViewCourseDetail(BaseUUIDModel):
    title: str = Field(..., min_length=3, max_length=255,
                       description="Course title")
    description: Optional[str] = Field(None, description="Course description")
    start_date: Optional[datetime] = Field(
        None, description="Course start date")
    teacher_name: Optional[str] = Field(
        None, description="Course teacher name")
    price: Optional[Decimal] = Field(None, description="Course price")
    preview_picture_path: Optional[str] = Field(None, description="Path to course preview picture for lazy loading")
    branch_id: Optional[UUID] = Field(None, description="Branch ID where course is held")
    branch_name: Optional[str] = Field(None, description="Branch name where course is held")


class InstructorViewCourseDetail(PublicViewCourseDetail):
    created_at: datetime = Field(..., description="Course creation date")
    enrolled_students_count: int = Field(...,
                                         description="Number of enrolled students")
    group_chat_link: Optional[str] = Field(None, description="Group chat link for course (visible only with edit permissions)")


class AdminViewCourseDetail(InstructorViewCourseDetail):
    creator_id: UUID = Field(..., description="Creator ID")
    creator_name: str = Field(..., description="Creator name")
    group_chat_link: Optional[str] = Field(None, description="Group chat link for course")


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
    start_date: Optional[datetime] = Field(
        None, description="Course start date")
    teacher_name: Optional[str] = Field(
        None, description="Course teacher name")
    preview_image: Optional[str] = Field(
        None, description="Preview image in base64 format")
    group_chat_link: Optional[str] = Field(
        None, description="Group chat link for course")
    branch_id: Optional[UUID] = Field(
        None, description="Branch ID where course will be held")
    
    @validator('title')
    def validate_title(cls, v):
        return v.strip() if v else v

class CourseCreateResponse(BaseUUIDModel):
    message: str

class CourseUpdate(CourseCreate):
    pass


class CourseStudent(BaseUUIDModel):
    email: str
    full_name: str 
    enrolled_at: datetime
    owe_money: bool
    discount_percentage: Optional[float] = Field(0.0, ge=0, le=100)
    discount_reason: Optional[str] = None

class CourseStudents(PaginatedResponse[CourseStudent]):
    pass

class _Invoice(BaseUUIDModel):
    amount_due: float
    created_at: datetime
    status: str  # 'DUE', 'PAID', 'OVERDUE', 'CANCELLED'

class CourseStudentPaymentDetail(BaseModel):
    invoices: dict[str, _Invoice]  # UUID as string key
    payments: dict[str, float]  # UUID as string key

class EnrollmentResponse(BaseModel):
    message: str


class UnEnrollmentResponse(BaseModel):
    message: str


class DeleteCourseResponse(BaseModel):
    message: str


# Removed CourseStudentsResponse class as it's replaced by PaginatedResponse[CourseStudent]
