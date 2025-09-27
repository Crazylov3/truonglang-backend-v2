"""Authentication router for login/logout functionality."""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.security import create_user_token
from app.core.cookies import set_cookie, clear_cookie
from app.core.operations import user as user_ops
from app.core.operations.audit import log_user_action
from app.models.user import User
from app.models.audit import AuditAction
from app.schemas.auth.login import UserLogin, UserLoginResponse, UserLogoutResponse
from app.config import settings
import traceback

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=UserLoginResponse)
async def login(
    response: Response,
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
                user_id=None,  # Unknown user
                user_email=form_data.username,
                user_role=None,
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
        
        # Create access token with proper user data
        access_token_expires = settings.access_token_expire_minutes * 60  # Convert to seconds
        access_token = create_user_token(
            user_id=user.id,
            user_role=user.role.name if hasattr(user.role, 'name') else str(user.role),
            expires_delta=access_token_expires
        )
        
        # Set secure cookie with JWT token
        set_cookie(
            response=response,
            name="access_token",
            value=access_token,
            secure=not settings.debug,  # Use secure cookies in production
            max_age=access_token_expires,
            httponly=True,
            samesite="lax"  # Allow cookie to be sent with navigation
        )
        
        # Update last login time
        # TODO: Implement update_last_login function
        # await user_ops.update_last_login(db, user.id)
        
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
        
        # Create user info for response
        from app.schemas.users.user_schemas import UserInfo
        user_info = UserInfo(
            id=user.id,
            email=user.email,
            role=user.role,
            full_name=user.full_name if hasattr(user, 'full_name') else None
        )
        
        return UserLoginResponse(
            message="Login successful",
            user=user_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Audit log unexpected error during login
        await log_user_action(
            db=db,
            action=AuditAction.LOGIN,
            user_id=None,
            user_email=form_data.username if 'form_data' in locals() else "unknown",
            user_role=None,
            operation_summary="Login failed due to system error",
            operation_details={"error": str(e)},
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            request_method="POST",
            request_path="/api/v1/auth/login"
        )
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )


@router.post("/logout", response_model=UserLogoutResponse)
async def logout(
    response: Response,
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """User logout endpoint."""
    try:
        # Clear the authentication cookie
        clear_cookie(
            response=response,
            name="access_token",
            secure=not settings.debug,
            httponly=True,
            samesite="lax"
        )
        
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
            message="Successfully logged out"
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
