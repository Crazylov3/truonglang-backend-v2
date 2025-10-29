import os
from uuid import UUID
from fastapi import Depends, HTTPException, status, Query, Path, UploadFile, File, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.validators import validate_uuid

from app.config import settings
from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.schemas.users.user_schemas import (
    UsersListResponse,
    UserProfileUpdate,
    UserRoleUpdateRequest,
    UserRoleUpdateResponse,
    DeleteUserResponse,
    UserInfo,
    UserProfile,
    TotalUsersResponse,
    TemporalUserCreate,
    TemporalUserResponse,
    TemporalUserBulkCreate,
    UserUpdate,
    UserUpdateResponse
)
from app.schemas.common import PaginatedResponse
from app.core.decorators import csrf_protect
from app.core.deps import require_role
from app.core.media.io_helper import save_image_to_disk, from_base64_to_image, async_save_image_to_disk
from app.core.operations import user as user_ops
from .users import router, logger

@router.get("/", response_model=UsersListResponse)
async def get_all_users(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=1000000, description="Items per page"),
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    public_id: Optional[int] = Query(None, description="Filter by public ID"),
    email: Optional[str] = Query(None, description="Search by email (partial match)"),
    first_name: Optional[str] = Query(None, description="Search by first name (partial match)"),
    last_name: Optional[str] = Query(None, description="Search by last name (partial match)"),
    current_school: Optional[str] = Query(None, description="Search by current school (partial match)"),
    current_grade: Optional[str] = Query(None, description="Search by current grade (partial match)"),
    default_discount_percentage: Optional[float] = Query(None, description="Filter by users with discount percentage greater than this value"),
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Get all users with advanced filtering and search (staff/admin only)."""
    # Calculate offset from page/per_page
    offset = (page - 1) * per_page
    
    users = await user_ops.list_users(
        db=db,
        role=role,
        public_id=public_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        current_school=current_school,
        current_grade=current_grade,
        default_discount_percentage=default_discount_percentage,
        limit=per_page,
        offset=offset
    )

    # Get total count for pagination
    total = await user_ops.count_users(
        db=db, 
        role=role,
        public_id=public_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        current_school=current_school,
        current_grade=current_grade,
        default_discount_percentage=default_discount_percentage
    )

    users_data = []
    for user in users:
        # Generate avatar URL if user has an avatar
        avatar_url = f"/v1/users/admin/avatar/{user.id}" if user.profile and user.profile.avatar else None

        user_data = UserInfo(
            id=user.id,
            public_id=user.public_id,
            email=user.email,
            role=user.role,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            profile=UserProfile(
                first_name=user.profile.first_name,
                last_name=user.profile.last_name,
                date_of_birth=user.profile.date_of_birth,
                avatar=avatar_url,  # Store URL instead of base64,
                current_school=user.profile.current_school if user.profile else None,
                current_grade=user.profile.current_grade if user.profile else None,
                default_discount_percentage=user.profile.default_discount_percentage if user.profile else None,
            ) if user.profile else None
        )
        users_data.append(user_data)

    return PaginatedResponse.create(
        items=users_data,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/total", response_model=TotalUsersResponse)
async def get_total_users(
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Get total users count and breakdown by role (staff/admin only)."""
    # Get total count
    total = await user_ops.count_users(db=db)
    
    # Get counts by role
    by_role = {}
    for role in UserRole:
        count = await user_ops.count_users(db=db, role=role)
        by_role[role] = count
    
    return TotalUsersResponse(
        total=total,
        by_role=by_role
    )


@router.get("/admin/avatar/{user_id}")
async def get_user_avatar(
    user_id: str = Path(..., description="User ID"),
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db),
):
    """Get user avatar image (staff/admin only)."""
    # Validate UUID
    user_uuid = validate_uuid(user_id)
    
    # Get user to check if they exist and have an avatar
    user = await user_ops.get_user_by_id(db, user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user has a profile and avatar
    if not user.profile or not user.profile.avatar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User avatar not found"
        )
    
    # Check if avatar file exists on disk
    avatar_path = user.profile.avatar
    if not os.path.exists(avatar_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avatar file not found on server"
        )
    
    # Return the image file with appropriate headers
    return FileResponse(
        path=avatar_path,
        media_type="image/png",
        filename=f"avatar_{user_id}.png",
        headers={
            "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
            "Content-Disposition": f"inline; filename=avatar_{user_id}.png"
        }
    )


@router.get("/{user_id}", response_model=UserInfo)
async def get_user_by_id(
    user_id: str = Path(..., description="User ID"),
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Get user by ID (staff/admin only)."""
    user_uuid = validate_uuid(user_id)
    user = await user_ops.get_user_by_id(db, user_uuid)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Generate avatar URL if user has an avatar
    avatar_url = f"/v1/users/admin/avatar/{user.id}" if user.profile and user.profile.avatar else None

    return UserInfo(
        id=user.id,
        public_id=user.public_id,
        email=user.email,
        role=user.role,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        profile=UserProfile(
            first_name=user.profile.first_name,
            last_name=user.profile.last_name,
            date_of_birth=user.profile.date_of_birth,
            avatar=avatar_url,  # Store URL instead of base64
            current_school=user.profile.current_school if user.profile else None,
            current_grade=user.profile.current_grade if user.profile else None,
            default_discount_percentage=user.profile.default_discount_percentage if user.profile else None
        ) if user.profile else None
    )


@router.put("/{user_id}/profile", response_model=UserProfile)
@csrf_protect
async def update_user_profile_by_id(
    profile_update: UserProfileUpdate,
    user_id: str = Path(..., description="User ID"),
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Update user profile by ID (staff/admin only)."""
    # Check if user exists
    user_uuid = validate_uuid(user_id)
    user = await user_ops.get_user_by_id(db, user_uuid)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Handle avatar upload
    avatar_path = None
    if profile_update.avatar:
        avatar_dir = os.path.join(settings.media_root, "avatars")
        os.makedirs(avatar_dir, exist_ok=True)
        save_image_path = os.path.join(avatar_dir, f"{user_id}.png")

        try:
            await async_save_image_to_disk(from_base64_to_image(
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
@csrf_protect
async def update_user_role(
    role_update: UserRoleUpdateRequest,
    user_id: str = Path(..., description="User ID"),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Update user role (admin only)."""
    user_uuid = validate_uuid(user_id)
    user = await user_ops.get_user_by_id(db, user_uuid)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent admins from changing their own role
    if current_user.id == user_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change your own role"
        )

    # Use the new update_user_role_by_id function
    success = await user_ops.update_user_role_by_id(db, user_uuid, role_update.new_role)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role"
        )

    return UserRoleUpdateResponse(
        id=user_uuid,
        email=user.email,
        role=role_update.new_role,
        message=f"User role updated successfully to {role_update.new_role}"
    )


@router.delete("/{user_id}", response_model=DeleteUserResponse)
@csrf_protect
async def delete_user(
    user_id: str = Path(..., description="User ID"),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Delete user (admin only)."""
    user_uuid = validate_uuid(user_id)
    user = await user_ops.get_user_by_id(db, user_uuid)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Use the new delete_user_by_id function
    success = await user_ops.delete_user_by_id(db, user_uuid)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )

    return DeleteUserResponse(
        message=f"User {user.email} deleted successfully"
    )


# Temporal User Management APIs
@router.post("/temporal", response_model=TemporalUserResponse)
@csrf_protect
async def create_temporal_user(
    user_data: TemporalUserCreate,
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db),
):
    """Create a single temporal user (student) with auto-generated credentials."""
    try:
        result = await user_ops.create_temporal_user(
            db=db,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            date_of_birth=user_data.date_of_birth,
            current_school=user_data.current_school,
            current_grade=user_data.current_grade,
            default_discount_percentage=user_data.default_discount_percentage
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create temporal user"
            )
        
        user, profile, email, password = result
        
        return TemporalUserResponse(
            id=user.id,
            public_id=user.public_id,
            email=email,
            password=password,
            role=user.role,
            profile=UserProfile(
                first_name=profile.first_name,
                last_name=profile.last_name,
                date_of_birth=profile.date_of_birth,
                current_school=profile.current_school,
                current_grade=profile.current_grade,
                default_discount_percentage=profile.default_discount_percentage
            ),
            message=f"Temporal user created successfully. Email: {email}, Password: {password}"
        )
        
    except Exception as e:
        logger.error(f"Error creating temporal user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create temporal user"
        )


@router.post("/temporal/bulk", response_model=TemporalUserBulkCreate)
@csrf_protect
async def bulk_create_temporal_users(
    file: UploadFile = File(..., description="CSV file with student data"),
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple temporal users from CSV file upload."""    
    try:
        logger.info(f"Bulk temporal user creation started by user {current_user.email} (ID: {current_user.id})")
        logger.info(f"Processing file: {file.filename} (size: {file.size} bytes)")
        
        # Validate file type
        if not file.filename.endswith('.csv'):
            logger.warning(f"Invalid file type uploaded: {file.filename}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be a CSV file"
            )
        
        # Read CSV content
        csv_content = await file.read()
        csv_content_str = csv_content.decode('utf-8')
        logger.info(f"CSV file read successfully: {len(csv_content_str)} characters")
        
        # Process CSV and create users
        logger.info("Starting bulk user creation process")
        created_users, failed_rows = await user_ops.bulk_create_temporal_users(
            db=db,
            csv_content=csv_content_str
        )
        
        logger.info(f"Bulk user creation completed: {len(created_users)} created, {len(failed_rows)} failed")
        
        # Convert created users to response format
        temporal_users = []
        for item in created_users:
            user = item['user']
            profile = item['profile']
            temporal_users.append(TemporalUserResponse(
                id=user.id,
                public_id=user.public_id,
                email=item['email'],
                password=item['password'],
                role=user.role,
                profile=UserProfile(
                    first_name=profile.first_name,
                    last_name=profile.last_name,
                    date_of_birth=profile.date_of_birth,
                    current_school=profile.current_school,
                    current_grade=profile.current_grade,
                    default_discount_percentage=profile.default_discount_percentage
                ),
                message=f"Created from row {item['row']}"
            ))
        
        # Log final results
        success_rate = (len(created_users) / (len(created_users) + len(failed_rows))) * 100 if (len(created_users) + len(failed_rows)) > 0 else 0
        logger.info(f"Bulk creation final results: {len(created_users)} created, {len(failed_rows)} failed (Success rate: {success_rate:.1f}%)")
        
        return TemporalUserBulkCreate(
            message=f"Bulk creation completed. {len(created_users)} users created, {len(failed_rows)} failed",
            total_created=len(created_users),
            failed_count=len(failed_rows),
            created_users=temporal_users,
            failed_rows=failed_rows
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk create temporal users: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process CSV file"
        )


@router.put("/manipulation/{user_id}", response_model=UserUpdateResponse)
@csrf_protect
async def update_user(
    user_id: str = Path(..., description="User ID"),
    user_data: UserUpdate = ...,
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db),
):
    """Update user information and profile (partial update) (Admin/Staff only)."""
    # Validate UUID
    user_uuid = validate_uuid(user_id)
    
    # Check if user exists
    user = await user_ops.get_user_by_id(db, user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Role-based restrictions
    # Staff cannot edit admin profiles
    if current_user.role == UserRole.STAFF and user.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff cannot edit admin profiles"
        )
    
    # Users cannot change their own role
    if user_data.role is not None and current_user.id == user_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change your own role"
        )
    
    # Only admins can change user roles
    if user_data.role is not None and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can change user roles"
        )
    
    # Update user
    updated_user = await user_ops.update_user(
        db=db,
        user_id=user_uuid,
        email=user_data.email,
        password=user_data.password,
        role=user_data.role,
        need_change_email=user_data.need_change_email,
        need_change_password=user_data.need_change_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        date_of_birth=user_data.date_of_birth,
        current_school=user_data.current_school,
        current_grade=user_data.current_grade,
        default_discount_percentage=user_data.default_discount_percentage
    )
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update user. Email might already exist."
        )
    
    # Prepare profile data for response
    profile_data = None
    if updated_user.profile:
        profile_data = UserProfile(
            first_name=updated_user.profile.first_name,
            last_name=updated_user.profile.last_name,
            date_of_birth=updated_user.profile.date_of_birth,
            current_school=updated_user.profile.current_school,
            current_grade=updated_user.profile.current_grade,
            default_discount_percentage=updated_user.profile.default_discount_percentage
        )
    
    return UserUpdateResponse(
        id=updated_user.id,
        public_id=updated_user.public_id,
        email=updated_user.email,
        role=updated_user.role,
        need_change_email=updated_user.need_change_email,
        need_change_password=updated_user.need_change_password,
        profile=profile_data,
        message="User updated successfully"
    )
