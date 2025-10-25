"""Core database operations.

This module provides centralized database operations that can be used
by both FastAPI endpoints and CLI tools. Each operation function handles
a single database task and accepts a database session as a parameter.
"""

# Import all operations
from . import user
from . import user_profile
from . import course
from . import enrollment
from . import payment
from . import attendance
from . import audit
from . import branch
from . import room
from . import schedule

__all__ = [
    "user",
    "user_profile", 
    "course",
    "enrollment",
    "payment",
    "attendance",
    "audit",
    "branch",
    "room",
    "schedule"
]
