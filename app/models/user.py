from sqlalchemy import Column, Integer, String, DateTime, Enum, func, ForeignKey
from sqlalchemy.orm import relationship
from enum import IntEnum
from app.database import Base


class UserRole(IntEnum):
    STUDENT = 1
    INSTRUCTOR = 2
    STAFF = 3
    ADMIN = 4


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    bio = Column(String(1000), nullable=True)
    role = Column(Enum(UserRole, values_callable=lambda obj: [str(e.value) for e in obj]), default=UserRole.STUDENT, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)  # Track last login
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    created_courses = relationship("Course", back_populates="instructor", foreign_keys="Course.instructor_id")
    enrollments = relationship("Enrollment", back_populates="student")

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email.split("@")[0]  # Fallback to email username

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role.value}')>" 


class UserAvatar(Base):
    __tablename__ = "user_avatars"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    avatar_url = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())