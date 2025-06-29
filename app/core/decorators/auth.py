import functools
from typing import Callable
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
import inspect

from app.database import get_db, get_redis
from app.models.user import UserRole
from app.core.deps import get_current_user


def authentication_required(*allowed_roles: UserRole):
    """
    Decorator to require authentication and optionally specific roles.
    
    Uses hierarchical role checking where higher roles can access lower role endpoints:
    - STUDENT = 1 (lowest)
    - INSTRUCTOR = 2 
    - STAFF = 3
    - ADMIN = 4 (highest)
    
    Usage:
        @authentication_required(UserRole.STUDENT)  # Any authenticated user can access
        @authentication_required(UserRole.INSTRUCTOR)  # Instructor, Staff, Admin can access
        @authentication_required()  # Any authenticated user
    """
    def decorator(func: Callable) -> Callable:
        # Get the function signature
        sig = inspect.signature(func)
        
        # Create a new function that includes authentication dependencies
        @functools.wraps(func)
        async def wrapper(
            request: Request,
            db: AsyncSession = Depends(get_db),
            redis_client: redis.Redis = Depends(get_redis),
            *args,
            **kwargs
        ):
            try:
                # Get current user
                current_user = await get_current_user(request, db, redis_client)
                
                # Check role requirements if specified
                if allowed_roles:
                    # Find the minimum required role level (lowest number in the hierarchy)
                    min_required_role = min(allowed_roles)
                    
                    # Check if user's role is at or above the minimum required level
                    if current_user.role < min_required_role:
                        # Get role names for error message
                        required_roles = [role.name.lower() for role in allowed_roles if role <= current_user.role]
                        if not required_roles:
                            required_roles = [role.name.lower() for role in allowed_roles]
                        
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Access denied. Minimum required role: {min_required_role.name.lower()} (level {min_required_role.value}). Your role: {current_user.role.name.lower()} (level {current_user.role.value})"
                        )
                
                # Build kwargs for the original function
                bound_args = sig.bind_partial(
                    request=request,
                    db=db,
                    redis_client=redis_client,
                    current_user=current_user,
                    *args,
                    **kwargs
                )
                bound_args.apply_defaults()
                
                return await func(**bound_args.arguments)
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Authentication error: {str(e)}"
                )
        
        # Separate original parameters into non-default and default
        non_default_params = []
        default_params = []
        
        for name, param in sig.parameters.items():
            if name not in ['request', 'db', 'redis_client', 'current_user']:
                if param.default == inspect.Parameter.empty:
                    non_default_params.append(param)
                else:
                    default_params.append(param)
        
        # Build new signature: non-defaults first, then defaults with dependencies
        new_params = [
            inspect.Parameter('request', inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Request),
        ]
        
        # Add non-default original parameters
        new_params.extend(non_default_params)
        
        # Add dependency parameters with defaults
        new_params.extend([
            inspect.Parameter('db', inspect.Parameter.POSITIONAL_OR_KEYWORD, 
                            annotation=AsyncSession, default=Depends(get_db)),
            inspect.Parameter('redis_client', inspect.Parameter.POSITIONAL_OR_KEYWORD,
                            annotation=redis.Redis, default=Depends(get_redis)),
        ])
        
        # Add default original parameters
        new_params.extend(default_params)
        
        wrapper.__signature__ = sig.replace(parameters=new_params)
        
        return wrapper
    return decorator
