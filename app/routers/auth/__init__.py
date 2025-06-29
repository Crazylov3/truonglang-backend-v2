from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta
import redis.asyncio as redis
from app.database import get_db, get_redis
from app.schemas.auth import UserRegister, UserLogin, Token, VerifyEmail, ForgotPassword, ResetPassword, ChangePassword
from app.schemas.users import UserResponse
from app.models.user import User
from app.core.security import (
    get_password_hash, 
    verify_password, 
    create_access_token,
    create_password_reset_token,
    verify_password_reset_token
)
from app.core.email import email_service
from app.core.deps import get_current_user
from app.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    redis_client: redis.Redis = Depends(get_redis)
):
    """Initiate user registration and send email verification OTP."""
    # Check if user already exists
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Generate OTP and store registration data temporarily
    otp = email_service.generate_otp()
    registration_data = {
        "email": user_data.email,
        "password": user_data.password,
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "otp": otp
    }
    
    # Store for 10 minutes
    await redis_client.setex(
        f"registration:{user_data.email}", 
        600, 
        str(registration_data)
    )
    
    # Send verification email
    email_sent = await email_service.send_verification_email(user_data.email, otp)
    
    return {
        "message": "Registration initiated. Please check your email for verification OTP to complete account creation.",
        "email_sent": email_sent
    }


@router.post("/verify-email", response_model=dict)
async def verify_email_and_create_account(
    verification_data: VerifyEmail,
    redis_client: redis.Redis = Depends(get_redis)
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
    
    # Parse registration data
    import ast
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
    from app.database import AsyncSessionLocal
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
    
    # Send welcome email
    await email_service.send_welcome_email(new_user.email, new_user.full_name)
    
    return {
        "message": "Account created successfully. You can now log in.",
        "user_id": new_user.id
    }


@router.post("/login", response_model=Token)
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return JWT token."""
    # Get user
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login time
    from datetime import datetime
    user.last_login_at = datetime.utcnow()
    await db.commit()
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"user_id": user.id, "email": user.email, "role": user.role.value},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout", response_model=dict)
async def logout(
    current_user: User = Depends(get_current_user)
):
    """Logout user."""
    # In a more sophisticated implementation, you would blacklist the JWT token
    # For now, we just return a success message since JWTs are stateless
    return {"message": "Successfully logged out"}


@router.post("/forgot-password", response_model=dict)
async def forgot_password(
    forgot_data: ForgotPassword,
    db: AsyncSession = Depends(get_db)
):
    """Send password reset email."""
    # Check if user exists
    result = await db.execute(select(User).where(User.email == forgot_data.email))
    user = result.scalar_one_or_none()
    
    # Always return success to prevent email enumeration
    if user:
        # Create password reset token
        reset_token = create_password_reset_token(user.email)
        
        # Send reset email
        await email_service.send_password_reset_email(user.email, reset_token)
    
    return {"message": "If the email exists, a password reset link has been sent."}


@router.post("/reset-password", response_model=dict)
async def reset_password(
    reset_data: ResetPassword,
    db: AsyncSession = Depends(get_db)
):
    """Reset password using token."""
    # Verify reset token
    email = verify_password_reset_token(reset_data.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Get user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update password
    user.hashed_password = get_password_hash(reset_data.new_password)
    await db.commit()
    
    return {"message": "Password reset successfully"}


@router.post("/change-password", response_model=dict)
async def change_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change current user's password."""
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()
    
    return {"message": "Password changed successfully"} 