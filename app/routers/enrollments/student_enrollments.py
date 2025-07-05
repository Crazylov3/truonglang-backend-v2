from app.routers.enrollments.enrollments import router
from typing import List
from app.schemas.courses.course_schemas import StudentViewCourseResponse
from fastapi import Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User, UserRole
from app.core.deps import get_current_user
from app.core.operations import enrollment as enrollment_ops
from app.schemas.enrollments import EnrollmentResponse
from app.core.decorators import csrf_protect

    
    
@router.get("/my-courses", response_model=List[StudentViewCourseResponse])
async def get_my_enrolled_courses(
    only_active: bool = Query(True, description="Only return active enrollments"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all courses the current student is enrolled in."""
    enrollments, _ = await enrollment_ops.get_user_enrollments(
        db=db,
        student_id=current_user.id,
        active_only=only_active
    )
    
    # Extract courses from enrollments
    courses = [
        StudentViewCourseResponse(
            id=enrollment.course.id,
            title=enrollment.course.title,
            description=enrollment.course.description,
            price=enrollment.course.price,
            created_at=enrollment.course.created_at,
            creator_name=enrollment.course.creator.profile.first_name + " " + enrollment.course.creator.profile.last_name
        )
        for enrollment in enrollments
    ]
    return courses


@router.get("/{course_id}/enrollment", response_model=EnrollmentResponse)
async def get_enrollment_by_course_id(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get enrollment by course ID."""
    enrollment = await enrollment_ops.get_enrollment(db, current_user.id, course_id)
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found"
        )
    
    return EnrollmentResponse(
        id=enrollment.id,
        student_id=enrollment.student_id,
        course_id=enrollment.course_id,
        enrolled_at=enrollment.enrolled_at,
        is_active=enrollment.is_active
    )


@router.put("/{course_id}/deactivate", response_model=EnrollmentResponse)
@csrf_protect
async def deactivate_enrollment(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate enrollment by course ID."""
    enrollment = await enrollment_ops.deactivate_enrollment(db, current_user.id, course_id)

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found"
        )
    
    return EnrollmentResponse(
        id=enrollment.id,
        student_id=enrollment.student_id,
        course_id=enrollment.course_id,
        enrolled_at=enrollment.enrolled_at,
        is_active=enrollment.is_active
    )