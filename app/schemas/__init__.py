# Database Schemas - Organized by Domain

# Import common schemas
from .common import (
    PaginatedResponse,
    MessageResponse,
    ErrorResponse,
    HealthResponse,
    BaseTimestampedModel
)

# Import domain-specific schemas
from .auth import *
from .users import *
from .courses import *
from .enrollments import *

# Export all schemas for backward compatibility
__all__ = [
    # Common schemas
    "PaginatedResponse",
    "MessageResponse", 
    "ErrorResponse",
    "HealthResponse",
    "BaseTimestampedModel",
    
    # Auth schemas
    "UserRegister",
    "UserLogin", 
    "Token",
    "TokenData",
    "VerifyEmail",
    "ForgotPassword",
    "ResetPassword",
    "ChangePassword",
    
    # User schemas
    "UserBase",
    "UserCreate",
    "UserUpdate", 
    "UserResponse",
    "UserProfile",
    
    # Course schemas
    "CourseBase",
    "CourseCreate",
    "CourseUpdate",
    "CourseResponse",
    "CourseDetailResponse",
    "CourseListResponse",
    
    # Enrollment schemas
    "EnrollmentResponse",
    "EnrollmentDetailResponse"
] 