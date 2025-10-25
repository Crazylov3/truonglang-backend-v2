"""Payment-related schemas."""

from typing import Optional, List
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from uuid import UUID
from app.schemas.common import PaginatedResponse, BaseUUIDModel


# Payment Period Schemas
class PaymentPeriodCreate(BaseModel):
    """Schema for creating a payment period."""
    amount: float = Field(..., description="Payment amount", gt=0)



class PaymentPeriodResponse(BaseUUIDModel):
    """Schema for payment period response."""
    course_id: UUID = Field(..., description="Course ID")
    amount: float = Field(..., description="Payment amount")
    created_at: datetime = Field(..., description="Creation timestamp")
    created_by: UUID = Field(..., description="Created by user ID")
    created_by_name: Optional[str] = Field(None, description="Created by user name")

    class Config:
        from_attributes = True



class PaymentPeriodsResponse(PaginatedResponse[PaymentPeriodResponse]):
    """Paginated response for payment periods."""
    pass


# Invoice Schemas
class InvoiceResponse(BaseModel):
    """Schema for invoice response."""
    invoice_id: UUID = Field(..., description="Invoice ID")
    enrollment_id: UUID = Field(..., description="Enrollment ID")
    payment_period_id: UUID = Field(..., description="Payment period ID")
    student_id: UUID = Field(..., description="Student ID")
    student_email: str = Field(..., description="Student email")
    student_name: str = Field(..., description="Student full name")
    amount_due: float = Field(..., description="Amount due")
    total_paid: float = Field(..., description="Total amount paid")
    status: str = Field(..., description="Invoice status")
    created_at: datetime = Field(..., description="Invoice creation date")
    is_paid: bool = Field(..., description="Whether invoice is fully paid")



class StudentInvoiceResponse(BaseModel):
    """Schema for student's invoice response."""
    invoice_id: UUID = Field(..., description="Invoice ID")
    course_id: UUID = Field(..., description="Course ID")
    course_title: str = Field(..., description="Course title")
    amount_due: float = Field(..., description="Amount due")
    total_paid: float = Field(..., description="Total amount paid")
    status: str = Field(..., description="Invoice status")
    created_at: datetime = Field(..., description="Invoice creation date")
    due_date: Optional[datetime] = Field(None, description="Payment due date")
    is_paid: bool = Field(..., description="Whether invoice is fully paid")


class InvoicesResponse(PaginatedResponse[InvoiceResponse]):
    """Paginated response for invoices."""
    pass


class StudentInvoicesResponse(PaginatedResponse[StudentInvoiceResponse]):
    """Paginated response for student invoices."""
    pass


class StudentCourseInvoicesResponse(BaseModel):
    """Non-paginated response for student invoices in a specific course."""
    invoices: List[StudentInvoiceResponse] = Field(..., description="List of all invoices for the course")
    total: int = Field(..., description="Total number of invoices")


# Payment Schemas
class PaymentCreate(BaseModel):
    """Schema for creating a payment."""
    amount: float = Field(..., description="Payment amount", gt=0)
    provider_reference: Optional[str] = Field(None, description="Payment provider reference")



class PaymentResponse(BaseUUIDModel):
    """Schema for payment response."""
    invoice_id: UUID = Field(..., description="Invoice ID")
    amount: float = Field(..., description="Payment amount")
    status: str = Field(..., description="Payment status")
    provider_reference: Optional[str] = Field(None, description="Payment provider reference")
    created_at: datetime = Field(..., description="Payment creation date")

    class Config:
        from_attributes = True


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