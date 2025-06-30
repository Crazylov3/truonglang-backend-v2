from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.orm import object_session
from enum import IntEnum
from app.database import Base


class CourseStatus(IntEnum):
    DRAFT = 1
    PUBLISHED = 2
    ARCHIVED = 3


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(CourseStatus, values_callable=lambda obj: [str(e.value) for e in obj]), default=CourseStatus.DRAFT, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    instructor = relationship("User", back_populates="created_courses", foreign_keys=[instructor_id])
    enrollments = relationship("Enrollment", back_populates="course")

    @property
    def enrolled_students_count(self):
        try:
            # Check if we're in an active session and if enrollments are loaded
            session = object_session(self)
            if session is None:
                # No active session - check if enrollments are already loaded
                if hasattr(self, '_sa_instance_state'):
                    state = self._sa_instance_state
                    if 'enrollments' in state.loaded_lazy_loaded_attrs:
                        return len(self.enrollments)
                # Return 0 if no session and enrollments not loaded
                return 0
            
            # We have an active session, safe to access enrollments
            return len(self.enrollments)
        except (DetachedInstanceError, AttributeError, RuntimeError):
            # Return 0 for any session-related errors
            return 0

    def __repr__(self):
        try:
            status_value = self.status.value if self.status else 'unknown'
            title = self.title if hasattr(self, 'title') else 'unknown'
            return f"<Course(id={self.id}, title='{title}', status='{status_value}')>"
        except (DetachedInstanceError, AttributeError):
            # Use __dict__ to avoid SQLAlchemy attribute access for detached instances
            obj_dict = object.__getattribute__(self, '__dict__')
            course_id = obj_dict.get('id', 'unknown')
            course_title = obj_dict.get('title', 'unknown')
            course_status = obj_dict.get('status', 'unknown')
            return f"<Course(id={course_id}, title='{course_title}', status='{course_status}')>" 
    