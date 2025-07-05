"""Enrollment database operations."""

from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

from app.models.enrollment import Enrollment
import logging

logger = logging.getLogger(__name__)


async def create_enrollment(
    db: AsyncSession,
    student_id: int,
    course_id: int
) -> Optional[Enrollment]:
    """Create a new enrollment."""
    try:
        # Check if already enrolled
        existing_enrollment = await db.execute(
            select(Enrollment).where(
                and_(
                    Enrollment.student_id == student_id,
                    Enrollment.course_id == course_id
                )
            )
        )
        
        if existing_enrollment.scalar_one_or_none():
            return None  # Already enrolled
        
        # Create enrollment
        enrollment = Enrollment(
            student_id=student_id,
            course_id=course_id,
            is_active=True
        )
        
        db.add(enrollment)
        await db.commit()
        await db.refresh(enrollment)
        
        return enrollment
        
    except SQLAlchemyError:
        await db.rollback()
        return None


async def get_enrollment(
    db: AsyncSession,
    student_id: int,
    course_id: int
) -> Optional[Enrollment]:
    """Get enrollment by student and course."""
    try:
        result = await db.execute(
            select(Enrollment).where(
                and_(
                    Enrollment.student_id == student_id,
                    Enrollment.course_id == course_id
                )
            )
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError:
        return None


async def deactivate_enrollment(
    db: AsyncSession,
    student_id: int,
    course_id: int
) -> bool:
    """Deactivate an enrollment (unenroll)."""
    try:
        result = await db.execute(
            select(Enrollment).where(
                and_(
                    Enrollment.student_id == student_id,
                    Enrollment.course_id == course_id
                )
            )
        )
        enrollment = result.scalar_one_or_none()
        
        if not enrollment:
            return False
        
        # Deactivate enrollment instead of deleting (to preserve history)
        enrollment.is_active = False
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False


async def get_user_enrollments(
    db: AsyncSession,
    student_id: int,
    active_only: bool = True,
    page: int = 1,
    per_page: int = 10
) -> Tuple[List[Enrollment], int]:
    """Get all enrollments for a user with pagination."""
    try:
        # Base query
        query = (
            select(Enrollment)
            .options(selectinload(Enrollment.course))
            .where(Enrollment.student_id == student_id)
        )

        if active_only:
            query = query.where(Enrollment.is_active == True)
        
        # Get total count
        count_query = select(func.count()).select_from(
            select(Enrollment.id)
            .where(Enrollment.student_id == student_id)
        )
        if active_only:
            count_query = count_query.where(Enrollment.is_active == True)
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # Apply pagination and ordering
        query = query.order_by(Enrollment.enrolled_at.desc())
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        result = await db.execute(query)
        enrollments = result.scalars().all()
        return enrollments, total
        
    except SQLAlchemyError as e:
        return [], 0


async def get_course_enrollments(
    db: AsyncSession,
    course_id: int,
    active_only: bool = True,
    page: int = 1,
    per_page: int = 10
) -> Tuple[List[Enrollment], int]:
    """Get all enrollments for a course with pagination."""
    try:
        # Base query
        query = (
            select(Enrollment)
            .options(selectinload(Enrollment.student))
            .where(Enrollment.course_id == course_id)
        )
        
        if active_only:
            query = query.where(Enrollment.is_active == True)
        
        # Get total count
        count_query = select(func.count()).select_from(
            select(Enrollment.id)
            .where(Enrollment.course_id == course_id)
        )
        if active_only:
            count_query = count_query.where(Enrollment.is_active == True)
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # Apply pagination and ordering
        query = query.order_by(Enrollment.enrolled_at.desc())
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        result = await db.execute(query)
        enrollments = result.scalars().all()
        return enrollments, total
        
    except SQLAlchemyError:
        return [], 0


async def check_enrollment_exists(
    db: AsyncSession,
    student_id: int,
    course_id: int,
    active_only: bool = True
) -> bool:
    """Check if enrollment exists."""
    try:
        query = select(Enrollment.id).where(
            and_(
                Enrollment.student_id == student_id,
                Enrollment.course_id == course_id
            )
        )
        
        if active_only:
            query = query.where(Enrollment.is_active == True)
        
        result = await db.execute(query)
        return result.scalar_one_or_none() is not None
        
    except SQLAlchemyError:
        return False 