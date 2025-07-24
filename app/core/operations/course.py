"""Course database operations."""

from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.sql import case
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from decimal import Decimal
from datetime import datetime
from app.models.course import Course, CourseEditPermission
from app.models.user import User, UserRole
from app.models.enrollment import Enrollment


async def create_course(
    db: AsyncSession,
    title: str,
    description: Optional[str],
    creator_id: int,
    price: Optional[Decimal] = None,
    location: Optional[str] = None,
    start_date: Optional[datetime] = None,
    teacher_name: Optional[str] = None
) -> Course:
    """Create a new course."""
    try:
        new_course = Course(
            title=title,
            description=description,
            creator_id=creator_id,
            price=price,
            location=location,
            start_date=start_date,
            teacher_name=teacher_name
        )
        
        db.add(new_course)
        await db.commit()
        await db.refresh(new_course)
        
        # Reload the course with relationships
        result = await db.execute(
            select(Course).options(selectinload(Course.enrollments)).where(Course.id == new_course.id)
        )
        course_with_enrollments = result.scalar_one()
        
        return course_with_enrollments
        
    except SQLAlchemyError as e:
        await db.rollback()
        raise e
    
async def grant_edit_permission(db: AsyncSession, course_id: int, instructor_id: int, granted_by: int) -> bool:
    """Grant edit permission to an instructor for a course."""
    try:
        new_permission = CourseEditPermission(course_id=course_id, instructor_id=instructor_id, granted_by=granted_by)
        db.add(new_permission)
        await db.commit()
        return True
    except SQLAlchemyError as e:
        await db.rollback()
        raise e
    
async def revoke_edit_permission(db: AsyncSession, course_id: int, instructor_id: int) -> bool:
    """Revoke edit permission from an instructor for a course."""
    try:
        result = await db.execute(select(CourseEditPermission).where(CourseEditPermission.course_id == course_id, CourseEditPermission.instructor_id == instructor_id))
        permission = result.scalar_one_or_none()
        if permission:
            await db.delete(permission)
            await db.commit()
            return True
        return False
    except SQLAlchemyError as e:
        await db.rollback()
        raise e


async def get_course_by_id(db: AsyncSession, course_id: int) -> Optional[Course]:
    """Get course by ID with relationships."""
    try:
        result = await db.execute(
            select(Course).options(
                selectinload(Course.creator),
                selectinload(Course.enrollments)
            ).where(Course.id == course_id)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError:
        return None


async def update_course(
    db: AsyncSession,
    course_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    price: Optional[Decimal] = None,
    location: Optional[str] = None,
    start_date: Optional[datetime] = None,
    teacher_name: Optional[str] = None
) -> Optional[Course]:
    """Update a course."""
    try:
        result = await db.execute(select(Course).where(Course.id == course_id))
        course = result.scalar_one_or_none()
        
        if not course:
            return None
        
        # Update fields if provided
        if title is not None:
            course.title = title
        if description is not None:
            course.description = description
        if price is not None:
            course.price = price
        if location is not None:
            course.location = location
        if start_date is not None:
            course.start_date = start_date
        if teacher_name is not None:
            course.teacher_name = teacher_name
        
        await db.commit()
        await db.refresh(course)
        
        # Reload the course with relationships
        result = await db.execute(
            select(Course).options(selectinload(Course.enrollments)).where(Course.id == course_id)
        )
        course_with_enrollments = result.scalar_one()
        
        return course_with_enrollments
        
    except SQLAlchemyError:
        await db.rollback()
        return None


async def delete_course(db: AsyncSession, course_id: int) -> bool:
    """Delete a course."""
    try:
        result = await db.execute(select(Course).where(Course.id == course_id))
        course = result.scalar_one_or_none()
        
        if not course:
            return False
        
        # Delete related records first to avoid foreign key constraint issues
        await db.execute(delete(CourseEditPermission).where(CourseEditPermission.course_id == course_id))
        await db.execute(delete(Enrollment).where(Enrollment.course_id == course_id))
        
        await db.delete(course)
        
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False

async def filter_courses_by_edit_permission(db: AsyncSession, instructor_id: int) -> List[Course]:
    """Filter courses by edit permission. Using CourseEditPermission"""
    try:
        result = await db.execute(select(CourseEditPermission).where(CourseEditPermission.instructor_id == instructor_id))
        course_edit_permissions = result.scalars().all()
        course_ids = [permission.course_id for permission in course_edit_permissions]
        
        return course_ids
    except SQLAlchemyError:
        return []
    

async def check_course_editable_permission(
    db: AsyncSession,
    course_id: int,
    user_id: int,
    user_role: UserRole
) -> bool:
    """Check if user can create payment periods for a course."""
    try:
      can_edit = False
      if user_role == UserRole.INSTRUCTOR:
          can_edit = course_id in await filter_courses_by_edit_permission(db, user_id)
      elif user_role >= UserRole.STAFF:
          can_edit = True
      return can_edit
        
    except SQLAlchemyError:
        return False


async def list_courses(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    creator_id: Optional[int] = None,
    instructor_id: Optional[int] = None,
    all_courses: bool = False
) -> Tuple[List[Course], int]:
    """List courses with pagination."""
    try:
        # Build query with preloaded relationships
        query = select(Course).options(
            selectinload(Course.creator),
            selectinload(Course.enrollments)
        )
        
        if not all_courses:
          if creator_id:  
              query = query.where(Course.creator_id == creator_id)
          
          if instructor_id:
              query = query.where(Course.id.in_(await filter_courses_by_edit_permission(db, instructor_id)))
          
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        result = await db.execute(query)
        courses = result.scalars().all()
        
        return courses, total
        
    except SQLAlchemyError:
        return [], 0

async def list_enrolled_courses(db: AsyncSession, student_id: int, page: int = 1, per_page: int = 20) -> Tuple[List[Course], int]:
    """List enrolled courses for a student."""
    try:
        # Get enrollment course IDs for the student
        enrollment_result = await db.execute(
            select(Enrollment.course_id)
            .where(Enrollment.student_id == student_id)
            .where(Enrollment.is_active == True)
        )
        course_ids = [row[0] for row in enrollment_result.all()]
        
        if not course_ids:
            return [], 0

        # Get total count
        count_query = select(func.count(Course.id)).where(Course.id.in_(course_ids))
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Query courses with pagination and load relationships
        offset = (page - 1) * per_page
        query = (
            select(Course)
            .options(
                selectinload(Course.creator),
                selectinload(Course.enrollments)
            )
            .where(Course.id.in_(course_ids))
            .offset(offset)
            .limit(per_page)
        )
        
        result = await db.execute(query)
        courses = result.scalars().all()

        return courses, total
        
    except SQLAlchemyError:
        return [], 0

async def get_course_students(
    db: AsyncSession,
    course_id: int,
    page: int = 1,
    per_page: int = 10
) -> Tuple[List[dict], int]:
    """Get students enrolled in a course with pagination, sorted by students who owe money first.
    
    Returns students with owe_money=True first (those with unpaid invoices for this course),
    followed by students with owe_money=False (all invoices paid or no invoices).
    """
    try:
        # Import payment models for the query
        from app.models.payment import Invoice, Payment, PaymentStatus
        
        # Count total students
        count_query = (
            select(Enrollment.id)
            .where(Enrollment.course_id == course_id)
            .where(Enrollment.is_active == True)
        )
        count_result = await db.execute(count_query)
        total = len(count_result.all())
        
        # Get enrolled students with profiles and payment status (paginated)
        offset = (page - 1) * per_page
        
        # Subquery to check if student has unpaid invoices (owes money)
        unpaid_subquery = (
            select(Enrollment.student_id)
            .join(Invoice, Enrollment.id == Invoice.enrollment_id)
            .outerjoin(Payment, Invoice.id == Payment.invoice_id)
            .where(Enrollment.course_id == course_id)
            .where(Enrollment.is_active == True)
            .group_by(Enrollment.student_id, Invoice.id)
            .having(
                func.coalesce(
                    func.sum(
                        case(
                            (Payment.status == PaymentStatus.SUCCESSFUL, Payment.amount),
                            else_=0
                        )
                    ), 0
                ) < Invoice.amount_due
            )
        ).subquery()
        
        query = (
            select(
                User, 
                Enrollment.enrolled_at, 
                Enrollment.is_active,
                case(
                    (User.id.in_(select(unpaid_subquery.c.student_id)), 1),
                    else_=0
                ).label('has_unpaid')
            )
            .join(Enrollment, User.id == Enrollment.student_id)
            .options(selectinload(User.profile))
            .where(Enrollment.course_id == course_id)
            .where(Enrollment.is_active == True)
            .order_by(
                case(
                    (User.id.in_(select(unpaid_subquery.c.student_id)), 0),
                    else_=1
                ),  # Students who owe money first (0), then students who paid (1)
                User.email  # Secondary sort by email
            )
            .offset(offset)
            .limit(per_page)
        )
        
        result = await db.execute(query)
        students_data = result.all()
        
        students = []
        for student, enrolled_at, _, has_unpaid in students_data:
            students.append({
                'id': student.id,
                'email': student.email,
                'full_name': student.full_name,
                'enrolled_at': enrolled_at,
                'owe_money': bool(has_unpaid)
            })
        
        return students, total
        
    except SQLAlchemyError:
        return [], 0


async def check_course_ownership(db: AsyncSession, course_id: int, user_id: int) -> bool:
    """Check if user is the creator of the course."""
    try:
        result = await db.execute(
            select(Course.creator_id).where(Course.id == course_id)
        )
        creator_id = result.scalar_one_or_none()
        return creator_id == user_id if creator_id else False
    except SQLAlchemyError:
        return False


async def get_course_title(db: AsyncSession, course_id: int) -> Optional[str]:
    """Get course title by ID."""
    try:
        result = await db.execute(
            select(Course.title).where(Course.id == course_id)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError:
        return None

async def get_course_student_detail(
    db: AsyncSession,
    course_id: int,
    student_id: int
) -> Optional[dict]:
    """Get detailed information about a student in a course including invoices and payments."""
    try:
        # Import payment models
        from app.models.payment import Invoice, Payment, PaymentStatus, CoursePaymentPeriod
        
        # First check if student is enrolled in the course
        enrollment_result = await db.execute(
            select(Enrollment)
            .where(Enrollment.course_id == course_id)
            .where(Enrollment.student_id == student_id)
            .where(Enrollment.is_active == True)
        )
        enrollment = enrollment_result.scalar_one_or_none()
        
        if not enrollment:
            return None
        
        # Get all invoices for this student and course
        invoices_result = await db.execute(
            select(Invoice, CoursePaymentPeriod)
            .join(CoursePaymentPeriod, Invoice.payment_period_id == CoursePaymentPeriod.id)
            .options(
                selectinload(Invoice.payments),
                selectinload(CoursePaymentPeriod.created_by_user)
            )
            .where(Invoice.enrollment_id == enrollment.id)
            .order_by(CoursePaymentPeriod.created_at.desc())
        )
        invoice_data = invoices_result.all()
        
        # Process invoices and calculate payments
        invoices_dict = {}
        payments_dict = {}
        
        for invoice, payment_period in invoice_data:
            # Calculate total paid for this invoice
            total_paid = sum(
                float(p.amount) for p in invoice.payments 
                if p.status == PaymentStatus.SUCCESSFUL
            )
            
            # Add to payments dict (invoice_id -> amount_paid)
            payments_dict[invoice.id] = total_paid
            
            # Add to invoices dict (invoice_id -> _Invoice object data)
            invoices_dict[invoice.id] = {
                'amount_due': float(invoice.amount_due),
                'created_at': invoice.created_at
            }
        
        return {
            'invoices': invoices_dict,
            'payments': payments_dict
        }
        
    except SQLAlchemyError:
        return None
