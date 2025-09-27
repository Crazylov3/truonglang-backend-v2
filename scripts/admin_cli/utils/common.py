"""Common utilities for admin CLI."""

import sys
from pathlib import Path
from typing import Optional
import asyncio
from functools import wraps

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from app.models import UserRole


def role_from_string(role_str: str) -> UserRole:
    """Convert string to UserRole enum."""
    role_map = {
        'student': UserRole.STUDENT,
        'instructor': UserRole.INSTRUCTOR,
        'staff': UserRole.STAFF,
        'admin': UserRole.ADMIN,
        '1': UserRole.STUDENT,
        '2': UserRole.INSTRUCTOR,
        '3': UserRole.STAFF,
        '4': UserRole.ADMIN,
    }
    return role_map.get(role_str.lower(), UserRole.STUDENT)


def role_to_string(role: UserRole) -> str:
    """Convert UserRole enum to string."""
    role_map = {
        UserRole.STUDENT: 'Student',
        UserRole.INSTRUCTOR: 'Instructor',
        UserRole.STAFF: 'Staff',
        UserRole.ADMIN: 'Admin',
    }
    return role_map.get(role, 'Unknown')


def async_command(f):
    """Decorator to run async functions in click commands."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


def parse_date(ctx=None, param=None, value=None):
    """Parse date string to datetime object. Can be used as Click callback."""
    # Handle both direct calls and Click callback usage
    if ctx is None and param is None:
        # Direct call: parse_date("2024-01-01")
        date_str = value
    else:
        # Click callback: parse_date(ctx, param, value)
        date_str = value
    
    if not date_str:
        return None
    
    from datetime import datetime
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse date: {date_str}. Try formats like: YYYY-MM-DD")