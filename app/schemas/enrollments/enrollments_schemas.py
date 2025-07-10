from pydantic import BaseModel
from datetime import datetime
from app.schemas.common import PaginatedResponse


class EnrollmentResponse(BaseModel):
    message: str

class Enrollment(BaseModel):
    id: int
    student_id: int
    course_id: int
    enrolled_at: datetime
    is_active: bool


class Enrollments(PaginatedResponse[Enrollment]):
    pass