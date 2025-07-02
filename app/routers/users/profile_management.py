import os
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.user_profile import UserProfile as UserProfileModel
from app.schemas.users.user_schemas import (
    UserProfileUpdate,
    UserInfo,
    UserProfile,
)
from app.core.decorators import csrf_protect
from app.core.deps import get_current_user
from app.core.media.io_helper import save_image_to_disk, from_base64_to_image, load_image_from_disk, from_image_to_base64
from .users import router, logger


@router.get("/me", response_model=UserInfo)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated user's profile."""
    # Load user with profile
    result = await db.execute(
        select(User)
        .options(selectinload(User.profile))
        .where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    avatar_base64 = from_image_to_base64(load_image_from_disk(user.profile.avatar)) if user.profile.avatar else None
    
    return UserInfo(
        id=user.id,
        email=user.email,
        role=user.role,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        profile= UserProfile(
            first_name=user.profile.first_name,
            last_name=user.profile.last_name,
            date_of_birth=user.profile.date_of_birth,
            avatar=avatar_base64 
        ) if user.profile else None
    )


@router.put("/me", response_model=UserProfile)
@csrf_protect
async def update_current_user_profile(
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's profile."""
    # Get or create user profile
    result = await db.execute(
        select(UserProfileModel).where(UserProfileModel.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        # Create new profile if it doesn't exist
        profile = UserProfileModel(
            user_id=current_user.id,
            first_name="",
            last_name=""
        )
        db.add(profile)
        await db.flush()
    
    # Update profile fields
    update_data = profile_update.dict(exclude_unset=True, exclude={"avatar"})
    for field, value in update_data.items():
        if hasattr(profile, field):
            setattr(profile, field, value)
    
    # Handle avatar upload
    if profile_update.avatar:
        avatar_dir = os.path.join(settings.MEDIA_ROOT, "avatars")
        os.makedirs(avatar_dir, exist_ok=True)
        save_image_path = os.path.join(avatar_dir, f"{current_user.id}.png")
        
        try:
            save_image_to_disk(from_base64_to_image(profile_update.avatar), save_image_path)
            profile.avatar = save_image_path
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid avatar image data"
            )
    
    await db.commit()
    await db.refresh(profile)
    
    return UserProfile(
        id=current_user.id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        date_of_birth=profile.date_of_birth,
        avatar=from_image_to_base64(load_image_from_disk(profile.avatar)) if profile.avatar else None
    )