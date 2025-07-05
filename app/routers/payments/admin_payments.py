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
from app.core.decorators import authentication_required
from app.models.user import UserRole


@router.get("/{course_id}/{user_id}", response_model=PaymentListResponse)
@authentication_required(UserRole.STAFF)
async def get_payments_by_course_and_user(
    course_id: int,
    user_id: int,
    only_pending: bool = Query(
        False, description="Only return pending payments"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """Get all payments for a course and user."""
    payments, total = await payment_ops.get_payments_by_course_and_user(db, course_id, user_id, PaymentStatus.PENDING if only_pending else None, page, per_page)
    
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

@router.put("/{payment_id}/status", response_model=PaymentInfoResponse)
@authentication_required(UserRole.STAFF)
async def update_payment_status(
    payment_id: int,
    status: PaymentStatus,
    db: AsyncSession = Depends(get_db)
):
    """Update the status of a payment."""
    payment = await payment_ops.update_payment_status(db, payment_id, status)
    return PaymentInfoResponse(
        id=payment.id,
        user_id=payment.user_id,
        course_id=payment.course_id,
        amount=payment.amount,
        status=payment.status,
        created_at=payment.created_at
    )
