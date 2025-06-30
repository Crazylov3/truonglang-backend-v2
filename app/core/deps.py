from fastapi import Depends, HTTPException, status, Request, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import json

from app.database import get_db
from app.models.user import User, UserRole


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
    
    # Get fresh user data from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    
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
        if current_user.role < required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role.name} or higher."
            )
        return current_user
    return role_checker