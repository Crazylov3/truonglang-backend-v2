from fastapi import Depends, HTTPException, status, Request, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import json

from app.database import get_db
from app.models.user import User, UserRole
from app.core.operations import user as user_operations
from app.core.security import verify_user_token


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from secure JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please log in.",
    )
    
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise credentials_exception
    
    token_data = verify_user_token(access_token)
    if not token_data:
        raise credentials_exception
    
    user_id = token_data.get("user_id")
    if not user_id:
        raise credentials_exception
    
    user = await user_operations.get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception
    
    if isinstance(user.role, int):
        try:
            user.role = UserRole(user.role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invalid user role in database: {user.role}"
            )
    
    # Compare role values - handle both role name and role value in token
    user_role_name = user.role.name if hasattr(user.role, 'name') else str(user.role)
    user_role_value = str(user.role.value if hasattr(user.role, 'value') else user.role)
    token_role = str(token_data.get("user_role"))
    
    # Accept either role name or role value from token for backward compatibility
    if token_role != user_role_name and token_role != user_role_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Role mismatch. DB role: {user_role_name} (value={user_role_value}), Token role: {token_role}. Please log in again."
        )
    
    return user


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None."""
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None


def require_role(required_role: UserRole):
    """Dependency factory for role-based authorization."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        # Ensure role is UserRole enum for comparison
        user_role = current_user.role
        if isinstance(user_role, int):
            user_role = UserRole(user_role)
        
        if user_role.value < required_role.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role.name} or higher."
            )
        return current_user
    return role_checker