# API Routers - Organized by Domain

from . import auth
from . import users  
from . import courses
from . import enrollments

# Export routers for easy access
__all__ = ["auth", "users", "courses", "enrollments"] 