# Import the main router that includes all sub-routers
from .courses import router
from .instructor_courses import *
from .public_courses import *
from .course_documents import *  # This imports the routes registered on the shared router

# Export the router for the main app to use
__all__ = ["router"] 