from sqlalchemy import Column, Integer, String, DateTime, func
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
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    created_courses = relationship("Course", back_populates="creator", foreign_keys="Course.creator_id")
    enrollments = relationship("Enrollment", back_populates="student")
    payments = relationship("Payment", back_populates="user")
    activity_logs = relationship("StudentActivityLog", back_populates="student")

    @property
    def full_name(self):
        if self.profile and self.profile.first_name and self.profile.last_name:
            return f"{self.profile.first_name} {self.profile.last_name}"
        elif self.profile and self.profile.display_name:
            return self.profile.display_name
        return self.email.split("@")[0]  # Fallback to email username

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role={self.role})>"