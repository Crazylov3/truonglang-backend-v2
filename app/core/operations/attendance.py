"""Attendance system database operations."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, date

from app.models.attendance import AttendanceCard, CardAssignment, AttendanceRecord, CardStatus, AttendanceType
from app.models.user import User


async def create_attendance_card(
    db: AsyncSession,
    card_uid: str,
    status: CardStatus = CardStatus.INACTIVE,
    notes: Optional[str] = None
) -> Optional[AttendanceCard]:
    """Create a new attendance card."""
    try:
        card = AttendanceCard(
            card_uid=card_uid,
            status=status,
            notes=notes
        )
        
        db.add(card)
        await db.commit()
        await db.refresh(card)
        
        return card
        
    except SQLAlchemyError:
        await db.rollback()
        return None


async def get_attendance_card(db: AsyncSession, card_uid: str) -> Optional[AttendanceCard]:
    """Get attendance card by UID."""
    try:
        result = await db.execute(
            select(AttendanceCard).where(AttendanceCard.card_uid == card_uid)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError:
        return None


async def update_card_status(
    db: AsyncSession,
    card_uid: str,
    status: CardStatus,
    notes: Optional[str] = None
) -> bool:
    """Update attendance card status."""
    try:
        result = await db.execute(
            select(AttendanceCard).where(AttendanceCard.card_uid == card_uid)
        )
        card = result.scalar_one_or_none()
        
        if not card:
            return False
        
        card.status = status
        if notes is not None:
            card.notes = notes
        
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False


async def assign_card_to_student(
    db: AsyncSession,
    student_id: int,
    card_uid: str
) -> Optional[CardAssignment]:
    """Assign a card to a student."""
    try:
        # Check if student already has an active card
        existing_assignment = await get_active_card_assignment(db, student_id)
        if existing_assignment:
            # Revoke existing assignment
            existing_assignment.revoked_at = datetime.utcnow()
        
        # Create new assignment
        assignment = CardAssignment(
            student_id=student_id,
            card_uid=card_uid
        )
        
        db.add(assignment)
        await db.commit()
        await db.refresh(assignment)
        
        return assignment
        
    except SQLAlchemyError:
        await db.rollback()
        return None


async def revoke_card_assignment(
    db: AsyncSession,
    student_id: int
) -> bool:
    """Revoke a student's card assignment."""
    try:
        result = await db.execute(
            select(CardAssignment).where(
                and_(
                    CardAssignment.student_id == student_id,
                    CardAssignment.revoked_at.is_(None)
                )
            )
        )
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            return False
        
        assignment.revoked_at = datetime.utcnow()
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False


async def get_active_card_assignment(
    db: AsyncSession,
    student_id: int
) -> Optional[CardAssignment]:
    """Get active card assignment for a student."""
    try:
        result = await db.execute(
            select(CardAssignment).where(
                and_(
                    CardAssignment.student_id == student_id,
                    CardAssignment.revoked_at.is_(None)
                )
            )
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError:
        return None


async def get_card_assignments_by_student(
    db: AsyncSession,
    student_id: int,
    include_revoked: bool = False
) -> List[CardAssignment]:
    """Get all card assignments for a student."""
    try:
        query = select(CardAssignment).where(CardAssignment.student_id == student_id)
        
        if not include_revoked:
            query = query.where(CardAssignment.revoked_at.is_(None))
        
        query = query.order_by(CardAssignment.assigned_at.desc())
        
        result = await db.execute(query)
        return result.scalars().all()
        
    except SQLAlchemyError:
        return []


async def create_attendance_record(
    db: AsyncSession,
    student_id: int,
    attendance_type: AttendanceType,
    card_uid: str
) -> Optional[AttendanceRecord]:
    """Create a new attendance record."""
    try:
        record = AttendanceRecord(
            student_id=student_id,
            type=attendance_type,
            card_uid_used=card_uid
        )
        
        db.add(record)
        await db.commit()
        await db.refresh(record)
        
        return record
        
    except SQLAlchemyError:
        await db.rollback()
        return None


async def get_attendance_records_by_student(
    db: AsyncSession,
    student_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100
) -> List[AttendanceRecord]:
    """Get attendance records for a student with optional date filtering."""
    try:
        query = select(AttendanceRecord).where(AttendanceRecord.student_id == student_id)
        
        if start_date:
            query = query.where(AttendanceRecord.swiped_at >= start_date)
        
        if end_date:
            query = query.where(AttendanceRecord.swiped_at <= end_date)
        
        query = query.order_by(AttendanceRecord.swiped_at.desc()).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
        
    except SQLAlchemyError:
        return []


async def get_attendance_records_by_course(
    db: AsyncSession,
    course_id: int,
    date: Optional[date] = None
) -> List[AttendanceRecord]:
    """Get attendance records for all students in a course."""
    try:
        # This would need to join with enrollments to get students in the course
        # For now, returning empty list - implement based on your specific needs
        return []
        
    except SQLAlchemyError:
        return []


async def get_attendance_summary_by_student(
    db: AsyncSession,
    student_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> dict:
    """Get attendance summary for a student."""
    try:
        query = select(
            AttendanceRecord.type,
            func.count(AttendanceRecord.id).label('count')
        ).where(AttendanceRecord.student_id == student_id)
        
        if start_date:
            query = query.where(AttendanceRecord.swiped_at >= start_date)
        
        if end_date:
            query = query.where(AttendanceRecord.swiped_at <= end_date)
        
        query = query.group_by(AttendanceRecord.type)
        
        result = await db.execute(query)
        records = result.fetchall()
        
        summary = {
            'check_ins': 0,
            'check_outs': 0,
            'total_records': 0
        }
        
        for record_type, count in records:
            if record_type == AttendanceType.CHECK_IN:
                summary['check_ins'] = count
            elif record_type == AttendanceType.CHECK_OUT:
                summary['check_outs'] = count
            summary['total_records'] += count
        
        return summary
        
    except SQLAlchemyError:
        return {'check_ins': 0, 'check_outs': 0, 'total_records': 0}


# Missing functions that the router needs
async def get_card_assignment(db: AsyncSession, assignment_id: int) -> Optional[CardAssignment]:
    """Get a specific card assignment by ID."""
    try:
        result = await db.execute(
            select(CardAssignment).where(CardAssignment.id == assignment_id)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError:
        return None


async def get_student_attendance_records(
    db: AsyncSession,
    student_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100
) -> List[AttendanceRecord]:
    """Get attendance records for a student (alias for get_attendance_records_by_student)."""
    return await get_attendance_records_by_student(db, student_id, start_date, end_date, limit)


async def get_student_attendance_summary(
    db: AsyncSession,
    student_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> dict:
    """Get attendance summary for a student (alias for get_attendance_summary_by_student)."""
    return await get_attendance_summary_by_student(db, student_id, start_date, end_date)


async def bulk_create_attendance_cards(
    db: AsyncSession,
    cards: List[dict]
) -> dict:
    """Bulk create attendance cards."""
    successful = []
    failed = []
    
    for card_data in cards:
        try:
            card = await create_attendance_card(
                db=db,
                card_uid=card_data['card_uid'],
                notes=card_data.get('notes')
            )
            if card:
                successful.append(card)
            else:
                failed.append(card_data)
        except Exception as e:
            failed.append(card_data)
    
    return {
        'successful': successful,
        'failed': failed
    }


async def bulk_assign_cards_for_class(
    db: AsyncSession,
    assignments: List[dict]
) -> dict:
    """Bulk assign cards to students for a class."""
    successful = []
    failed = []
    
    for assignment_data in assignments:
        try:
            assignment = await assign_card_to_student(
                db=db,
                student_id=assignment_data['student_id'],
                card_uid=assignment_data['card_uid']
            )
            if assignment:
                successful.append(assignment)
            else:
                failed.append(assignment_data)
        except Exception as e:
            failed.append(assignment_data)
    
    return {
        'successful': successful,
        'failed': failed
    }


async def bulk_revoke_card_assignments(
    db: AsyncSession,
    assignment_ids: List[int]
) -> dict:
    """Bulk revoke card assignments."""
    successful = []
    failed = []
    
    for assignment_id in assignment_ids:
        try:
            assignment = await get_card_assignment(db, assignment_id)
            if assignment:
                result = await revoke_card_assignment(db, assignment_id)
                if result:
                    successful.append(assignment_id)
                else:
                    failed.append(assignment_id)
            else:
                failed.append(assignment_id)
        except Exception as e:
            failed.append(assignment_id)
    
    return {
        'successful': successful,
        'failed': failed
    }


async def bulk_import_attendance_records(
    db: AsyncSession,
    records: List[dict]
) -> dict:
    """Bulk import attendance records."""
    successful = []
    failed = []
    
    for record_data in records:
        try:
            record = await create_attendance_record(
                db=db,
                student_id=record_data['student_id'],
                attendance_type=record_data['type'],
                card_uid=record_data['card_uid']
            )
            if record:
                successful.append(record)
            else:
                failed.append(record_data)
        except Exception as e:
            failed.append(record_data)
    
    return {
        'successful': successful,
        'failed': failed
    }
