from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint, Boolean, DECIMAL, Text, text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel


class Enrollment(BaseModel):
    __tablename__ = "enrollments"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Discount fields
    discount_percentage = Column(DECIMAL(5, 2), nullable=False, default=0, comment="Tỉ lệ miễn giảm học phí áp dụng cho lần đăng ký này")
    discount_reason = Column(Text, nullable=True, comment="Lý do miễn giảm")
    discount_approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, comment="ID của người duyệt miễn giảm")

    # Relationships
    student = relationship("User", back_populates="enrollments", foreign_keys=[student_id])
    course = relationship("Course", back_populates="enrollments")
    discount_approver = relationship("User", foreign_keys=[discount_approved_by])

    # Ensure a student can only enroll once per course
    __table_args__ = (
        UniqueConstraint('student_id', 'course_id', name='unique_student_course'),
    )

    def __repr__(self):
        return f"<Enrollment(id={self.id}, student_id={self.student_id}, course_id={self.course_id}, is_active={self.is_active})>" 
  