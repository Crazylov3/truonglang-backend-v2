from app.routers.enrollments.enrollments import router
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.core.deps import get_current_user
from app.core.operations import enrollment as enrollment_ops
from app.schemas.enrollments import Enrollments, Enrollment
from app.core.decorators import authentication_required
from app.models.user import UserRole

@router.get("/instructor/enrollments/{course_id}", response_model=Enrollments)
@authentication_required(allowed_role=UserRole.INSTRUCTOR)
async def get_enrollments_by_course_id(
    course_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get enrollments by course ID for instructor."""
    enrollments, total = await enrollment_ops.get_course_enrollments(db, course_id)
    enrollment_responses = [
        Enrollment(
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
        page=1,
        per_page=10
    )