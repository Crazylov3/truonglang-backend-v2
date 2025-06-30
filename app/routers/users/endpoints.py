import os
from datetime import datetime
from fastapi import HTTPException, status, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole, UserAvatar
from app.schemas.users import UserResponse, UserUpdate, UserProfile
from app.core.decorators import authentication_required
from app.core.deps import get_current_user
from app.core.media.io_helper import load_image_from_disk, from_image_to_base64, save_image_to_disk, from_base64_to_image


async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated user's profile."""

    result = await db.execute(select(UserAvatar).where(UserAvatar.user_id == current_user.id))
    avatar = result.scalar_one_or_none()
    
    user_profile = UserProfile(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        bio=current_user.bio,
        role=current_user.role,
        last_login_at=current_user.last_login_at,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        full_name=current_user.full_name,
        avatar=from_image_to_base64(load_image_from_disk(avatar.avatar_url)) if avatar else None
    )
    return user_profile


async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's profile."""
    for field, value in user_update.dict(exclude_unset=True).items():
        if hasattr(current_user, field):
            setattr(current_user, field, value)
    if user_update.avatar:
        save_image_path = os.path.join(settings.MEDIA_ROOT, f"avatars/{current_user.id}.png")
        save_image_to_disk(from_base64_to_image(user_update.avatar), save_image_path)
        
        
        result = await db.execute(select(UserAvatar).where(UserAvatar.user_id == current_user.id))
        avatar = result.scalar_one_or_none()
        
        if avatar:
            avatar.avatar_url = save_image_path
            avatar.updated_at = datetime.utcnow()
        else:
            avatar = UserAvatar(user_id=current_user.id, avatar_url=save_image_path)
            db.add(avatar)
    
    await db.commit()
    await db.refresh(current_user)
    
    return UserResponse.from_orm(current_user)

@authentication_required(allowed_role=UserRole.STAFF)
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    role: Optional[UserRole] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get all users (staff/admin only)."""
    query = select(User)
    
    if role:
        query = query.where(User.role == role)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    
    count_query = select(func.count(User.id))
    if role:
        count_query = count_query.where(User.role == role)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    return {
        "users": [UserResponse.from_orm(user) for user in users],
        "total": total,
        "skip": skip,
        "limit": limit
    }
@authentication_required(allowed_role=UserRole.STAFF)
async def get_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get user by ID (staff/admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.from_orm(user)


@authentication_required(allowed_role=UserRole.ADMIN)
async def update_user_role(
    user_id: int,
    new_role: UserRole,
    db: AsyncSession = Depends(get_db),
):
    """Update user role (admin only)."""
    
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.role = new_role
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.from_orm(user)

@authentication_required(allowed_role=UserRole.ADMIN)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete user (staff/admin only)."""
    
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    await db.delete(user)
    await db.commit()
    
    return {"message": "User deleted successfully"}