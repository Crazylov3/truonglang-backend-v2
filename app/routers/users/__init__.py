from fastapi import APIRouter, status
from typing import List, Optional

# Import decorated endpoint functions
from .endpoints import (
    get_current_user_profile,
    update_current_user_profile,
    get_all_users,
    create_user,
    get_user_by_id,
    update_user_role,
    delete_user
)

# Import schemas for response models
from app.schemas.users import UserResponse, UserProfile
from app.models.user import UserRole

router = APIRouter(prefix="/users", tags=["users"])

# User profile endpoints
router.get("/me", response_model=UserProfile)(get_current_user_profile)
router.put("/me", response_model=UserResponse)(update_current_user_profile)

# Admin/Staff user management endpoints
router.get("/", response_model=dict)(get_all_users)
router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)(create_user)
router.get("/{user_id}", response_model=UserResponse)(get_user_by_id)
router.put("/{user_id}/role", response_model=UserResponse)(update_user_role)
router.delete("/{user_id}", response_model=dict)(delete_user) 