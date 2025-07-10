# Import from the new modular course schemas
from .course_schemas import (
    PublicViewCourseDetail,
    PublicViewCoursesDetail,
    InstructorViewCourseDetail,
    InstructorViewCoursesDetail,
    AdminViewCourseDetail,
    AdminViewCoursesDetail,
    CourseStudent,
    CourseStudents,
    EnrollmentResponse,
    UnEnrollmentResponse,

    # manipulation schemas
    CourseCreate,
    CourseCreateResponse,
    CourseUpdate
)

# Keep the old imports for backward compatibility
__all__ = [
    "PublicViewCourseDetail",
    "PublicViewCoursesDetail",
    "InstructorViewCourseDetail",
    "InstructorViewCoursesDetail",
    "AdminViewCourseDetail",
    "AdminViewCoursesDetail",
    "CourseStudent",
    "CourseStudents",
    "EnrollmentResponse",
    "UnEnrollmentResponse",

    # manipulation schemas
    "CourseCreate",
    "CourseCreateResponse",
    "CourseUpdate"
] 