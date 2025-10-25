"""Branch database operations."""

from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, exists
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.models.location import Branch, Room
from app.models.course import Course


async def create_branch(
    db: AsyncSession,
    name: str,
    address: str,
    contact_info: Optional[str] = None
) -> Branch:
    """Create a new branch."""
    try:
        branch = Branch(
            name=name,
            address=address,
            contact_info=contact_info
        )
        
        db.add(branch)
        await db.commit()
        await db.refresh(branch)
        
        return branch
        
    except IntegrityError:
        await db.rollback()
        raise ValueError(f"Branch with name '{name}' already exists")
    except SQLAlchemyError as e:
        await db.rollback()
        raise e


async def get_branch_by_id(db: AsyncSession, branch_id: UUID) -> Optional[Branch]:
    """Get branch by ID."""
    try:
        result = await db.execute(
            select(Branch).where(Branch.id == branch_id)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError:
        return None


async def get_branch_by_name(db: AsyncSession, name: str) -> Optional[Branch]:
    """Get branch by name."""
    try:
        result = await db.execute(
            select(Branch).where(Branch.name == name)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError:
        return None


async def update_branch(
    db: AsyncSession,
    branch_id: UUID,
    name: Optional[str] = None,
    address: Optional[str] = None,
    contact_info: Optional[str] = None
) -> Optional[Branch]:
    """Update a branch."""
    try:
        branch = await get_branch_by_id(db, branch_id)
        if not branch:
            return None
        
        if name is not None:
            branch.name = name
        if address is not None:
            branch.address = address
        if contact_info is not None:
            branch.contact_info = contact_info
        
        await db.commit()
        await db.refresh(branch)
        
        return branch
        
    except IntegrityError:
        await db.rollback()
        raise ValueError(f"Branch with name '{name}' already exists")
    except SQLAlchemyError:
        await db.rollback()
        return None


async def delete_branch(db: AsyncSession, branch_id: UUID) -> bool:
    """Delete a branch if no active courses or rooms."""
    try:
        # Check if branch has any rooms
        has_rooms = await db.execute(
            select(exists().where(Room.branch_id == branch_id))
        )
        if has_rooms.scalar():
            raise ValueError("Cannot delete branch with existing rooms")
        
        # Check if branch has any courses
        has_courses = await db.execute(
            select(exists().where(Course.branch_id == branch_id))
        )
        if has_courses.scalar():
            raise ValueError("Cannot delete branch with existing courses")
        
        branch = await get_branch_by_id(db, branch_id)
        if not branch:
            return False
        
        await db.delete(branch)
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False


async def list_branches(
    db: AsyncSession,
    search: Optional[str] = None
) -> Tuple[List[Branch], int]:
    """List all branches with optional search."""
    try:
        query = select(Branch)
        
        if search:
            query = query.where(
                Branch.name.ilike(f"%{search}%") | 
                Branch.address.ilike(f"%{search}%")
            )
        
        # Order by name
        query = query.order_by(Branch.name)
        
        result = await db.execute(query)
        branches = result.scalars().all()
        
        return branches, len(branches)
        
    except SQLAlchemyError:
        return [], 0


async def get_branch_statistics(db: AsyncSession, branch_id: UUID) -> dict:
    """Get statistics for a branch."""
    try:
        # Count rooms
        room_count_result = await db.execute(
            select(func.count(Room.id)).where(Room.branch_id == branch_id)
        )
        room_count = room_count_result.scalar() or 0
        
        # Count all courses for this branch
        course_count_result = await db.execute(
            select(func.count(Course.id))
            .where(Course.branch_id == branch_id)
        )
        course_count = course_count_result.scalar() or 0
        
        return {
            "room_count": room_count,
            "course_count": course_count
        }
        
    except SQLAlchemyError:
        return {
            "room_count": 0,
            "course_count": 0
        }