from fastapi import APIRouter
from typing import List

# Import endpoint functions
from .endpoints import (
    get_my_enrolled_courses,
    get_all_enrollments,
    delete_enrollment
)

# Import schemas for response models
from app.schemas.enrollments import EnrollmentDetailResponse
from app.schemas.courses import CourseResponse

router = APIRouter(prefix="/enrollments", tags=["enrollments"])

# Register endpoint routes
router.get("/my-courses", response_model=List[CourseResponse])(get_my_enrolled_courses)
router.get("/", response_model=List[EnrollmentDetailResponse])(get_all_enrollments)
router.delete("/{enrollment_id}", response_model=dict)(delete_enrollment) 