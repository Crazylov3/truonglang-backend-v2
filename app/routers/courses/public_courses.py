from fastapi import Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional
from math import ceil
from app.database import get_db
from app.models.course import Course, CoursePaymentType
from app.models.user import User
from app.core.deps import get_current_user_optional
from app.schemas.courses.course_schemas import (
    CourseListResponse,
    CourseDetailResponse,
    CourseResponse
)
from .courses import router, logger


@router.get("/", response_model=CourseListResponse)
async def get_courses(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    payment_type: Optional[CoursePaymentType] = Query(None, description="Filter by payment type"),
    creator_id: Optional[int] = Query(None, description="Filter by creator ID"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated list of courses."""
    # Build query with preloaded relationships
    query = select(Course).options(
        selectinload(Course.creator),
        selectinload(Course.enrollments)
    )
    
    # Apply filters
    if payment_type:
        query = query.where(Course.payment_type == payment_type)
    
    if creator_id:
        query = query.where(Course.creator_id == creator_id)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    
    result = await db.execute(query)
    courses = result.scalars().all()
    courses_data = []
    for course in courses:
        courses_data.append(CourseResponse(
            id=course.id,
            title=course.title,
            description=course.description
        ))
    
    return CourseListResponse(
        items=courses_data,
        total=total,
        page=page,
        per_page=per_page,
        pages=ceil(total / per_page) if total > 0 else 0,
        has_next=page < ceil(total / per_page) if total > 0 else False,
        has_prev=page > 1
    )


@router.get("/{course_id}", response_model=CourseDetailResponse)
async def get_course(
    course_id: int = Path(..., description="Course ID"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific course by ID."""
    query = select(Course).options(
        selectinload(Course.creator),
        selectinload(Course.enrollments)
    ).where(Course.id == course_id)
    result = await db.execute(query)
    course = result.scalar_one_or_none()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    return course 