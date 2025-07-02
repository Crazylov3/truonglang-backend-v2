from pydantic import BaseModel, EmailStr
from app.schemas.users.user_schemas import UserInfo

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserLoginResponse(BaseModel):
    message: str
    user: UserInfo

class UserLogoutResponse(BaseModel):
    message: str

    