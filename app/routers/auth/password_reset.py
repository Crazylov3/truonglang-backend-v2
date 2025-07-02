from fastapi import Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.schemas.auth.password_reset import UserPasswordReset, UserPasswordResetResponse, UserPasswordResetVerifyEmail, UserPasswordResetVerifyEmailResponse
from app.models.user import User
from app.core.security import get_password_hash
from .auth import router
from app.core.decorators import csrf_protect
import redis.asyncio as redis
from app.database import get_redis
from app.config import settings
from app.core.email import email_service


@router.post("/reset-password", response_model=UserPasswordResetResponse)
@csrf_protect
async def reset_password(
    user_data: UserPasswordReset,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Reset password using OTP."""
    # Check if user exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    otp = email_service.generate_otp()
    # Store OTP in Redis
    await redis_client.setex(f"password_reset:{user_data.email}", settings.otp_expire_minutes * 60, otp)
    success = await email_service.send_password_reset_otp_email(user_data.email, otp)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email. Please try again later."
        )
    return UserPasswordResetResponse(message="If the email exists, a password reset email has been sent.")


@router.post("/reset-password/verify-email", response_model=UserPasswordResetVerifyEmailResponse)
@csrf_protect
async def verify_email_and_reset_password(
    user_data: UserPasswordResetVerifyEmail,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Verify email OTP and reset password."""

    # Get stored OTP from Redis
    stored_otp = await redis_client.get(f"password_reset:{user_data.email}")

    if not stored_otp or stored_otp != user_data.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )

    # Get user
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update password
    user.hashed_password = get_password_hash(user_data.new_password)
    await db.commit()

    # Delete used OTP
    await redis_client.delete(f"password_reset:{user_data.email}")

    return UserPasswordResetVerifyEmailResponse(message="Password reset successfully")
