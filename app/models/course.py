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
    
    # For ONE_TIME payments - as per DBMS schema
    price = Column(DECIMAL(10, 2), nullable=True, comment="Used if payment_type is ONE_TIME")

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
    