from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from uuid import UUID
from app.models.user import UserRole
from app.schemas.common import PaginatedResponse, BaseUUIDModel


class UserProfile(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    date_of_birth: Optional[date] = None
    avatar: Optional[str] = None
    current_school: Optional[str] = Field(None, max_length=255)
    current_grade: Optional[str] = Field(None, max_length=50)
    default_discount_percentage: Optional[float] = Field(0.0, ge=0, le=100)

class UserInfo(BaseUUIDModel):
    public_id: int
    email: str
    role: UserRole
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    profile: Optional[UserProfile] = None

    @property
    def full_name(self) -> str:
        if self.profile:
            return f"{self.profile.first_name} {self.profile.last_name}"
        return self.email.split("@")[0]

class UserProfileUpdate(UserProfile):
    pass

UsersListResponse = PaginatedResponse[UserInfo]


class UserRoleUpdateRequest(BaseModel):
    new_role: UserRole


class UserRoleUpdateResponse(BaseUUIDModel):
    email: EmailStr
    role: UserRole
    message: str


class DeleteUserResponse(BaseModel):
    message: str


class AvatarResponse(BaseModel):
    avatar: str 


class TotalUsersResponse(BaseModel):
    total: int
    by_role: dict[UserRole, int]




# Temporal User Schemas
class TemporalUserCreate(BaseModel):
    """Schema for creating a temporal user (student)."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    current_school: Optional[str] = Field(None, max_length=255)
    current_grade: Optional[str] = Field(None, max_length=50)
    default_discount_percentage: Optional[float] = Field(0.0, ge=0, le=100)


class TemporalUserResponse(BaseModel):
    """Response for created temporal user."""
    id: UUID
    public_id: int
    email: str
    password: str
    role: UserRole
    profile: UserProfile
    message: str


class TemporalUserBulkCreate(BaseModel):
    """Schema for bulk creating temporal users from CSV."""
    message: str
    total_created: int
    failed_count: int
    created_users: List[TemporalUserResponse]
    failed_rows: List[Dict[str, Any]]


class UserUpdate(BaseModel):
    """Schema for updating user information and profile (partial update)."""
    # User fields
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6, max_length=100)
    role: Optional[UserRole] = None
    need_change_email: Optional[bool] = None
    need_change_password: Optional[bool] = None
    
    # Profile fields
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    date_of_birth: Optional[date] = None
    current_school: Optional[str] = Field(None, max_length=255)
    current_grade: Optional[str] = Field(None, max_length=50)
    default_discount_percentage: Optional[float] = Field(None, ge=0, le=100)


class UserUpdateResponse(BaseModel):
    """Response for updated user information."""
    id: UUID
    public_id: int
    email: str
    role: UserRole
    need_change_email: bool
    need_change_password: bool
    profile: Optional[UserProfile] = None
    message: str