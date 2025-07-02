from fastapi import Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import date, datetime, timedelta
from app.database import get_db
from app.models.user import User, UserRole
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.student_activity_log import StudentActivityLog
from app.core.deps import get_current_user
from app.core.decorators import csrf_protect, authentication_required
from app.schemas.activity.student_activity import (
    LogActivityRequest, 
    LogActivityResponse, 
    GetMyActivityResponse, 
    GetMyActivitySummaryResponse,
    ActivityEntry,
    CourseActivitySummary
)
from .activity import router, logger


@router.post("/log", response_model=LogActivityResponse)
@authentication_required(allowed_role=UserRole.STUDENT)
@csrf_protect
async def log_activity(
    request: LogActivityRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Log student activity for today in a specific course."""
    # Check if user is enrolled in the course
    result = await db.execute(
        select(Enrollment).where(
            and_(
                Enrollment.student_id == current_user.id,
                Enrollment.course_id == request.course_id,
                Enrollment.is_active == True
            )
        )
    )
    enrollment = result.scalar_one_or_none()
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enrolled in this course or enrollment is inactive"
        )
    
    today = date.today()
    
    # Check if activity already logged for today
    existing_activity = await db.execute(
        select(StudentActivityLog).where(
            and_(
                StudentActivityLog.student_id == current_user.id,
                StudentActivityLog.course_id == request.course_id,
                StudentActivityLog.activity_date == today
            )
        )
    )
    
    if existing_activity.scalar_one_or_none():
        return LogActivityResponse(message="Activity already logged for today", date=today)
    
    # Create activity log entry
    activity_log = StudentActivityLog(
        student_id=current_user.id,
        course_id=request.course_id,
        activity_date=today
    )
    
    db.add(activity_log)
    await db.commit()
    await db.refresh(activity_log)
    
    return LogActivityResponse(message="Activity logged successfully", date=today)


@router.get("/my-activity", response_model=GetMyActivityResponse)
async def get_my_activity(
    course_id: Optional[int] = Query(None, description="Filter by course ID"),
    start_date: Optional[date] = Query(None, description="Start date for activity range"),
    end_date: Optional[date] = Query(None, description="End date for activity range"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's activity log."""
    query = (
        select(StudentActivityLog)
        .options(selectinload(StudentActivityLog.course))
        .where(StudentActivityLog.student_id == current_user.id)
        .order_by(desc(StudentActivityLog.activity_date))
    )
    
    if course_id:
        query = query.where(StudentActivityLog.course_id == course_id)
    
    if start_date:
        query = query.where(StudentActivityLog.activity_date >= start_date)
    
    if end_date:
        query = query.where(StudentActivityLog.activity_date <= end_date)
    
    result = await db.execute(query)
    activities = result.scalars().all()
    
    # Convert to response format
    activity_entries = []
    for activity in activities:
        entry = ActivityEntry(
            id=activity.id,
            student_id=activity.student_id,
            course_id=activity.course_id,
            activity_date=activity.activity_date,
            course_title=activity.course.title if activity.course else None
        )
        activity_entries.append(entry)
    
    return GetMyActivityResponse(activities=activity_entries)


@router.get("/my-activity/summary", response_model=GetMyActivitySummaryResponse)
async def get_my_activity_summary(
    course_id: Optional[int] = Query(None, description="Filter by course ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to summarize"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get activity summary for the current user."""
    start_date = date.today() - timedelta(days=days)
    
    query = (
        select(
            StudentActivityLog.course_id,
            Course.title,
            func.count(StudentActivityLog.id).label('activity_days')
        )
        .join(Course, StudentActivityLog.course_id == Course.id)
        .where(StudentActivityLog.student_id == current_user.id)
        .where(StudentActivityLog.activity_date >= start_date)
        .group_by(StudentActivityLog.course_id, Course.title)
        .order_by(desc('activity_days'))
    )
    
    if course_id:
        query = query.where(StudentActivityLog.course_id == course_id)
    
    result = await db.execute(query)
    summary = result.all()
    
    total_activity_days = sum(row.activity_days for row in summary)
    
    courses = [
        CourseActivitySummary(
            course_id=row.course_id,
            course_title=row.title,
            activity_days=row.activity_days
        )
        for row in summary
    ]
    
    return GetMyActivitySummaryResponse(
        period=f"Last {days} days",
        start_date=start_date,
        end_date=date.today(),
        total_activity_days=total_activity_days,
        courses=courses
    ) 