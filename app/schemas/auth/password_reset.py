from pydantic import BaseModel, EmailStr
from app.schemas.users import UserInfo


class UserPasswordReset(BaseModel):
    email: EmailStr

class UserPasswordResetResponse(BaseModel):
    message: str

class UserPasswordResetVerifyEmail(BaseModel):
    new_password: str
    email: EmailStr
    otp: str 

class UserPasswordResetVerifyEmailResponse(BaseModel):
    message: str
