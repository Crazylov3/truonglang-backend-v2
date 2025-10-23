"""API routers for the application."""

from .auth import auth, auth_code, password_reset, register
from .users import users, profile_management, user_management
from .courses import courses, instructor_courses, public_courses
from .enrollments import enrollments, instructor_enrollments, student_enrollments
from .payments import payments, instructor_payments, student_payments
from .attendance import attendance
from .audit import audit

__all__ = [
    "auth", "auth_code", "password_reset", "register",
    "users", "profile_management", "user_management",
    "courses", "instructor_courses", "public_courses",
    "enrollments", "instructor_enrollments", "student_enrollments",
    "payments", "instructor_payments", "student_payments",
    "attendance",
    "audit"
] 