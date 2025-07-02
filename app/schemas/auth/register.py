from pydantic import BaseModel, EmailStr, validator
from typing import Optional


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v
    
class UserRegisterResponse(BaseModel):
    message: str


class UserRegisterVerifyEmail(BaseModel):
    email: EmailStr
    otp: str

class UserRegisterVerifyEmailResponse(BaseModel):
    message: str