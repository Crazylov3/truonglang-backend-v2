from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/users", tags=["users"])

