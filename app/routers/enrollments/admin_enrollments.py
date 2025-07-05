from app.routers.enrollments.enrollments import router
from typing import List
from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import UserRole
from app.core.operations import enrollment as enrollment_ops
from app.schemas.enrollments import EnrollmentResponse, EnrollmentListResponse
from app.schemas.common import PaginatedResponse
from app.core.decorators import authentication_required
from .enrollments import logger


@router.get("/courses/{course_id}/enrollments", response_model=EnrollmentListResponse)
@authentication_required(UserRole.STAFF)
async def get_enrollments_by_course_id(
    course_id: int,
    only_active: bool = Query(
        True, description="Only return active enrollments"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """Get enrollments by course ID for staff."""
    enrollments, total = await enrollment_ops.get_course_enrollments(
        db, course_id, only_active, page, per_page
    )
    
    enrollment_responses = [
        EnrollmentResponse(
            id=enrollment.id,
            student_id=enrollment.student_id,
            course_id=enrollment.course_id,
            enrolled_at=enrollment.enrolled_at,
            is_active=enrollment.is_active)
        for enrollment in enrollments
    ]
    
    return PaginatedResponse.create(
        items=enrollment_responses,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/users/{user_id}/enrollments", response_model=EnrollmentListResponse)
@authentication_required(UserRole.STAFF)
async def get_enrollments_by_user_id(
    user_id: int,
    only_active: bool = Query(
        True, description="Only return active enrollments"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """Get enrollments by user ID for staff."""
    enrollments, total = await enrollment_ops.get_user_enrollments(
        db, user_id, only_active, page, per_page
    )
    
    enrollment_responses = [
        EnrollmentResponse(
            id=enrollment.id,
            student_id=enrollment.student_id,
            course_id=enrollment.course_id,
            enrolled_at=enrollment.enrolled_at,
            is_active=enrollment.is_active)
        for enrollment in enrollments
    ]
    
    return PaginatedResponse.create(
        items=enrollment_responses,
        total=total,
        page=page,
        per_page=per_page
    )