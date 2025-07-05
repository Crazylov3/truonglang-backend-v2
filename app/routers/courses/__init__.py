# Import the main router that includes all sub-routers
from .courses import router
from .admin_courses import *
from .instructor_courses import *
from .student_courses import *
from .public_courses import *

# Export the router for the main app to use
__all__ = ["router"] 