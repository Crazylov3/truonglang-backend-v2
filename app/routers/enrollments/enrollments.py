from fastapi import APIRouter
import logging

router = APIRouter(prefix="/enrollments", tags=["enrollments"])

logger = logging.getLogger(__name__)