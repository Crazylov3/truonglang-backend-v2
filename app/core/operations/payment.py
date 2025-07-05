"""Payment database operations."""

from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from decimal import Decimal

from app.models.payment import Payment, PaymentStatus


async def create_payment(
    db: AsyncSession,
    user_id: int,
    course_id: int,
    amount: Decimal,
    provider_reference: Optional[str] = None,
    status: PaymentStatus = PaymentStatus.PENDING
) -> Optional[Payment]:
    """Create a new payment."""
    try:
        payment = Payment(
            user_id=user_id,
            course_id=course_id,
            amount=amount,
            status=status,
            provider_reference=provider_reference
        )
        
        db.add(payment)
        await db.commit()
        await db.refresh(payment)
        
        return payment
        
    except SQLAlchemyError:
        await db.rollback()
        return None


async def get_payment_by_id(db: AsyncSession, payment_id: int) -> Optional[Payment]:
    """Get payment by ID with relationships."""
    try:
        result = await db.execute(
            select(Payment).options(
                selectinload(Payment.user),
                selectinload(Payment.course)
            ).where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError:
        return None


async def update_payment_status(
    db: AsyncSession,
    payment_id: int,
    status: PaymentStatus,
    provider_reference: Optional[str] = None
) -> bool:
    """Update payment status."""
    try:
        result = await db.execute(select(Payment).where(Payment.id == payment_id))
        payment = result.scalar_one_or_none()
        
        if not payment:
            return False
        
        payment.status = status
        if provider_reference:
            payment.provider_reference = provider_reference
        
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False


async def get_user_payments(
    db: AsyncSession,
    user_id: int,
    status: Optional[PaymentStatus] = None,
    page: int = 1,
    per_page: int = 10
) -> Tuple[List[Payment], int]:
    """Get all payments for a user with pagination."""
    try:
        # Base query for payments
        query = (
            select(Payment)
            .options(selectinload(Payment.course))
            .where(Payment.user_id == user_id)
        )
        
        if status:
            query = query.where(Payment.status == status)
        
        # Get total count
        count_query = select(func.count()).select_from(
            select(Payment.id)
            .where(Payment.user_id == user_id)
        )
        if status:
            count_query = count_query.where(Payment.status == status)
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # Apply pagination and ordering
        query = query.order_by(Payment.created_at.desc())
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        result = await db.execute(query)
        payments = result.scalars().all()
        return payments, total
        
    except SQLAlchemyError:
        return [], 0

async def get_payments_by_course_and_user(
    db: AsyncSession,
    course_id: int,
    user_id: int,
    status: Optional[PaymentStatus] = None,
    page: int = 1,
    per_page: int = 10
) -> Tuple[List[Payment], int]:
    """Get all payments for a course and user."""
    try:
        # Base query
        query = (
            select(Payment)
            .options(selectinload(Payment.user))
            .where(Payment.course_id == course_id)
            .where(Payment.user_id == user_id)
        )
        
        if status:
            query = query.where(Payment.status == status)

        # Get total count
        count_query = select(func.count()).select_from(
            select(Payment.id)
            .where(Payment.course_id == course_id)
            .where(Payment.user_id == user_id)
        )
        if status:
            count_query = count_query.where(Payment.status == status)
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # Apply pagination and ordering
        query = query.order_by(Payment.created_at.desc())
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)

        result = await db.execute(query)
        payments = result.scalars().all()
        return payments, total
        
    except SQLAlchemyError:
        return [], 0

async def get_course_payments(
    db: AsyncSession,
    course_id: int,
    status: Optional[PaymentStatus] = None
) -> List[Payment]:
    """Get all payments for a course."""
    try:
        query = (
            select(Payment)
            .options(selectinload(Payment.user))
            .where(Payment.course_id == course_id)
        )
        
        if status:
            query = query.where(Payment.status == status)
        
        query = query.order_by(Payment.created_at.desc())
        
        result = await db.execute(query)
        payments = result.scalars().all()
        return payments
        
    except SQLAlchemyError:
        return []


async def get_payments_by_status(
    db: AsyncSession,
    status: PaymentStatus,
    limit: int = 100
) -> List[Payment]:
    """Get payments by status."""
    try:
        query = (
            select(Payment)
            .options(
                selectinload(Payment.user),
                selectinload(Payment.course)
            )
            .where(Payment.status == status)
            .order_by(Payment.created_at.desc())
            .limit(limit)
        )
        
        result = await db.execute(query)
        payments = result.scalars().all()
        return payments
        
    except SQLAlchemyError:
        return []


async def delete_payment(db: AsyncSession, payment_id: int) -> bool:
    """Delete a payment."""
    try:
        result = await db.execute(select(Payment).where(Payment.id == payment_id))
        payment = result.scalar_one_or_none()
        
        if not payment:
            return False
        
        await db.delete(payment)
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False
