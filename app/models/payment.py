from sqlalchemy import Column, Integer, DateTime, ForeignKey, Float, String, PrimaryKeyConstraint, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
from enum import IntEnum


class PaymentStatus(IntEnum):
    PENDING = 1
    PAID = 2
    FAILED = 3

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    transaction_reference = Column(String(64), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Payment(Base):
    __tablename__ = "payments"
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(Enum(PaymentStatus, values_callable=lambda obj: [str(e.value) for e in obj]), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # primary key is the enrollment_id and created_at
    __table_args__ = (
        PrimaryKeyConstraint('enrollment_id', 'created_at', name='pk_payment'),
    )

    def __repr__(self):
        return f"<Payment(enrollment_id={self.enrollment_id}, created_at={self.created_at})>" 
  
  