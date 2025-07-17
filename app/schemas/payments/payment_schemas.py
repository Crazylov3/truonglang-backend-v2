"""Payment-related schemas."""

from typing import Optional, List
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from app.schemas.common import PaginatedResponse


# Payment Period Schemas
class PaymentPeriodCreate(BaseModel):
    """Schema for creating a payment period."""
    amount: Decimal = Field(..., description="Payment amount", gt=0)

    class Config:
        json_encoders = {
            Decimal: str
        }


class PaymentPeriodResponse(BaseModel):
    """Schema for payment period response."""
    id: int = Field(..., description="Payment period ID")
    course_id: int = Field(..., description="Course ID")
    amount: Decimal = Field(..., description="Payment amount")
    created_at: datetime = Field(..., description="Creation timestamp")
    created_by: int = Field(..., description="Created by user ID")
    created_by_name: Optional[str] = Field(None, description="Created by user name")

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: str
        }


class PaymentPeriodsResponse(PaginatedResponse[PaymentPeriodResponse]):
    """Paginated response for payment periods."""
    pass


# Invoice Schemas
class InvoiceResponse(BaseModel):
    """Schema for invoice response."""
    invoice_id: int = Field(..., description="Invoice ID")
    student_id: int = Field(..., description="Student ID")
    student_email: str = Field(..., description="Student email")
    student_name: str = Field(..., description="Student full name")
    amount_due: Decimal = Field(..., description="Amount due")
    total_paid: Decimal = Field(..., description="Total amount paid")
    status: str = Field(..., description="Invoice status")
    created_at: datetime = Field(..., description="Invoice creation date")
    is_paid: bool = Field(..., description="Whether invoice is fully paid")

    class Config:
        json_encoders = {
            Decimal: str
        }


class StudentInvoiceResponse(BaseModel):
    """Schema for student's invoice response."""
    invoice_id: int = Field(..., description="Invoice ID")
    course_id: int = Field(..., description="Course ID")
    course_title: str = Field(..., description="Course title")
    payment_period_title: Optional[str] = Field(None, description="Payment period title")
    amount_due: Decimal = Field(..., description="Amount due")
    total_paid: Decimal = Field(..., description="Total amount paid")
    status: str = Field(..., description="Invoice status")
    created_at: datetime = Field(..., description="Invoice creation date")
    due_date: Optional[datetime] = Field(None, description="Payment due date")
    is_paid: bool = Field(..., description="Whether invoice is fully paid")

    class Config:
        json_encoders = {
            Decimal: str
        }


class InvoicesResponse(PaginatedResponse[InvoiceResponse]):
    """Paginated response for invoices."""
    pass


class StudentInvoicesResponse(PaginatedResponse[StudentInvoiceResponse]):
    """Paginated response for student invoices."""
    pass


# Payment Schemas
class PaymentCreate(BaseModel):
    """Schema for creating a payment."""
    amount: Decimal = Field(..., description="Payment amount", gt=0)
    provider_reference: Optional[str] = Field(None, description="Payment provider reference")

    class Config:
        json_encoders = {
            Decimal: str
        }


class PaymentResponse(BaseModel):
    """Schema for payment response."""
    id: int = Field(..., description="Payment ID")
    invoice_id: int = Field(..., description="Invoice ID")
    amount: Decimal = Field(..., description="Payment amount")
    status: str = Field(..., description="Payment status")
    provider_reference: Optional[str] = Field(None, description="Payment provider reference")
    created_at: datetime = Field(..., description="Payment creation date")

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: str
        }


# Success Response Schemas
class PaymentPeriodCreateResponse(BaseModel):
    """Response for successful payment period creation."""
    message: str = Field(..., description="Success message")
    invoices_generated: int = Field(..., description="Number of invoices generated")


class PaymentCreateResponse(BaseModel):
    """Response for successful payment creation."""
    message: str = Field(..., description="Success message")
    payment: PaymentResponse = Field(..., description="Created payment")
    invoice_status: str = Field(..., description="Updated invoice status") 