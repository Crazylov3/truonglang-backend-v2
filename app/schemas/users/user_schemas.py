from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List
from datetime import datetime, date
from app.models.user import UserRole
from app.schemas.common import PaginatedResponse


class UserProfile(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    date_of_birth: Optional[date] = None
    avatar: Optional[str] = None

class UserInfo(BaseModel):
    id: int
    email: EmailStr
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


class UserRoleUpdateResponse(BaseModel):
    id: int
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


UserSearchResponse = PaginatedResponse[UserInfo]