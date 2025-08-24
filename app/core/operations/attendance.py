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
