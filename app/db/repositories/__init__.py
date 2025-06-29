from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.course import Course
from app.models.enrollment import Enrollment

T = TypeVar('T')


class BaseRepository(Generic[T], ABC):
    """Base repository class with common database operations."""
    
    def __init__(self, session: AsyncSession, model_class: type[T]):
        self.session = session
        self.model_class = model_class
    
    async def create(self, **kwargs) -> T:
        """Create a new record."""
        instance = self.model_class(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
    
    async def get_by_id(self, id: int) -> Optional[T]:
        """Get a record by ID."""
        result = await self.session.execute(
            select(self.model_class).where(self.model_class.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all records with pagination."""
        result = await self.session.execute(
            select(self.model_class).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def update(self, id: int, **kwargs) -> Optional[T]:
        """Update a record by ID."""
        result = await self.session.execute(
            update(self.model_class)
            .where(self.model_class.id == id)
            .values(**kwargs)
            .returning(self.model_class)
        )
        return result.scalar_one_or_none()
    
    async def delete(self, id: int) -> bool:
        """Delete a record by ID."""
        result = await self.session.execute(
            delete(self.model_class).where(self.model_class.id == id)
        )
        return result.rowcount > 0
    
    async def count(self, **filters) -> int:
        """Count records with optional filters."""
        query = select(func.count(self.model_class.id))
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                query = query.where(getattr(self.model_class, key) == value)
        result = await self.session.execute(query)
        return result.scalar()
    
    async def exists(self, **filters) -> bool:
        """Check if record exists with given filters."""
        query = select(self.model_class.id)
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                query = query.where(getattr(self.model_class, key) == value)
        result = await self.session.execute(query.limit(1))
        return result.scalar_one_or_none() is not None


class UserRepository(BaseRepository[User]):
    """User repository with user-specific operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_role(self, role: str, skip: int = 0, limit: int = 100) -> List[User]:
        """Get users by role."""
        result = await self.session.execute(
            select(User).where(User.role == role).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def get_users_with_last_login(self, days: int = 30, skip: int = 0, limit: int = 100) -> List[User]:
        """Get users who logged in within the last N days."""
        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        result = await self.session.execute(
            select(User)
            .where(User.last_login_at >= cutoff_date)
            .order_by(User.last_login_at.desc())
            .offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def get_users_never_logged_in(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get users who have never logged in."""
        result = await self.session.execute(
            select(User)
            .where(User.last_login_at.is_(None))
            .order_by(User.created_at.desc())
            .offset(skip).limit(limit)
        )
        return result.scalars().all()


class CourseRepository(BaseRepository[Course]):
    """Course repository with course-specific operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Course)
    
    async def get_by_instructor(self, instructor_id: int, skip: int = 0, limit: int = 100) -> List[Course]:
        """Get courses by instructor."""
        result = await self.session.execute(
            select(Course)
            .options(selectinload(Course.instructor))
            .where(Course.instructor_id == instructor_id)
            .offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Course]:
        """Get courses by status."""
        result = await self.session.execute(
            select(Course)
            .options(selectinload(Course.instructor))
            .where(Course.status == status)
            .offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def get_published_courses(self, skip: int = 0, limit: int = 100) -> List[Course]:
        """Get published courses."""
        return await self.get_by_status("published", skip, limit)
    
    async def search_courses(self, search_term: str, skip: int = 0, limit: int = 100) -> List[Course]:
        """Search courses by title or description."""
        result = await self.session.execute(
            select(Course)
            .options(selectinload(Course.instructor))
            .where(
                Course.title.ilike(f"%{search_term}%") |
                Course.description.ilike(f"%{search_term}%")
            )
            .offset(skip).limit(limit)
        )
        return result.scalars().all()


class EnrollmentRepository(BaseRepository[Enrollment]):
    """Enrollment repository with enrollment-specific operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Enrollment)
    
    async def get_by_student(self, student_id: int) -> List[Enrollment]:
        """Get enrollments by student."""
        result = await self.session.execute(
            select(Enrollment)
            .options(
                selectinload(Enrollment.course),
                selectinload(Enrollment.student)
            )
            .where(Enrollment.student_id == student_id)
        )
        return result.scalars().all()
    
    async def get_by_course(self, course_id: int) -> List[Enrollment]:
        """Get enrollments by course."""
        result = await self.session.execute(
            select(Enrollment)
            .options(
                selectinload(Enrollment.course),
                selectinload(Enrollment.student)
            )
            .where(Enrollment.course_id == course_id)
        )
        return result.scalars().all()
    
    async def is_enrolled(self, student_id: int, course_id: int) -> bool:
        """Check if student is enrolled in course."""
        result = await self.session.execute(
            select(Enrollment.id)
            .where(
                Enrollment.student_id == student_id,
                Enrollment.course_id == course_id
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None
    
    async def get_enrollment(self, student_id: int, course_id: int) -> Optional[Enrollment]:
        """Get specific enrollment."""
        result = await self.session.execute(
            select(Enrollment)
            .where(
                Enrollment.student_id == student_id,
                Enrollment.course_id == course_id
            )
        )
        return result.scalar_one_or_none()


__all__ = [
    "BaseRepository",
    "UserRepository", 
    "CourseRepository",
    "EnrollmentRepository"
] 