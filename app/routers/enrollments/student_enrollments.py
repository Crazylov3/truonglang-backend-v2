from app.routers.enrollments.enrollments import router
from fastapi import Depends,  Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.core.deps import get_current_user
from app.core.operations import enrollment as enrollment_ops
from app.schemas.enrollments import EnrollmentResponse, Enrollments, Enrollment

    
@router.get("/my-enrollments", response_model=Enrollments)
async def get_my_enrollments(
    active_only: bool = Query(
        True, description="Only return active enrollments"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get my enrollments."""
    enrollments, total = await enrollment_ops.get_user_enrollments(db, current_user.id, active_only, page, per_page)
    enrollment_responses = [
        EnrollmentResponse(
            id=enrollment.id,
            student_id=enrollment.student_id,
            course_id=enrollment.course_id,
            enrolled_at=enrollment.enrolled_at,
            is_active=enrollment.is_active)
        for enrollment in enrollments
    ]
    return Enrollments.create(
        items=enrollment_responses,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/my-enrollments/{course_id}", response_model=Enrollment)
async def get_my_enrollment(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get my enrollment for a specific course."""
    enrollment = await enrollment_ops.get_enrollment(db, current_user.id, course_id)
    return Enrollment(
        id=enrollment.id,
        student_id=enrollment.student_id,
        course_id=enrollment.course_id,
        enrolled_at=enrollment.enrolled_at,
        is_active=enrollment.is_active
    )