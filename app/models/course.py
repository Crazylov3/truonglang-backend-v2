from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, DECIMAL, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.orm import object_session
from enum import IntEnum
from .base import BaseModel


class CoursePaymentType(IntEnum):
    ONE_TIME = 1
    SUBSCRIPTION = 2


class BillingInterval(IntEnum):
    DAY = 1
    WEEK = 2
    MONTH = 3
    YEAR = 4


class Course(BaseModel):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Payment model fields
    payment_type = Column(Integer, nullable=False, default=CoursePaymentType.ONE_TIME)
    
    # For ONE_TIME payments
    price = Column(DECIMAL(10, 2), nullable=True, comment="Used if payment_type is ONE_TIME")
    
    # For SUBSCRIPTION payments
    subscription_price = Column(DECIMAL(10, 2), nullable=True, comment="Price per billing interval")
    billing_interval = Column(Integer, nullable=True, comment="e.g., MONTH, DAY")
    billing_interval_count = Column(Integer, nullable=True, comment="e.g., for 'every 10 days', interval is DAY and count is 10")
    is_usage_based = Column(Boolean, default=False, comment="Set to true for 'learning days' model")

    # Relationships
    creator = relationship("User", back_populates="created_courses", foreign_keys=[creator_id])
    enrollments = relationship("Enrollment", back_populates="course")
    payments = relationship("Payment", back_populates="course")
    activity_logs = relationship("StudentActivityLog", back_populates="course")

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
            payment_type_value = self.payment_type if self.payment_type else 'unknown'
            title = self.title if hasattr(self, 'title') else 'unknown'
            return f"<Course(id={self.id}, title='{title}', payment_type={payment_type_value})>"
        except (DetachedInstanceError, AttributeError):
            # Use __dict__ to avoid SQLAlchemy attribute access for detached instances
            obj_dict = object.__getattribute__(self, '__dict__')
            course_id = obj_dict.get('id', 'unknown')
            course_title = obj_dict.get('title', 'unknown')
            course_payment_type = obj_dict.get('payment_type', 'unknown')
            return f"<Course(id={course_id}, title='{course_title}', payment_type={course_payment_type})>" 
    