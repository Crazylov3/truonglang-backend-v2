from fastapi import HTTPException, status, Response, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import ast
from app.database import get_db
from app.schemas.auth import UserRegister, UserLogin, VerifyEmail, ForgotPassword, ResetPassword, ChangePassword
from app.models.user import User
from app.core.security import (
    get_password_hash,
    verify_password,
)
from app.core.email import email_service
from app.core.deps import get_current_user
from app.core.cookies import set_cookie, clear_cookie, get_user_cookie_from_template
from app.config import settings
from app.core.decorators import csrf_protect, ensure_csrf_token
import json
import redis.asyncio as redis
from app.database import get_redis
from app.database import AsyncSessionLocal
import logging

logger = logging.getLogger(__name__)


@csrf_protect
async def register(
    user_data: UserRegister,
    redis_client: redis.Redis = Depends(get_redis)
):
    """Register a new user account."""

    async with AsyncSessionLocal() as db:
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    otp = email_service.generate_otp()
    registration_data = {
        "email": user_data.email,
        "password": user_data.password,
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "otp": otp
    }

    # Store user data in Redis
    await redis_client.setex(f"registration:{user_data.email}", settings.otp_expire_minutes * 60, json.dumps(registration_data))

    # Send verification email
    success = await email_service.send_verification_email(user_data.email, otp)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email. Please try again later."
        )

    return {
        "message": "If the email exists, a verification email has been sent."
    }


@csrf_protect
async def verify_email_and_create_account(
    verification_data: VerifyEmail,
    redis_client: redis.Redis = Depends(get_redis),
):
    """Verify email OTP and create user account."""
    # Get stored registration data
    registration_key = f"registration:{verification_data.email}"
    stored_data = await redis_client.get(registration_key)
    if not stored_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration expired or not found. Please register again."
        )

    try:
        registration_data = ast.literal_eval(stored_data)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid registration data"
        )

    # Verify OTP
    if registration_data.get("otp") != verification_data.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP"
        )

    # Create user account
    async with AsyncSessionLocal() as db:
        hashed_password = get_password_hash(registration_data["password"])
        new_user = User(
            email=registration_data["email"],
            hashed_password=hashed_password,
            first_name=registration_data.get("first_name"),
            last_name=registration_data.get("last_name")
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

    # Remove registration data from Redis
    await redis_client.delete(registration_key)

    return {
        "message": "Account created successfully. You can now log in.",
    }


@csrf_protect
async def login(
    login_data: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and create secure cookies."""
    # Get user
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()

    # print all users
    users = await db.execute(select(User))
    logger.info(f"Users: {users.scalars().all()}")
    logger.info(f"User: {login_data.email}")

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Update last login time
    user.last_login_at = datetime.utcnow()
    await db.commit()

    # Get user cookie data
    user_cookie_data = get_user_cookie_from_template(user)

    # Set user data cookie as JSON with expiration
    is_development = settings.debug
    cookie_max_age = settings.access_token_expire_minutes * 60  # Convert to seconds

    set_cookie(
        response,
        "user_data",
        json.dumps(user_cookie_data),
        secure=not is_development,
        httponly=True,  # Secure from XSS
        max_age=cookie_max_age
    )

    # Also set user role separately for easy access
    set_cookie(
        response,
        "user_role",
        user.role.value,
        secure=not is_development,
        httponly=True,
        max_age=cookie_max_age
    )

    return {
        "message": "Login successful",
        "user": {
            "email": user.email,
            "role": user.role.value,
            "full_name": user.full_name
        }
    }


@csrf_protect
async def logout(
    response: Response
):
    """Logout user by clearing cookies."""
    # Clear user cookies
    clear_cookie(response, "user_data")
    clear_cookie(response, "user_role")

    return {"message": "Successfully logged out"}


@csrf_protect
async def forgot_password(
    forgot_data: ForgotPassword,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Send password reset OTP."""
    # Check if user exists
    result = await db.execute(select(User).where(User.email == forgot_data.email))
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    if user:
        # Generate OTP instead of complex token
        otp = email_service.generate_otp()

        # Store OTP in Redis with email as key
        await redis_client.setex(
            f"password_reset:{forgot_data.email}",
            settings.otp_expire_minutes * 60,  # Convert to seconds
            otp
        )

        # Send OTP email
        await email_service.send_password_reset_otp_email(user.email, otp)

    return {"message": "If the email exists, a password reset OTP has been sent."}


@csrf_protect
async def reset_password(
    reset_data: ResetPassword,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Reset password using OTP."""

    # Get stored OTP from Redis
    stored_otp = await redis_client.get(f"password_reset:{reset_data.email}")

    if not stored_otp or stored_otp != reset_data.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )

    # Get user
    result = await db.execute(select(User).where(User.email == reset_data.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update password
    user.hashed_password = get_password_hash(reset_data.new_password)
    await db.commit()

    # Delete used OTP
    await redis_client.delete(f"password_reset:{reset_data.email}")

    return {"message": "Password reset successfully"}


@csrf_protect
async def change_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change current user's password."""

    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )

    # Update password
    current_user.hashed_password = get_password_hash(
        password_data.new_password)
    await db.commit()

    return {"message": "Password changed successfully"}


@ensure_csrf_token
async def get_csrf_token():
    """Generate and return a CSRF token - decorator handles all the complexity."""
    return {"message": "CSRF token generated successfully"}
