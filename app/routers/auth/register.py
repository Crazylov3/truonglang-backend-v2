from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import ast
import json
import redis.asyncio as redis
from app.database import get_db, get_redis, AsyncSessionLocal
from app.schemas.auth.register import UserRegister, UserRegisterResponse, UserRegisterVerifyEmail, UserRegisterVerifyEmailResponse
from app.models.user import User, UserRole
from app.core.operations import user as user_operations
from app.core.email import email_service
from app.config import settings
from .auth import router
from .auth import logger
from app.core.decorators import csrf_protect


@router.post("/register", response_model=UserRegisterResponse, status_code=status.HTTP_201_CREATED)
@csrf_protect
async def register(
    user_data: UserRegister,
    redis_client: redis.Redis = Depends(get_redis)
):
    """Register a new user account."""

    async with AsyncSessionLocal() as db:
        # Check if user already exists using operations
        user = await user_operations.get_user_by_email(db, user_data.email)
        if user:
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
    logger.info(f"Registration data stored in Redis: {registration_data}")

    # Send verification email
    success = await email_service.send_verification_email(user_data.email, otp)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email. Please try again later."
        )

    return UserRegisterResponse(message="If the email exists, a verification email has been sent.")

@router.post("/register/verify-email", response_model=UserRegisterVerifyEmailResponse)
@csrf_protect
async def verify_email_and_create_account(
    user_data: UserRegisterVerifyEmail,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Verify email OTP and create user account."""
    # Get stored registration data
    registration_key = f"registration:{user_data.email}"
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
    if registration_data.get("otp") != user_data.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP"
        )

    # Create user account and profile using operations
    try:
        await user_operations.create_user(
            db=db,
            email=registration_data["email"],
            password=registration_data["password"],
            first_name=registration_data.get("first_name"),
            last_name=registration_data.get("last_name"),
            role=UserRole.STUDENT
        )
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account"
        )

    # Remove registration data from Redis
    await redis_client.delete(registration_key)

    return UserRegisterVerifyEmailResponse(message="Account created successfully. You can now log in.")
