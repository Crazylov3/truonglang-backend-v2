from fastapi import Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import date
from app.database import get_db
from app.models.user import User, UserRole
from app.models.student_activity_log import StudentActivityLog
from app.core.decorators import authentication_required
from app.schemas.activity.admin_activity import (
    GetAllActivityResponse,
    AdminActivityEntry
)
from .activity import router, logger


@router.get("/admin/all", response_model=GetAllActivityResponse)
@authentication_required(allowed_role=UserRole.STAFF)
async def get_all_activity(
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    course_id: Optional[int] = Query(None, description="Filter by course ID"),
    student_id: Optional[int] = Query(None, description="Filter by student ID"),
    start_date: Optional[date] = Query(None, description="Start date for activity range"),
    end_date: Optional[date] = Query(None, description="End date for activity range"),
    db: AsyncSession = Depends(get_db)
):
    """Get all activity logs with filtering (Staff and Admin only)."""
    query = (
        select(StudentActivityLog)
        .options(
            selectinload(StudentActivityLog.student).selectinload(User.profile),
            selectinload(StudentActivityLog.course)
        )
        .order_by(desc(StudentActivityLog.activity_date))
    )
    
    if course_id:
        query = query.where(StudentActivityLog.course_id == course_id)
    
    if student_id:
        query = query.where(StudentActivityLog.student_id == student_id)
    
    if start_date:
        query = query.where(StudentActivityLog.activity_date >= start_date)
    
    if end_date:
        query = query.where(StudentActivityLog.activity_date <= end_date)
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    activities = result.scalars().all()
    
    # Convert to response format
    activity_entries = []
    for activity in activities:
        entry = AdminActivityEntry(
            id=activity.id,
            student_id=activity.student_id,
            course_id=activity.course_id,
            activity_date=activity.activity_date,
            student_email=activity.student.email if activity.student else None,
            student_first_name=activity.student.profile.first_name if activity.student and activity.student.profile else None,
            student_last_name=activity.student.profile.last_name if activity.student and activity.student.profile else None,
            course_title=activity.course.title if activity.course else None
        )
        activity_entries.append(entry)
    
    return GetAllActivityResponse(activities=activity_entries) 