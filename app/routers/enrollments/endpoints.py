from fastapi import Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.user import User, UserRole
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.subscription import Subscription
from app.core.deps import get_current_user


async def get_my_enrolled_courses(
    only_active: bool = Query(True, description="Only return active enrollments"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all courses the current student is enrolled in."""
    query = (
        select(Course)
        .join(Enrollment, Course.id == Enrollment.course_id)
        .options(selectinload(Course.creator))
        .where(Enrollment.student_id == current_user.id)
        .order_by(Enrollment.enrolled_at.desc())
    )
    
    if only_active:
        query = query.where(Enrollment.is_active == True)
    
    result = await db.execute(query)
    courses = result.scalars().all()
    
    return courses


async def get_my_enrollments_with_subscriptions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's enrollments with subscription information."""
    query = (
        select(Enrollment)
        .options(
            selectinload(Enrollment.course),
            selectinload(Enrollment.subscription)
        )
        .where(Enrollment.student_id == current_user.id)
        .where(Enrollment.is_active == True)
        .order_by(Enrollment.enrolled_at.desc())
    )
    
    result = await db.execute(query)
    enrollments = result.scalars().all()
    
    enrollment_data = []
    for enrollment in enrollments:
        data = {
            "id": enrollment.id,
            "course": {
                "id": enrollment.course.id,
                "title": enrollment.course.title,
                "payment_type": enrollment.course.payment_type,
                "price": enrollment.course.price,
                "subscription_price": enrollment.course.subscription_price,
                "is_usage_based": enrollment.course.is_usage_based
            },
            "enrolled_at": enrollment.enrolled_at,
            "is_active": enrollment.is_active,
            "subscription": None
        }
        
        if enrollment.subscription:
            data["subscription"] = {
                "id": enrollment.subscription.id,
                "status": enrollment.subscription.status,
                "current_period_starts_at": enrollment.subscription.current_period_starts_at,
                "current_period_ends_at": enrollment.subscription.current_period_ends_at,
                "canceled_at": enrollment.subscription.canceled_at
            }
        
        enrollment_data.append(data)
    
    return enrollment_data


async def get_all_enrollments(
    skip: int = Query(0, ge=0, description="Number of enrollments to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of enrollments to return"),
    course_id: int = Query(None, description="Filter by course ID"),
    student_id: int = Query(None, description="Filter by student ID"),
    only_active: bool = Query(True, description="Only return active enrollments"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all enrollments with filtering (Staff and Admin only)."""
    if current_user.role < UserRole.STAFF:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Staff access or above required. Your role: {current_user.role} (level {current_user.value})"
        )
    
    query = (
        select(Enrollment)
        .options(
            selectinload(Enrollment.student).selectinload(User.profile),
            selectinload(Enrollment.course),
            selectinload(Enrollment.subscription)
        )
    )
    
    if course_id:
        query = query.where(Enrollment.course_id == course_id)
    
    if student_id:
        query = query.where(Enrollment.student_id == student_id)
    
    if only_active:
        query = query.where(Enrollment.is_active == True)
    
    query = query.offset(skip).limit(limit).order_by(Enrollment.enrolled_at.desc())
    
    result = await db.execute(query)
    enrollments = result.scalars().all()
    
    return enrollments


async def toggle_enrollment_status(
    enrollment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Toggle enrollment active status (Staff and Admin only)."""
    if current_user.role < UserRole.STAFF:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access or above required"
        )
    
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
    
    # Toggle status
    enrollment.is_active = not enrollment.is_active
    await db.commit()
    await db.refresh(enrollment)
    
    return {
        "message": f"Enrollment {'activated' if enrollment.is_active else 'deactivated'} successfully",
        "enrollment": enrollment
    }


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
    if current_user.role >= UserRole.STAFF:
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