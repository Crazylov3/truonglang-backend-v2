import os
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.users.user_schemas import (
    UserProfileUpdate,
    UserInfo,
    UserProfile,
)
from app.core.decorators import csrf_protect
from app.core.deps import get_current_user
from app.core.operations import user as user_ops
from app.core.operations import user_profile as profile_ops
from app.core.media.io_helper import save_image_to_disk, from_base64_to_image, load_image_from_disk, from_image_to_base64
from .users import router, logger


@router.get("/me", response_model=UserInfo)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated user's profile."""
    # Get user with profile using operations
    user = await user_ops.get_user_by_id(db, current_user.id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    avatar_base64 = from_image_to_base64(load_image_from_disk(user.profile.avatar)) if user.profile and user.profile.avatar else None
    
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
    # Get current profile
    profile = await profile_ops.get_user_profile(db, current_user.id)
    
    if not profile:
        # Create new profile if it doesn't exist
        profile = await profile_ops.create_user_profile(
            db=db,
            user_id=current_user.id,
            first_name="",
            last_name=""
        )
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user profile"
            )
    
    # Prepare update data
    update_data = profile_update.dict(exclude_unset=True, exclude={"avatar"})
    
    # Handle avatar upload
    avatar_path = None
    if profile_update.avatar:
        avatar_dir = os.path.join(settings.MEDIA_ROOT, "avatars")
        os.makedirs(avatar_dir, exist_ok=True)
        save_image_path = os.path.join(avatar_dir, f"{current_user.id}.png")
        
        try:
            save_image_to_disk(from_base64_to_image(profile_update.avatar), save_image_path)
            avatar_path = save_image_path
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid avatar image data"
            )
    
    # Update profile using operations
    success = await profile_ops.update_user_profile(
        db=db,
        user_id=current_user.id,
        first_name=update_data.get("first_name"),
        last_name=update_data.get("last_name"),
        date_of_birth=update_data.get("date_of_birth"),
        avatar=avatar_path
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )
    
    # Get updated profile
    updated_profile = await profile_ops.get_user_profile(db, current_user.id)
    
    return UserProfile(
        id=current_user.id,
        first_name=updated_profile.first_name,
        last_name=updated_profile.last_name,
        date_of_birth=updated_profile.date_of_birth,
        avatar=from_image_to_base64(load_image_from_disk(updated_profile.avatar)) if updated_profile.avatar else None
    )