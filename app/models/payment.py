from sqlalchemy import Column, DateTime, ForeignKey, DECIMAL, String, Enum as SQLAEnum, text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from enum import Enum
from .base import BaseModel


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESSFUL = "SUCCESSFUL"
    FAILED = "FAILED"


class Payment(BaseModel):
    __tablename__ = "payments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    status = Column(SQLAEnum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    amount = Column(DECIMAL(10, 2), nullable=False)
    provider_reference = Column(String(255), unique=True, nullable=True, comment="ID from Stripe, PayPal, etc.")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    invoice = relationship("Invoice", back_populates="payments", foreign_keys=[invoice_id])

    def __repr__(self):
        return f"<Payment(id={self.id}, invoice_id={self.invoice_id}, amount={self.amount}, status={self.status})>"