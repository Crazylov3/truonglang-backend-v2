from fastapi import Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.auth.login import UserLogin, UserLoginResponse, UserLogoutResponse
from app.schemas.users.user_schemas import UserInfo
from app.core.operations import user as user_operations
import json
from app.config import settings
from .auth import router
from .auth import logger
from app.core.decorators import csrf_protect
from app.core.cookies import get_user_cookie_from_template, set_cookie, clear_cookie


@router.post("/login", response_model=UserLoginResponse)
@csrf_protect
async def login(
    user_data: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and create secure cookies."""
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

    user_info = UserInfo(
        id=user.id,
        email=user.email,
        role=user.role,
    )

    # Get user cookie data
    user_cookie_data = get_user_cookie_from_template(user_info)

    # Set user data cookie as JSON with expiration
    is_development = settings.debug
    cookie_max_age = settings.access_token_expire_minutes * 60

    set_cookie(
        response,
        "user_data",
        json.dumps(user_cookie_data),
        secure=not is_development,
        httponly=True,
        max_age=cookie_max_age
    )

    # Set user role as integer value
    set_cookie(
        response,
        "user_role",
        str(user.role),  # role is now an integer
        secure=not is_development,
        httponly=True,
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
    # Clear user cookies
    clear_cookie(response, "user_data")
    clear_cookie(response, "user_role")

    return UserLogoutResponse(message="Successfully logged out")
