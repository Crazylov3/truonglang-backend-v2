from fastapi import Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from math import ceil
from app.database import get_db
from app.schemas.courses.course_schemas import (
    EnrollmentResponse,
    UnenrollmentResponse,
    PublicViewCourseDetail,
    PublicViewCoursesDetail
)
from app.core.operations import course as course_ops
from app.core.operations import enrollment as enrollment_ops
from app.core.deps import get_current_user
from app.core.decorators import csrf_protect, authentication_required
from app.models.user import User, UserRole
from .courses import router, logger


@router.get("/", response_model=PublicViewCoursesDetail)
async def get_courses(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    creator_id: Optional[int] = Query(None, description="Filter by creator ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated list of courses."""
    courses, total = await course_ops.list_courses(
        db=db,
        page=page,
        per_page=per_page,
        creator_id=creator_id
    )

    courses = [PublicViewCourseDetail(
        id=course.id,
        title=course.title,
        description=course.description,
        location=course.location,
        start_date=course.start_date,
        teacher_name=course.teacher_name,
        price=course.price
    ) for course in courses]
    
    return PublicViewCoursesDetail.create(
        items=courses,
        total=total,
        page=page,
        per_page=per_page
    )

@router.get("/{course_id}", response_model=PublicViewCourseDetail)
async def get_course(
    course_id: int = Path(..., description="Course ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific course by ID."""
    course = await course_ops.get_course_by_id(db, course_id)
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    return PublicViewCourseDetail(
        id=course.id,
        title=course.title,
        description=course.description,
        location=course.location,
        start_date=course.start_date,
        teacher_name=course.teacher_name,
        price=course.price
    ) 


@router.post("/{course_id}/enroll", response_model=EnrollmentResponse)
@authentication_required(allowed_role=UserRole.STUDENT)
@csrf_protect
async def enroll_in_course(
    course_id: int = Path(..., description="Course ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Enroll in a course (Students only)."""
    # Check if course exists
    course = await course_ops.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Check if already enrolled
    if await enrollment_ops.check_enrollment_exists(db, current_user.id, course_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already enrolled in this course"
        )
    
    # Create enrollment
    enrollment = await enrollment_ops.create_enrollment(
        db=db,
        student_id=current_user.id,
        course_id=course_id
    )
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create enrollment"
        )
    
    return EnrollmentResponse(
        message="Enrolled in course successfully"
    )


@router.post("/{course_id}/unenroll", response_model=UnenrollmentResponse)
@authentication_required(allowed_role=UserRole.STUDENT)
@csrf_protect
async def unenroll_from_course(
    course_id: int = Path(..., description="Course ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Unenroll from a course (Students only)."""
    enrollment = await enrollment_ops.get_enrollment(db, current_user.id, course_id)
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found"
        )
    
    await enrollment_ops.deactivate_enrollment(db, current_user.id, course_id)
    return UnenrollmentResponse(
        message="Unenrolled from course successfully"
    )