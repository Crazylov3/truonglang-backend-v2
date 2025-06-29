from app.core.csrf import CSRFManager
import functools
from typing import Callable
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import inspect
from app.core.cookies import set_cookie
from app.config import settings


def ensure_csrf_token(func: Callable) -> Callable:
    """
    Decorator to generate and return CSRF token in response.

    WORKS WITH ANY SIGNATURE - automatically injects request:

    @ensure_csrf_token
    async def get_token():
        return {"message": "Ready"}

    @ensure_csrf_token  
    async def get_token_with_params(user_id: int):
        return {"message": f"Ready for user {user_id}"}
    """
    # Get the original function signature
    original_sig = inspect.signature(func)

    @functools.wraps(func)
    async def wrapper(request: Request, **kwargs):
        # Call original function with only the parameters it expects
        filtered_kwargs = {}
        param_names = list(original_sig.parameters.keys())
        
        # Add request only if the original function expects it
        if 'request' in param_names:
            filtered_kwargs['request'] = request
            
        # Add other parameters
        for key, value in kwargs.items():
            if key in param_names:
                filtered_kwargs[key] = value

        result = await func(**filtered_kwargs)

        # Check if CSRF token already exists in cookie
        existing_token = request.cookies.get("csrftoken")
        if not existing_token:
            # Generate new CSRF token
            csrf_manager = CSRFManager()
            csrf_token = csrf_manager.generate_csrf_token()
        else:
            csrf_token = existing_token

        # Convert result to dict if needed and add CSRF token
        if isinstance(result, dict):
            result["csrf_token"] = csrf_token
            response = JSONResponse(content=result)
        else:
            response = result
            if isinstance(response, JSONResponse):
                # Try to add CSRF token to existing JSON content
                try:
                    import json
                    content = json.loads(response.body.decode() if response.body else "{}")
                    if isinstance(content, dict):
                        content["csrf_token"] = csrf_token
                        response = JSONResponse(content=content)
                except:
                    pass

        # Convert to JSONResponse if still not
        if not isinstance(response, JSONResponse):
            if isinstance(result, dict):
                response = JSONResponse(content=result)
            else:
                response = JSONResponse(content={"result": result, "csrf_token": csrf_token})

        # Set CSRF token in cookie and header
        if not existing_token:
            set_cookie(response, "csrftoken", csrf_token, 
                      secure=not settings.debug, httponly=False)  # Must be readable by JS
        
        response.headers["X-Csrftoken"] = csrf_token
        
        return response

    # Create new signature with proper parameter ordering
    # 1. Non-default parameters first
    # 2. Default parameters last
    
    non_default_params = []
    default_params = []
    
    # Separate original parameters
    for name, param in original_sig.parameters.items():
        if name not in ['request']:
            if param.default == inspect.Parameter.empty:
                non_default_params.append(param)
            else:
                default_params.append(param)
    
    # Build final parameter list
    new_params = [
        # Start with request (no default)
        inspect.Parameter('request', inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Request)
    ]
    
    # Add non-default original parameters
    new_params.extend(non_default_params)
    
    # Add default parameters
    new_params.extend(default_params)

    # Set the new signature for FastAPI
    wrapper.__signature__ = original_sig.replace(parameters=new_params)
    
    return wrapper


def csrf_protect(func: Callable) -> Callable:
    """
    Decorator to require CSRF token validation using Django's approach.
    Compares token in cookie with token in header/form.
    """
    original_sig = inspect.signature(func)
    
    @functools.wraps(func)
    async def wrapper(request: Request, **kwargs):
        # Skip CSRF for GET, HEAD, OPTIONS requests
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            # Call original function with filtered parameters
            filtered_kwargs = {}
            param_names = list(original_sig.parameters.keys())

            if 'request' in param_names:
                filtered_kwargs['request'] = request

            for key, value in kwargs.items():
                if key in param_names:
                    filtered_kwargs[key] = value

            return await func(**filtered_kwargs)
        
        # Validate CSRF token using Django's approach
        csrf_manager = CSRFManager()
        is_valid = await csrf_manager.validate_csrf_token_async(request)
        
        if not is_valid:
            raise HTTPException(
                status_code=403, 
                detail="CSRF token validation failed."
            )
        
        # Call original function with filtered parameters
        filtered_kwargs = {}
        param_names = list(original_sig.parameters.keys())

        # Add request only if the original function expects it
        if 'request' in param_names:
            filtered_kwargs['request'] = request

        # Add other parameters
        for key, value in kwargs.items():
            if key in param_names:
                filtered_kwargs[key] = value

        return await func(**filtered_kwargs)

    # Create new signature with proper parameter ordering
    # 1. Non-default parameters first
    # 2. Default parameters last
    
    non_default_params = []
    default_params = []
    
    # Separate original parameters
    for name, param in original_sig.parameters.items():
        if name not in ['request']:
            if param.default == inspect.Parameter.empty:
                non_default_params.append(param)
            else:
                default_params.append(param)
    
    # Build final parameter list
    new_params = [
        # Start with request (no default)
        inspect.Parameter('request', inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Request)
    ]
    
    # Add non-default original parameters
    new_params.extend(non_default_params)
    
    # Add default parameters
    new_params.extend(default_params)

    # Set the new signature for FastAPI
    wrapper.__signature__ = original_sig.replace(parameters=new_params)
    return wrapper