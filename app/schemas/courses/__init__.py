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
    
    # Enrollment schemas
    "EnrollmentResponse",
    "UnenrollmentResponse",
    "DeleteCourseResponse",
    
    # Student schemas
    "CourseStudent"
] 