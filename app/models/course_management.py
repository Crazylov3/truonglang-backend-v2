from sqlalchemy import Column, String, DateTime, ForeignKey, DECIMAL, Boolean, Integer, text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel


class CourseEditPermission(BaseModel):
    __tablename__ = "course_edit_permissions"

    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), primary_key=True)
    instructor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    course = relationship("Course", foreign_keys=[course_id])
    instructor = relationship("User", foreign_keys=[instructor_id])
    granted_by_user = relationship("User", foreign_keys=[granted_by])

    def __repr__(self):
        return f"<CourseEditPermission(course_id={self.course_id}, instructor_id={self.instructor_id})>"


class CoursePaymentPeriod(BaseModel):
    __tablename__ = "course_payment_period"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Relationships
    course = relationship("Course", foreign_keys=[course_id])
    created_by_user = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<CoursePaymentPeriod(id={self.id}, course_id={self.course_id}, amount={self.amount})>"


class CourseDocument(BaseModel):
    __tablename__ = "course_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False, index=True)
    document_path = Column(String(500), nullable=True, comment="Path to document file")
    document_name = Column(String(255), nullable=False)
    document_type = Column(String(50), nullable=True, comment="File type: PDF, DOCX, etc.")
    document_size = Column(Integer, nullable=True, comment="File size in bytes")
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Relationships
    course = relationship("Course", foreign_keys=[course_id], back_populates="course_documents")
    uploader = relationship("User", foreign_keys=[uploaded_by])
    
    def __repr__(self):
        return f"<CourseDocument(id={self.id}, course_id={self.course_id}, document_name='{self.document_name}')>"