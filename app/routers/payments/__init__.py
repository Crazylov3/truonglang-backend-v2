"""Payment routers package."""
from .payments import *
from .instructor_payments import *
from .student_payments import *

# Export the router for the main app to use
__all__ = ["router"] 