"""Attendance system database operations."""

from typing import Optional, List, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from sqlalchemy import delete as sa_delete
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, date

from app.models.attendance import AttendanceCard, CardAssignment, AttendanceRecord, CardStatus, AttendanceType
from app.models.user import User
async def get_card_assignee_public_id(db: AsyncSession, card_uid: str) -> Optional[int]:
    """Return public_id of the user currently assigned to the card (revoked_at is NULL)."""
    try:
        result = await db.execute(
            select(User.public_id)
            .select_from(CardAssignment)
            .join(User, User.id == CardAssignment.student_id)
            .where(and_(CardAssignment.card_uid == card_uid, CardAssignment.revoked_at.is_(None)))
        )
        row = result.first()
        return row[0] if row else None
    except SQLAlchemyError:
        return None


async def search_attendance_cards(
    db: AsyncSession,
    *,
    uid: Optional[str] = None,
    branch_id: Optional[UUID] = None,
    status: Optional[CardStatus] = None,
    limit: int = 100,
    offset: int = 0
) -> List[tuple[AttendanceCard, Optional[int]]]:
    """Search attendance cards with optional filters and include assignee public_id.

    Returns a list of tuples: (AttendanceCard, assigned_public_id)
    """
    try:
        # Base query with LEFT JOIN to get current assignee public_id
        query = (
            select(AttendanceCard, User.public_id)
            .select_from(AttendanceCard)
            .join(CardAssignment, and_(CardAssignment.card_uid == AttendanceCard.card_uid, CardAssignment.revoked_at.is_(None)), isouter=True)
            .join(User, User.id == CardAssignment.student_id, isouter=True)
        )

        if uid:
            query = query.where(AttendanceCard.card_uid.ilike(f"%{uid}%"))
        if branch_id:
            query = query.where(AttendanceCard.branch_id == branch_id)
        if status:
            query = query.where(AttendanceCard.status == status)

        query = query.order_by(AttendanceCard.issued_at.desc()).limit(limit).offset(offset)

        result = await db.execute(query)
        return result.all()
    except SQLAlchemyError:
        return []


async def count_attendance_cards(
    db: AsyncSession,
    *,
    uid: Optional[str] = None,
    branch_id: Optional[UUID] = None,
    status: Optional[CardStatus] = None,
) -> int:
    """Count total attendance cards matching the optional filters."""
    try:
        from sqlalchemy import func as _func
        query = select(_func.count(AttendanceCard.card_uid))
        if uid:
            query = query.where(AttendanceCard.card_uid.ilike(f"%{uid}%"))
        if branch_id:
            query = query.where(AttendanceCard.branch_id == branch_id)
        if status:
            query = query.where(AttendanceCard.status == status)
        result = await db.execute(query)
        return int(result.scalar_one() or 0)
    except SQLAlchemyError:
        return 0

async def update_attendance_card(
    db: AsyncSession,
    card_uid: str,
    *,
    status: Optional[CardStatus] = None,
    notes: Optional[str] = None,
    branch_id: Optional[UUID] = None,
    card_uuid: Optional[UUID] = None
) -> Optional[AttendanceCard]:
    """Update mutable fields of an attendance card.

    Does not allow changing the primary key (card_uid).
    """
    try:
        result = await db.execute(
            select(AttendanceCard).where(AttendanceCard.card_uid == card_uid)
        )
        card = result.scalar_one_or_none()
        if not card:
            return None

        if status is not None:
            card.status = status
        if notes is not None:
            card.notes = notes
        if branch_id is not None:
            card.branch_id = branch_id
        if card_uuid is not None:
            card.card_uuid = card_uuid

        await db.commit()
        await db.refresh(card)
        return card
    except SQLAlchemyError:
        await db.rollback()
        return None


async def create_attendance_card(
    db: AsyncSession,
    card_uid: str,
    branch_id: UUID,
    card_uuid: Optional[UUID] = None,
    status: CardStatus = CardStatus.INACTIVE,
    notes: Optional[str] = None
) -> Optional[AttendanceCard]:
    """Create a new attendance card."""
    try:
        card = AttendanceCard(
            card_uid=card_uid,
            branch_id=branch_id,
            card_uuid=card_uuid,
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
    student_id: UUID,
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
    student_id: UUID
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
    student_id: UUID
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
    student_id: UUID,
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
    student_id: UUID,
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
    student_id: UUID,
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
    student_id: UUID,
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
async def get_card_assignment(db: AsyncSession, assignment_id: UUID) -> Optional[CardAssignment]:
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
    student_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100
) -> List[AttendanceRecord]:
    """Get attendance records for a student (alias for get_attendance_records_by_student)."""
    return await get_attendance_records_by_student(db, student_id, start_date, end_date, limit)


async def get_student_attendance_summary(
    db: AsyncSession,
    student_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> dict:
    """Get attendance summary for a student (alias for get_attendance_summary_by_student)."""
    return await get_attendance_summary_by_student(db, student_id, start_date, end_date)


async def bulk_create_attendance_cards(
    db: AsyncSession,
    cards: List[Any]
) -> dict:
    """Bulk create attendance cards."""
    successful = []
    failed = []

    # Helper to read fields from dicts or Pydantic models
    def _get(obj: Any, field: str, default: Any = None):
        if isinstance(obj, dict):
            return obj.get(field, default)
        return getattr(obj, field, default)

    try:
        # Build all model instances first
        instances: List[AttendanceCard] = []
        for card_data in cards:
            instances.append(
                AttendanceCard(
                    card_uid=_get(card_data, 'card_uid'),
                    branch_id=_get(card_data, 'branch_id'),
                    card_uuid=_get(card_data, 'card_uuid'),
                    status=_get(card_data, 'status', CardStatus.INACTIVE),
                    notes=_get(card_data, 'notes')
                )
            )

        # Single batch add and commit
        db.add_all(instances)
        await db.commit()

        # Refresh instances to populate defaults
        for instance in instances:
            try:
                await db.refresh(instance)
            except Exception:
                # Non-fatal if refresh fails for some
                pass

        successful = instances
    except Exception:
        await db.rollback()
        # If batch fails entirely, mark all as failed
        failed = cards

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
    assignment_ids: List[UUID]
) -> dict:
    """Bulk revoke card assignments."""
    successful = []
    failed = []
    
    for assignment_id in assignment_ids:
        try:
            assignment = await get_card_assignment(db, assignment_id)
            if assignment:
                # For bulk by assignment_id, mark revoked_at now
                assignment.revoked_at = datetime.utcnow()
                await db.commit()
                result = True
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


async def update_card_assignment(
    db: AsyncSession,
    assignment_id: UUID,
    *,
    card_uid: Optional[str] = None,
    revoked: Optional[bool] = None
) -> Optional[CardAssignment]:
    """Update a single card assignment (change card, or revoke)."""
    try:
        result = await db.execute(
            select(CardAssignment).where(CardAssignment.id == assignment_id)
        )
        assignment = result.scalar_one_or_none()
        if not assignment:
            return None

        if card_uid is not None:
            assignment.card_uid = card_uid
        if revoked is True and assignment.revoked_at is None:
            assignment.revoked_at = datetime.utcnow()
        if revoked is False:
            assignment.revoked_at = None

        await db.commit()
        await db.refresh(assignment)
        return assignment
    except SQLAlchemyError:
        await db.rollback()
        return None


async def delete_card_assignment(
    db: AsyncSession,
    assignment_id: UUID
) -> bool:
    """Hard delete a card assignment by ID."""
    try:
        result = await db.execute(
            select(CardAssignment).where(CardAssignment.id == assignment_id)
        )
        assignment = result.scalar_one_or_none()
        if not assignment:
            return False
        await db.delete(assignment)
        await db.commit()
        return True
    except SQLAlchemyError:
        await db.rollback()
        return False


async def delete_attendance_card(
    db: AsyncSession,
    card_uid: str
) -> bool:
    """Delete an attendance card and its related assignments."""
    try:
        # Ensure card exists
        result = await db.execute(
            select(AttendanceCard).where(AttendanceCard.card_uid == card_uid)
        )
        card = result.scalar_one_or_none()
        if not card:
            return False

        # Delete all assignments referencing this card to avoid FK violations
        assignments_result = await db.execute(
            select(CardAssignment).where(CardAssignment.card_uid == card_uid)
        )
        assignments = assignments_result.scalars().all()
        for a in assignments:
            await db.delete(a)

        # Delete the card itself
        await db.delete(card)
        await db.commit()
        return True
    except SQLAlchemyError:
        await db.rollback()
        return False


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
