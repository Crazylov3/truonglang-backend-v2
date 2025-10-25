"""Simple authentication code flow for cross-domain authentication."""

import json
import secrets
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.core.deps import get_db
from app.core.security import create_user_token
# Removed cookie wrapper functions - using FastAPI Response methods directly
from app.core.operations import user as user_ops
from app.core.operations.audit import log_user_action
from app.models.audit import AuditAction
from app.schemas.auth.auth_code import (
    AuthCodeRequest, AuthCodeResponse,
    ExchangeAuthCodeRequest, ExchangeAuthCodeResponse
)
from app.core.decorators import csrf_protect
from app.schemas.users.user_schemas import UserInfo
from app.config import settings
from app.database import get_redis
import traceback
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth-code"])


@router.post("/login-with-code", response_model=AuthCodeResponse)
@csrf_protect
async def login_with_auth_code(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Login and return authentication code instead of setting cookies.
    Perfect for cross-domain scenarios where cookies can't be shared.
    """
    try:
        # Authenticate user (same as regular login)
        user = await user_ops.authenticate_user(db, form_data.username, form_data.password)
        logger.info(f"User: {user}")
        if not user:
            # Skip audit log for failed login to avoid the error
            pass
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extract all user data while still in session
        user_id = user.id
        user_email = user.email
        user_role = user.role.value if hasattr(user.role, 'value') else str(user.role)
        user_role_name = user.role.name if hasattr(user.role, 'name') else str(user.role)
        user_role_value = user.role.value if hasattr(user.role, 'value') else str(user.role)
        user_last_login = user.last_login_at
        user_created_at = user.created_at
        
        # Generate secure 5-minute authentication code
        auth_code = secrets.token_urlsafe(32)
        auth_code_expires = 300  # 5 minutes
        
        # Store user data with the auth code in Redis
        auth_data = {
            "user_id": str(user_id),  # Convert UUID to string for JSON serialization
            "user_email": user_email,
            "user_role": user_role_name,
            "issued_at": datetime.utcnow().isoformat(),
            "ip_address": request.client.host if request and request.client else None,
            "user_agent": request.headers.get("user-agent") if request else None
        }
        
        # Store in Redis with 5-minute expiration
        await redis_client.setex(
            f"auth_code:{auth_code}",
            auth_code_expires,
            json.dumps(auth_data)
        )
        
        # Audit log successful login with auth code
        await log_user_action(
            db=db,
            action=AuditAction.LOGIN,
            user_id=user_id,
            user_email=user_email,
            user_role=user_role_value,
            operation_summary="User logged in successfully - auth code generated",
            operation_details={
                "login_method": "auth_code",
                "auth_code_prefix": auth_code[:8] + "...",
                "expires_in": auth_code_expires
            },
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            request_method="POST",
            request_path="/api/v1/auth/login-with-code"
        )
        
        # Create user info for response
        user_info = UserInfo(
            id=user_id,
            public_id=user.public_id,
            email=user_email,
            role=user_role,
            last_login_at=user_last_login,
            created_at=user_created_at,
            profile=None  # Will be populated by Pydantic if profile exists
        )
        
        return AuthCodeResponse(
            message="Login successful - use auth code to get tokens",
            auth_code=auth_code,
            expires_in=auth_code_expires,
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
            operation_summary="Login with auth code failed due to system error",
            operation_details={"error": str(e)},
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            request_method="POST",
            request_path="/api/v1/auth/login-with-code"
        )
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )


@router.post("/exchange-code", response_model=ExchangeAuthCodeResponse)
@csrf_protect
async def exchange_auth_code_for_tokens(
    exchange_request: ExchangeAuthCodeRequest,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Exchange authentication code for access and refresh tokens.
    Sets HTTP-only cookies for the requesting domain.
    """
    try:
        # Validate authentication code
        auth_data_raw = await redis_client.get(f"auth_code:{exchange_request.auth_code}")
        if not auth_data_raw:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired authentication code"
            )
        
        # Parse auth data
        auth_data = json.loads(auth_data_raw)
        
        # Get user from database to ensure they still exist
        user_id = UUID(auth_data["user_id"])
        user = await user_ops.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not found"
            )
        
        # Extract user data while still in session
        user_email = user.email
        user_role = user.role.value if hasattr(user.role, 'value') else str(user.role)
        user_role_name = user.role.name if hasattr(user.role, 'name') else str(user.role)
        user_role_value = user.role.value if hasattr(user.role, 'value') else str(user.role)
        user_last_login = user.last_login_at
        user_created_at = user.created_at
        
        # Generate short-lived access token (30 minutes)
        access_token_expires = 1800  # 30 minutes
        access_token = create_user_token(
            user_id=user_id,
            user_role=user_role_name,
            expires_delta=access_token_expires
        )
        
        # Generate long-lived refresh token (7 days)
        refresh_token = secrets.token_urlsafe(64)
        refresh_token_expires = 604800  # 7 days
        
        # Store refresh token in Redis
        refresh_data = {
            "user_id": str(user_id),  # Convert UUID to string for JSON serialization
            "user_email": user_email,
            "user_role": user_role_name,
            "issued_at": datetime.utcnow().isoformat(),
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent") if request else None,
            "domain": request.headers.get("host") if request else None
        }
        
        await redis_client.setex(
            f"refresh_token:{refresh_token}",
            refresh_token_expires,
            json.dumps(refresh_data)
        )
        
        # Set HTTP-only cookies for THIS domain (not cross-domain)
        # This avoids all cross-domain cookie issues
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=access_token_expires,
            httponly=True,
            secure=not settings.debug,  # Only secure in production
            samesite="lax",  # Allow same-site navigation
            path="/",
            domain=None  # Let browser set for current domain only
        )
        
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=refresh_token_expires,
            httponly=True,
            secure=not settings.debug,
            samesite="lax",
            # path="/api/v1/auth/refresh-token",  # Only sent to refresh endpoint
            path="/",  # Only sent to refresh endpoint
            domain=None  # Let browser set for current domain only
        )
        
        # Delete used authentication code (one-time use)
        await redis_client.delete(f"auth_code:{exchange_request.auth_code}")
        
        # Audit log successful token exchange
        await log_user_action(
            db=db,
            action=AuditAction.LOGIN,
            user_id=user_id,
            user_email=user_email,
            user_role=user_role_value,
            operation_summary="Auth code exchanged for tokens successfully",
            operation_details={
                "auth_code_prefix": exchange_request.auth_code[:8] + "...",
                "access_token_expires_in": access_token_expires,
                "refresh_token_expires_in": refresh_token_expires,
                "target_domain": request.headers.get("host") if request else None
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            request_method="POST",
            request_path="/api/v1/auth/exchange-code"
        )
        
        # Create user info for response
        user_info = UserInfo(
            id=user_id,
            public_id=user.public_id,
            email=user_email,
            role=user_role,
            last_login_at=user_last_login,
            created_at=user_created_at,
            profile=None
        )
        
        return ExchangeAuthCodeResponse(
            message="Tokens set successfully",
            expires_in=access_token_expires,
            user=user_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Audit log error
        await log_user_action(
            db=db,
            action=AuditAction.LOGIN,
            user_id=None,
            user_email="unknown",
            user_role=None,
            operation_summary="Failed to exchange auth code for tokens",
            operation_details={
                "error": str(e),
                "auth_code_prefix": exchange_request.auth_code[:8] + "..." if exchange_request.auth_code else "none"
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            request_method="POST",
            request_path="/api/v1/auth/exchange-code"
        )
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to exchange authentication code"
        )


@router.post("/refresh-token")
async def refresh_access_token(
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Refresh access token using refresh token from cookie.
    """
    try:
        # Get refresh token from cookie
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found in cookies"
            )
        
        # Validate refresh token
        token_data_raw = await redis_client.get(f"refresh_token:{refresh_token}")
        if not token_data_raw:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        # Parse token data
        token_data = json.loads(token_data_raw)
        
        # Get user from database
        user_id = UUID(token_data["user_id"])
        user = await user_ops.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Extract user data while still in session
        user_email = user.email
        user_role_name = user.role.name if hasattr(user.role, 'name') else str(user.role)
        user_role_value = user.role.value if hasattr(user.role, 'value') else str(user.role)
        
        # Generate new access token (30 minutes)
        access_token_expires = 1800
        new_access_token = create_user_token(
            user_id=user_id,
            user_role=user_role_name,
            expires_delta=access_token_expires
        )
        
        # Optionally rotate refresh token for better security
        new_refresh_token = secrets.token_urlsafe(64)
        refresh_token_expires = 604800  # 7 days
        
        # Update refresh token data in Redis
        refresh_data = {
            "user_id": str(user_id),  # Convert UUID to string for JSON serialization
            "user_email": user_email,
            "user_role": user_role_name,
            "issued_at": datetime.utcnow().isoformat(),
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent") if request else None,
            "domain": request.headers.get("host") if request else None
        }
        
        # Delete old refresh token and store new one
        await redis_client.delete(f"refresh_token:{refresh_token}")
        await redis_client.setex(
            f"refresh_token:{new_refresh_token}",
            refresh_token_expires,
            json.dumps(refresh_data)
        )
        
        # Set new access token cookie (sent with all requests)
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            max_age=access_token_expires,
            httponly=True,
            secure=not settings.debug,
            samesite="lax",
            path="/",
            domain=None
        )
        
        # Set new refresh token cookie (only sent to refresh endpoint)
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            max_age=refresh_token_expires,
            httponly=True,
            secure=not settings.debug,
            samesite="lax",
            # path="/api/v1/auth/refresh-token",
            path="/",
            domain=None
        )
        
        # Audit log token refresh
        await log_user_action(
            db=db,
            action=AuditAction.LOGIN,
            user_id=user_id,
            user_email=user_email,
            user_role=user_role_value,
            operation_summary="Access token refreshed successfully with refresh token rotation",
            operation_details={
                "access_token_expires_in": access_token_expires,
                "refresh_token_rotated": True,
                "domain": request.headers.get("host") if request else None
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            request_method="POST",
            request_path="/api/v1/auth/refresh-token"
        )
        
        return {
            "message": "Access token refreshed successfully",
            "expires_in": access_token_expires
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Audit log error
        await log_user_action(
            db=db,
            action=AuditAction.LOGIN,
            user_id=None,
            user_email="unknown",
            user_role=None,
            operation_summary="Failed to refresh access token",
            operation_details={"error": str(e)},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            request_method="POST",
            request_path="/api/v1/auth/refresh-token"
        )
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh access token"
        )


@router.post("/logout")
async def logout_with_refresh_cleanup(
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Logout user and clean up both access and refresh tokens.
    Works with the new auth code flow.
    """
    try:
        # Get refresh token from cookie to invalidate it
        refresh_token = request.cookies.get("refresh_token")
        
        # Try to get user info for audit logging
        user_id = None
        user_email = "unknown"
        user_role = None
        
        if refresh_token:
            # Get user info from refresh token for audit
            token_data_raw = await redis_client.get(f"refresh_token:{refresh_token}")
            if token_data_raw:
                token_data = json.loads(token_data_raw)
                user_id = token_data.get("user_id")
                user_email = token_data.get("user_email", "unknown")
                user_role = token_data.get("user_role")
                
                # Delete refresh token from Redis
                await redis_client.delete(f"refresh_token:{refresh_token}")
        
        # Clear both cookies
        response.delete_cookie(
            key="access_token",
            path="/",
            httponly=True,
            secure=not settings.debug,
            samesite="lax",
            domain=None
        )
        
        response.delete_cookie(
            key="refresh_token",
            path="/api/v1/auth/refresh-token",  # Must match the path where it was set
            httponly=True,
            secure=not settings.debug,
            samesite="lax",
            domain=None
        )
        
        # Audit log successful logout
        await log_user_action(
            db=db,
            action=AuditAction.LOGOUT,
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            operation_summary="User logged out successfully - tokens cleared",
            operation_details={
                "logout_method": "auth_code_flow",
                "refresh_token_invalidated": refresh_token is not None
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            request_method="POST",
            request_path="/api/v1/auth/logout"
        )
        
        return {
            "message": "Successfully logged out - all tokens cleared"
        }
        
    except Exception as e:
        # Audit log logout error
        await log_user_action(
            db=db,
            action=AuditAction.LOGOUT,
            user_id=None,
            user_email="unknown",
            user_role=None,
            operation_summary="Logout failed due to system error",
            operation_details={"error": str(e)},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            request_method="POST",
            request_path="/api/v1/auth/logout"
        )
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during logout"
        )
