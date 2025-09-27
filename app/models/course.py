from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, DECIMAL, Boolean
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
    location = Column(String(255), nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    teacher_name = Column(String(255), nullable=True)
    
    # For ONE_TIME payments - as per DBMS schema
    price = Column(DECIMAL(10, 2), nullable=True, comment="Used if payment_type is ONE_TIME")
    preview_picture_path = Column(String(500), nullable=True, comment="Path to course preview picture for lazy loading")

    # Relationships
    creator = relationship("User", back_populates="created_courses", foreign_keys=[creator_id])
    enrollments = relationship("Enrollment", back_populates="course")
    edit_permissions = relationship("CourseEditPermission", back_populates="course")
    payment_periods = relationship("CoursePaymentPeriod", back_populates="course")
    course_documents = relationship("CourseDocument", back_populates="course")

    @property
    def enrolled_students_count(self):
        """Get count of enrolled students."""
        return len([e for e in self.enrollments if e.is_active]) if self.enrollments else 0
    
    def __repr__(self):
        return f"<Course(id={self.id}, title='{self.title}', creator_id={self.creator_id})>"


class CourseEditPermission(BaseModel):
    __tablename__ = "course_edit_permissions"

    course_id = Column(Integer, ForeignKey("courses.id"), primary_key=True)
    instructor_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    course = relationship("Course", back_populates="edit_permissions", foreign_keys=[course_id])
    instructor = relationship("User", back_populates="edit_permissions", foreign_keys=[instructor_id])
    granted_by_user = relationship("User", back_populates="granted_edit_permissions", foreign_keys=[granted_by])

    def __repr__(self):
        return f"<CourseEditPermission(course_id={self.course_id}, instructor_id={self.instructor_id})>"


class CourseDocument(BaseModel):
    __tablename__ = "course_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    document_path = Column(String(500), nullable=True, comment="Path to document file")
    document_name = Column(String(255), nullable=False)
    document_type = Column(String(50), nullable=True, comment="File type: PDF, DOCX, etc.")
    document_size = Column(Integer, nullable=True, comment="File size in bytes")
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    course = relationship("Course", back_populates="course_documents")
    uploader = relationship("User", foreign_keys=[uploaded_by])
    
    def __repr__(self):
        return f"<CourseDocument(id={self.id}, course_id={self.course_id}, document_name='{self.document_name}')>"