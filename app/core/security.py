from datetime import datetime, timedelta
from typing import Optional, Union
from uuid import UUID
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[int] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + timedelta(seconds=expires_delta)
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_access_token(token: str) -> Optional[dict]:
    """Verify a JWT access token and return the payload."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None


def create_user_token(user_id: Union[UUID, str], user_role: str, expires_delta: Optional[int] = None) -> str:
    """Create a JWT token for a user."""
    token_data = {
        "sub": str(user_id),
        "role": user_role,
        "iat": datetime.utcnow().timestamp()
    }
    return create_access_token(token_data, expires_delta)


def verify_user_token(token: str) -> Optional[dict]:
    """Verify a user JWT token and return user info."""
    payload = verify_access_token(token)
    if not payload:
        return None
    
    # Validate required fields
    user_id = payload.get("sub")
    user_role = payload.get("role")
    
    if not user_id or not user_role:
        return None
    
    try:
        # Try to convert to UUID first, fallback to string
        try:
            user_id_value = UUID(user_id)
        except (ValueError, TypeError):
            user_id_value = user_id
            
        return {
            "user_id": user_id_value,
            "user_role": user_role,
            "issued_at": payload.get("iat"),
            "expires_at": payload.get("exp")
        }
    except Exception:
        return None
