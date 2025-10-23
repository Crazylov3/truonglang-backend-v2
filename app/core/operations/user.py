"""User database operations."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import logging
from app.models.user import User, UserRole
from app.models.user_profile import UserProfile
from app.core.security import get_password_hash, verify_password

logger = logging.getLogger(__name__)

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email address."""
    try:
        result = await db.execute(
            select(User).options(selectinload(User.profile)).where(User.email == email)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError:
        return None


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID."""
    try:
        result = await db.execute(
            select(User).options(selectinload(User.profile)).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError:
        return None


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """Authenticate a user with email and password."""
    try:
        user = await get_user_by_email(db, email)
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        return user
    except SQLAlchemyError:
        return None


async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    first_name: str = None,
    last_name: str = None,
    role: UserRole = UserRole.STUDENT,
    date_of_birth=None
) -> User:
    """Create a new user with optional profile."""
    try:
        # Hash the password
        hashed_password = get_password_hash(password)
        
        # Create user object
        user = User(
            email=email,
            hashed_password=hashed_password,
            role=role,
            last_login_at=datetime.utcnow()  # Set last_login_at to current time
        )
        
        db.add(user)
        await db.flush()  # Get the user ID
        
        # Create user profile if names are provided
        if first_name and last_name:
            profile = UserProfile(
                user_id=user.id,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date_of_birth
            )
            db.add(profile)
        
        await db.commit()
        await db.refresh(user)
        
        # Load the profile relationship
        result = await db.execute(
            select(User).options(selectinload(User.profile)).where(User.id == user.id)
        )
        user_with_profile = result.scalar_one()
        
        return user_with_profile
        
    except SQLAlchemyError as e:
        await db.rollback()
        raise e


async def update_user_password(db: AsyncSession, email: str, new_password: str) -> bool:
    """Update user's password."""
    try:
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        user.hashed_password = get_password_hash(new_password)
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False


async def update_user_last_login(db: AsyncSession, user_id: int) -> bool:
    """Update user's last login timestamp."""
    try:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        user.last_login_at = datetime.utcnow()
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False


async def update_user_role(db: AsyncSession, email: str, new_role: UserRole) -> bool:
    """Update user's role."""
    try:
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
            
        user.role = new_role
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False


async def update_user_role_by_id(db: AsyncSession, user_id: int, new_role: UserRole) -> bool:
    """Update user's role by ID."""
    try:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
            
        user.role = new_role
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False


async def update_user_profile(
    db: AsyncSession,
    user_id: int,
    first_name: str = None,
    last_name: str = None,
    date_of_birth=None,
    avatar: str = None
) -> bool:
    """Update user profile information."""
    try:
        result = await db.execute(
            select(User).options(selectinload(User.profile)).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        # Create profile if it doesn't exist
        if not user.profile:
            if first_name and last_name:
                profile = UserProfile(
                    user_id=user.id,
                    first_name=first_name,
                    last_name=last_name,
                    date_of_birth=date_of_birth,
                    avatar=avatar
                )
                db.add(profile)
        else:
            # Update existing profile
            if first_name is not None:
                user.profile.first_name = first_name
            if last_name is not None:
                user.profile.last_name = last_name
            if date_of_birth is not None:
                user.profile.date_of_birth = date_of_birth
            if avatar is not None:
                user.profile.avatar = avatar
        
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False


async def delete_user(db: AsyncSession, email: str) -> bool:
    """Delete user and their profile."""
    try:
        result = await db.execute(
            select(User).options(selectinload(User.profile)).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.error(f"User with email {email} not found")
            return False
        
        # Delete dependent rows for NOT NULL FKs before deleting the user
        # 1) Delete enrollments and their invoices/payments
        try:
            from app.models import Enrollment
            from app.models.payment import Invoice, Payment
            enrollments_result = await db.execute(
                select(Enrollment).options(
                    selectinload(Enrollment.invoices).selectinload(Invoice.payments)
                ).where(Enrollment.student_id == user.id)
            )
            enrollments = enrollments_result.scalars().all()
            for enrollment in enrollments:
                # Delete payments for each invoice
                for invoice in list(enrollment.invoices or []):
                    for payment in list(invoice.payments or []):
                        await db.delete(payment)
                    await db.delete(invoice)
                await db.delete(enrollment)
        except Exception:
            # Log and continue to rollback in outer except if needed
            logger.error("Error deleting user enrollments/invoices/payments", exc_info=True)

        # Delete profile first if it exists (due to foreign key constraints)
        if user.profile:
            await db.delete(user.profile)
        
        await db.delete(user)
        await db.commit()
        return True
        
    except SQLAlchemyError:
        logger.error(f"Error deleting user with email {email}", exc_info=True)
        await db.rollback()
        return False


async def delete_user_by_id(db: AsyncSession, user_id: int) -> bool:
    """Delete user by ID and their profile."""
    try:
        result = await db.execute(
            select(User).options(selectinload(User.profile)).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        # Delete dependent rows for NOT NULL FKs before deleting the user
        # 1) Delete enrollments and their invoices/payments
        try:
            from app.models import Enrollment
            from app.models.payment import Invoice, Payment
            enrollments_result = await db.execute(
                select(Enrollment).options(
                    selectinload(Enrollment.invoices).selectinload(Invoice.payments)
                ).where(Enrollment.student_id == user.id)
            )
            enrollments = enrollments_result.scalars().all()
            for enrollment in enrollments:
                # Delete payments for each invoice
                for invoice in list(enrollment.invoices or []):
                    for payment in list(invoice.payments or []):
                        await db.delete(payment)
                    await db.delete(invoice)
                await db.delete(enrollment)
        except Exception:
            # Log and continue to rollback in outer except if needed
            logger.error("Error deleting user enrollments/invoices/payments", exc_info=True)

        # Delete profile first if it exists (due to foreign key constraints)
        if user.profile:
            await db.delete(user.profile)
        
        await db.delete(user)
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False


async def list_users(
    db: AsyncSession,
    role: Optional[UserRole] = None,
    limit: int = 50,
    offset: int = 0
) -> List[User]:
    """List users with optional filtering."""
    try:
        query = select(User).options(selectinload(User.profile)).order_by(User.created_at.desc())
        
        if role:
            query = query.where(User.role == role)
        
        query = query.offset(offset).limit(limit)
        
        result = await db.execute(query)
        users = result.scalars().all()
        return users
        
    except SQLAlchemyError:
        return []


async def count_users(db: AsyncSession, role: Optional[UserRole] = None) -> int:
    """Count users with optional filtering."""
    try:
        query = select(func.count(User.id))
        
        if role:
            query = query.where(User.role == role)
        
        result = await db.execute(query)
        return result.scalar() or 0
        
    except SQLAlchemyError:
        return 0


async def search_users(
    db: AsyncSession,
    email: str = None,
    name: str = None,
    role: UserRole = None
) -> List[User]:
    """Search users by various criteria."""
    try:
        from sqlalchemy import or_, and_
        query = select(User).options(selectinload(User.profile))
        conditions = []
        
        if email:
            conditions.append(User.email.ilike(f"%{email}%"))
        
        if name:
            # Search in profile names
            profile_condition = or_(
                User.profile.has(UserProfile.first_name.ilike(f"%{name}%")),
                User.profile.has(UserProfile.last_name.ilike(f"%{name}%"))
            )
            conditions.append(profile_condition)
        
        if role:
            conditions.append(User.role == role)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await db.execute(query.order_by(User.created_at.desc()))
        users = result.scalars().all()
        return users
        
    except SQLAlchemyError:
        return []
