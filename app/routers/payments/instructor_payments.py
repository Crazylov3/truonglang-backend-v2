"""Payment-related API routes."""

from fastapi import Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.payments import (
    PaymentPeriodCreate,
    PaymentPeriodCreateResponse,
    PaymentPeriodsResponse,
    PaymentPeriodResponse,
    InvoicesResponse,
    InvoiceResponse,
)
from app.core.operations import payment as payment_ops
from app.core.operations import course as course_ops
from app.core.deps import get_current_user
from app.core.decorators import csrf_protect, authentication_required
from app.models.user import User, UserRole
from .payments import router


# Payment Period Endpoints (for Instructors/Staff)
@router.post("/courses/{course_id}/payment-periods", response_model=PaymentPeriodCreateResponse)
@authentication_required(allowed_role=UserRole.INSTRUCTOR)
@csrf_protect
async def create_payment_period(
    payment_period_create: PaymentPeriodCreate,
    course_id: int = Path(..., description="Course ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a payment period for a course (Instructors/Staff/Admin only)."""
    
    # Check if course exists
    course = await course_ops.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Check permissions
    has_permission = await course_ops.check_course_editable_permission(
        db, course_id, current_user.id, current_user.role
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to create payment periods for this course"
        )
    
    # Create payment period and generate invoices
    payment_period = await payment_ops.create_payment_period(
        db=db,
        course_id=course_id,
        amount=payment_period_create.amount,
        created_by=current_user.id
    )
    
    if not payment_period:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment period"
        )
    
    # Count enrolled students to show how many invoices were generated
    enrolled_count = len([e for e in course.enrollments if e.is_active])
    
    return PaymentPeriodCreateResponse(
        message="Payment period created successfully",
        invoices_generated=enrolled_count
    )


@router.get("/courses/{course_id}/payment-periods", response_model=PaymentPeriodsResponse)
@authentication_required(allowed_role=UserRole.INSTRUCTOR)
async def get_course_payment_periods(
    course_id: int = Path(..., description="Course ID"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get payment periods for a course (Instructors/Staff/Admin only)."""
    
    # Check if course exists
    course = await course_ops.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Check permissions
    has_permission = await course_ops.check_course_editable_permission(
        db, course_id, current_user.id, current_user.role
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to view payment periods for this course"
        )
    
    # Get payment periods
    payment_periods, total = await payment_ops.get_payment_periods_by_course(
        db, course_id, page, per_page
    )
    
    # Convert to response format
    payment_period_responses = []
    for period in payment_periods:
        payment_period_responses.append(PaymentPeriodResponse(
            id=period.id,
            course_id=period.course_id,
            amount=period.amount,
            created_at=period.created_at,
            created_by=period.created_by,
            created_by_name=period.created_by_user.full_name if period.created_by_user else None
        ))
    
    return PaymentPeriodsResponse.create(
        items=payment_period_responses,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/courses/{course_id}/payment-periods/{period_id}/invoices", response_model=InvoicesResponse)
@authentication_required(allowed_role=UserRole.INSTRUCTOR)
async def get_payment_period_invoices(
    course_id: int = Path(..., description="Course ID"),
    period_id: int = Path(..., description="Payment period ID"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get invoices for a payment period - shows which students paid/unpaid (Instructors/Staff/Admin only)."""
    
    # Check if course exists
    course = await course_ops.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Check permissions
    has_permission = await course_ops.check_course_editable_permission(
        db, course_id, current_user.id, current_user.role
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to view invoices for this course"
        )
    
    # Get invoices for the payment period
    invoices, total = await payment_ops.get_invoices_by_payment_period(
        db, period_id, page, per_page
    )

    invoices_responses = [
        InvoiceResponse(
            invoice_id=invoice["invoice_id"],
            student_id=invoice["student_id"],
            student_email=invoice["student_email"], 
            student_name=invoice["student_name"],
            amount_due=invoice["amount_due"],
            total_paid=invoice["total_paid"],
            status=invoice["status"],
            created_at=invoice["created_at"],
            is_paid=invoice["is_paid"]
        ) for invoice in invoices
    ]
    
    return InvoicesResponse.create(
        items=invoices_responses,
        total=total,
        page=page,
        per_page=per_page
    )

