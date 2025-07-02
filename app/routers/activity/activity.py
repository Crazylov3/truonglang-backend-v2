from fastapi import APIRouter
import logging

# Create router
router = APIRouter(prefix="/activity", tags=["activity"])

logger = logging.getLogger(__name__)

# Import sub-routers to register their endpoints
from . import student_activity
from . import instructor_activity
from . import admin_activity 