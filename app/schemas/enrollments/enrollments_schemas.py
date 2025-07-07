from pydantic import BaseModel
from datetime import datetime
from app.schemas.users import UserResponse
from app.schemas.common import PaginatedResponse


# class EnrollmentResponse(BaseModel):
#     id: int
#     student_id: int
#     course_id: int
#     enrolled_at: datetime
#     is_active: bool

#     class Config:
#         from_attributes = True


# class EnrollmentDetailResponse(EnrollmentResponse):
#     student: UserResponse
#     course: CourseResponse


# class EnrollmentListResponse(PaginatedResponse[EnrollmentResponse]):
#     """Paginated response for enrollments."""
#     pass