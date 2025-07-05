from fastapi import APIRouter
import logging

router = APIRouter(prefix="/payments", tags=["payments"])

logger = logging.getLogger(__name__)
