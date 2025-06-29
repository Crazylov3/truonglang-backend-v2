from fastapi import APIRouter, status
from typing import List

# Import endpoint functions
from .endpoints import (
    get_courses,
    get_course,
    create_course,
    update_course,
    delete_course,
    enroll_in_course,
    unenroll_from_course,
    get_course_students
)

# Import schemas for response models
from app.schemas.courses import (
    CourseResponse, 
    CourseDetailResponse,
    CourseListResponse
)
from app.schemas.enrollments import EnrollmentResponse

router = APIRouter(prefix="/courses", tags=["courses"])

# Register endpoint routes
router.get("/", response_model=CourseListResponse)(get_courses)
router.get("/{course_id}", response_model=CourseDetailResponse)(get_course)
router.post("/", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)(create_course)
router.put("/{course_id}", response_model=CourseResponse)(update_course)
router.delete("/{course_id}", response_model=dict)(delete_course)
router.post("/{course_id}/enroll", response_model=EnrollmentResponse)(enroll_in_course)
router.delete("/{course_id}/enroll", response_model=dict)(unenroll_from_course)
router.get("/{course_id}/students", response_model=List[dict])(get_course_students) 