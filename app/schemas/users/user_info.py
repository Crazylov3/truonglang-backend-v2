from pydantic import BaseModel, EmailStr, validator
from typing import Optional

class UserInfo(BaseModel):
    id: int
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None