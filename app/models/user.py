from sqlalchemy import Column, String, DateTime, Boolean, func, Enum as SQLAEnum, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from enum import Enum
from .base import BaseModel

class UserRole(str, Enum):
    STUDENT = "STUDENT"
    INSTRUCTOR = "INSTRUCTOR"
    STAFF = "STAFF"
    ADMIN = "ADMIN"


class User(BaseModel):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLAEnum(UserRole), nullable=False, default=UserRole.STUDENT)
    need_change_email = Column(Boolean, nullable=False, default=False)
    need_change_password = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    created_courses = relationship("Course", back_populates="creator", foreign_keys="Course.creator_id")
    enrollments = relationship("Enrollment", back_populates="student", foreign_keys="[Enrollment.student_id]")
    
    # Audit logging relationship
    audit_logs = relationship("AuditLog", back_populates="user")

    @property
    def full_name(self):
        if self.profile and self.profile.first_name and self.profile.last_name:
            return f"{self.profile.first_name} {self.profile.last_name}"
        return self.email.split("@")[0]  # Fallback to email username

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role={self.role})>"