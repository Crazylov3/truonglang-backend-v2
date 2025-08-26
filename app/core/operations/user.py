"""User database operations."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from passlib.context import CryptContext
from datetime import datetime

from app.models.user import User, UserRole
from app.models.user_profile import UserProfile

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


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
        hashed_password = hash_password(password)
        
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
        
        user.hashed_password = hash_password(new_password)
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
            return False
        
        # Delete profile first if it exists (due to foreign key constraints)
        if user.profile:
            await db.delete(user.profile)
        
        await db.delete(user)
        await db.commit()
        return True
        
    except SQLAlchemyError:
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
        query = select(User).options(selectinload(User.profile))
        conditions = []
        
        if email:
            conditions.append(User.email.ilike(f"%{email}%"))
        
        if name:
            # Search in profile names
            profile_condition = (
                User.profile.has(UserProfile.first_name.ilike(f"%{name}%")) |
                User.profile.has(UserProfile.last_name.ilike(f"%{name}%"))
            )
            conditions.append(profile_condition)
        
        if role:
            conditions.append(User.role == role)
        
        if conditions:
            query = query.where(*conditions)
        
        result = await db.execute(query.order_by(User.created_at.desc()))
        users = result.scalars().all()
        return users
        
    except SQLAlchemyError:
        return []
