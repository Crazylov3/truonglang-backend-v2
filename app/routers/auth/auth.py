from fastapi import APIRouter
import logging
from app.core.decorators import ensure_csrf_token

# Create router
router = APIRouter(prefix="/auth", tags=["authentication"])

logger = logging.getLogger(__name__)

@router.get("/csrf-token", response_model=dict)
@ensure_csrf_token
async def get_csrf_token():
    """Generate and return a CSRF token - decorator handles all the complexity."""
    return {"message": "CSRF token generated successfully"}
