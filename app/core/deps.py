from fastapi import Depends, HTTPException, status, Request, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import json

from app.database import get_db
from app.models.user import User, UserRole
from app.core.operations import user as user_operations


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from cookie data."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please log in.",
    )
    
    # Get user data from cookie
    user_data_cookie = request.cookies.get("user_data")
    if not user_data_cookie:
        raise credentials_exception
    
    try:
        # Parse user data from JSON cookie
        user_data = json.loads(user_data_cookie)
        user_id = user_data.get("user_id")
        
        if not user_id:
            raise credentials_exception
            
    except (json.JSONDecodeError, ValueError, TypeError):
        raise credentials_exception
    
    # Get fresh user data from database using operations
    user = await user_operations.get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception
    
    # Ensure role is properly converted to UserRole enum
    if isinstance(user.role, int):
        try:
            user.role = UserRole(user.role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invalid user role in database: {user.role}"
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