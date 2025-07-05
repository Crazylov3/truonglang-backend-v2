from fastapi import Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from math import ceil
from app.database import get_db
from app.models.user import User
from app.core.deps import get_current_user_optional
from app.schemas.courses.course_schemas import (
    CourseListResponse,
    CourseDetailResponse
)
from app.core.operations import course as course_ops
from .courses import router, logger


@router.get("/", response_model=CourseListResponse)
async def get_courses(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    creator_id: Optional[int] = Query(None, description="Filter by creator ID"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated list of courses."""
    courses, total = await course_ops.list_courses(
        db=db,
        page=page,
        per_page=per_page,
        creator_id=creator_id
    )
    
    return CourseListResponse(
        items=courses,
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
    course = await course_ops.get_course_by_id(db, course_id)
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    return course 