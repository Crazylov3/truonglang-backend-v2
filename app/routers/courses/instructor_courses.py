from fastapi import Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User, UserRole
from app.core.deps import get_current_user
from app.core.decorators import csrf_protect, authentication_required
from app.schemas.courses.course_schemas import (
    CourseCreate,
    CourseUpdate,
    CourseResponse,
    CourseStudent
)
from app.schemas.common import PaginatedResponse
from app.core.operations import course as course_ops
from .courses import router, logger


@router.post("/", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
@authentication_required(allowed_role=UserRole.INSTRUCTOR)
@csrf_protect
async def create_course(
    course_data: CourseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new course."""
    try:
        course = await course_ops.create_course(
            db=db,
            title=course_data.title,
            description=course_data.description,
            creator_id=current_user.id,
            price=course_data.price
        )
        return course
    except Exception as e:
        logger.error(f"Error creating course: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create course"
        )


@router.put("/{course_id}", response_model=CourseResponse)
@authentication_required(allowed_role=UserRole.INSTRUCTOR)
@csrf_protect
async def update_course(
    course_update: CourseUpdate,
    course_id: int = Path(..., description="Course ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a course."""
    # Check if course exists
    course = await course_ops.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Check permissions
    can_edit = False
    if current_user.role == UserRole.INSTRUCTOR:
        # Instructors can only edit their own courses
        can_edit = await course_ops.check_course_ownership(db, course_id, current_user.id)
    elif current_user.role >= UserRole.STAFF:
        # Staff and Admin can edit any course
        can_edit = True
    
    if not can_edit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to edit this course"
        )
    
    # Update course
    update_data = course_update.dict(exclude_unset=True)
    updated_course = await course_ops.update_course(
        db=db,
        course_id=course_id,
        **update_data
    )
    
    if not updated_course:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update course"
        )
    
    return updated_course


@router.get("/{course_id}/students", response_model=PaginatedResponse[CourseStudent])
@authentication_required(allowed_role=UserRole.INSTRUCTOR)
async def get_course_students(
    course_id: int = Path(..., description="Course ID"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get students enrolled in a course with pagination."""
    # Check if course exists
    course = await course_ops.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Check permissions
    can_view = False
    if current_user.role == UserRole.INSTRUCTOR:
        # Instructors can only view students of their own courses
        can_view = await course_ops.check_course_ownership(db, course_id, current_user.id)
    elif current_user.role >= UserRole.STAFF:
        # Staff and Admin can view students of any course
        can_view = True
    
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to view course students"
        )
    
    # Get course students
    students_data, total = await course_ops.get_course_students(
        db=db,
        course_id=course_id,
        page=page,
        per_page=per_page
    )
    
    students = [
        CourseStudent(
            id=student_data['id'],
            email=student_data['email'],
            full_name=student_data['full_name'],
            enrolled_at=student_data['enrolled_at'],
            is_active=student_data['is_active']
        )
        for student_data in students_data
    ]
    
    return PaginatedResponse.create(
        items=students,
        total=total,
        page=page,
        per_page=per_page
    )
