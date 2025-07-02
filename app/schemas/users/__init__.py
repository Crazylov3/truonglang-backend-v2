# Import from the new modular user schemas
from .user_schemas import (
    UserProfileUpdate,
    UserInfo,
    UsersListResponse,
    UserRoleUpdateRequest,
    UserRoleUpdateResponse,
    DeleteUserResponse,
    AvatarResponse
)

# Keep the existing schemas for backward compatibility
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None

    @validator('bio')
    def validate_bio(cls, v):
        if v and len(v) > 1000:
            raise ValueError('Bio must be 1000 characters or less')
        return v

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    avatar: Optional[str] = None

    @validator('bio')
    def validate_bio(cls, v):
        if v and len(v) > 1000:
            raise ValueError('Bio must be 1000 characters or less')
        return v


class UserResponse(UserBase):
    id: int
    role: UserRole
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

    @property
    def full_name(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email.split("@")[0]


class UserProfile(UserResponse):
    """Extended user profile with additional computed fields."""
    avatar: Optional[str] = None


__all__ = [
    # New modular schemas
    "UserProfileUpdate",
    "UserInfo",
    "UsersListResponse",
    "UserRoleUpdateRequest",
    "UserRoleUpdateResponse",
    "DeleteUserResponse",
    "AvatarResponse",
    
    # Legacy schemas for backward compatibility
    "UserBase",
    "UserUpdate", 
    "UserResponse",
    "UserProfile"
] 