from app.routers.payments.payments import router
from typing import List
from app.schemas.payments import PaymentInfoResponse, PaymentListResponse
from app.schemas.common import PaginatedResponse
from app.core.operations import payment as payment_ops
from fastapi import Depends, Query, HTTPException, status
from app.core.deps import get_current_user
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.payment import PaymentStatus


@router.get("/my-payments", response_model=PaymentListResponse)
async def get_my_payments(
    only_pending: bool = Query(
        False, description="Only return pending payments"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all payments for the current user."""

    payments, total = await payment_ops.get_user_payments(
        db, current_user.id, PaymentStatus.PENDING if only_pending else None, page=page, per_page=per_page
    )

    payment_responses = [
        PaymentInfoResponse(
            id=payment.id,
            user_id=payment.user_id,
            course_id=payment.course_id,
            amount=payment.amount,
            status=payment.status,
            created_at=payment.created_at
        ) for payment in payments
    ]

    return PaginatedResponse.create(
        items=payment_responses,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/my-payments/{payment_id}", response_model=PaymentInfoResponse)
async def get_payment_by_id(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a payment by ID."""
    payment = await payment_ops.get_payment_by_id(db, payment_id)
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    if payment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this payment"
        )
    return PaymentInfoResponse(
        id=payment.id,
        user_id=payment.user_id,
        course_id=payment.course_id,
        amount=payment.amount,
        status=payment.status,
        created_at=payment.created_at
    )
