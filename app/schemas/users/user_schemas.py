from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List
from datetime import datetime, date
from app.models.user import UserRole
from app.schemas.common import PaginatedResponse


class UserProfile(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    display_name: Optional[str] = Field(None, max_length=100)
    date_of_birth: Optional[date] = None
    headline: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = Field(None, max_length=1000)
    location: Optional[str] = Field(None, max_length=100)
    language: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)
    website_url: Optional[str] = Field(None, max_length=255)
    linkedin_url: Optional[str] = Field(None, max_length=255)
    twitter_handle: Optional[str] = Field(None, max_length=50)
    github_url: Optional[str] = Field(None, max_length=255)
    avatar: Optional[str] = Field(None, description="Base64 encoded avatar image")

class UserInfo(BaseModel):
    id: int
    email: EmailStr
    role: UserRole
    last_login_at: Optional[datetime] = None
    created_at: datetime
    profile: Optional[UserProfile] = None

    @property
    def full_name(self) -> str:
        if self.profile:
            return f"{self.profile.first_name} {self.profile.last_name}"
        return self.email.split("@")[0]

class UserProfileUpdate(UserProfile):
    @validator('bio')
    def validate_bio(cls, v):
        if v and len(v) > 1000:
            raise ValueError('Bio must be 1000 characters or less')
        return v

class UserInfoResponse(UserInfo):
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def public_name(self) -> str:
        return self.display_name if self.display_name else self.full_name

class UsersListResponse(BaseModel):
    users: List[UserInfo]
    total: int
    skip: int
    limit: int


class UserRoleUpdateRequest(BaseModel):
    new_role: UserRole


class UserRoleUpdateResponse(BaseModel):
    id: int
    email: EmailStr
    role: UserRole
    message: str


class DeleteUserResponse(BaseModel):
    message: str


class AvatarResponse(BaseModel):
    avatar: str 