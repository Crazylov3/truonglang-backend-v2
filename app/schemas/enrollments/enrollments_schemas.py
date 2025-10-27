from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict
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


class BulkEnrollmentRequest(BaseModel):
    """Request schema for bulk enrollment of students."""
    student_identifiers: List[str] = Field(..., description="List of student identifiers (UUID, email, or public_id)")


class BulkEnrollmentResponse(BaseModel):
    """Response schema for bulk enrollment operations."""
    success_count: int = Field(..., description="Number of successfully enrolled students")
    failure_count: int = Field(..., description="Number of failed enrollments")
    successful: List[Dict] = Field(..., description="List of successful enrollments with student details")
    failed: List[Dict] = Field(..., description="List of failed enrollments with error reasons")