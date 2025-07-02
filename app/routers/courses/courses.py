from fastapi import APIRouter
import logging

# Create router
router = APIRouter(prefix="/courses", tags=["courses"])

logger = logging.getLogger(__name__)

# Import sub-routers to register their endpoints
from . import public_courses
from . import student_courses
from . import instructor_courses
from . import admin_courses 