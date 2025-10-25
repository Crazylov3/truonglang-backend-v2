from fastapi import Depends, HTTPException, status, Query, Path
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from math import ceil
import os
from app.database import get_db
from app.core.validators import validate_uuid
from app.schemas.courses.course_schemas import (
    EnrollmentResponse,
    UnEnrollmentResponse,
    PublicViewCourseDetail,
    PublicViewCoursesDetail
)
from app.core.operations import course as course_ops
from app.core.operations import enrollment as enrollment_ops
from app.core.deps import get_current_user
from app.core.decorators import csrf_protect, authentication_required
from app.models.user import User, UserRole
from .courses import router, logger


@router.get("/", response_model=PublicViewCoursesDetail)
async def get_courses(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    creator_id: Optional[str] = Query(None, description="Filter by creator ID (UUID)"),
    branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
    room_id: Optional[str] = Query(None, description="Filter by room ID (shows courses scheduled in this room)"),
    title: Optional[str] = Query(None, description="Search by course title (partial match)"),
    teacher_name: Optional[str] = Query(None, description="Search by teacher name (partial match)"),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated list of courses with advanced filtering."""
    # Validate and convert UUIDs
    creator_uuid = validate_uuid(creator_id) if creator_id else None
    branch_uuid = validate_uuid(branch_id) if branch_id else None
    room_uuid = validate_uuid(room_id) if room_id else None
    
    courses, total = await course_ops.list_courses(
        db=db,
        page=page,
        per_page=per_page,
        creator_id=creator_uuid,
        branch_id=branch_uuid,
        room_id=room_uuid,
        title=title,
        teacher_name=teacher_name
    )

    courses = [PublicViewCourseDetail(
        id=course.id,
        title=course.title,
        description=course.description,
        start_date=course.start_date,
        teacher_name=course.teacher_name,
        price=course.price,
        preview_picture_path=course.preview_picture_path,
        branch_id=course.branch_id,
        branch_name=course.branch.name if course.branch else None
    ) for course in courses]
    
    return PublicViewCoursesDetail.create(
        items=courses,
        total=total,
        page=page,
        per_page=per_page
    )

@router.get('/enrolled-courses', response_model=PublicViewCoursesDetail)
@authentication_required(allowed_role=UserRole.STUDENT)
@csrf_protect
async def get_enrolled_courses(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
    room_id: Optional[str] = Query(None, description="Filter by room ID (shows courses scheduled in this room)"),
    title: Optional[str] = Query(None, description="Search by course title (partial match)"),
    teacher_name: Optional[str] = Query(None, description="Search by teacher name (partial match)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get enrolled courses for a student with filtering options."""
    # Validate and convert UUIDs
    branch_uuid = validate_uuid(branch_id) if branch_id else None
    room_uuid = validate_uuid(room_id) if room_id else None
    
    courses, total = await course_ops.list_enrolled_courses(
        db, 
        current_user.id, 
        page, 
        per_page,
        branch_id=branch_uuid,
        room_id=room_uuid,
        title=title,
        teacher_name=teacher_name
    )
    
    # Convert Course objects to PublicViewCourseDetail objects
    course_details = [PublicViewCourseDetail(
        id=course.id,
        title=course.title,
        description=course.description,
        start_date=course.start_date,
        teacher_name=course.teacher_name,
        price=course.price,
        preview_picture_path=course.preview_picture_path,
        branch_id=course.branch_id,
        branch_name=course.branch.name if course.branch else None
    ) for course in courses]
    
    return PublicViewCoursesDetail.create(items=course_details, total=total, page=page, per_page=per_page)

@router.get("/{course_id}", response_model=PublicViewCourseDetail)
async def get_course(
    course_id: str = Path(..., description="Course ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific course by ID."""
    course_uuid = validate_uuid(course_id)
    course = await course_ops.get_course_by_id(db, course_uuid)
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    return PublicViewCourseDetail(
        id=course.id,
        title=course.title,
        description=course.description,
        start_date=course.start_date,
        teacher_name=course.teacher_name,
        price=course.price,
        preview_picture_path=course.preview_picture_path,
        branch_id=course.branch_id,
        branch_name=course.branch.name if course.branch else None
    ) 


@router.get("/{course_id}/preview")
async def get_course_preview_image(
    course_id: str = Path(..., description="Course ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get course preview image."""
    course_uuid = validate_uuid(course_id)
    course = await course_ops.get_course_by_id(db, course_uuid)
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    if not course.preview_picture_path or not os.path.exists(course.preview_picture_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course preview image not found"
        )
    
    # Determine media type based on file extension
    _, ext = os.path.splitext(course.preview_picture_path)
    media_type = "image/jpeg"
    if ext.lower() in ['.png']:
        media_type = "image/png"
    elif ext.lower() in ['.gif']:
        media_type = "image/gif"
    elif ext.lower() in ['.webp']:
        media_type = "image/webp"
    
    return FileResponse(
        path=course.preview_picture_path,
        media_type=media_type,
        filename=f"course_{course_id}_preview{ext}"
    )


@router.post("/{course_id}/enroll", response_model=EnrollmentResponse)
@authentication_required(allowed_role=UserRole.STUDENT)
@csrf_protect
async def enroll_in_course(
    course_id: str = Path(..., description="Course ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Enroll in a course (Students only)."""
    # Check if course exists
    course_uuid = validate_uuid(course_id)
    course = await course_ops.get_course_by_id(db, course_uuid)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Check if already enrolled
    if await enrollment_ops.check_enrollment_exists(db, current_user.id, course_uuid):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already enrolled in this course"
        )
    
    # Create enrollment
    enrollment = await enrollment_ops.create_enrollment(
        db=db,
        student_id=current_user.id,
        course_id=course_uuid
    )
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create enrollment"
        )
    
    return EnrollmentResponse(
        message="Enrolled in course successfully"
    )


@router.post("/{course_id}/unenroll", response_model=UnEnrollmentResponse)
@authentication_required(allowed_role=UserRole.STUDENT)
@csrf_protect
async def unenroll_from_course(
    course_id: str = Path(..., description="Course ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Unenroll from a course (Students only)."""
    course_uuid = validate_uuid(course_id)
    enrollment = await enrollment_ops.get_enrollment(db, current_user.id, course_uuid)
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found"
        )
    
    await enrollment_ops.deactivate_enrollment(db, current_user.id, course_uuid)
    return UnEnrollmentResponse(
        message="Unenrolled from course successfully"
    )