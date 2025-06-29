from pydantic import BaseModel
from datetime import datetime
from app.schemas.courses import CourseResponse
from app.schemas.users import UserResponse


class EnrollmentResponse(BaseModel):
    id: int
    student_id: int
    course_id: int
    enrolled_at: datetime

    class Config:
        from_attributes = True


class EnrollmentDetailResponse(EnrollmentResponse):
    student: UserResponse
    course: CourseResponse

__all__ = [
    "EnrollmentResponse",
    "EnrollmentDetailResponse"
] 