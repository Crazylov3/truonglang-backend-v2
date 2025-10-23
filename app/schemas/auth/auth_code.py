from pydantic import BaseModel, Field
from typing import Optional
from app.schemas.users.user_schemas import UserInfo


class AuthCodeRequest(BaseModel):
    """Request to generate authentication code after login."""
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")
    return_auth_code: bool = Field(True, description="Return auth code instead of setting cookies")


class AuthCodeResponse(BaseModel):
    """Response containing authentication code."""
    message: str = Field(..., description="Success message")
    auth_code: str = Field(..., description="5-minute authentication code")
    expires_in: int = Field(..., description="Code expiration time in seconds")
    user: UserInfo = Field(..., description="User information")


class ExchangeAuthCodeRequest(BaseModel):
    """Request to exchange auth code for tokens."""
    auth_code: str = Field(..., description="Authentication code from login")


class ExchangeAuthCodeResponse(BaseModel):
    """Response after exchanging auth code for tokens."""
    message: str = Field(..., description="Success message")
    expires_in: int = Field(..., description="Access token expiration in seconds")
    user: UserInfo = Field(..., description="User information")
