from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID
from app.schemas.common import PaginatedResponse, BaseUUIDModel


class EnrollmentResponse(BaseModel):
    message: str

class Enrollment(BaseUUIDModel):
    student_id: UUID
    course_id: UUID
    enrolled_at: datetime
    is_active: bool
    discount_percentage: float = Field(0.0, ge=0, le=100, description="Discount percentage")
    discount_reason: Optional[str] = Field(None, description="Reason for discount")
    discount_approved_by: Optional[UUID] = Field(None, description="User who approved the discount")


class Enrollments(PaginatedResponse[Enrollment]):
    pass