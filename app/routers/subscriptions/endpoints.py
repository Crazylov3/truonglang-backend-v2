from fastapi import Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime, timedelta
from app.database import get_db
from app.models.user import User, UserRole
from app.models.course import Course, CoursePaymentType
from app.models.enrollment import Enrollment
from app.models.subscription import Subscription, SubscriptionStatus
from app.core.deps import get_current_user
from app.core.decorators import csrf_protect, authentication_required


async def get_my_subscriptions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's subscriptions."""
    query = (
        select(Subscription)
        .join(Enrollment, Subscription.enrollment_id == Enrollment.id)
        .options(
            selectinload(Subscription.enrollment).selectinload(Enrollment.course)
        )
        .where(Enrollment.student_id == current_user.id)
        .order_by(Subscription.created_at.desc())
    )
    
    result = await db.execute(query)
    subscriptions = result.scalars().all()
    
    return subscriptions


async def get_subscription_by_id(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get subscription details by ID."""
    query = (
        select(Subscription)
        .options(
            selectinload(Subscription.enrollment).selectinload(Enrollment.course),
            selectinload(Subscription.enrollment).selectinload(Enrollment.student)
        )
        .where(Subscription.id == subscription_id)
    )
    
    result = await db.execute(query)
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Check permissions
    can_view = False
    if current_user.role == UserRole.STUDENT:
        # Students can only view their own subscriptions
        can_view = subscription.enrollment.student_id == current_user.id
    elif current_user.role == UserRole.INSTRUCTOR:
        # Instructors can view subscriptions for their courses
        can_view = subscription.enrollment.course.creator_id == current_user.id
    elif current_user.role >= UserRole.STAFF:
        # Staff and admin can view all subscriptions
        can_view = True
    
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to view this subscription"
        )
    
    return subscription


@authentication_required(allowed_role=UserRole.STUDENT)
@csrf_protect
async def create_subscription(
    course_id: int,
    current_user: User,
    db: AsyncSession
):
    """Create a subscription for a course enrollment."""
    # Check if course exists and is subscription-based
    result = await db.execute(
        select(Course).where(
            and_(
                Course.id == course_id,
                Course.payment_type == CoursePaymentType.SUBSCRIPTION
            )
        )
    )
    course = result.scalar_one_or_none()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or not subscription-based"
        )
    
    # Check if user is enrolled in the course
    result = await db.execute(
        select(Enrollment).where(
            and_(
                Enrollment.student_id == current_user.id,
                Enrollment.course_id == course_id,
                Enrollment.is_active == True
            )
        )
    )
    enrollment = result.scalar_one_or_none()
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must be enrolled in the course to create a subscription"
        )
    
    # Check if subscription already exists
    existing_subscription = await db.execute(
        select(Subscription).where(Subscription.enrollment_id == enrollment.id)
    )
    
    if existing_subscription.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription already exists for this enrollment"
        )
    
    # Create subscription
    now = datetime.utcnow()
    
    # Calculate billing period based on course settings
    if course.billing_interval and course.billing_interval_count:
        if course.billing_interval == 1:  # DAY
            period_end = now + timedelta(days=course.billing_interval_count)
        elif course.billing_interval == 2:  # WEEK
            period_end = now + timedelta(weeks=course.billing_interval_count)
        elif course.billing_interval == 3:  # MONTH
            period_end = now + timedelta(days=course.billing_interval_count * 30)
        elif course.billing_interval == 4:  # YEAR
            period_end = now + timedelta(days=course.billing_interval_count * 365)
        else:
            period_end = now + timedelta(days=30)  # Default to 30 days
    else:
        period_end = now + timedelta(days=30)  # Default to 30 days
    
    subscription = Subscription(
        enrollment_id=enrollment.id,
        status=SubscriptionStatus.TRIALING,  # Start with trial status
        current_period_starts_at=now,
        current_period_ends_at=period_end
    )
    
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)
    
    return subscription


@authentication_required(allowed_role=UserRole.STUDENT)
@csrf_protect
async def cancel_subscription(
    subscription_id: int,
    current_user: User,
    db: AsyncSession
):
    """Cancel a subscription."""
    query = (
        select(Subscription)
        .join(Enrollment, Subscription.enrollment_id == Enrollment.id)
        .where(Subscription.id == subscription_id)
    )
    
    result = await db.execute(query)
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Check permissions (students can only cancel their own subscriptions)
    if current_user.role == UserRole.STUDENT:
        enrollment_result = await db.execute(
            select(Enrollment).where(Enrollment.id == subscription.enrollment_id)
        )
        enrollment = enrollment_result.scalar_one()
        if enrollment.student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only cancel your own subscriptions"
            )
    
    # Update subscription status
    subscription.status = SubscriptionStatus.CANCELED
    subscription.canceled_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(subscription)
    
    return {"message": "Subscription canceled successfully", "subscription": subscription}


@authentication_required(allowed_role=UserRole.STAFF)
async def get_all_subscriptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[SubscriptionStatus] = Query(None),
    course_id: Optional[int] = Query(None),
    student_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get all subscriptions with filtering (Staff and Admin only)."""
    query = (
        select(Subscription)
        .options(
            selectinload(Subscription.enrollment).selectinload(Enrollment.course),
            selectinload(Subscription.enrollment).selectinload(Enrollment.student).selectinload(User.profile)
        )
    )
    
    if status:
        query = query.where(Subscription.status == status)
    
    if course_id:
        query = query.join(Enrollment).where(Enrollment.course_id == course_id)
    
    if student_id:
        query = query.join(Enrollment).where(Enrollment.student_id == student_id)
    
    query = query.offset(skip).limit(limit).order_by(Subscription.created_at.desc())
    
    result = await db.execute(query)
    subscriptions = result.scalars().all()
    
    return subscriptions


@authentication_required(allowed_role=UserRole.STAFF)
@csrf_protect
async def update_subscription_status(
    subscription_id: int,
    new_status: SubscriptionStatus,
    db: AsyncSession = Depends(get_db)
):
    """Update subscription status (Staff and Admin only)."""
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    subscription.status = new_status
    
    # Set canceled_at if canceling
    if new_status == SubscriptionStatus.CANCELED and not subscription.canceled_at:
        subscription.canceled_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(subscription)
    
    return {
        "message": f"Subscription status updated to {new_status}",
        "subscription": subscription
    }


@authentication_required(allowed_role=UserRole.STAFF)
@csrf_protect
async def extend_subscription_period(
    subscription_id: int,
    days: int = Query(..., ge=1, le=365, description="Number of days to extend"),
    db: AsyncSession = Depends(get_db)
):
    """Extend subscription billing period (Staff and Admin only)."""
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Extend the current period
    subscription.current_period_ends_at += timedelta(days=days)
    
    await db.commit()
    await db.refresh(subscription)
    
    return {
        "message": f"Subscription period extended by {days} days",
        "subscription": subscription
    } 