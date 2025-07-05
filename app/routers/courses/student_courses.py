from fastapi import Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User, UserRole
from app.core.deps import get_current_user
from app.core.decorators import csrf_protect, authentication_required
from app.schemas.courses.course_schemas import (
    EnrollmentResponse,
    UnenrollmentResponse
)
from app.core.operations import course as course_ops
from app.core.operations import enrollment as enrollment_ops
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
    
    return enrollment
