"""Room database operations."""

from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, exists, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.models.location import Room, Branch, CourseSchedule


async def create_room(
    db: AsyncSession,
    branch_id: UUID,
    room_number: str,
    capacity: Optional[int] = None
) -> Room:
    """Create a new room."""
    try:
        # Verify branch exists
        branch_exists = await db.execute(
            select(exists().where(Branch.id == branch_id))
        )
        if not branch_exists.scalar():
            raise ValueError(f"Branch with ID {branch_id} does not exist")
        
        room = Room(
            branch_id=branch_id,
            room_number=room_number,
            capacity=capacity
        )
        
        db.add(room)
        await db.commit()
        await db.refresh(room)
        
        # Load with relationships
        result = await db.execute(
            select(Room)
            .options(selectinload(Room.branch))
            .where(Room.id == room.id)
        )
        return result.scalar_one()
        
    except IntegrityError:
        await db.rollback()
        raise ValueError(f"Room '{room_number}' already exists in this branch")
    except SQLAlchemyError as e:
        await db.rollback()
        raise e


async def get_room_by_id(db: AsyncSession, room_id: UUID) -> Optional[Room]:
    """Get room by ID with branch info."""
    try:
        result = await db.execute(
            select(Room)
            .options(selectinload(Room.branch))
            .where(Room.id == room_id)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError:
        return None


async def get_room_by_branch_and_number(
    db: AsyncSession, 
    branch_id: UUID, 
    room_number: str
) -> Optional[Room]:
    """Get room by branch ID and room number."""
    try:
        result = await db.execute(
            select(Room)
            .where(
                and_(
                    Room.branch_id == branch_id,
                    Room.room_number == room_number
                )
            )
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError:
        return None


async def update_room(
    db: AsyncSession,
    room_id: UUID,
    room_number: Optional[str] = None,
    capacity: Optional[int] = None
) -> Optional[Room]:
    """Update a room."""
    try:
        room = await get_room_by_id(db, room_id)
        if not room:
            return None
        
        if room_number is not None:
            room.room_number = room_number
        if capacity is not None:
            room.capacity = capacity
        
        await db.commit()
        await db.refresh(room)
        
        # Reload with relationships
        return await get_room_by_id(db, room_id)
        
    except IntegrityError:
        await db.rollback()
        raise ValueError(f"Room '{room_number}' already exists in this branch")
    except SQLAlchemyError:
        await db.rollback()
        return None


async def delete_room(db: AsyncSession, room_id: UUID) -> bool:
    """Delete a room if no scheduled courses."""
    try:
        # Check if room has any scheduled courses
        has_schedules = await db.execute(
            select(exists().where(CourseSchedule.room_id == room_id))
        )
        if has_schedules.scalar():
            raise ValueError("Cannot delete room with scheduled courses")
        
        room = await get_room_by_id(db, room_id)
        if not room:
            return False
        
        await db.delete(room)
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False


async def list_rooms(
    db: AsyncSession,
    branch_id: Optional[UUID] = None,
    search: Optional[str] = None
) -> Tuple[List[Room], int]:
    """List all rooms with optional filtering and search."""
    try:
        query = select(Room).options(selectinload(Room.branch))
        
        if branch_id:
            query = query.where(Room.branch_id == branch_id)
        
        if search:
            query = query.where(Room.room_number.ilike(f"%{search}%"))
        
        # Order by branch and room number
        query = query.order_by(Room.branch_id, Room.room_number)
        
        result = await db.execute(query)
        rooms = result.scalars().all()
        
        return rooms, len(rooms)
        
    except SQLAlchemyError:
        return [], 0


async def get_room_statistics(db: AsyncSession, room_id: UUID) -> dict:
    """Get statistics for a room."""
    try:
        # Count scheduled courses
        schedule_count_result = await db.execute(
            select(func.count(CourseSchedule.id))
            .where(CourseSchedule.room_id == room_id)
        )
        schedule_count = schedule_count_result.scalar() or 0
        
        return {
            "schedule_count": schedule_count
        }
        
    except SQLAlchemyError:
        return {
            "schedule_count": 0
        }