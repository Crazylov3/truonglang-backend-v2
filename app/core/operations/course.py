"""Course database operations."""

from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from decimal import Decimal

from app.models.course import Course
from app.models.user import User
from app.models.enrollment import Enrollment


async def create_course(
    db: AsyncSession,
    title: str,
    description: Optional[str],
    creator_id: int,
    price: Optional[Decimal] = None
) -> Course:
    """Create a new course."""
    try:
        new_course = Course(
            title=title,
            description=description,
            creator_id=creator_id,
            price=price
        )
        
        db.add(new_course)
        await db.commit()
        await db.refresh(new_course)
        
        # Reload the course with relationships
        result = await db.execute(
            select(Course).options(selectinload(Course.enrollments)).where(Course.id == new_course.id)
        )
        course_with_enrollments = result.scalar_one()
        
        return course_with_enrollments
        
    except SQLAlchemyError as e:
        await db.rollback()
        raise e


async def get_course_by_id(db: AsyncSession, course_id: int) -> Optional[Course]:
    """Get course by ID with relationships."""
    try:
        result = await db.execute(
            select(Course).options(
                selectinload(Course.creator),
                selectinload(Course.enrollments)
            ).where(Course.id == course_id)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError:
        return None


async def update_course(
    db: AsyncSession,
    course_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    price: Optional[Decimal] = None
) -> Optional[Course]:
    """Update a course."""
    try:
        result = await db.execute(select(Course).where(Course.id == course_id))
        course = result.scalar_one_or_none()
        
        if not course:
            return None
        
        # Update fields if provided
        if title is not None:
            course.title = title
        if description is not None:
            course.description = description
        if price is not None:
            course.price = price
        
        await db.commit()
        await db.refresh(course)
        
        # Reload the course with relationships
        result = await db.execute(
            select(Course).options(selectinload(Course.enrollments)).where(Course.id == course_id)
        )
        course_with_enrollments = result.scalar_one()
        
        return course_with_enrollments
        
    except SQLAlchemyError:
        await db.rollback()
        return None


async def delete_course(db: AsyncSession, course_id: int) -> bool:
    """Delete a course."""
    try:
        result = await db.execute(select(Course).where(Course.id == course_id))
        course = result.scalar_one_or_none()
        
        if not course:
            return False
        
        await db.delete(course)
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False


async def list_courses(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    creator_id: Optional[int] = None
) -> Tuple[List[Course], int]:
    """List courses with pagination."""
    try:
        # Build query with preloaded relationships
        query = select(Course).options(
            selectinload(Course.creator),
            selectinload(Course.enrollments)
        )
        
        # Apply filters
        if creator_id:
            query = query.where(Course.creator_id == creator_id)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        result = await db.execute(query)
        courses = result.scalars().all()
        
        return courses, total
        
    except SQLAlchemyError:
        return [], 0


async def get_course_students(
    db: AsyncSession,
    course_id: int,
    page: int = 1,
    per_page: int = 10
) -> Tuple[List[dict], int]:
    """Get students enrolled in a course with pagination."""
    try:
        # Count total students
        count_query = (
            select(Enrollment.id)
            .where(Enrollment.course_id == course_id)
            .where(Enrollment.is_active == True)
        )
        count_result = await db.execute(count_query)
        total = len(count_result.all())
        
        # Get enrolled students with profiles (paginated)
        offset = (page - 1) * per_page
        query = (
            select(User, Enrollment.enrolled_at, Enrollment.is_active)
            .join(Enrollment, User.id == Enrollment.student_id)
            .options(selectinload(User.profile))
            .where(Enrollment.course_id == course_id)
            .where(Enrollment.is_active == True)
            .offset(offset)
            .limit(per_page)
        )
        
        result = await db.execute(query)
        students_data = result.all()
        
        students = []
        for student, enrolled_at, is_active in students_data:
            students.append({
                'id': student.id,
                'email': student.email,
                'full_name': student.full_name,
                'enrolled_at': enrolled_at,
                'is_active': is_active
            })
        
        return students, total
        
    except SQLAlchemyError:
        return [], 0


async def check_course_ownership(db: AsyncSession, course_id: int, user_id: int) -> bool:
    """Check if user is the creator of the course."""
    try:
        result = await db.execute(
            select(Course.creator_id).where(Course.id == course_id)
        )
        creator_id = result.scalar_one_or_none()
        return creator_id == user_id if creator_id else False
    except SQLAlchemyError:
        return False


async def get_course_title(db: AsyncSession, course_id: int) -> Optional[str]:
    """Get course title by ID."""
    try:
        result = await db.execute(
            select(Course.title).where(Course.id == course_id)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError:
        return None
