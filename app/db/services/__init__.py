from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import redis.asyncio as redis

from app.core.security import get_password_hash, verify_password
from app.core.email import email_service
from app.db.repositories import UserRepository, CourseRepository, EnrollmentRepository
from app.models.user import User, UserRole
from app.models.course import Course, CourseStatus
from app.models.enrollment import Enrollment
from app.schemas.common import PaginatedResponse


class BaseService:
    """Base service class."""
    
    def __init__(self, session: AsyncSession):
        self.session = session


class AuthService(BaseService):
    """Authentication and authorization service."""
    
    def __init__(self, session: AsyncSession, redis_client: redis.Redis):
        super().__init__(session)
        self.redis_client = redis_client
        self.user_repo = UserRepository(session)
    
    async def register_user(self, email: str, password: str, **kwargs) -> Dict[str, Any]:
        """Store user registration data temporarily and send verification email."""
        # Check if user already exists
        if await self.user_repo.get_by_email(email):
            raise ValueError("Email already registered")
        
        # Generate OTP and store registration data in Redis temporarily
        otp = email_service.generate_otp()
        
        # Store user registration data with OTP for 10 minutes
        registration_data = {
            "email": email,
            "password": password,
            "first_name": kwargs.get("first_name"),
            "last_name": kwargs.get("last_name"),
            "otp": otp
        }
        
        await self.redis_client.setex(
            f"registration:{email}", 
            600,  # 10 minutes
            str(registration_data)
        )
        
        # Send verification email
        email_sent = await email_service.send_verification_email(email, otp)
        
        return {
            "message": "Registration initiated. Please verify your email to complete account creation.",
            "email_sent": email_sent
        }
    
    async def verify_email_and_create_user(self, email: str, otp: str) -> Dict[str, Any]:
        """Verify email OTP and create user account."""
        # Get stored registration data
        registration_key = f"registration:{email}"
        stored_data = await self.redis_client.get(registration_key)
        
        if not stored_data:
            raise ValueError("Registration expired or not found. Please register again.")
        
        # Parse registration data (in a real app, use proper serialization like JSON)
        import ast
        try:
            registration_data = ast.literal_eval(stored_data)
        except:
            raise ValueError("Invalid registration data")
        
        # Verify OTP
        if registration_data.get("otp") != otp:
            raise ValueError("Invalid OTP")
        
        # Create user account
        hashed_password = get_password_hash(registration_data["password"])
        user = await self.user_repo.create(
            email=email,
            hashed_password=hashed_password,
            first_name=registration_data.get("first_name"),
            last_name=registration_data.get("last_name")
        )
        
        # Remove registration data from Redis
        await self.redis_client.delete(registration_key)
        
        # Send welcome email
        await email_service.send_welcome_email(user.email, user.full_name)
        
        return {
            "message": "Account created successfully. You can now log in.",
            "user_id": user.id
        }
    
    async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user and return user data (for session-based auth)."""
        user = await self.user_repo.get_by_email(email)
        
        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")
        
        # Update last login time
        await self.user_repo.update(user.id, last_login_at=datetime.utcnow())
        
        # Return user data (session management handled at router level)
        return {
            "message": "Authentication successful",
            "user": user
        }


class UserService(BaseService):
    """User management service."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.user_repo = UserRepository(session)
    
    async def get_user_profile(self, user_id: int) -> Optional[User]:
        """Get user profile with additional info."""
        return await self.user_repo.get_by_id(user_id)
    
    async def update_user_profile(self, user_id: int, **kwargs) -> Optional[User]:
        """Update user profile."""
        return await self.user_repo.update(user_id, **kwargs)
    
    async def get_users_paginated(self, skip: int = 0, limit: int = 100, 
                                role: Optional[UserRole] = None) -> Dict[str, Any]:
        """Get paginated list of users."""
        if role:
            users = await self.user_repo.get_by_role(role.value, skip, limit)
            total = await self.user_repo.count(role=role.value)
        else:
            users = await self.user_repo.get_all(skip, limit)
            total = await self.user_repo.count()
        
        page = skip // limit + 1 if limit > 0 else 1
        pages = (total + limit - 1) // limit if total > 0 and limit > 0 else 0
        
        return {
            "items": users,
            "total": total,
            "page": page,
            "per_page": limit,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1
        }
    
    async def delete_user(self, user_id: int) -> bool:
        """Delete a user."""
        return await self.user_repo.delete(user_id)


class CourseService(BaseService):
    """Course management service."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.course_repo = CourseRepository(session)
    
    async def create_course(self, instructor_id: int, **kwargs) -> Course:
        """Create a new course."""
        return await self.course_repo.create(instructor_id=instructor_id, **kwargs)
    
    async def get_courses_paginated(self, skip: int = 0, limit: int = 100,
                                  status: Optional[CourseStatus] = None,
                                  instructor_id: Optional[int] = None,
                                  search: Optional[str] = None) -> Dict[str, Any]:
        """Get paginated courses with filters."""
        if search:
            courses = await self.course_repo.search_courses(search, skip, limit)
            total = len(courses)  # Simple count for search
        elif status:
            courses = await self.course_repo.get_by_status(status.value, skip, limit)
            total = await self.course_repo.count(status=status.value)
        elif instructor_id:
            courses = await self.course_repo.get_by_instructor(instructor_id, skip, limit)
            total = await self.course_repo.count(instructor_id=instructor_id)
        else:
            courses = await self.course_repo.get_all(skip, limit)
            total = await self.course_repo.count()
        
        page = skip // limit + 1 if limit > 0 else 1
        pages = (total + limit - 1) // limit if total > 0 and limit > 0 else 0
        
        return {
            "items": courses,
            "total": total,
            "page": page,
            "per_page": limit,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1
        }
    
    async def update_course(self, course_id: int, **kwargs) -> Optional[Course]:
        """Update a course."""
        return await self.course_repo.update(course_id, **kwargs)
    
    async def delete_course(self, course_id: int) -> bool:
        """Delete a course."""
        return await self.course_repo.delete(course_id)


class EnrollmentService(BaseService):
    """Enrollment management service."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.enrollment_repo = EnrollmentRepository(session)
        self.course_repo = CourseRepository(session)
    
    async def enroll_student(self, student_id: int, course_id: int) -> Enrollment:
        """Enroll a student in a course."""
        # Check if already enrolled
        if await self.enrollment_repo.is_enrolled(student_id, course_id):
            raise ValueError("Already enrolled in this course")
        
        # Check if course exists and is published
        course = await self.course_repo.get_by_id(course_id)
        if not course or course.status != CourseStatus.PUBLISHED:
            raise ValueError("Course not available for enrollment")
        
        return await self.enrollment_repo.create(
            student_id=student_id,
            course_id=course_id
        )
    
    async def unenroll_student(self, student_id: int, course_id: int) -> bool:
        """Unenroll a student from a course."""
        enrollment = await self.enrollment_repo.get_enrollment(student_id, course_id)
        if not enrollment:
            raise ValueError("Not enrolled in this course")
        
        return await self.enrollment_repo.delete(enrollment.id)
    
    async def get_student_enrollments(self, student_id: int) -> List[Enrollment]:
        """Get all enrollments for a student."""
        return await self.enrollment_repo.get_by_student(student_id)
    
    async def get_course_enrollments(self, course_id: int) -> List[Enrollment]:
        """Get all enrollments for a course."""
        return await self.enrollment_repo.get_by_course(course_id)


__all__ = [
    "BaseService",
    "AuthService",
    "UserService", 
    "CourseService",
    "EnrollmentService"
] 