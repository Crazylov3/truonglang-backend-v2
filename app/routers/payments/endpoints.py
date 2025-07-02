from fastapi import Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload
from typing import Optional
from decimal import Decimal
from datetime import datetime, timedelta
from app.database import get_db
from app.models.user import User, UserRole
from app.models.course import Course, CoursePaymentType
from app.models.enrollment import Enrollment
from app.models.subscription import Subscription
from app.models.payment import Payment, PaymentStatus
from app.core.deps import get_current_user
from app.core.decorators import csrf_protect, authentication_required


async def get_my_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[PaymentStatus] = Query(None, description="Filter by payment status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's payment history."""
    query = (
        select(Payment)
        .options(
            selectinload(Payment.course),
            selectinload(Payment.subscription)
        )
        .where(Payment.user_id == current_user.id)
        .order_by(desc(Payment.created_at))
    )
    
    if status:
        query = query.where(Payment.status == status)
    
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    payments = result.scalars().all()
    
    return payments


async def get_payment_by_id(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get payment details by ID."""
    query = (
        select(Payment)
        .options(
            selectinload(Payment.course),
            selectinload(Payment.subscription),
            selectinload(Payment.user)
        )
        .where(Payment.id == payment_id)
    )
    
    result = await db.execute(query)
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Check permissions
    can_view = False
    if current_user.role == UserRole.STUDENT:
        # Students can only view their own payments
        can_view = payment.user_id == current_user.id
    elif current_user.role == UserRole.INSTRUCTOR:
        # Instructors can view payments for their courses
        can_view = payment.course.creator_id == current_user.id
    elif current_user.role >= UserRole.STAFF:
        # Staff and admin can view all payments
        can_view = True
    
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to view this payment"
        )
    
    return payment


@authentication_required(allowed_role=UserRole.STUDENT)
@csrf_protect
async def create_payment(
    course_id: int,
    amount: Decimal = Query(..., description="Payment amount"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a payment for a course."""
    # Check if course exists
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # For one-time payments, check if user is enrolled
    if course.payment_type == CoursePaymentType.ONE_TIME:
        enrollment_result = await db.execute(
            select(Enrollment).where(
                and_(
                    Enrollment.student_id == current_user.id,
                    Enrollment.course_id == course_id
                )
            )
        )
        enrollment = enrollment_result.scalar_one_or_none()
        
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must be enrolled in the course for one-time payment"
            )
        
        # Create payment without subscription
        payment = Payment(
            user_id=current_user.id,
            course_id=course_id,
            amount=amount,
            status=PaymentStatus.PENDING
        )
    
    else:  # Subscription payment
        # Check if user has an active subscription
        subscription_result = await db.execute(
            select(Subscription)
            .join(Enrollment, Subscription.enrollment_id == Enrollment.id)
            .where(
                and_(
                    Enrollment.student_id == current_user.id,
                    Enrollment.course_id == course_id
                )
            )
        )
        subscription = subscription_result.scalar_one_or_none()
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must have an active subscription for subscription payment"
            )
        
        # Create payment with subscription
        payment = Payment(
            user_id=current_user.id,
            course_id=course_id,
            subscription_id=subscription.id,
            amount=amount,
            status=PaymentStatus.PENDING
        )
    
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    
    return payment


@authentication_required(allowed_role=UserRole.STAFF)
@csrf_protect
async def update_payment_status(
    payment_id: int,
    new_status: PaymentStatus,
    provider_reference: Optional[str] = Query(None, description="Payment provider reference ID"),
    db: AsyncSession = Depends(get_db)
):
    """Update payment status (Staff and Admin only)."""
    result = await db.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    payment.status = new_status
    
    if provider_reference:
        payment.provider_reference = provider_reference
    
    await db.commit()
    await db.refresh(payment)
    
    return {
        "message": f"Payment status updated to {new_status}",
        "payment": payment
    }


@authentication_required(allowed_role=UserRole.INSTRUCTOR)
async def get_course_payments(
    course_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[PaymentStatus] = Query(None, description="Filter by payment status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get payments for a specific course (instructor/staff/admin only)."""
    # Check if course exists and user has permission
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Check permissions
    can_view = False
    if current_user.role == UserRole.INSTRUCTOR:
        # Instructors can only view payments for their own courses
        can_view = course.creator_id == current_user.id
    elif current_user.role >= UserRole.STAFF:
        # Staff and admin can view all course payments
        can_view = True
    
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to view course payments"
        )
    
    query = (
        select(Payment)
        .options(
            selectinload(Payment.user).selectinload(User.profile),
            selectinload(Payment.subscription)
        )
        .where(Payment.course_id == course_id)
        .order_by(desc(Payment.created_at))
    )
    
    if status:
        query = query.where(Payment.status == status)
    
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    payments = result.scalars().all()
    
    return payments


@authentication_required(allowed_role=UserRole.STAFF)
async def get_all_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[PaymentStatus] = Query(None),
    course_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get all payments with filtering (Staff and Admin only)."""
    query = (
        select(Payment)
        .options(
            selectinload(Payment.user).selectinload(User.profile),
            selectinload(Payment.course),
            selectinload(Payment.subscription)
        )
        .order_by(desc(Payment.created_at))
    )
    
    if status:
        query = query.where(Payment.status == status)
    
    if course_id:
        query = query.where(Payment.course_id == course_id)
    
    if user_id:
        query = query.where(Payment.user_id == user_id)
    
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    payments = result.scalars().all()
    
    return payments


@authentication_required(allowed_role=UserRole.STAFF)
async def get_payment_statistics(
    course_id: Optional[int] = Query(None, description="Filter by course ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """Get payment statistics (Staff and Admin only)."""
    from sqlalchemy import func, case
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = select(
        func.count(Payment.id).label('total_payments'),
        func.sum(Payment.amount).label('total_amount'),
        func.sum(case((Payment.status == PaymentStatus.PAID, Payment.amount), else_=0)).label('paid_amount'),
        func.sum(case((Payment.status == PaymentStatus.PENDING, Payment.amount), else_=0)).label('pending_amount'),
        func.sum(case((Payment.status == PaymentStatus.FAILED, Payment.amount), else_=0)).label('failed_amount'),
        func.sum(case((Payment.status == PaymentStatus.REFUNDED, Payment.amount), else_=0)).label('refunded_amount'),
        func.count(case((Payment.status == PaymentStatus.PAID, 1))).label('paid_count'),
        func.count(case((Payment.status == PaymentStatus.PENDING, 1))).label('pending_count'),
        func.count(case((Payment.status == PaymentStatus.FAILED, 1))).label('failed_count'),
        func.count(case((Payment.status == PaymentStatus.REFUNDED, 1))).label('refunded_count')
    ).where(Payment.created_at >= start_date)
    
    if course_id:
        query = query.where(Payment.course_id == course_id)
    
    result = await db.execute(query)
    stats = result.first()
    
    return {
        "period": f"Last {days} days",
        "start_date": start_date.date(),
        "end_date": datetime.utcnow().date(),
        "total_payments": stats.total_payments or 0,
        "total_amount": float(stats.total_amount or 0),
        "paid_amount": float(stats.paid_amount or 0),
        "pending_amount": float(stats.pending_amount or 0),
        "failed_amount": float(stats.failed_amount or 0),
        "refunded_amount": float(stats.refunded_amount or 0),
        "paid_count": stats.paid_count or 0,
        "pending_count": stats.pending_count or 0,
        "failed_count": stats.failed_count or 0,
        "refunded_count": stats.refunded_count or 0
    } 