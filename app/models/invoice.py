from sqlalchemy import Column, DateTime, ForeignKey, DECIMAL, UniqueConstraint, Enum as SQLAEnum, text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from enum import Enum
from .base import BaseModel


class InvoiceStatus(str, Enum):
    DUE = "DUE"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class Invoice(BaseModel):
    __tablename__ = "invoices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    enrollment_id = Column(UUID(as_uuid=True), ForeignKey("enrollments.id"), nullable=False)
    payment_period_id = Column(UUID(as_uuid=True), ForeignKey("course_payment_period.id"), nullable=False)
    status = Column(SQLAEnum(InvoiceStatus), nullable=False, default=InvoiceStatus.DUE)
    amount_due = Column(DECIMAL(10, 2), nullable=False, comment="Số tiền phải trả SAU KHI đã áp dụng miễn giảm")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    enrollment = relationship("Enrollment", foreign_keys=[enrollment_id])
    payment_period = relationship("CoursePaymentPeriod", foreign_keys=[payment_period_id])
    payments = relationship("Payment", back_populates="invoice")
    
    # Ensure one invoice per enrollment per payment period
    __table_args__ = (
        UniqueConstraint('enrollment_id', 'payment_period_id', name='unique_enrollment_payment_period'),
    )
    
    def __repr__(self):
        return f"<Invoice(id={self.id}, enrollment_id={self.enrollment_id}, status={self.status}, amount_due={self.amount_due})>"