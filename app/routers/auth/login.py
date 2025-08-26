"""Authentication router for login/logout functionality."""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.security import create_access_token, verify_password
from app.core.operations import user as user_ops
from app.core.operations.audit import log_user_action
from app.models.user import User
from app.models.audit import AuditAction
from app.schemas.auth.login import UserLogin, UserLoginResponse, UserLogoutResponse
from app.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=UserLoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """User login endpoint."""
    try:
        # Authenticate user
        user = await user_ops.authenticate_user(db, form_data.username, form_data.password)
        if not user:
            # Audit log failed login attempt
            await log_user_action(
                db=db,
                action=AuditAction.LOGIN,
                user_id=0,  # Unknown user
                user_email=form_data.username,
                user_role=0,
                operation_summary="Failed login attempt - invalid credentials",
                operation_details={"username": form_data.username},
                ip_address=request.client.host if request and request.client else None,
                user_agent=request.headers.get("user-agent") if request else None,
                request_method="POST",
                request_path="/api/v1/auth/login"
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        # Update last login time
        await user_ops.update_last_login(db, user.id)
        
        # Audit log successful login
        await log_user_action(
            db=db,
            action=AuditAction.LOGIN,
            user_id=user.id,
            user_email=user.email,
            user_role=user.role,
            operation_summary="User logged in successfully",
            operation_details={"login_method": "password"},
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            request_method="POST",
            request_path="/api/v1/auth/login"
        )
        
        return UserLoginResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            email=user.email,
            role=user.role
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Audit log unexpected error during login
        await log_user_action(
            db=db,
            action=AuditAction.LOGIN,
            user_id=0,
            user_email=form_data.username if 'form_data' in locals() else "unknown",
            user_role=0,
            operation_summary="Login failed due to system error",
            operation_details={"error": str(e)},
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            request_method="POST",
            request_path="/api/v1/auth/login"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )


@router.post("/logout", response_model=UserLogoutResponse)
async def logout(
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """User logout endpoint."""
    try:
        # Audit log successful logout
        await log_user_action(
            db=db,
            action=AuditAction.LOGOUT,
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role,
            operation_summary="User logged out successfully",
            operation_details={"logout_method": "api_call"},
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            request_method="POST",
            request_path="/api/v1/auth/logout"
        )
        
        return UserLogoutResponse(
            message="Successfully logged out",
            user_id=current_user.id,
            email=current_user.email
        )
        
    except Exception as e:
        # Audit log logout error
        await log_user_action(
            db=db,
            action=AuditAction.LOGOUT,
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role,
            operation_summary="Logout failed due to system error",
            operation_details={"error": str(e)},
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            request_method="POST",
            request_path="/api/v1/auth/logout"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during logout"
        )
