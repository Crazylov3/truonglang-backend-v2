from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import List
from app.database import get_db
from app.schemas.enrollments import EnrollmentDetailResponse
from app.schemas.courses import CourseResponse
from app.models.user import User, UserRole
from app.models.course import Course, CourseStatus
from app.models.enrollment import Enrollment
from app.core.deps import get_current_user, require_student

router = APIRouter(prefix="/enrollments", tags=["enrollments"])


@router.get("/my-courses", response_model=List[CourseResponse])
async def get_my_enrolled_courses(
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Get all courses the current student is enrolled in."""
    query = (
        select(Course)
        .join(Enrollment, Course.id == Enrollment.course_id)
        .where(Enrollment.student_id == current_user.id)
        .order_by(Enrollment.enrolled_at.desc())
    )
    
    result = await db.execute(query)
    courses = result.scalars().all()
    
    return courses


@router.get("/", response_model=List[EnrollmentDetailResponse])
async def get_all_enrollments(
    skip: int = Query(0, ge=0, description="Number of enrollments to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of enrollments to return"),
    course_id: int = Query(None, description="Filter by course ID"),
    student_id: int = Query(None, description="Filter by student ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all enrollments with filtering (Staff and Admin only)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    query = (
        select(Enrollment)
        .options(
            selectinload(Enrollment.student),
            selectinload(Enrollment.course)
        )
    )
    
    if course_id:
        query = query.where(Enrollment.course_id == course_id)
    
    if student_id:
        query = query.where(Enrollment.student_id == student_id)
    
    query = query.offset(skip).limit(limit).order_by(Enrollment.enrolled_at.desc())
    
    result = await db.execute(query)
    enrollments = result.scalars().all()
    
    return enrollments


@router.delete("/{enrollment_id}", response_model=dict)
async def delete_enrollment(
    enrollment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an enrollment (Staff and Admin only, or student unenrolling themselves)."""
    # Get enrollment
    result = await db.execute(
        select(Enrollment).where(Enrollment.id == enrollment_id)
    )
    enrollment = result.scalar_one_or_none()
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found"
        )
    
    # Check permissions
    can_delete = False
    if current_user.role in [UserRole.STAFF, UserRole.ADMIN]:
        can_delete = True
    elif current_user.role == UserRole.STUDENT and enrollment.student_id == current_user.id:
        can_delete = True
    
    if not can_delete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to delete this enrollment"
        )
    
    await db.delete(enrollment)
    await db.commit()
    
    return {"message": "Enrollment deleted successfully"} 