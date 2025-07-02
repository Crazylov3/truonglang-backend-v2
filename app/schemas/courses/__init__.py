# Import from the new modular course schemas
from .course_schemas import (
    CourseBase,
    CourseCreate,
    CourseUpdate,
    CourseResponse,
    CourseDetailResponse,
    CourseListResponse,
    EnrollmentResponse,
    UnenrollmentResponse,
    DeleteCourseResponse,
    CourseStudent,
    CourseStudentsResponse
)

# Keep the old imports for backward compatibility
__all__ = [
    "CourseBase",
    "CourseCreate", 
    "CourseUpdate",
    "CourseResponse",
    "CourseDetailResponse",
    "CourseListResponse",
    "EnrollmentResponse",
    "UnenrollmentResponse",
    "DeleteCourseResponse",
    "CourseStudent",
    "CourseStudentsResponse"
] 