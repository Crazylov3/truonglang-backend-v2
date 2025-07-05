from pydantic import BaseModel, validator, Field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from app.models.course import CoursePaymentType, BillingInterval
from app.schemas.users import UserResponse
from app.schemas.common import PaginatedResponse


class CourseBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255, description="Course title")
    description: Optional[str] = Field(None, description="Course description")

    @validator('title')
    def validate_title(cls, v):
        return v.strip()


class CourseCreate(CourseBase):
    payment_type: CoursePaymentType = Field(default=CoursePaymentType.ONE_TIME, description="Payment model for the course")
    price: Optional[Decimal] = Field(None, ge=0, description="One-time price (required if payment_type is ONE_TIME)")
    subscription_price: Optional[Decimal] = Field(None, ge=0, description="Subscription price per billing interval")
    billing_interval: Optional[BillingInterval] = Field(None, description="Billing interval for subscriptions")
    billing_interval_count: Optional[int] = Field(None, ge=1, description="Number of intervals between billings")
    is_usage_based: bool = Field(default=False, description="Whether this is usage-based billing")

    @validator('price')
    def validate_one_time_price(cls, v, values):
        payment_type = values.get('payment_type')
        if payment_type == CoursePaymentType.ONE_TIME and v is None:
            raise ValueError('Price is required for one-time payment courses')
        if payment_type == CoursePaymentType.SUBSCRIPTION and v is not None:
            raise ValueError('Price should not be set for subscription courses')
        return v

    @validator('subscription_price')
    def validate_subscription_price(cls, v, values):
        payment_type = values.get('payment_type')
        if payment_type == CoursePaymentType.SUBSCRIPTION and v is None:
            raise ValueError('Subscription price is required for subscription courses')
        if payment_type == CoursePaymentType.ONE_TIME and v is not None:
            raise ValueError('Subscription price should not be set for one-time payment courses')
        return v


class CourseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    payment_type: Optional[CoursePaymentType] = None
    price: Optional[Decimal] = Field(None, ge=0)
    subscription_price: Optional[Decimal] = Field(None, ge=0)
    billing_interval: Optional[BillingInterval] = None
    billing_interval_count: Optional[int] = Field(None, ge=1)
    is_usage_based: Optional[bool] = None

    @validator('title')
    def validate_title(cls, v):
        return v.strip() if v else v


class CourseResponse(CourseBase):
    id: int

class CourseDetailResponse(CourseResponse):
    creator: UserResponse


class CourseListResponse(PaginatedResponse[CourseResponse]):
    pass


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