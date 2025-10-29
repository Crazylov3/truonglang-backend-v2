"""Course schedule management router."""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID
from datetime import time

from app.database import get_db
from app.models.user import User, UserRole
from app.models.location import DayOfWeek
from app.core.deps import get_current_user
from app.core.decorators import csrf_protect
from app.core.deps import require_role
from app.core.validators import validate_uuid
from app.core.operations import schedule as schedule_ops
from app.core.operations import course as course_ops
from app.schemas.locations.location_schemas import (
    CourseScheduleCreate,
    CourseScheduleUpdate,
    CourseScheduleResponse,
    CourseSchedulesResponse,
    WeekScheduleResponse,
    WeekScheduleItem
)
from math import ceil
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/schedules",
    tags=["schedules"]
)


@router.post("/course/{course_id}", response_model=List[CourseScheduleResponse], status_code=status.HTTP_201_CREATED)
@csrf_protect
async def create_course_schedule(
    course_id: str = Path(..., description="Course ID"),
    schedule_data: CourseScheduleCreate = Body(..., description="Schedule data"),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR)),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a schedule for a course.
    
    - Instructors can only create schedules for courses they own or have edit permissions
    - Staff and Admin can create schedules for any course
    - Checks for room availability conflicts
    """
    course_uuid = validate_uuid(course_id)
    
    # Check permissions
    if current_user.role == UserRole.INSTRUCTOR:
        editable_courses = await course_ops.filter_courses_by_edit_permission(db, current_user.id)
        if course_uuid not in editable_courses:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to manage this course"
            )
    
    try:
        schedule = await schedule_ops.create_schedule(
            db=db,
            course_id=course_uuid,
            room_id=schedule_data.room_id,
            day_of_week=schedule_data.day_of_week,
            start_time=schedule_data.start_time,
            end_time=schedule_data.end_time
        )
        
        # Get schedule with related data
        schedule = await schedule_ops.get_schedule_by_id(db, schedule.id)
        
        return [CourseScheduleResponse(
            id=schedule.id,
            course_id=schedule.course_id,
            room_id=schedule.room_id,
            day_of_week=schedule.day_of_week,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            course_title=schedule.course.title if schedule.course else None,
            room_number=schedule.room.room_number if schedule.room else None,
            branch_name=schedule.room.branch.name if schedule.room and schedule.room.branch else None
        )]
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create schedule"
        )


@router.post("/course/{course_id}/bulk", response_model=List[CourseScheduleResponse], status_code=status.HTTP_201_CREATED)
@csrf_protect
async def bulk_create_schedules(
    course_id: str = Path(..., description="Course ID"),
    schedules: List[CourseScheduleCreate] = Body(..., description="List of schedules"),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR)),
    db: AsyncSession = Depends(get_db)
):
    """
    Create multiple schedules for a course at once.
    
    - All schedules must be valid (no conflicts)
    - If any schedule has a conflict, none will be created
    """
    course_uuid = validate_uuid(course_id)
    
    # Check permissions
    if current_user.role == UserRole.INSTRUCTOR:
        editable_courses = await course_ops.filter_courses_by_edit_permission(db, current_user.id)
        if course_uuid not in editable_courses:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to manage this course"
            )
    
    try:
        # Convert to dict format for operations
        schedule_dicts = [
            {
                "room_id": s.room_id,
                "day_of_week": s.day_of_week,
                "start_time": s.start_time,
                "end_time": s.end_time
            }
            for s in schedules
        ]
        
        created = await schedule_ops.bulk_create_schedules(db, course_uuid, schedule_dicts)
        
        # Get schedules with related data
        result = []
        for schedule in created:
            schedule = await schedule_ops.get_schedule_by_id(db, schedule.id)
            result.append(CourseScheduleResponse(
                id=schedule.id,
                course_id=schedule.course_id,
                room_id=schedule.room_id,
                day_of_week=schedule.day_of_week,
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                course_title=schedule.course.title if schedule.course else None,
                room_number=schedule.room.room_number if schedule.room else None,
                branch_name=schedule.room.branch.name if schedule.room and schedule.room.branch else None
            ))
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating schedules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create schedules"
        )


@router.get("/course/{course_id}", response_model=CourseSchedulesResponse)
async def get_course_schedules(
    course_id: str = Path(..., description="Course ID"),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all schedules for a course.
    
    - Students can only see schedules for courses they're enrolled in
    - Instructors can see schedules for courses they teach
    - Staff and Admin can see all schedules
    """
    course_uuid = validate_uuid(course_id)
    
    # Check access permissions
    if current_user.role == UserRole.STUDENT:
        enrollment = await course_ops.check_enrollment(db, current_user.id, course_uuid)
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You're not enrolled in this course"
            )
    elif current_user.role == UserRole.INSTRUCTOR:
        has_permission = await course_ops.check_instructor_permission(db, current_user.id, course_uuid)
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this course"
            )
    
    schedules = await schedule_ops.get_course_schedules(db, course_uuid)
    
    schedule_responses = [
        CourseScheduleResponse(
            id=s.id,
            course_id=s.course_id,
            room_id=s.room_id,
            day_of_week=s.day_of_week,
            start_time=s.start_time,
            end_time=s.end_time,
            course_title=s.course.title if s.course else None,
            room_number=s.room.room_number if s.room else None,
            branch_name=s.room.branch.name if s.room and s.room.branch else None
        )
        for s in schedules
    ]
    
    return CourseSchedulesResponse(
        course_id=course_uuid,
        schedules=schedule_responses,
        total=len(schedules)
    )


@router.get("/week", response_model=WeekScheduleResponse)
async def get_week_schedule(
    branch_id: Optional[str] = Query(None, description="Filter by branch"),
    room_id: Optional[str] = Query(None, description="Filter by room"),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db)
):
    """
    Get weekly schedule view.
    
    - Can filter by branch or room
    - Students see their enrolled courses
    - Instructors see their courses
    - Staff/Admin see all
    """
    branch_uuid = validate_uuid(branch_id) if branch_id else None
    room_uuid = validate_uuid(room_id) if room_id else None
    
    # For students, get their enrolled course IDs first
    enrolled_course_ids = []
    if current_user.role == UserRole.STUDENT:
        enrolled_courses, _ = await course_ops.list_enrolled_courses(
            db, current_user.id, page=1, per_page=1000
        )
        enrolled_course_ids = [course.id for course in enrolled_courses]
    
    # Get schedules based on user role
    if current_user.role == UserRole.STAFF or current_user.role == UserRole.ADMIN:
        # Staff and Admin see all schedules (with optional filters)
        week_data = await schedule_ops.get_week_schedule(
            db,
            branch_id=branch_uuid,
            room_id=room_uuid
        )
    elif current_user.role == UserRole.INSTRUCTOR:
        # Instructors see their own courses
        week_data = await schedule_ops.get_week_schedule(
            db,
            branch_id=branch_uuid,
            room_id=room_uuid,
            instructor_id=current_user.id
        )
    else:
        # Students see only enrolled courses
        if not enrolled_course_ids:
            # Return empty schedule if not enrolled in any courses
            return WeekScheduleResponse()
        
        week_data = await schedule_ops.get_week_schedule_for_courses(
            db,
            course_ids=enrolled_course_ids,
            branch_id=branch_uuid,
            room_id=room_uuid
        )
    
    # Convert to response format
    response = WeekScheduleResponse()
    
    for day, schedules in week_data.items():
        items = []
        for schedule in schedules:
            items.append(WeekScheduleItem(
                schedule_id=schedule.id,
                course_id=schedule.course_id,
                course_title=schedule.course.title,
                room_number=schedule.room.room_number,
                branch_name=schedule.room.branch.name,
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                instructor_name=schedule.course.teacher_name
            ))
        
        setattr(response, day, items)
    
    return response


@router.get("/{schedule_id}", response_model=CourseScheduleResponse)
async def get_schedule(
    schedule_id: str = Path(..., description="Schedule ID"),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db)
):
    """Get schedule details by ID."""
    schedule_uuid = validate_uuid(schedule_id)
    schedule = await schedule_ops.get_schedule_by_id(db, schedule_uuid)
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    # Check access permissions
    if current_user.role == UserRole.STUDENT:
        enrollment = await course_ops.check_enrollment(
            db, current_user.id, schedule.course_id
        )
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this schedule"
            )
    elif current_user.role == UserRole.INSTRUCTOR:
        has_permission = await course_ops.check_instructor_permission(
            db, current_user.id, schedule.course_id
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this schedule"
            )
    
    return CourseScheduleResponse(
        id=schedule.id,
        course_id=schedule.course_id,
        room_id=schedule.room_id,
        day_of_week=schedule.day_of_week,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        course_title=schedule.course.title if schedule.course else None,
        room_number=schedule.room.room_number if schedule.room else None,
        branch_name=schedule.room.branch.name if schedule.room and schedule.room.branch else None
    )


@router.put("/{schedule_id}", response_model=CourseScheduleResponse)
@csrf_protect
async def update_schedule(
    schedule_id: str = Path(..., description="Schedule ID"),
    schedule_update: CourseScheduleUpdate = Body(...),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR)),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a schedule.
    
    - Checks for room conflicts
    - Only course owner/editor or staff/admin can update
    """
    schedule_uuid = validate_uuid(schedule_id)
    
    # Get schedule to check course permissions
    schedule = await schedule_ops.get_schedule_by_id(db, schedule_uuid)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    # Check permissions
    if current_user.role == UserRole.INSTRUCTOR:
        editable_courses = await course_ops.filter_courses_by_edit_permission(db, current_user.id)
        if schedule.course_id not in editable_courses:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to manage this schedule"
            )
    
    try:
        updated = await schedule_ops.update_schedule(
            db=db,
            schedule_id=schedule_uuid,
            room_id=schedule_update.room_id,
            day_of_week=schedule_update.day_of_week,
            start_time=schedule_update.start_time,
            end_time=schedule_update.end_time
        )
        
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found"
            )
        
        # Get updated schedule with related data
        updated = await schedule_ops.get_schedule_by_id(db, updated.id)
        
        return CourseScheduleResponse(
            id=updated.id,
            course_id=updated.course_id,
            room_id=updated.room_id,
            day_of_week=updated.day_of_week,
            start_time=updated.start_time,
            end_time=updated.end_time,
            course_title=updated.course.title if updated.course else None,
            room_number=updated.room.room_number if updated.room else None,
            branch_name=updated.room.branch.name if updated.room and updated.room.branch else None
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update schedule"
        )


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
@csrf_protect
async def delete_schedule(
    schedule_id: str = Path(..., description="Schedule ID"),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR)),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a schedule.
    
    - Only course owner/editor or staff/admin can delete
    """
    schedule_uuid = validate_uuid(schedule_id)
    
    # Get schedule to check course permissions
    schedule = await schedule_ops.get_schedule_by_id(db, schedule_uuid)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    # Check permissions
    if current_user.role == UserRole.INSTRUCTOR:
        editable_courses = await course_ops.filter_courses_by_edit_permission(db, current_user.id)
        if schedule.course_id not in editable_courses:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to manage this schedule"
            )
    
    try:
        success = await schedule_ops.delete_schedule(db, schedule_uuid)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found"
            )
    except Exception as e:
        logger.error(f"Error deleting schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete schedule"
        )


@router.get("/room/{room_id}/availability", response_model=List[CourseScheduleResponse])
async def check_room_availability(
    room_id: str = Path(..., description="Room ID"),
    day_of_week: Optional[DayOfWeek] = Query(None, description="Filter by day"),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR)),
    db: AsyncSession = Depends(get_db)
):
    """
    Check room availability by viewing existing schedules.
    
    - Useful for instructors when planning new schedules
    """
    room_uuid = validate_uuid(room_id)
    
    schedules = await schedule_ops.get_room_schedules(db, room_uuid, day_of_week)
    
    return [
        CourseScheduleResponse(
            id=s.id,
            course_id=s.course_id,
            room_id=s.room_id,
            day_of_week=s.day_of_week,
            start_time=s.start_time,
            end_time=s.end_time,
            course_title=s.course.title if s.course else None,
            room_number=s.room.room_number if s.room else None,
            branch_name=s.room.branch.name if s.room and s.room.branch else None
        )
        for s in schedules
    ]