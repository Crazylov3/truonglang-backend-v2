from fastapi import APIRouter
import logging

# Create router
router = APIRouter(prefix="/courses", tags=["courses"])

logger = logging.getLogger(__name__)