# Import from the new modular course schemas
from .course_schemas import (
    CourseBase,
    CourseCreate,
    CourseUpdate,
    CourseResponse,
    CourseDetailResponse,
    CourseListResponse,
    StudentViewCourseResponse,
    EnrollmentResponse,
    UnenrollmentResponse,
    DeleteCourseResponse,
    CourseStudent
)

# Keep the old imports for backward compatibility
__all__ = [
    # Course schemas
    "CourseBase",
    "CourseCreate", 
    "CourseUpdate",
    "CourseResponse",
    "CourseDetailResponse",
    "CourseListResponse",
    "StudentViewCourseResponse",
    
    # Enrollment schemas
    "EnrollmentResponse",
    "UnenrollmentResponse",
    "DeleteCourseResponse",
    
    # Student schemas
    "CourseStudent"
] 