"""Admin CLI command modules."""

from .users import users_group
from .courses import courses_group
from .system import system_group
from .audit import audit_group
from .attendance import attendance_group
from .reports import reports_group

__all__ = [
    'users_group',
    'courses_group', 
    'system_group',
    'audit_group',
    'attendance_group',
    'reports_group'
]