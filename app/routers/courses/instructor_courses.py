from fastapi import Depends, HTTPException, status, Path, Query, Response
import os
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User, UserRole
from app.core.deps import get_current_user
from app.core.decorators import csrf_protect, authentication_required
from app.core.validators import validate_uuid
from app.schemas.courses.course_schemas import (
    CourseCreate,
    CourseUpdate,
    InstructorViewCoursesDetail,
    InstructorViewCourseDetail,
    CourseStudent,
    CourseStudents,
    CourseCreateResponse,
    CourseStudentPaymentDetail,
    _Invoice
)
import traceback
from app.schemas.common import PaginatedResponse
from app.core.operations import course as course_ops
from app.core.media.io_helper import from_base64_to_image, async_save_image_to_disk
from app.config import settings
from .courses import router, logger
from math import ceil
from datetime import datetime


@router.get("/instructor/courses", response_model=InstructorViewCoursesDetail)
@authentication_required(allowed_role=UserRole.INSTRUCTOR)
async def get_courses(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
    room_id: Optional[str] = Query(None, description="Filter by room ID (shows courses scheduled in this room)"),
    title: Optional[str] = Query(None, description="Search by course title (partial match)"),
    teacher_name: Optional[str] = Query(None, description="Search by teacher name (partial match)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated list of courses with advanced filtering."""
    # Validate and convert UUIDs
    branch_uuid = validate_uuid(branch_id) if branch_id else None
    room_uuid = validate_uuid(room_id) if room_id else None
    
    courses, total = await course_ops.list_courses(
        db=db,
        page=page,
        per_page=per_page,
        instructor_id=current_user.id,
        all_courses=current_user.role == UserRole.ADMIN or current_user.role == UserRole.STAFF,
        branch_id=branch_uuid,
        room_id=room_uuid,
        title=title,
        teacher_name=teacher_name
    )

    # Get list of course IDs that instructor can edit
    editable_course_ids = await course_ops.filter_courses_by_edit_permission(db, current_user.id) if current_user.role == UserRole.INSTRUCTOR else []
    
    courses_list = []
    for course in courses:
        # Check if user has permission to see group_chat_link
        # Staff/Admin always see it, Instructors only if they have edit permission
        can_see_group_chat = current_user.role == UserRole.STAFF or current_user.role == UserRole.ADMIN or course.id in editable_course_ids
        
        course_data = InstructorViewCourseDetail(
            id=course.id,
            title=course.title,
            description=course.description,
            start_date=course.start_date,
            teacher_name=course.teacher_name,
            price=course.price,
            created_at=course.created_at,
            enrolled_students_count=course.enrolled_students_count,
            preview_picture_path=course.preview_picture_path,
            group_chat_link=course.group_chat_link if can_see_group_chat else None,
            branch_id=course.branch_id,
            branch_name=course.branch.name if course.branch else None
        )
        courses_list.append(course_data)
    
    return InstructorViewCoursesDetail(
        items=courses_list,
        total=total,
        page=page,
        per_page=per_page,
        pages=ceil(total / per_page) if total > 0 else 0,
        has_next=page < ceil(total / per_page) if total > 0 else False,
        has_prev=page > 1
    )


@router.post("/instructor/create-course", response_model=CourseCreateResponse, status_code=status.HTTP_201_CREATED)
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
            price=course_data.price,
            start_date=course_data.start_date,
            teacher_name=course_data.teacher_name,
            branch_id=course_data.branch_id,
            group_chat_link=course_data.group_chat_link
        )
        
        # Handle preview image if provided
        if course_data.preview_image:
            try:
                # Create directory for course previews
                preview_dir = os.path.join(settings.media_root, "course_previews")
                os.makedirs(preview_dir, exist_ok=True)
                
                # Generate unique filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                preview_filename = f"course_{course.id}_preview_{timestamp}.png"
                preview_path = os.path.join(preview_dir, preview_filename)
                
                # Convert base64 to image and save
                image_data = from_base64_to_image(course_data.preview_image)
                await async_save_image_to_disk(image_data, preview_path)
                
                # Update course with preview path
                course = await course_ops.update_course(
                    db=db,
                    course_id=course.id,
                    preview_picture_path=preview_path
                )
            except Exception as e:
                logger.error(f"Error saving preview image: {e}")
                # Continue without preview image rather than failing the entire course creation
        
        await course_ops.grant_edit_permission(db, course.id, current_user.id, current_user.id)
        return CourseCreateResponse(
            id=course.id,
            message=f"Course {course.title} created successfully"
        )
    except Exception as e:
        logger.error(f"Error creating course: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create course"
        )

@router.get("/instructor/course/{course_id}", response_model=InstructorViewCourseDetail)
@authentication_required(allowed_role=UserRole.INSTRUCTOR)
async def get_course(
    course_id: str = Path(..., description="Course ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific course by ID."""
    course_uuid = validate_uuid(course_id)
    course = await course_ops.get_course_by_id(db, course_uuid)
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Check if user has access
    if current_user.role == UserRole.INSTRUCTOR:
        editable_course_ids = await course_ops.filter_courses_by_edit_permission(db, current_user.id)
        has_access = course_uuid in editable_course_ids
    else:  # Staff/Admin
        has_access = True
    
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this course"
        )
    
    # Check if user can see group_chat_link
    # Staff/Admin always see it, Instructors only if they have edit permission
    can_see_group_chat = current_user.role == UserRole.STAFF or current_user.role == UserRole.ADMIN or has_access
    
    return InstructorViewCourseDetail(
        id=course.id,
        title=course.title,
        description=course.description,
        start_date=course.start_date,
        teacher_name=course.teacher_name,
        price=course.price,
        created_at=course.created_at,
        enrolled_students_count=course.enrolled_students_count,
        preview_picture_path=course.preview_picture_path,
        group_chat_link=course.group_chat_link if can_see_group_chat else None,
        branch_id=course.branch_id,
        branch_name=course.branch.name if course.branch else None
    )


@router.put("/instructor/course/{course_id}", response_model=InstructorViewCourseDetail)
@authentication_required(allowed_role=UserRole.INSTRUCTOR)
@csrf_protect
async def update_course(
    course_update: CourseUpdate,
    course_id: str = Path(..., description="Course ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a course."""
    
    course_uuid = validate_uuid(course_id)
    course = await course_ops.get_course_by_id(db, course_uuid)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    can_edit = False
    if current_user.role == UserRole.INSTRUCTOR:
        can_edit = course_uuid in await course_ops.filter_courses_by_edit_permission(db, current_user.id)
    elif current_user.role == UserRole.STAFF or current_user.role == UserRole.ADMIN:
        can_edit = True
    
    if not can_edit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to edit this course"
        )
    
    update_data = course_update.dict(exclude_unset=True)
    
    # Handle preview image if provided
    if course_update.preview_image:
        try:
            # Create directory for course previews
            preview_dir = os.path.join(settings.media_root, "course_previews")
            os.makedirs(preview_dir, exist_ok=True)
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            preview_filename = f"course_{course_uuid}_preview_{timestamp}.png"
            preview_path = os.path.join(preview_dir, preview_filename)
            
            # Convert base64 to image and save
            image_data = from_base64_to_image(course_update.preview_image)
            await async_save_image_to_disk(image_data, preview_path)
            
            # Add preview path to update data
            update_data['preview_picture_path'] = preview_path
            # Remove base64 data from update
            update_data.pop('preview_image', None)
        except Exception as e:
            logger.error(f"Error saving preview image during update: {e}")
            # Continue without preview image rather than failing the entire update
            update_data.pop('preview_image', None)
    
    updated_course = await course_ops.update_course(
        db=db,
        course_id=course_uuid,
        **update_data
    )
    
    if not updated_course:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update course"
        )
    
    # Check if user can see group_chat_link
    # Staff/Admin always see it, Instructors only if they have edit permission
    can_see_group_chat = current_user.role == UserRole.STAFF or current_user.role == UserRole.ADMIN or can_edit
    
    return InstructorViewCourseDetail(
        id=updated_course.id,
        title=updated_course.title,
        description=updated_course.description,
        start_date=updated_course.start_date,
        teacher_name=updated_course.teacher_name,
        price=updated_course.price,
        created_at=updated_course.created_at,
        enrolled_students_count=updated_course.enrolled_students_count,
        preview_picture_path=updated_course.preview_picture_path,
        group_chat_link=updated_course.group_chat_link if can_see_group_chat else None,
        branch_id=updated_course.branch_id,
        branch_name=updated_course.branch.name if updated_course.branch else None
    )

@router.delete("/instructor/course/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
@authentication_required(allowed_role=UserRole.INSTRUCTOR)
@csrf_protect
async def delete_course(
    course_id: str = Path(..., description="Course ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a course."""
    course_uuid = validate_uuid(course_id)
    course = await course_ops.get_course_by_id(db, course_uuid)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    edit_permissions = await course_ops.filter_courses_by_edit_permission(db, current_user.id)
    logger.info(f"Edit permissions: {edit_permissions}, course_uuid: {course_uuid}, current_user_id: {current_user.id}")
    if course_uuid not in edit_permissions and current_user.role != UserRole.STAFF and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this course"
        )
    
    await course_ops.delete_course(db, course_uuid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/instructor/course/{course_id}/students", response_model=CourseStudents)
@authentication_required(allowed_role=UserRole.INSTRUCTOR)
async def get_course_students(
    course_id: str = Path(..., description="Course ID"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=10000, description="Items per page"),
    student_id: Optional[str] = Query(None, description="Filter by student ID"),
    first_name: Optional[str] = Query(None, description="Filter by first name (partial match)"),
    last_name: Optional[str] = Query(None, description="Filter by last name (partial match)"),
    email: Optional[str] = Query(None, description="Filter by email (partial match)"),
    owe_money: Optional[bool] = Query(None, description="Filter by payment status (True = owes money, False = paid)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get students enrolled in a course with pagination and filtering."""
    course_uuid = validate_uuid(course_id)
    course = await course_ops.get_course_by_id(db, course_uuid)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    can_view = False
    if current_user.role == UserRole.INSTRUCTOR:
        can_view = course_uuid in await course_ops.filter_courses_by_edit_permission(db, current_user.id)
    elif current_user.role == UserRole.STAFF or current_user.role == UserRole.ADMIN:
        can_view = True
    
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to view course students"
        )
    
    # Validate and convert student_id if provided
    student_uuid = validate_uuid(student_id) if student_id else None
    
    students_data, total = await course_ops.get_course_students(
        db=db,
        course_id=course_uuid,
        student_id=student_uuid,
        first_name=first_name,
        last_name=last_name,
        email=email,
        owe_money=owe_money,
        page=page,
        per_page=per_page
    )
    
    students = [
        CourseStudent(
            id=student_data['id'],
            public_id=student_data['public_id'],
            email=student_data['email'],
            full_name=student_data['full_name'],
            enrolled_at=student_data['enrolled_at'],
            owe_money=student_data['owe_money']
        )
        for student_data in students_data
    ]
    
    return CourseStudents.create(
        items=students,
        total=total,
        page=page,
        per_page=per_page
    )

@router.get("/instructor/course/{course_id}/students-payment-detail/{student_id}", response_model=CourseStudentPaymentDetail)
@authentication_required(allowed_role=UserRole.INSTRUCTOR)
async def get_course_student_detail(
    course_id: str = Path(..., description="Course ID"),
    student_id: str = Path(..., description="Student ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a student in a course."""
    
    # Check if course exists and user has permission
    course_uuid = validate_uuid(course_id)
    course = await course_ops.get_course_by_id(db, course_uuid)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Check permissions (instructor must own course or have edit permission)
    can_edit = False
    if current_user.role == UserRole.INSTRUCTOR:
        can_edit = course_uuid in await course_ops.filter_courses_by_edit_permission(db, current_user.id)
    elif current_user.role == UserRole.STAFF or current_user.role == UserRole.ADMIN:
        can_edit = True
    
    if not can_edit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to view student details for this course"
        )
    
    # Get student details
    student_uuid = validate_uuid(student_id)
    student_detail = await course_ops.get_course_student_detail(db, course_uuid, student_uuid)
    
    if not student_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found or not enrolled in this course"
        )
    
    # Convert invoices dict to _Invoice objects
    invoices_with_objects = {}
    for invoice_id, invoice_data in student_detail["invoices"].items():
        invoices_with_objects[invoice_id] = _Invoice(
            amount_due=invoice_data["amount_due"],
            created_at=invoice_data["created_at"]
        )
    
    return CourseStudentPaymentDetail(
        invoices=invoices_with_objects,
        payments=student_detail["payments"]
    )