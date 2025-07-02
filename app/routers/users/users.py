from fastapi import APIRouter
import logging

# Create router
router = APIRouter(prefix="/users", tags=["users"])

logger = logging.getLogger(__name__)