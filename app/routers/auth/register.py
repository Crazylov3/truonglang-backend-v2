from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import ast
import json
import redis.asyncio as redis
from app.database import get_db, get_redis, AsyncSessionLocal
from app.schemas.auth.register import UserRegister, UserRegisterResponse, UserRegisterVerifyEmail, UserRegisterVerifyEmailResponse
from app.models.user import User, UserRole
from app.models.user_profile import UserProfile
from app.core.security import get_password_hash
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

    # Create user account and profile
    async with AsyncSessionLocal() as db:
        hashed_password = get_password_hash(registration_data["password"])
        
        # Create user with core authentication data only
        new_user = User(
            email=registration_data["email"],
            hashed_password=hashed_password,
            role=UserRole.STUDENT  # Default role
        )

        db.add(new_user)
        await db.flush()  # Flush to get the user ID
        
        # Create user profile with personal information
        user_profile = UserProfile(
            user_id=new_user.id,
            first_name=registration_data.get("first_name", ""),
            last_name=registration_data.get("last_name", "")
        )
        
        db.add(user_profile)
        await db.commit()
        await db.refresh(new_user)

    # Remove registration data from Redis
    await redis_client.delete(registration_key)

    return UserRegisterVerifyEmailResponse(message="Account created successfully. You can now log in.")
