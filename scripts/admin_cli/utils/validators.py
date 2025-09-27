"""Validation utilities for admin CLI."""

import re
import click
from typing import Optional


def validate_email(ctx, param, value):
    """Validate email format."""
    if not value:
        return value
    
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, value):
        raise click.BadParameter(f"Invalid email format: {value}")
    return value.lower()


def validate_phone(ctx, param, value):
    """Validate phone number format."""
    if not value:
        return value
    
    # Remove all non-digit characters
    cleaned = re.sub(r'\D', '', value)
    
    # Check if it's a valid length (10-15 digits)
    if not 10 <= len(cleaned) <= 15:
        raise click.BadParameter("Phone number must be 10-15 digits")
    
    return cleaned


def validate_password(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password strength.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    
    return True, None


def validate_date(ctx, param, value):
    """Validate date format."""
    if not value:
        return value
    
    from .common import parse_date
    try:
        return parse_date(value)
    except ValueError as e:
        raise click.BadParameter(str(e))


def validate_positive_number(ctx, param, value):
    """Validate that a number is positive."""
    if value is not None and value <= 0:
        raise click.BadParameter(f"{param.name} must be a positive number")
    return value