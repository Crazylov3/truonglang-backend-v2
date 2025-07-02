from sqlalchemy import Column, Integer, ForeignKey, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import BaseModel


class StudentActivityLog(BaseModel):
    __tablename__ = "student_activity_log"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    activity_date = Column(Date, nullable=False)

    # Relationships
    student = relationship("User", back_populates="activity_logs")
    course = relationship("Course", back_populates="activity_logs")

    # Prevents duplicate logs for the same student, in the same course, on the same day.
    __table_args__ = (
        UniqueConstraint('student_id', 'course_id', 'activity_date', name='unique_student_course_activity'),
    )

    def __repr__(self):
        return f"<StudentActivityLog(id={self.id}, student_id={self.student_id}, course_id={self.course_id}, activity_date={self.activity_date})>" 