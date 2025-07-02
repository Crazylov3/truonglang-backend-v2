from fastapi import Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import date, timedelta
from app.database import get_db
from app.models.user import User, UserRole
from app.models.course import Course
from app.models.student_activity_log import StudentActivityLog
from app.core.deps import get_current_user
from app.core.decorators import authentication_required
from app.schemas.activity.instructor_activity import (
    GetCourseActivityResponse,
    GetCourseActivitySummaryResponse,
    StudentActivityEntry,
    StudentSummary,
    DailyActivity
)
from .activity import router, logger


@router.get("/course/{course_id}/activity", response_model=GetCourseActivityResponse)
@authentication_required(allowed_role=UserRole.INSTRUCTOR)
async def get_course_activity(
    course_id: int = Path(..., description="Course ID"),
    start_date: Optional[date] = Query(None, description="Start date for activity range"),
    end_date: Optional[date] = Query(None, description="End date for activity range"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get activity log for a specific course (instructor/staff/admin only)."""
    # Check if course exists and user has permission
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Check permissions
    can_view = False
    if current_user.role == UserRole.INSTRUCTOR:
        # Instructors can only view activity for their own courses
        can_view = course.creator_id == current_user.id
    elif current_user.role >= UserRole.STAFF:
        # Staff and admin can view all course activities
        can_view = True
    
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to view course activity"
        )
    
    query = (
        select(StudentActivityLog)
        .options(
            selectinload(StudentActivityLog.student).selectinload(User.profile)
        )
        .where(StudentActivityLog.course_id == course_id)
        .order_by(desc(StudentActivityLog.activity_date))
    )
    
    if start_date:
        query = query.where(StudentActivityLog.activity_date >= start_date)
    
    if end_date:
        query = query.where(StudentActivityLog.activity_date <= end_date)
    
    result = await db.execute(query)
    activities = result.scalars().all()
    
    # Convert to response format
    activity_entries = []
    for activity in activities:
        entry = StudentActivityEntry(
            id=activity.id,
            student_id=activity.student_id,
            course_id=activity.course_id,
            activity_date=activity.activity_date,
            student_email=activity.student.email if activity.student else None,
            student_first_name=activity.student.profile.first_name if activity.student and activity.student.profile else None,
            student_last_name=activity.student.profile.last_name if activity.student and activity.student.profile else None
        )
        activity_entries.append(entry)
    
    return GetCourseActivityResponse(activities=activity_entries)


@router.get("/course/{course_id}/activity/summary", response_model=GetCourseActivitySummaryResponse)
@authentication_required(allowed_role=UserRole.INSTRUCTOR)
async def get_course_activity_summary(
    course_id: int = Path(..., description="Course ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to summarize"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get activity summary for a course."""
    # Check permissions (same as get_course_activity)
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    can_view = False
    if current_user.role == UserRole.INSTRUCTOR:
        can_view = course.creator_id == current_user.id
    elif current_user.role >= UserRole.STAFF:
        can_view = True
    
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to view course activity"
        )
    
    start_date = date.today() - timedelta(days=days)
    
    # Get student activity summary
    query = (
        select(
            StudentActivityLog.student_id,
            User.email,
            func.count(StudentActivityLog.id).label('activity_days')
        )
        .join(User, StudentActivityLog.student_id == User.id)
        .where(StudentActivityLog.course_id == course_id)
        .where(StudentActivityLog.activity_date >= start_date)
        .group_by(StudentActivityLog.student_id, User.email)
        .order_by(desc('activity_days'))
    )
    
    result = await db.execute(query)
    student_summary = result.all()
    
    # Get daily activity counts
    daily_query = (
        select(
            StudentActivityLog.activity_date,
            func.count(StudentActivityLog.id).label('student_count')
        )
        .where(StudentActivityLog.course_id == course_id)
        .where(StudentActivityLog.activity_date >= start_date)
        .group_by(StudentActivityLog.activity_date)
        .order_by(StudentActivityLog.activity_date)
    )
    
    daily_result = await db.execute(daily_query)
    daily_activity = daily_result.all()
    
    total_unique_students = len(student_summary)
    total_activity_entries = sum(row.activity_days for row in student_summary)
    
    students = [
        StudentSummary(
            student_id=row.student_id,
            email=row.email,
            activity_days=row.activity_days
        )
        for row in student_summary
    ]
    
    daily_activities = [
        DailyActivity(
            date=row.activity_date,
            active_students=row.student_count
        )
        for row in daily_activity
    ]
    
    return GetCourseActivitySummaryResponse(
        course_id=course_id,
        course_title=course.title,
        period=f"Last {days} days",
        start_date=start_date,
        end_date=date.today(),
        total_unique_active_students=total_unique_students,
        total_activity_entries=total_activity_entries,
        students=students,
        daily_activity=daily_activities
    ) 