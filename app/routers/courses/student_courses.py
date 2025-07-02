from fastapi import Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.database import get_db
from app.models.course import Course
from app.models.user import User, UserRole
from app.models.enrollment import Enrollment
from app.core.deps import get_current_user
from app.core.decorators import csrf_protect, authentication_required
from app.schemas.courses.course_schemas import (
    EnrollmentResponse,
    UnenrollmentResponse
)
from .courses import router, logger


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
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Check if already enrolled
    existing_enrollment = await db.execute(
        select(Enrollment).where(
            and_(
                Enrollment.student_id == current_user.id,
                Enrollment.course_id == course_id
            )
        )
    )
    
    if existing_enrollment.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already enrolled in this course"
        )
    
    # Create enrollment
    enrollment = Enrollment(
        student_id=current_user.id,
        course_id=course_id,
        is_active=True
    )
    
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    
    return enrollment


@router.delete("/{course_id}/enroll", response_model=UnenrollmentResponse)
@authentication_required(allowed_role=UserRole.STUDENT)
@csrf_protect
async def unenroll_from_course(
    course_id: int = Path(..., description="Course ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Unenroll from a course (Students only)."""
    # Find enrollment
    result = await db.execute(
        select(Enrollment).where(
            and_(
                Enrollment.student_id == current_user.id,
                Enrollment.course_id == course_id
            )
        )
    )
    enrollment = result.scalar_one_or_none()
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not enrolled in this course"
        )
    
    # Deactivate enrollment instead of deleting (to preserve history)
    enrollment.is_active = False
    await db.commit()
    
    return UnenrollmentResponse(message="Successfully unenrolled from course") 