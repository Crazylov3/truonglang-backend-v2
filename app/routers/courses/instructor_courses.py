from fastapi import Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.course import Course
from app.models.user import User, UserRole
from app.models.enrollment import Enrollment
from app.core.deps import get_current_user
from app.core.decorators import csrf_protect, authentication_required
from app.schemas.courses.course_schemas import (
    CourseCreate,
    CourseUpdate,
    CourseResponse,
    CourseStudentsResponse,
    CourseStudent
)
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
    # Set creator_id based on current user
    new_course = Course(
        title=course_data.title,
        description=course_data.description,
        creator_id=current_user.id,
        payment_type=course_data.payment_type,
        price=course_data.price,
        subscription_price=course_data.subscription_price,
        billing_interval=course_data.billing_interval,
        billing_interval_count=course_data.billing_interval_count,
        is_usage_based=course_data.is_usage_based
    )
    
    db.add(new_course)
    await db.commit()
    await db.refresh(new_course)
    
    # Reload the course with enrollments for the response
    result = await db.execute(
        select(Course).options(selectinload(Course.enrollments)).where(Course.id == new_course.id)
    )
    course_with_enrollments = result.scalar_one()
    
    return course_with_enrollments


@router.put("/{course_id}", response_model=CourseResponse)
@authentication_required(allowed_role=UserRole.INSTRUCTOR)
@csrf_protect
async def update_course(
    course_id: int = Path(..., description="Course ID"),
    course_update: CourseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a course."""
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Check permissions
    can_edit = False
    if current_user.role == UserRole.INSTRUCTOR:
        # Instructors can only edit their own courses
        can_edit = course.creator_id == current_user.id
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
    for field, value in update_data.items():
        setattr(course, field, value)
    
    await db.commit()
    await db.refresh(course)
    
    # Reload the course with enrollments for the response
    result = await db.execute(
        select(Course).options(selectinload(Course.enrollments)).where(Course.id == course_id)
    )
    course_with_enrollments = result.scalar_one()
    
    return course_with_enrollments


@router.get("/{course_id}/students", response_model=CourseStudentsResponse)
@authentication_required(allowed_role=UserRole.INSTRUCTOR)
async def get_course_students(
    course_id: int = Path(..., description="Course ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get students enrolled in a course."""
    # Check if course exists
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
        # Instructors can only view students of their own courses
        can_view = course.creator_id == current_user.id
    elif current_user.role >= UserRole.STAFF:
        # Staff and Admin can view students of any course
        can_view = True
    
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to view course students"
        )
    
    # Get enrolled students with profiles
    query = (
        select(User, Enrollment.enrolled_at, Enrollment.is_active)
        .join(Enrollment, User.id == Enrollment.student_id)
        .options(selectinload(User.profile))
        .where(Enrollment.course_id == course_id)
        .where(Enrollment.is_active == True)
    )
    
    result = await db.execute(query)
    students_data = result.all()
    
    students = [
        CourseStudent(
            id=student.id,
            email=student.email,
            full_name=student.full_name,
            enrolled_at=enrolled_at,
            is_active=is_active
        )
        for student, enrolled_at, is_active in students_data
    ]
    
    return CourseStudentsResponse(students=students) 