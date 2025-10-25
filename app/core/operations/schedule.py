"""Course schedule operations."""

from typing import List, Optional, Tuple
from uuid import UUID
from datetime import time
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Course, Room, Branch
from app.models.location import CourseSchedule, DayOfWeek
from app.models.user import User, UserRole
import logging

logger = logging.getLogger(__name__)


async def create_schedule(
    db: AsyncSession,
    course_id: UUID,
    room_id: UUID,
    day_of_week: DayOfWeek,
    start_time: time,
    end_time: time
) -> CourseSchedule:
    """Create a new course schedule."""
    # Validate course exists
    course = await db.get(Course, course_id)
    if not course:
        raise ValueError("Course not found")
    
    # Validate room exists
    room = await db.get(Room, room_id)
    if not room:
        raise ValueError("Room not found")
    
    # Check for time conflicts in the same room
    conflict = await check_room_schedule_conflict(
        db, room_id, day_of_week, start_time, end_time
    )
    if conflict:
        raise ValueError(
            f"Room is already scheduled for course '{conflict.course.title}' "
            f"on {day_of_week.value} from {conflict.start_time} to {conflict.end_time}"
        )
    
    # Create schedule
    schedule = CourseSchedule(
        course_id=course_id,
        room_id=room_id,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time
    )
    
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    
    return schedule


async def update_schedule(
    db: AsyncSession,
    schedule_id: UUID,
    room_id: Optional[UUID] = None,
    day_of_week: Optional[DayOfWeek] = None,
    start_time: Optional[time] = None,
    end_time: Optional[time] = None
) -> Optional[CourseSchedule]:
    """Update a course schedule."""
    schedule = await db.get(CourseSchedule, schedule_id)
    if not schedule:
        return None
    
    # Prepare update values
    update_room = room_id if room_id is not None else schedule.room_id
    update_day = day_of_week if day_of_week is not None else schedule.day_of_week
    update_start = start_time if start_time is not None else schedule.start_time
    update_end = end_time if end_time is not None else schedule.end_time
    
    # Check if room exists (if changing room)
    if room_id and room_id != schedule.room_id:
        room = await db.get(Room, room_id)
        if not room:
            raise ValueError("Room not found")
    
    # Check for conflicts (excluding current schedule)
    conflict = await check_room_schedule_conflict(
        db, update_room, update_day, update_start, update_end,
        exclude_schedule_id=schedule_id
    )
    if conflict:
        raise ValueError(
            f"Room is already scheduled for course '{conflict.course.title}' "
            f"on {update_day.value} from {conflict.start_time} to {conflict.end_time}"
        )
    
    # Update schedule
    if room_id is not None:
        schedule.room_id = room_id
    if day_of_week is not None:
        schedule.day_of_week = day_of_week
    if start_time is not None:
        schedule.start_time = start_time
    if end_time is not None:
        schedule.end_time = end_time
    
    await db.commit()
    await db.refresh(schedule)
    
    return schedule


async def delete_schedule(db: AsyncSession, schedule_id: UUID) -> bool:
    """Delete a course schedule."""
    schedule = await db.get(CourseSchedule, schedule_id)
    if not schedule:
        return False
    
    await db.delete(schedule)
    await db.commit()
    
    return True


async def get_schedule_by_id(
    db: AsyncSession,
    schedule_id: UUID
) -> Optional[CourseSchedule]:
    """Get a schedule by ID with related data."""
    result = await db.execute(
        select(CourseSchedule)
        .options(
            selectinload(CourseSchedule.course),
            selectinload(CourseSchedule.room).selectinload(Room.branch)
        )
        .where(CourseSchedule.id == schedule_id)
    )
    return result.scalar_one_or_none()


async def get_course_schedules(
    db: AsyncSession,
    course_id: UUID
) -> List[CourseSchedule]:
    """Get all schedules for a course."""
    result = await db.execute(
        select(CourseSchedule)
        .options(
            selectinload(CourseSchedule.course),
            selectinload(CourseSchedule.room).selectinload(Room.branch)
        )
        .where(CourseSchedule.course_id == course_id)
        .order_by(
            CourseSchedule.day_of_week,
            CourseSchedule.start_time
        )
    )
    return list(result.scalars().all())


async def get_room_schedules(
    db: AsyncSession,
    room_id: UUID,
    day_of_week: Optional[DayOfWeek] = None
) -> List[CourseSchedule]:
    """Get all schedules for a room, optionally filtered by day."""
    query = select(CourseSchedule).options(
        selectinload(CourseSchedule.course),
        selectinload(CourseSchedule.room).selectinload(Room.branch)
    ).where(CourseSchedule.room_id == room_id)
    
    if day_of_week:
        query = query.where(CourseSchedule.day_of_week == day_of_week)
    
    query = query.order_by(CourseSchedule.start_time)
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_branch_schedules(
    db: AsyncSession,
    branch_id: UUID,
    day_of_week: Optional[DayOfWeek] = None
) -> List[CourseSchedule]:
    """Get all schedules for a branch, optionally filtered by day."""
    query = (
        select(CourseSchedule)
        .join(Room)
        .options(
            selectinload(CourseSchedule.course),
            selectinload(CourseSchedule.room).selectinload(Room.branch)
        )
        .where(Room.branch_id == branch_id)
    )
    
    if day_of_week:
        query = query.where(CourseSchedule.day_of_week == day_of_week)
    
    query = query.order_by(
        CourseSchedule.day_of_week,
        CourseSchedule.start_time
    )
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_instructor_schedules(
    db: AsyncSession,
    instructor_id: UUID,
    day_of_week: Optional[DayOfWeek] = None
) -> List[CourseSchedule]:
    """Get all schedules for courses taught by an instructor."""
    query = (
        select(CourseSchedule)
        .join(Course)
        .options(
            selectinload(CourseSchedule.course),
            selectinload(CourseSchedule.room).selectinload(Room.branch)
        )
        .where(Course.creator_id == instructor_id)
    )
    
    if day_of_week:
        query = query.where(CourseSchedule.day_of_week == day_of_week)
    
    query = query.order_by(
        CourseSchedule.day_of_week,
        CourseSchedule.start_time
    )
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def check_room_schedule_conflict(
    db: AsyncSession,
    room_id: UUID,
    day_of_week: DayOfWeek,
    start_time: time,
    end_time: time,
    exclude_schedule_id: Optional[UUID] = None
) -> Optional[CourseSchedule]:
    """Check if there's a schedule conflict for a room."""
    query = select(CourseSchedule).options(
        selectinload(CourseSchedule.course)
    ).where(
        and_(
            CourseSchedule.room_id == room_id,
            CourseSchedule.day_of_week == day_of_week,
            or_(
                # New schedule starts during existing schedule
                and_(
                    CourseSchedule.start_time <= start_time,
                    CourseSchedule.end_time > start_time
                ),
                # New schedule ends during existing schedule
                and_(
                    CourseSchedule.start_time < end_time,
                    CourseSchedule.end_time >= end_time
                ),
                # New schedule completely contains existing schedule
                and_(
                    start_time <= CourseSchedule.start_time,
                    end_time >= CourseSchedule.end_time
                )
            )
        )
    )
    
    if exclude_schedule_id:
        query = query.where(CourseSchedule.id != exclude_schedule_id)
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_week_schedule(
    db: AsyncSession,
    branch_id: Optional[UUID] = None,
    room_id: Optional[UUID] = None,
    instructor_id: Optional[UUID] = None
) -> dict:
    """Get weekly schedule view."""
    query = (
        select(CourseSchedule)
        .options(
            selectinload(CourseSchedule.course),
            selectinload(CourseSchedule.room).selectinload(Room.branch)
        )
    )
    
    if branch_id:
        query = query.join(Room).where(Room.branch_id == branch_id)
    elif room_id:
        query = query.where(CourseSchedule.room_id == room_id)
    elif instructor_id:
        query = query.join(Course).where(Course.creator_id == instructor_id)
    
    result = await db.execute(query)
    schedules = result.scalars().all()
    logger.info(f"Schedules: {schedules}")
    
    # Group by day of week
    week_schedule = {
        "monday": [],
        "tuesday": [],
        "wednesday": [],
        "thursday": [],
        "friday": [],
        "saturday": [],
        "sunday": []
    }
    
    for schedule in schedules:
        day_key = schedule.day_of_week.value.lower()
        week_schedule[day_key].append(schedule)
    
    # Sort each day by start time
    for day in week_schedule:
        week_schedule[day].sort(key=lambda s: s.start_time)
    
    return week_schedule


async def get_week_schedule_for_courses(
    db: AsyncSession,
    course_ids: List[UUID],
    branch_id: Optional[UUID] = None,
    room_id: Optional[UUID] = None
) -> dict:
    """Get weekly schedule view for specific courses."""
    query = (
        select(CourseSchedule)
        .options(
            selectinload(CourseSchedule.course),
            selectinload(CourseSchedule.room).selectinload(Room.branch)
        )
        .where(CourseSchedule.course_id.in_(course_ids))
    )
    
    if branch_id:
        query = query.join(Room).where(Room.branch_id == branch_id)
    elif room_id:
        query = query.where(CourseSchedule.room_id == room_id)
    
    result = await db.execute(query)
    schedules = result.scalars().all()
    
    # Group by day of week
    week_schedule = {
        "monday": [],
        "tuesday": [],
        "wednesday": [],
        "thursday": [],
        "friday": [],
        "saturday": [],
        "sunday": []
    }
    
    for schedule in schedules:
        day_key = schedule.day_of_week.value.lower()
        week_schedule[day_key].append(schedule)
    
    # Sort each day by start time
    for day in week_schedule:
        week_schedule[day].sort(key=lambda s: s.start_time)
    
    return week_schedule


async def bulk_create_schedules(
    db: AsyncSession,
    course_id: UUID,
    schedules: List[dict]
) -> List[CourseSchedule]:
    """Create multiple schedules for a course."""
    # Validate course exists
    course = await db.get(Course, course_id)
    if not course:
        raise ValueError("Course not found")
    
    created_schedules = []
    
    for schedule_data in schedules:
        # Check each schedule for conflicts
        conflict = await check_room_schedule_conflict(
            db,
            schedule_data["room_id"],
            schedule_data["day_of_week"],
            schedule_data["start_time"],
            schedule_data["end_time"]
        )
        if conflict:
            raise ValueError(
                f"Room conflict on {schedule_data['day_of_week'].value}: "
                f"Room already scheduled for '{conflict.course.title}'"
            )
        
        schedule = CourseSchedule(
            course_id=course_id,
            room_id=schedule_data["room_id"],
            day_of_week=schedule_data["day_of_week"],
            start_time=schedule_data["start_time"],
            end_time=schedule_data["end_time"]
        )
        
        db.add(schedule)
        created_schedules.append(schedule)
    
    await db.commit()
    
    # Refresh all schedules
    for schedule in created_schedules:
        await db.refresh(schedule)
    
    return created_schedules