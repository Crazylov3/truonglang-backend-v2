import functools
from typing import Callable
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
import inspect
import traceback

from app.database import get_db, get_redis
from app.models.user import UserRole
from app.core.deps import get_current_user


def authentication_required(allowed_role: UserRole = UserRole.STUDENT):
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
            *args,
            **kwargs
        ):
            try:
                # Get current user
                current_user = await get_current_user(request, db)
                
                # Ensure role is UserRole enum for comparison
                user_role = current_user.role
                if isinstance(user_role, int):
                    try:
                        user_role = UserRole(user_role)
                    except ValueError:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Invalid user role: {user_role}"
                        )
                
                # Check role requirements if specified
                if user_role.value < allowed_role.value:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Access denied. Minimum required role: {allowed_role.name.lower()} (level {allowed_role.value}). Your role: {user_role.name.lower()} (level {user_role.value})"
                    )
                
                # Filter arguments to only include what the original function expects
                filtered_kwargs = {}
                param_names = list(sig.parameters.keys())
                
                # Add parameters only if the original function expects them
                if 'request' in param_names:
                    filtered_kwargs['request'] = request
                if 'db' in param_names:
                    filtered_kwargs['db'] = db
                if 'current_user' in param_names:
                    filtered_kwargs['current_user'] = current_user
                
                # Add other parameters from kwargs
                for key, value in kwargs.items():
                    if key in param_names:
                        filtered_kwargs[key] = value
                
                return await func(**filtered_kwargs)
                
            except HTTPException:
                raise
            except Exception as e:
                print(traceback.format_exc())
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Something went wrong: {str(e)}"
                )
        
        # Separate original parameters into non-default and default
        non_default_params = []
        default_params = []
        
        for name, param in sig.parameters.items():
            if name not in ['request', 'db', 'current_user']:
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
        ])
        
        # Add default original parameters
        new_params.extend(default_params)
        
        wrapper.__signature__ = sig.replace(parameters=new_params)
        
        return wrapper
    return decorator
