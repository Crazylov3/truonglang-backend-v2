"""Course database operations."""

from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, or_
from sqlalchemy.sql import case
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from decimal import Decimal
from datetime import datetime
from app.models.course import *
from app.models.course_management import *
from app.models.user import *
from app.models.user_profile import *
from app.models.enrollment import *
from app.models.location import CourseSchedule
from app.models.payment import *
from app.models.invoice import *



async def create_course(
    db: AsyncSession,
    title: str,
    description: Optional[str],
    creator_id: UUID,
    price: Optional[Decimal] = None,
    start_date: Optional[datetime] = None,
    teacher_name: Optional[str] = None,
    branch_id: Optional[UUID] = None,
    group_chat_link: Optional[str] = None,
    preview_picture_path: Optional[str] = None
) -> Course:
    """Create a new course."""
    try:
        new_course = Course(
            title=title,
            description=description,
            creator_id=creator_id,
            price=price,
            start_date=start_date,
            teacher_name=teacher_name,
            branch_id=branch_id,
            group_chat_link=group_chat_link,
            preview_picture_path=preview_picture_path
        )
        
        db.add(new_course)
        await db.commit()
        await db.refresh(new_course)
        
        # Reload the course with relationships
        result = await db.execute(
            select(Course)
            .options(selectinload(Course.enrollments))
            .options(selectinload(Course.course_documents))
            .options(selectinload(Course.branch))
            .where(Course.id == new_course.id)
        )
        course_with_enrollments = result.scalar_one()
        
        return course_with_enrollments
        
    except SQLAlchemyError as e:
        await db.rollback()
        raise e


async def check_enrollment(
    db: AsyncSession,
    student_id: UUID,
    course_id: UUID
) -> Optional[Enrollment]:
    """Check if a student is enrolled in a course."""
    result = await db.execute(
        select(Enrollment)
        .where(
            Enrollment.student_id == student_id,
            Enrollment.course_id == course_id,
            Enrollment.is_active == True
        )
    )
    return result.scalar_one_or_none()


async def check_instructor_permission(
    db: AsyncSession,
    instructor_id: UUID,
    course_id: UUID
) -> bool:
    """Check if an instructor has permission to manage a course."""
    # Check if instructor is the course creator
    course = await db.get(Course, course_id)
    if course and course.creator_id == instructor_id:
        return True
    
    # Check if instructor has been granted permission
    result = await db.execute(
        select(CourseEditPermission)
        .where(
            CourseEditPermission.course_id == course_id,
            CourseEditPermission.instructor_id == instructor_id
        )
    )
    permission = result.scalar_one_or_none()
    return permission is not None

    
async def grant_edit_permission(db: AsyncSession, course_id: UUID, instructor_id: UUID, granted_by: UUID) -> bool:
    """Grant edit permission to an instructor for a course."""
    try:
        new_permission = CourseEditPermission(course_id=course_id, instructor_id=instructor_id, granted_by=granted_by)
        db.add(new_permission)
        await db.commit()
        return True
    except SQLAlchemyError as e:
        await db.rollback()
        raise e
    
async def revoke_edit_permission(db: AsyncSession, course_id: UUID, instructor_id: UUID) -> bool:
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


async def get_course_by_id(db: AsyncSession, course_id: UUID) -> Optional[Course]:
    """Get course by ID with relationships."""
    try:
        result = await db.execute(
            select(Course).options(
                selectinload(Course.creator),
                selectinload(Course.enrollments),
                selectinload(Course.branch)
            ).where(Course.id == course_id)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError:
        return None


async def update_course(
    db: AsyncSession,
    course_id: UUID,
    title: Optional[str] = None,
    description: Optional[str] = None,
    price: Optional[Decimal] = None,
    start_date: Optional[datetime] = None,
    teacher_name: Optional[str] = None,
    preview_picture_path: Optional[str] = None,
    branch_id: Optional[UUID] = None,
    group_chat_link: Optional[str] = None
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
        if start_date is not None:
            course.start_date = start_date
        if teacher_name is not None:
            course.teacher_name = teacher_name
        if preview_picture_path is not None:
            course.preview_picture_path = preview_picture_path
        if branch_id is not None:
            course.branch_id = branch_id
        if group_chat_link is not None:
            course.group_chat_link = group_chat_link
        
        await db.commit()
        await db.refresh(course)
        
        # Reload the course with relationships
        result = await db.execute(
            select(Course).options(
                selectinload(Course.enrollments),
                selectinload(Course.branch)
            ).where(Course.id == course_id)
        )
        course_with_enrollments = result.scalar_one()
        
        return course_with_enrollments
        
    except SQLAlchemyError:
        await db.rollback()
        return None


async def delete_course(db: AsyncSession, course_id: UUID) -> bool:
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

async def filter_courses_by_edit_permission(db: AsyncSession, instructor_id: UUID) -> List[UUID]:
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
    course_id: UUID,
    user_id: UUID,
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
    creator_id: Optional[UUID] = None,
    instructor_id: Optional[UUID] = None,
    all_courses: bool = False,
    branch_id: Optional[UUID] = None,
    room_id: Optional[UUID] = None,
    title: Optional[str] = None,
    teacher_name: Optional[str] = None
) -> Tuple[List[Course], int]:
    """List courses with pagination."""
    try:
        # Build query with preloaded relationships
        query = select(Course).options(
            selectinload(Course.creator),
            selectinload(Course.enrollments),
            selectinload(Course.branch)
        )
        
        # Apply filters
        if not all_courses:
          if creator_id:  
              query = query.where(Course.creator_id == creator_id)
          
          if instructor_id:
              query = query.where(Course.id.in_(await filter_courses_by_edit_permission(db, instructor_id)))
        
        # Filter by branch
        if branch_id:
            query = query.where(Course.branch_id == branch_id)
        
        # Filter by room (via schedules)
        if room_id:
            # Subquery to get course IDs that have schedules in the specified room
            room_course_ids = select(CourseSchedule.course_id).where(
                CourseSchedule.room_id == room_id
            ).distinct()
            query = query.where(Course.id.in_(room_course_ids))
        
        # Filter by title (case-insensitive partial match)
        if title:
            query = query.where(Course.title.ilike(f"%{title}%"))
        
        # Filter by teacher name (case-insensitive partial match)
        if teacher_name:
            query = query.where(Course.teacher_name.ilike(f"%{teacher_name}%"))
          
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

async def list_enrolled_courses(
    db: AsyncSession, 
    student_id: UUID, 
    page: int = 1, 
    per_page: int = 20,
    branch_id: Optional[UUID] = None,
    room_id: Optional[UUID] = None,
    title: Optional[str] = None,
    teacher_name: Optional[str] = None
) -> Tuple[List[Course], int]:
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

        # Build base query with enrolled courses
        query = (
            select(Course)
            .options(
                selectinload(Course.creator),
                selectinload(Course.enrollments),
                selectinload(Course.branch)
            )
            .where(Course.id.in_(course_ids))
        )
        
        # Apply additional filters
        if branch_id:
            query = query.where(Course.branch_id == branch_id)
        
        # Filter by room (via schedules)
        if room_id:
            room_course_ids = select(CourseSchedule.course_id).where(
                CourseSchedule.room_id == room_id
            ).distinct()
            query = query.where(Course.id.in_(room_course_ids))
        
        # Filter by title (case-insensitive partial match)
        if title:
            query = query.where(Course.title.ilike(f"%{title}%"))
        
        # Filter by teacher name (case-insensitive partial match)
        if teacher_name:
            query = query.where(Course.teacher_name.ilike(f"%{teacher_name}%"))
        
        # Update total count with filters
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

async def get_course_students(
    db: AsyncSession,
    course_id: UUID,
    student_id: Optional[UUID] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
    owe_money: Optional[bool] = None,
    page: int = 1,
    per_page: int = 10
) -> Tuple[List[dict], int]:
    """Get students enrolled in a course with pagination and filtering, sorted by students who owe money first.
    
    Returns students with owe_money=True first (those with unpaid invoices for this course),
    followed by students with owe_money=False (all invoices paid or no invoices).
    """
    try:
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
        
        # Build base query for counting
        base_query = (
            select(User.id)
            .join(Enrollment, User.id == Enrollment.student_id)
            .where(Enrollment.course_id == course_id)
            .where(Enrollment.is_active == True)
        )
        
        # Apply filters
        if student_id:
            base_query = base_query.where(User.id == student_id)
        
        if email:
            base_query = base_query.where(User.email.ilike(f"%{email}%"))
        
        # Join with profile if needed for name filters
        if first_name or last_name or owe_money is not None:
            base_query = base_query.join(UserProfile, User.id == UserProfile.user_id)
            
            if first_name:
                base_query = base_query.where(UserProfile.first_name.ilike(f"%{first_name}%"))
            
            if last_name:
                base_query = base_query.where(UserProfile.last_name.ilike(f"%{last_name}%"))
        
        # Apply owe_money filter to base query
        if owe_money is not None:
            if owe_money:
                # Only count students who owe money
                base_query = base_query.where(User.id.in_(select(unpaid_subquery.c.student_id)))
            else:
                # Only count students who don't owe money
                base_query = base_query.where(~User.id.in_(select(unpaid_subquery.c.student_id)))
        
        # Get total count with filters
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0
        
        # Get enrolled students with profiles and payment status (paginated)
        offset = (page - 1) * per_page
        
        # Build the main query to fetch students with all data
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
        )
        
        # Apply the same filters to the main query
        if student_id:
            query = query.where(User.id == student_id)
        
        if email:
            query = query.where(User.email.ilike(f"%{email}%"))
        
        if first_name or last_name or owe_money is not None:
            query = query.join(UserProfile, User.id == UserProfile.user_id)
            
            if first_name:
                query = query.where(UserProfile.first_name.ilike(f"%{first_name}%"))
            
            if last_name:
                query = query.where(UserProfile.last_name.ilike(f"%{last_name}%"))
        
        # Apply owe_money filter
        if owe_money is not None:
            if owe_money:
                # Only show students who owe money
                query = query.where(User.id.in_(select(unpaid_subquery.c.student_id)))
            else:
                # Only show students who don't owe money (paid or no invoices)
                query = query.where(~User.id.in_(select(unpaid_subquery.c.student_id)))
        
        # Order by owe_money status (those who owe first), then by email
        query = query.order_by(
            case(
                (User.id.in_(select(unpaid_subquery.c.student_id)), 0),
                else_=1
            ),  # Students who owe money first (0), then students who paid (1)
            User.email  # Secondary sort by email
        ).offset(offset).limit(per_page)
        
        result = await db.execute(query)
        students_data = result.all()
        
        students = []
        for student, enrolled_at, _, has_unpaid in students_data:
            students.append({
                'id': student.id,
                'public_id': student.public_id,
                'email': student.email,
                'full_name': student.full_name,
                'enrolled_at': enrolled_at,
                'owe_money': bool(has_unpaid)
            })
        
        return students, total
        
    except SQLAlchemyError:
        return [], 0


async def check_course_ownership(db: AsyncSession, course_id: UUID, user_id: UUID) -> bool:
    """Check if user is the creator of the course."""
    try:
        result = await db.execute(
            select(Course.creator_id).where(Course.id == course_id)
        )
        creator_id = result.scalar_one_or_none()
        return creator_id == user_id if creator_id else False
    except SQLAlchemyError:
        return False


async def get_course_title(db: AsyncSession, course_id: UUID) -> Optional[str]:
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
    course_id: UUID,
    student_id: UUID
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
