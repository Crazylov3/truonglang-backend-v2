from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, DECIMAL
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import BaseModel


class Course(BaseModel):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # For ONE_TIME payments - as per DBMS schema
    price = Column(DECIMAL(10, 2), nullable=True, comment="Used if payment_type is ONE_TIME")

    # Details
    location = Column(String(255), nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    teacher_name = Column(String(255), nullable=True)


    # Relationships - only essential ones from DBMS
    creator = relationship("User", back_populates="created_courses", foreign_keys=[creator_id])
    enrollments = relationship("Enrollment", back_populates="course")
    payments = relationship("Payment", back_populates="course")

    @property
    def enrolled_students_count(self):
        """Get count of enrolled students."""
        return len(self.enrollments) if self.enrollments else 0

    def __repr__(self):
        return f"<Course(id={self.id}, title='{self.title}', creator_id={self.creator_id})>" 


class CourseEditPermission(BaseModel):
    __tablename__ = "course_edit_permissions"

    course_id = Column(Integer, ForeignKey("courses.id"), primary_key=True)
    instructor_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    course = relationship("Course", back_populates="edit_permissions", foreign_keys=[course_id])
    instructor = relationship("User", back_populates="edit_permissions", foreign_keys=[instructor_id])
    granted_by_user = relationship("User", back_populates="granted_edit_permissions", foreign_keys=[granted_by])

    def __repr__(self):
        return f"<CourseEditPermission(course_id={self.course_id}, instructor_id={self.instructor_id})>"