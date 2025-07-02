from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import IntEnum
from .base import BaseModel


class SubscriptionStatus(IntEnum):
    ACTIVE = 1
    CANCELED = 2
    PAST_DUE = 3  # Payment failed, access might be restricted
    TRIALING = 4


class Subscription(BaseModel):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), unique=True, nullable=False)
    status = Column(Integer, nullable=False, default=SubscriptionStatus.ACTIVE)
    
    # Tracks the current billing period
    current_period_starts_at = Column(DateTime(timezone=True), nullable=False)
    current_period_ends_at = Column(DateTime(timezone=True), nullable=False, comment="For time-based, this is calculated. For usage-based, this is updated when a cycle ends.")
    
    # Date when the subscription was cancelled. User may retain access until current_period_ends_at.
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    enrollment = relationship("Enrollment", back_populates="subscription")
    payments = relationship("Payment", back_populates="subscription")

    def __repr__(self):
        return f"<Subscription(id={self.id}, enrollment_id={self.enrollment_id}, status={self.status})>" 