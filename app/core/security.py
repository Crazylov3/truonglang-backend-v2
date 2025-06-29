from datetime import datetime, timedelta
from typing import Optional
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


def create_password_reset_token(email: str) -> str:
    """Create a password reset token (still uses JWT for email-based tokens)."""
    data = {"sub": email, "type": "password_reset"}
    expires_delta = timedelta(minutes=settings.password_reset_expire_minutes or 30)
    
    expire = datetime.utcnow() + expires_delta
    data.update({"exp": expire})
    
    encoded_jwt = jwt.encode(data, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_password_reset_token(token: str) -> Optional[str]:
    """Verify a password reset token and return the email."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") == "password_reset":
            return payload.get("sub")
        return None
    except JWTError:
        return None 