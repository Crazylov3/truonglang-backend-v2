import os
from fastapi import Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.users.user_schemas import (
    UsersListResponse,
    UserProfileUpdate,
    UserRoleUpdateRequest,
    UserRoleUpdateResponse,
    DeleteUserResponse,
    UserInfo,
    UserProfile
)
from app.core.decorators import authentication_required, csrf_protect
from app.core.media.io_helper import save_image_to_disk, from_base64_to_image, from_image_to_base64, load_image_from_disk
from app.core.operations import user as user_ops
from .users import router


@router.get("/", response_model=UsersListResponse)
@authentication_required(allowed_role=UserRole.STAFF)
async def get_all_users(
    skip: int = Query(
        0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(100, ge=1, le=1000,
                       description="Maximum number of records to return"),
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    db: AsyncSession = Depends(get_db)
):
    """Get all users (staff/admin only)."""
    users = await user_ops.list_users(
        db=db,
        role=role,
        limit=limit,
        offset=skip
    )

    # Get total count for pagination
    total = await user_ops.count_users(db=db, role=role)

    users_data = []
    for user in users:
        avatar_base64 = from_image_to_base64(load_image_from_disk(
            user.profile.avatar)) if user.profile and user.profile.avatar else None

        user_data = UserInfo(
            id=user.id,
            email=user.email,
            role=user.role,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            profile=UserProfile(
                first_name=user.profile.first_name,
                last_name=user.profile.last_name,
                date_of_birth=user.profile.date_of_birth,
                avatar=avatar_base64
            ) if user.profile else None,
        )
        users_data.append(user_data)

    return UsersListResponse(
        users=users_data,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{user_id}", response_model=UserInfo)
@authentication_required(allowed_role=UserRole.STAFF)
async def get_user_by_id(
    user_id: int = Path(..., description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get user by ID (staff/admin only)."""
    user = await user_ops.get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    avatar_base64 = from_image_to_base64(load_image_from_disk(
        user.profile.avatar)) if user.profile and user.profile.avatar else None

    return UserInfo(
        id=user.id,
        email=user.email,
        role=user.role,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        profile=UserProfile(
            first_name=user.profile.first_name,
            last_name=user.profile.last_name,
            date_of_birth=user.profile.date_of_birth,
            avatar=avatar_base64
        ) if user.profile else None
    )


@router.put("/{user_id}/profile", response_model=UserProfile)
@authentication_required(allowed_role=UserRole.STAFF)
@csrf_protect
async def update_user_profile_by_id(
    profile_update: UserProfileUpdate,
    user_id: int = Path(..., description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """Update user profile by ID (staff/admin only)."""
    # Check if user exists
    user = await user_ops.get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Handle avatar upload
    avatar_path = None
    if profile_update.avatar:
        avatar_dir = os.path.join(settings.MEDIA_ROOT, "avatars")
        os.makedirs(avatar_dir, exist_ok=True)
        save_image_path = os.path.join(avatar_dir, f"{user_id}.png")

        try:
            save_image_to_disk(from_base64_to_image(
                profile_update.avatar), save_image_path)
            avatar_path = save_image_path
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid avatar image data"
            )

    # Update profile using operations
    update_data = profile_update.dict(exclude_unset=True, exclude={"avatar"})
    if avatar_path:
        update_data["avatar"] = avatar_path

    success = await user_ops.update_user_profile(
        db=db,
        user_id=user_id,
        **update_data
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

    return UserProfile(
        first_name=update_data.get("first_name"),
        last_name=update_data.get("last_name"),
        date_of_birth=update_data.get("date_of_birth"),
        avatar=profile_update.avatar
    )


@router.put("/{user_id}/role", response_model=UserRoleUpdateResponse)
@authentication_required(allowed_role=UserRole.ADMIN)
@csrf_protect
async def update_user_role(
    role_update: UserRoleUpdateRequest,
    user_id: int = Path(..., description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """Update user role (admin only)."""
    user = await user_ops.get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Use the new update_user_role_by_id function
    success = await user_ops.update_user_role_by_id(db, user_id, role_update.new_role)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role"
        )

    return UserRoleUpdateResponse(
        id=user_id,
        email=user.email,
        role=role_update.new_role,
        message=f"User role updated successfully to {role_update.new_role}"
    )


@router.delete("/{user_id}", response_model=DeleteUserResponse)
@authentication_required(allowed_role=UserRole.ADMIN)
@csrf_protect
async def delete_user(
    user_id: int = Path(..., description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """Delete user (admin only)."""
    user = await user_ops.get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Use the new delete_user_by_id function
    success = await user_ops.delete_user_by_id(db, user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )

    return DeleteUserResponse(
        message=f"User {user.email} deleted successfully"
    )
