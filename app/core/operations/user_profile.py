"""User profile database operations."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from datetime import date

from app.models.user_profile import UserProfile


async def create_user_profile(
    db: AsyncSession,
    user_id: int,
    first_name: str,
    last_name: str,
    date_of_birth: Optional[date] = None,
    avatar: Optional[str] = None
) -> Optional[UserProfile]:
    """Create a new user profile."""
    try:
        profile = UserProfile(
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            avatar=avatar
        )
        
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        
        return profile
        
    except SQLAlchemyError:
        await db.rollback()
        return None


async def get_user_profile(db: AsyncSession, user_id: int) -> Optional[UserProfile]:
    """Get user profile by user ID."""
    try:
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError:
        return None


async def update_user_profile(
    db: AsyncSession,
    user_id: int,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    date_of_birth: Optional[date] = None,
    avatar: Optional[str] = None
) -> bool:
    """Update user profile."""
    try:
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            return False
        
        # Update fields if provided
        if first_name is not None:
            profile.first_name = first_name
        if last_name is not None:
            profile.last_name = last_name
        if date_of_birth is not None:
            profile.date_of_birth = date_of_birth
        if avatar is not None:
            profile.avatar = avatar
        
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False


async def delete_user_profile(db: AsyncSession, user_id: int) -> bool:
    """Delete user profile."""
    try:
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            return False
        
        await db.delete(profile)
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False
