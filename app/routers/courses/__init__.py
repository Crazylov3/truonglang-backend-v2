from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from math import ceil
from app.database import get_db
from app.schemas.courses import (
    CourseCreate, 
    CourseUpdate, 
    CourseResponse, 
    CourseDetailResponse,
    CourseListResponse
)
from app.schemas.enrollments import EnrollmentResponse
from app.models.course import Course, CourseStatus
from app.models.user import User, UserRole
from app.models.enrollment import Enrollment
from app.core.deps import (
    get_current_user,
    get_current_user_optional,
    require_instructor_staff_or_admin,
    require_staff_or_admin,
    require_student
)

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("/", response_model=CourseListResponse)
async def get_courses(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[CourseStatus] = Query(None, description="Filter by course status"),
    instructor_id: Optional[int] = Query(None, description="Filter by instructor ID"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated list of courses."""
    # Build query
    query = select(Course).options(selectinload(Course.instructor))
    
    # Apply filters based on user role
    if not current_user or current_user.role == UserRole.STUDENT:
        # Students and anonymous users can only see published courses
        query = query.where(Course.status == CourseStatus.PUBLISHED)
    elif current_user.role == UserRole.INSTRUCTOR:
        # Instructors can see published courses and their own courses
        query = query.where(
            or_(
                Course.status == CourseStatus.PUBLISHED,
                Course.instructor_id == current_user.id
            )
        )
    # Staff and Admin can see all courses (no additional filter needed)
    
    # Apply additional filters
    if status and (not current_user or current_user.role in [UserRole.STAFF, UserRole.ADMIN]):
        query = query.where(Course.status == status)
    
    if instructor_id:
        query = query.where(Course.instructor_id == instructor_id)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    
    result = await db.execute(query)
    courses = result.scalars().all()
    
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
    course_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific course by ID."""
    query = select(Course).options(selectinload(Course.instructor)).where(Course.id == course_id)
    result = await db.execute(query)
    course = result.scalar_one_or_none()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Check access permissions
    can_access = False
    
    if not current_user:
        # Anonymous users can only see published courses
        can_access = course.status == CourseStatus.PUBLISHED
    elif current_user.role == UserRole.STUDENT:
        # Students can only see published courses
        can_access = course.status == CourseStatus.PUBLISHED
    elif current_user.role == UserRole.INSTRUCTOR:
        # Instructors can see published courses and their own courses
        can_access = (course.status == CourseStatus.PUBLISHED or 
                     course.instructor_id == current_user.id)
    else:
        # Staff and Admin can see all courses
        can_access = True
    
    if not can_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    return course


@router.post("/", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    course_data: CourseCreate,
    current_user: User = Depends(require_instructor_staff_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new course."""
    # Set instructor_id based on user role
    instructor_id = current_user.id
    if current_user.role in [UserRole.STAFF, UserRole.ADMIN]:
        # Staff and Admin can create courses for themselves or specify another instructor
        # For simplicity, we'll use the current user as instructor
        # In a real app, you might want to add instructor_id to the request body
        instructor_id = current_user.id
    
    new_course = Course(
        title=course_data.title,
        description=course_data.description,
        instructor_id=instructor_id,
        status=course_data.status
    )
    
    db.add(new_course)
    await db.commit()
    await db.refresh(new_course)
    
    return new_course


@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: int,
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
        can_edit = course.instructor_id == current_user.id
    elif current_user.role in [UserRole.STAFF, UserRole.ADMIN]:
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
    
    return course


@router.delete("/{course_id}", response_model=dict)
async def delete_course(
    course_id: int,
    current_user: User = Depends(require_staff_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete a course (Staff and Admin only)."""
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    await db.delete(course)
    await db.commit()
    
    return {"message": f"Course '{course.title}' deleted successfully"}


@router.post("/{course_id}/enroll", response_model=EnrollmentResponse)
async def enroll_in_course(
    course_id: int,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Enroll in a course (Students only)."""
    # Check if course exists and is published
    result = await db.execute(
        select(Course).where(
            and_(Course.id == course_id, Course.status == CourseStatus.PUBLISHED)
        )
    )
    course = result.scalar_one_or_none()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or not available for enrollment"
        )
    
    # Check if already enrolled
    existing_enrollment = await db.execute(
        select(Enrollment).where(
            and_(
                Enrollment.student_id == current_user.id,
                Enrollment.course_id == course_id
            )
        )
    )
    
    if existing_enrollment.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already enrolled in this course"
        )
    
    # Create enrollment
    enrollment = Enrollment(
        student_id=current_user.id,
        course_id=course_id
    )
    
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    
    return enrollment


@router.delete("/{course_id}/enroll", response_model=dict)
async def unenroll_from_course(
    course_id: int,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Unenroll from a course (Students only)."""
    # Find enrollment
    result = await db.execute(
        select(Enrollment).where(
            and_(
                Enrollment.student_id == current_user.id,
                Enrollment.course_id == course_id
            )
        )
    )
    enrollment = result.scalar_one_or_none()
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not enrolled in this course"
        )
    
    await db.delete(enrollment)
    await db.commit()
    
    return {"message": "Successfully unenrolled from course"}


@router.get("/{course_id}/students", response_model=List[dict])
async def get_course_students(
    course_id: int,
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
        can_view = course.instructor_id == current_user.id
    elif current_user.role in [UserRole.STAFF, UserRole.ADMIN]:
        # Staff and Admin can view students of any course
        can_view = True
    
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to view course students"
        )
    
    # Get enrolled students
    query = (
        select(User, Enrollment.enrolled_at)
        .join(Enrollment, User.id == Enrollment.student_id)
        .where(Enrollment.course_id == course_id)
    )
    
    result = await db.execute(query)
    students_data = result.all()
    
    students = [
        {
            "id": student.id,
            "email": student.email,
            "full_name": student.full_name,
            "enrolled_at": enrolled_at
        }
        for student, enrolled_at in students_data
    ]
    
    return students 