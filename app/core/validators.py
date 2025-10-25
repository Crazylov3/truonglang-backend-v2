"""Common validators for API endpoints."""
from uuid import UUID
from typing import Union
from fastapi import HTTPException, status


def validate_uuid(value: Union[str, UUID]) -> UUID:
    """Validate and convert string to UUID.
    
    Args:
        value: String or UUID to validate
        
    Returns:
        UUID object
        
    Raises:
        HTTPException: If value is not a valid UUID
    """
    if isinstance(value, UUID):
        return value
    
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {value}"
        )


def validate_uuid_param(param_name: str = "id") -> callable:
    """Create a FastAPI dependency for UUID parameter validation.
    
    Args:
        param_name: Name of the parameter for error messages
        
    Returns:
        Dependency function that validates UUID
    """
    def validator(value: str) -> UUID:
        try:
            return UUID(value)
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {param_name} format. Expected UUID, got: {value}"
            )
    return validator