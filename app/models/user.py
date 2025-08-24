from sqlalchemy import Column, Integer, String, DateTime, Boolean, func
from sqlalchemy.orm import relationship
from enum import IntEnum
from .base import BaseModel

class UserRole(IntEnum):
    STUDENT = 1
    INSTRUCTOR = 2
    STAFF = 3
    ADMIN = 4


class User(BaseModel):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Integer, nullable=False, default=UserRole.STUDENT)
    need_change_email = Column(Boolean, nullable=False, default=False)
    need_change_password = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    created_courses = relationship("Course", back_populates="creator", foreign_keys="Course.creator_id")
    enrollments = relationship("Enrollment", back_populates="student")
    
    # Updated relationships for new billing structure
    granted_edit_permissions = relationship("CourseEditPermission", back_populates="granted_by_user", foreign_keys="CourseEditPermission.granted_by")
    edit_permissions = relationship("CourseEditPermission", back_populates="instructor", foreign_keys="CourseEditPermission.instructor_id")
    created_payment_periods = relationship("CoursePaymentPeriod", back_populates="created_by_user")
    
    # New relationships for attendance system
    card_assignments = relationship("CardAssignment", back_populates="student")
    attendance_records = relationship("AttendanceRecord", back_populates="student")

    @property
    def full_name(self):
        if self.profile and self.profile.first_name and self.profile.last_name:
            return f"{self.profile.first_name} {self.profile.last_name}"
        return self.email.split("@")[0]  # Fallback to email username

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role={self.role})>"