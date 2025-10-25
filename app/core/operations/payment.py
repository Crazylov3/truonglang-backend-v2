"""Payment and billing database operations."""

from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from decimal import Decimal
from datetime import datetime
from app.models.payment import *
from app.models.enrollment import Enrollment
from app.models.course import *
from app.models.course_management import *
from app.models.invoice import *
from app.models.user import *
import traceback


async def create_payment_period(
    db: AsyncSession,
    course_id: int,
    amount: Decimal,
    created_by: int
) -> Optional[CoursePaymentPeriod]:
    """Create a payment period and generate invoices for all enrolled students."""
    try:
        # Create the payment period
        payment_period = CoursePaymentPeriod(
            course_id=course_id,
            amount=amount,
            created_by=created_by
        )
        
        db.add(payment_period)
        await db.flush()  # Get the ID without committing
        
        # Get all active enrollments for this course
        enrollments_result = await db.execute(
            select(Enrollment).where(
                and_(
                    Enrollment.course_id == course_id,
                    Enrollment.is_active == True
                )
            )
        )
        enrollments = enrollments_result.scalars().all()
        
        # Generate invoices for all enrolled students
        invoices = []
        for enrollment in enrollments:
            invoice = Invoice(
                enrollment_id=enrollment.id,
                payment_period_id=payment_period.id,
                amount_due=amount,
                status=InvoiceStatus.DUE
            )
            invoices.append(invoice)
        
        if invoices:
            db.add_all(invoices)
        
        await db.commit()
        await db.refresh(payment_period)
        
        return payment_period
        
    except SQLAlchemyError:
        await db.rollback()
        traceback.print_exc()
        return None


async def get_payment_periods_by_course(
    db: AsyncSession,
    course_id: int,
    page: int = 1,
    per_page: int = 20
) -> Tuple[List[CoursePaymentPeriod], int]:
    """Get payment periods for a course with pagination."""
    try:
        # Get total count
        count_query = select(func.count(CoursePaymentPeriod.id)).where(
            CoursePaymentPeriod.course_id == course_id
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Get payment periods with pagination
        offset = (page - 1) * per_page
        query = (
            select(CoursePaymentPeriod)
            .options(selectinload(CoursePaymentPeriod.created_by_user))
            .where(CoursePaymentPeriod.course_id == course_id)
            .order_by(CoursePaymentPeriod.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        
        result = await db.execute(query)
        payment_periods = result.scalars().all()
        
        return payment_periods, total
        
    except SQLAlchemyError:
        return [], 0


async def get_invoices_by_payment_period(
    db: AsyncSession,
    payment_period_id: int,
    page: int = 1,
    per_page: int = 50
) -> Tuple[List[dict], int]:
    """Get invoices for a payment period with student details."""
    try:
        # Get total count
        count_query = select(func.count(Invoice.id)).where(
            Invoice.payment_period_id == payment_period_id
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Get invoices with student details
        offset = (page - 1) * per_page
        query = (
            select(Invoice, User, Enrollment)
            .join(Enrollment, Invoice.enrollment_id == Enrollment.id)
            .join(User, Enrollment.student_id == User.id)
            .options(
                selectinload(Invoice.payments),
                selectinload(User.profile)
            )
            .where(Invoice.payment_period_id == payment_period_id)
            .order_by(User.email)
            .offset(offset)
            .limit(per_page)
        )
        
        result = await db.execute(query)
        invoice_data = result.all()
        
        invoices = []
        for invoice, user, enrollment in invoice_data:
            # Calculate total paid amount
            total_paid = sum(p.amount for p in invoice.payments if p.status == PaymentStatus.SUCCESSFUL)
            
            # Convert status to string for API
            status_map = {
                InvoiceStatus.DUE: "DUE",
                InvoiceStatus.PAID: "PAID", 
                InvoiceStatus.OVERDUE: "OVERDUE",
                InvoiceStatus.CANCELLED: "CANCELLED"
            }
            
            invoices.append({
                'invoice_id': invoice.id,
                'student_id': user.id,
                'student_email': user.email,
                'student_name': user.full_name,
                'amount_due': invoice.amount_due,
                'total_paid': total_paid,
                'status': status_map.get(invoice.status, "UNKNOWN"),
                'created_at': invoice.created_at,
                'is_paid': total_paid >= invoice.amount_due
            })
        
        return invoices, total
        
    except SQLAlchemyError:
        return [], 0


async def get_student_invoices(
    db: AsyncSession,
    student_id: int,
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None
) -> Tuple[List[dict], int]:
    """Get invoices for a student with course details."""
    try:
        # Build base query
        base_query = (
            select(Invoice, Course, CoursePaymentPeriod)
            .join(Enrollment, Invoice.enrollment_id == Enrollment.id)
            .join(Course, Enrollment.course_id == Course.id)
            .join(CoursePaymentPeriod, Invoice.payment_period_id == CoursePaymentPeriod.id)
            .where(Enrollment.student_id == student_id)
        )
        
        # Convert string status to integer for filtering
        if status:
            status_map = {
                "DUE": InvoiceStatus.DUE,
                "PAID": InvoiceStatus.PAID,
                "OVERDUE": InvoiceStatus.OVERDUE,
                "CANCELLED": InvoiceStatus.CANCELLED
            }
            if status in status_map:
                base_query = base_query.where(Invoice.status == status_map[status])
        
        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Get invoices with pagination
        offset = (page - 1) * per_page
        query = (
            base_query
            .options(selectinload(Invoice.payments))
            .order_by(Invoice.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        
        result = await db.execute(query)
        invoice_data = result.all()
        
        invoices = []
        for invoice, course, payment_period in invoice_data:
            # Calculate total paid amount
            total_paid = sum(p.amount for p in invoice.payments if p.status == PaymentStatus.SUCCESSFUL)
            
            # Convert status to string for API
            status_map = {
                InvoiceStatus.DUE: "DUE",
                InvoiceStatus.PAID: "PAID",
                InvoiceStatus.OVERDUE: "OVERDUE", 
                InvoiceStatus.CANCELLED: "CANCELLED"
            }
            
            invoices.append({
                'invoice_id': invoice.id,
                'course_id': course.id,
                'course_title': course.title,
                'amount_due': invoice.amount_due,
                'total_paid': total_paid,
                'status': status_map.get(invoice.status, "UNKNOWN"),
                'created_at': invoice.created_at,
                'due_date': None,  # Not available in original model
                'is_paid': total_paid >= invoice.amount_due
            })
        
        return invoices, total
        
    except SQLAlchemyError:
        return [], 0


async def get_student_invoices_by_course(
    db: AsyncSession,
    student_id: int,
    course_id: int,
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None
) -> Tuple[List[dict], int]:
    """Get invoices for a student filtered by a specific course."""
    try:
        # Build base query with course filter
        base_query = (
            select(Invoice, Course, CoursePaymentPeriod)
            .join(Enrollment, Invoice.enrollment_id == Enrollment.id)
            .join(Course, Enrollment.course_id == Course.id)
            .join(CoursePaymentPeriod, Invoice.payment_period_id == CoursePaymentPeriod.id)
            .where(Enrollment.student_id == student_id)
            .where(Course.id == course_id)  # Filter by specific course
        )
        
        # Convert string status to integer for filtering
        if status:
            status_map = {
                "DUE": InvoiceStatus.DUE,
                "PAID": InvoiceStatus.PAID,
                "OVERDUE": InvoiceStatus.OVERDUE,
                "CANCELLED": InvoiceStatus.CANCELLED
            }
            if status in status_map:
                base_query = base_query.where(Invoice.status == status_map[status])
        
        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Get invoices with pagination
        offset = (page - 1) * per_page
        query = (
            base_query
            .options(selectinload(Invoice.payments))
            .order_by(Invoice.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        
        result = await db.execute(query)
        invoice_data = result.all()
        
        invoices = []
        for invoice, course, payment_period in invoice_data:
            # Calculate total paid amount
            total_paid = sum(p.amount for p in invoice.payments if p.status == PaymentStatus.SUCCESSFUL)
            
            # Convert status to string for API
            status_map = {
                InvoiceStatus.DUE: "DUE",
                InvoiceStatus.PAID: "PAID",
                InvoiceStatus.OVERDUE: "OVERDUE", 
                InvoiceStatus.CANCELLED: "CANCELLED"
            }
            
            invoices.append({
                'invoice_id': invoice.id,
                'course_id': course.id,
                'course_title': course.title,
                'amount_due': invoice.amount_due,
                'total_paid': total_paid,
                'status': status_map.get(invoice.status, "UNKNOWN"),
                'created_at': invoice.created_at,
                'due_date': None,  # Not available in original model
                'is_paid': total_paid >= invoice.amount_due
            })
        
        return invoices, total
        
    except SQLAlchemyError:
        return [], 0


async def get_invoice_by_id(
    db: AsyncSession,
    invoice_id: int,
    student_id: Optional[int] = None
) -> Optional[Invoice]:
    """Get invoice by ID with optional student verification."""
    try:
        query = (
            select(Invoice)
            .options(
                selectinload(Invoice.enrollment),
                selectinload(Invoice.payment_period),
                selectinload(Invoice.payments)
            )
            .where(Invoice.id == invoice_id)
        )
        
        if student_id:
            query = query.join(Enrollment).where(Enrollment.student_id == student_id)
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
        
    except SQLAlchemyError:
        return None


async def create_payment(
    db: AsyncSession,
    invoice_id: int,
    amount: Decimal,
    provider_reference: Optional[str] = None,
    status: str = "PENDING"
) -> Optional[Payment]:
    """Create a payment record for an invoice."""
    try:
        # Convert string status to integer
        status_map = {
            "PENDING": PaymentStatus.PENDING,
            "SUCCESSFUL": PaymentStatus.SUCCESSFUL,
            "FAILED": PaymentStatus.FAILED
        }
        payment_status = status_map.get(status, PaymentStatus.PENDING)
        
        payment = Payment(
            invoice_id=invoice_id,
            amount=amount,
            provider_reference=provider_reference,
            status=payment_status
        )
        
        db.add(payment)
        await db.commit()
        await db.refresh(payment)
        
        return payment
        
    except SQLAlchemyError:
        await db.rollback()
        traceback.print_exc()
        return None


async def update_invoice_status(db: AsyncSession, invoice_id: int) -> bool:
    """Update invoice status based on payments."""
    try:
        result = await db.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        invoice = result.scalar_one_or_none()
        
        if not invoice:
            return False
        
        payments_result = await db.execute(
            select(Payment).where(Payment.invoice_id == invoice_id)
        )
        payments = payments_result.scalars().all()
        
        total_paid = sum(p.amount for p in payments if p.status == PaymentStatus.SUCCESSFUL)
        if total_paid >= invoice.amount_due:
            invoice.status = InvoiceStatus.PAID
        else:
            invoice.status = InvoiceStatus.DUE
        
        db.add(invoice)
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        traceback.print_exc()
        return False