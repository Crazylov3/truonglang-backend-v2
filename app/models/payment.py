from sqlalchemy import Column, Integer, DateTime, ForeignKey, DECIMAL, String, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import IntEnum
from .base import BaseModel


class InvoiceStatus(IntEnum):
    DUE = 1
    PAID = 2
    OVERDUE = 3
    CANCELLED = 4


class PaymentStatus(IntEnum):
    PENDING = 1
    SUCCESSFUL = 2
    FAILED = 3


class CoursePaymentPeriod(BaseModel):
    __tablename__ = "course_payment_period"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    course = relationship("Course", back_populates="payment_periods")
    created_by_user = relationship("User", back_populates="created_payment_periods")
    invoices = relationship("Invoice", back_populates="payment_period")

    def __repr__(self):
        return f"<CoursePaymentPeriod(id={self.id}, course_id={self.course_id}, amount={self.amount})>"


class Invoice(BaseModel):
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False)
    payment_period_id = Column(Integer, ForeignKey("course_payment_period.id"), nullable=False)
    status = Column(Integer, nullable=False, default=InvoiceStatus.DUE)
    amount_due = Column(DECIMAL(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    enrollment = relationship("Enrollment", back_populates="invoices")
    payment_period = relationship("CoursePaymentPeriod", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice")

    # Ensure unique constraint as per DBMS
    __table_args__ = (
        UniqueConstraint('enrollment_id', 'payment_period_id', name='unique_enrollment_payment_period'),
    )

    def __repr__(self):
        return f"<Invoice(id={self.id}, enrollment_id={self.enrollment_id}, status={self.status}, amount_due={self.amount_due})>"


class Payment(BaseModel):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    status = Column(Integer, nullable=False, default=PaymentStatus.PENDING)
    amount = Column(DECIMAL(10, 2), nullable=False)
    provider_reference = Column(String(255), unique=True, nullable=True, comment="ID from Stripe, PayPal, etc.")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    invoice = relationship("Invoice", back_populates="payments")

    def __repr__(self):
        return f"<Payment(id={self.id}, invoice_id={self.invoice_id}, amount={self.amount}, status={self.status})>" 
  
  