from fastapi import APIRouter, status

# Import endpoint functions
from .endpoints import (
    register,
    verify_email_and_create_account,
    login,
    logout,
    forgot_password,
    reset_password,
    change_password,
    get_csrf_token,
    verify_otp
)

# Import schemas for response models
from app.schemas.auth import LoginResponse, LogoutResponse

router = APIRouter(prefix="/auth", tags=["authentication"])

# # Register endpoint routes
router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)(register)
router.post("/login", response_model=LoginResponse)(login)
router.post("/login/verify-email", response_model=dict)(verify_email_and_create_account)
router.post("/logout", response_model=LogoutResponse)(logout)
router.post("/forgot-password", response_model=dict)(forgot_password)
router.post("/reset-password", response_model=dict)(reset_password)
router.post("/change-password", response_model=dict)(change_password)
router.get("/csrf-token", response_model=dict)(get_csrf_token)
router.get("/verify-otp", response_model=dict)(verify_otp)  # For testing OTP 