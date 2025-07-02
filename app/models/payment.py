from sqlalchemy import Column, Integer, DateTime, ForeignKey, DECIMAL, String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import IntEnum
from .base import BaseModel


class PaymentStatus(IntEnum):
    PENDING = 1
    PAID = 2
    FAILED = 3
    REFUNDED = 4


class Payment(BaseModel):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True, comment="NULL for one-time payments")
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, comment="Denormalized for easy lookup")
    
    amount = Column(DECIMAL(10, 2), nullable=False)
    status = Column(Integer, nullable=False, default=PaymentStatus.PENDING)
    provider_reference = Column(String(255), unique=True, nullable=True, comment="ID from Stripe, PayPal, etc.")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payments")
    course = relationship("Course", back_populates="payments")

    def __repr__(self):
        return f"<Payment(id={self.id}, user_id={self.user_id}, amount={self.amount}, status={self.status})>" 
  
  