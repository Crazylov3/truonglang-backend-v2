import functools
from typing import Set, Union, Callable, Any, List
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
import inspect

from app.database import get_db, get_redis
from app.models.user import User, UserRole
from app.core.deps import get_current_user
from app.core.csrf import CSRFManager


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


def csrf_protect(func: Callable) -> Callable:
    """
    Decorator to require CSRF token validation.
    
    Usage:
        @csrf_protect
        async def my_endpoint(...):
            pass
    """
    sig = inspect.signature(func)
    
    @functools.wraps(func)
    async def wrapper(
        request: Request,
        redis_client: redis.Redis = Depends(get_redis),
        *args,
        **kwargs
    ):
        # Skip CSRF for GET, HEAD, OPTIONS requests
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            bound_args = sig.bind_partial(request=request, redis_client=redis_client, *args, **kwargs)
            bound_args.apply_defaults()
            return await func(**bound_args.arguments)
        
        # Get session ID from cookie
        session_id = request.cookies.get("session_id")
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session required for CSRF protection"
            )
        
        # Get CSRF token from header or form data
        csrf_token = request.headers.get("X-CSRF-Token")
        if not csrf_token:
            # Try to get from form data if content-type is form
            content_type = request.headers.get("content-type", "")
            if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                try:
                    form_data = await request.form()
                    csrf_token = form_data.get("csrf_token")
                except:
                    pass
        
        if not csrf_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token required in X-CSRF-Token header or csrf_token form field"
            )
        
        # Validate CSRF token
        csrf_manager = CSRFManager(redis_client)
        is_valid = await csrf_manager.validate_csrf_token(session_id, csrf_token)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid CSRF token"
            )
        
        # Call original function with proper parameters
        bound_args = sig.bind_partial(request=request, redis_client=redis_client, *args, **kwargs)
        bound_args.apply_defaults()
        return await func(**bound_args.arguments)
    
    # Create new signature: keep original parameters but inject dependencies where needed
    new_params = []
    
    for name, param in sig.parameters.items():
        if name == 'request':
            # Ensure request has proper annotation
            new_params.append(
                inspect.Parameter('request', inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Request)
            )
        elif name == 'redis_client':
            # Add redis_client as dependency
            new_params.append(
                inspect.Parameter('redis_client', inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                annotation=redis.Redis, default=Depends(get_redis))
            )
        else:
            # Keep original parameter as-is
            new_params.append(param)
    
    # If request or redis_client weren't in original signature, add them at appropriate positions
    param_names = [p.name for p in new_params]
    
    if 'request' not in param_names:
        new_params.insert(0, inspect.Parameter('request', inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Request))
    
    if 'redis_client' not in param_names:
        # Add redis_client as dependency after request but before other parameters without defaults
        insert_index = 1  # After request
        for i, param in enumerate(new_params[1:], 1):
            if param.default != inspect.Parameter.empty:
                insert_index = i
                break
        else:
            insert_index = len(new_params)
        
        new_params.insert(insert_index, 
                         inspect.Parameter('redis_client', inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                         annotation=redis.Redis, default=Depends(get_redis)))
    
    wrapper.__signature__ = sig.replace(parameters=new_params)
    
    return wrapper


# Convenience decorators for specific roles
def require_student(func: Callable) -> Callable:
    """Decorator to require student role or above (any authenticated user)."""
    return authentication_required(UserRole.STUDENT)(func)


def require_instructor(func: Callable) -> Callable:
    """Decorator to require instructor role or above (instructor, staff, admin)."""
    return authentication_required(UserRole.INSTRUCTOR)(func)


def require_staff(func: Callable) -> Callable:
    """Decorator to require staff role or above (staff, admin)."""
    return authentication_required(UserRole.STAFF)(func)


def require_admin(func: Callable) -> Callable:
    """Decorator to require admin role only."""
    return authentication_required(UserRole.ADMIN)(func)


# Legacy convenience decorators (now simplified with hierarchy)
def require_instructor_or_above(func: Callable) -> Callable:
    """Decorator to require instructor role or above. Same as require_instructor."""
    return authentication_required(UserRole.INSTRUCTOR)(func)


def require_staff_or_admin(func: Callable) -> Callable:
    """Decorator to require staff role or above. Same as require_staff."""
    return authentication_required(UserRole.STAFF)(func) 