from sqlalchemy import Column, String, Text, DateTime, ForeignKey, DECIMAL, Boolean, text, Integer
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel


class Course(BaseModel):
    __tablename__ = "courses"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=True)
    teacher_name = Column(String(255), nullable=True)
    
    # Branch information
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True, comment="Chi nhánh nơi tổ chức khóa học")
    
    # Pricing and media
    price = Column(DECIMAL(10, 2), nullable=True)
    preview_picture_path = Column(String(500), nullable=True)
    group_chat_link = Column(String(500), nullable=True, comment="Link nhóm Zalo, Facebook, etc. của lớp học")

    # Relationships
    creator = relationship("User", back_populates="created_courses", foreign_keys=[creator_id])
    enrollments = relationship("Enrollment", back_populates="course")
    course_documents = relationship("CourseDocument", back_populates="course", cascade="all, delete-orphan")
    branch = relationship("Branch", back_populates="courses")

    @property
    def enrolled_students_count(self):
        """Get count of enrolled students."""
        return len([e for e in self.enrollments if e.is_active]) if self.enrollments else 0
    
    def __repr__(self):
        return f"<Course(id={self.id}, title='{self.title}', creator_id={self.creator_id})>"




