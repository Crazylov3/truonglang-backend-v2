"""Payment-related API routes."""

from fastapi import Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.database import get_db
from app.schemas.payments import (
    StudentInvoicesResponse,
    PaymentCreate,
    PaymentCreateResponse,
    PaymentResponse,
)
from app.core.operations import payment as payment_ops
from app.core.deps import get_current_user
from app.core.decorators import csrf_protect, authentication_required
from app.models.user import User, UserRole
from .payments import router


# Student Invoice Endpoints
@router.get("/students/me/invoices", response_model=StudentInvoicesResponse)
@authentication_required(allowed_role=UserRole.STUDENT)
async def get_my_invoices(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=50, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by invoice status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get invoices for the current student."""
    
    invoices, total = await payment_ops.get_student_invoices(
        db, current_user.id, page, per_page, status
    )
    
    return StudentInvoicesResponse.create(
        items=invoices,
        total=total,
        page=page,
        per_page=per_page
    )


# Payment Endpoints
@router.post("/invoices/{invoice_id}/payments", response_model=PaymentCreateResponse)
@authentication_required(allowed_role=UserRole.STUDENT)
@csrf_protect
async def create_payment(
    payment_create: PaymentCreate,
    invoice_id: int = Path(..., description="Invoice ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a payment for an invoice (Students only)."""
    
    # Get invoice and verify it belongs to the current student
    invoice = await payment_ops.get_invoice_by_id(db, invoice_id, current_user.id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found or does not belong to you"
        )
    
    # Check if invoice is already paid
    from app.models.payment import PaymentStatus
    total_paid = sum(p.amount for p in invoice.payments if p.status == PaymentStatus.SUCCESSFUL)
    if total_paid >= invoice.amount_due:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice is already fully paid"
        )
    
    # Create payment (start as PENDING, would be updated by payment processor webhook)
    payment = await payment_ops.create_payment(
        db=db,
        invoice_id=invoice_id,
        amount=payment_create.amount,
        provider_reference=payment_create.provider_reference,
        status="SUCCESSFUL"  # For demo purposes, mark as successful immediately
    )
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment"
        )

    # Update invoice status now that payment is committed
    await payment_ops.update_invoice_status(db, invoice_id)
    
    # Get updated invoice to check new status
    updated_invoice = await payment_ops.get_invoice_by_id(db, invoice_id)
    
    # Convert status to string for response
    from app.models.payment import InvoiceStatus
    status_map = {
        InvoiceStatus.DUE: "DUE",
        InvoiceStatus.PAID: "PAID",
        InvoiceStatus.OVERDUE: "OVERDUE",
        InvoiceStatus.CANCELLED: "CANCELLED"
    }
    
    # Convert payment status to string for response
    payment_status_map = {
        PaymentStatus.PENDING: "PENDING",
        PaymentStatus.SUCCESSFUL: "SUCCESSFUL", 
        PaymentStatus.FAILED: "FAILED"
    }
    
    return PaymentCreateResponse(
        message="Payment created successfully",
        payment=PaymentResponse(
            id=payment.id,
            invoice_id=payment.invoice_id,
            amount=payment.amount,
            status=payment_status_map.get(payment.status, "UNKNOWN"),
            provider_reference=payment.provider_reference,
            created_at=payment.created_at
        ),
        invoice_status=status_map.get(updated_invoice.status, "UNKNOWN")
    ) 