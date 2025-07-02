import os
from fastapi import Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole
from app.models.user_profile import UserProfile as UserProfileModel
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
    query = select(User).options(selectinload(User.profile))

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

    users_data = []
    for user in users:
        avatar_base64 = from_image_to_base64(load_image_from_disk(
            user.profile.avatar)) if user.profile.avatar else None

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
    result = await db.execute(
        select(User)
        .options(selectinload(User.profile))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    avatar_base64 = from_image_to_base64(load_image_from_disk(
        user.profile.avatar)) if user.profile.avatar else None

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
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get or create user profile
    result = await db.execute(
        select(UserProfileModel).where(UserProfileModel.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        # Create new profile if it doesn't exist
        profile = UserProfileModel(
            user_id=user_id,
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
        save_image_path = os.path.join(avatar_dir, f"{user_id}.png")

        try:
            save_image_to_disk(from_base64_to_image(
                profile_update.avatar), save_image_path)
            profile.avatar = save_image_path
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid avatar image data"
            )

    await db.commit()
    await db.refresh(profile)

    return UserProfile(
        first_name=profile.first_name,
        last_name=profile.last_name,
        date_of_birth=profile.date_of_birth,
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
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.role = role_update.new_role
    await db.commit()
    await db.refresh(user)

    return UserRoleUpdateResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        message=f"User role updated to {role_update.new_role.name}"
    )


@router.delete("/{user_id}", response_model=DeleteUserResponse)
@authentication_required(allowed_role=UserRole.ADMIN)
@csrf_protect
async def delete_user(
    user_id: int = Path(..., description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """Delete user (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    await db.delete(user)
    await db.commit()

    return DeleteUserResponse(message="User deleted successfully")
