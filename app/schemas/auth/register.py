from pydantic import BaseModel, EmailStr, validator
from typing import Optional


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
class UserRegisterResponse(BaseModel):
    message: str


class UserRegisterVerifyEmail(BaseModel):
    email: EmailStr
    otp: str

class UserRegisterVerifyEmailResponse(BaseModel):
    message: str