from fastapi import Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.auth.login import UserLogin, UserLoginResponse, UserLogoutResponse
from app.schemas.users.user_schemas import UserInfo, UserProfile
from app.core.operations import user as user_operations
from app.core.security import create_user_token
import json
from app.config import settings
from .auth import router
from .auth import logger
from app.core.decorators import csrf_protect
from app.core.cookies import set_cookie, clear_cookie


@router.post("/login", response_model=UserLoginResponse)
@csrf_protect
async def login(
    user_data: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and create secure JWT token."""
    # Get user with profile data using operations
    user = await user_operations.get_user_by_email(db, user_data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user_operations.verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Update last login time using operations
    await user_operations.update_user_last_login(db, user.id)

    # Generate avatar URL if user has an avatar
    avatar_url = f"/users/avatar/{user.id}" if user.profile and user.profile.avatar else None

    user_info = UserInfo(
        id=user.id,
        email=user.email,
        role=user.role,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        profile=UserProfile(
            first_name=user.profile.first_name,
            last_name=user.profile.last_name,
            date_of_birth=user.profile.date_of_birth,
            avatar=avatar_url  # Store URL instead of base64
        ) if user.profile else None,
    )
    cookie_max_age = settings.access_token_expire_minutes * 60
    access_token = create_user_token(user.id, user.role, cookie_max_age)
    is_development = settings.debug

    set_cookie(
        response,
        "access_token",
        access_token,
        secure=not is_development,
        httponly=True,  # Prevent JavaScript access for security
        max_age=cookie_max_age
    )

    # Set user display data cookie (non-sensitive info only)
    user_display_data = {
        "id": user_info.id,
        "last_name": user_info.profile.last_name if user_info.profile else None,
        "first_name": user_info.profile.first_name if user_info.profile else None,
        "avatar_url": avatar_url,  # Store URL instead of base64
        "role": user.role,
    }

    set_cookie(
        response,
        "giaoducthanglong_user_data",
        json.dumps(user_display_data),
        secure=not is_development,
        httponly=False,  # Allow JavaScript access for UI display
        max_age=cookie_max_age
    )

    return UserLoginResponse(
        message="Login successful",
        user=user_info
    )


@router.post("/logout", response_model=UserLogoutResponse)
async def logout(
    response: Response
):
    """Logout user by clearing cookies."""
    clear_cookie(response, "access_token")
    clear_cookie(response, "giaoducthanglong_user_data")

    return UserLogoutResponse(message="Successfully logged out")
