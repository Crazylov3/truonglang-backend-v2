"""Attendance management router for card-based attendance system."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, datetime
import csv
import io

from app.core.deps import get_db, get_current_user, require_role
from app.core.operations.attendance import (
    create_attendance_card, get_attendance_card, update_card_status,
    assign_card_to_student, get_card_assignment, revoke_card_assignment,
    create_attendance_record, get_student_attendance_records, get_student_attendance_summary,
    bulk_create_attendance_cards, bulk_assign_cards_for_class, bulk_revoke_card_assignments,
    bulk_import_attendance_records
)
from app.core.operations.audit import log_database_operation
from app.models.user import User, UserRole
from app.models.attendance import CardStatus, AttendanceType
from app.models.audit import AuditAction
from app.schemas.attendance.attendance_schemas import (
    AttendanceCardCreate, AttendanceCardResponse, CardStatusUpdateRequest,
    CardAssignmentCreate, CardAssignmentResponse,
    AttendanceRecordCreate, AttendanceRecordResponse, AttendanceSummaryResponse,
    AttendanceRecordsResponse, AttendanceCardsResponse, CardAssignmentsResponse,
    BulkCardCreateRequest, BulkCardCreateResponse,
    BulkCardAssignmentRequest, BulkCardAssignmentResponse,
    BulkAttendanceRecordRequest, BulkAttendanceRecordResponse
)

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/cards/bulk", response_model=BulkCardCreateResponse)
async def bulk_create_attendance_cards_endpoint(
    request: BulkCardCreateRequest,
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Bulk create attendance cards (Staff/Admin only)."""
    try:
        result = await bulk_create_attendance_cards(db, request.cards)
        
        # Audit log the bulk operation
        await log_database_operation(
            db=db,
            action=AuditAction.CREATE,
            table_name="attendance_cards",
            operation_summary=f"Bulk created {len(result.successful)} attendance cards",
            operation_details={
                "total_requested": len(request.cards),
                "successful_count": len(result.successful),
                "failed_count": len(result.failed),
                "failed_reasons": [f.card_uid for f in result.failed]
            },
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role
        )
        
        return result
        
    except Exception as e:
        # Audit log the failed operation
        await log_database_operation(
            db=db,
            action=AuditAction.CREATE,
            table_name="attendance_cards",
            operation_summary="Bulk attendance card creation failed",
            operation_details={"error": str(e)},
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role
        )
        raise


@router.post("/cards/bulk-csv", response_model=BulkCardCreateResponse)
async def bulk_create_attendance_cards_from_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Bulk create attendance cards from CSV file (Staff/Admin only)."""
    try:
        # Read CSV content
        content = await file.read()
        csv_text = content.decode('utf-8')
        
        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(csv_text))
        cards = []
        
        for row in csv_reader:
            cards.append(AttendanceCardCreate(
                card_uid=row['card_uid'],
                notes=row.get('notes', '')
            ))
        
        # Create cards
        request = BulkCardCreateRequest(cards=cards)
        result = await bulk_create_attendance_cards(db, request)
        
        # Audit log the CSV import operation
        await log_database_operation(
            db=db,
            action=AuditAction.CREATE,
            table_name="attendance_cards",
            operation_summary=f"CSV import: Created {len(result.successful)} attendance cards",
            operation_details={
                "file_name": file.filename,
                "file_size": len(content),
                "total_requested": len(cards),
                "successful_count": len(result.successful),
                "failed_count": len(result.failed)
            },
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role
        )
        
        return result
        
    except Exception as e:
        # Audit log the failed CSV import
        await log_database_operation(
            db=db,
            action=AuditAction.CREATE,
            table_name="attendance_cards",
            operation_summary="CSV import of attendance cards failed",
            operation_details={"error": str(e), "file_name": file.filename},
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role
        )
        raise


@router.get("/cards/{card_uid}", response_model=AttendanceCardResponse)
async def get_attendance_card_endpoint(
    card_uid: str,
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Get attendance card details (Staff/Admin only)."""
    card = await get_attendance_card(db, card_uid)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Audit log the read operation
    await log_database_operation(
        db=db,
        action=AuditAction.READ,
        table_name="attendance_cards",
        record_id=card_uid,
        operation_summary=f"Retrieved attendance card: {card_uid}",
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=current_user.role
    )
    
    return card


@router.patch("/cards/{card_uid}/status", response_model=AttendanceCardResponse)
async def update_attendance_card_status_endpoint(
    card_uid: str,
    status_update: CardStatusUpdateRequest,
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Update attendance card status (Staff/Admin only)."""
    try:
        # Get old values for audit
        old_card = await get_attendance_card(db, card_uid)
        if not old_card:
            raise HTTPException(status_code=404, detail="Card not found")
        
        old_status = old_card.status
        
        # Update status
        card = await update_card_status(db, card_uid, status_update.status)
        
        # Audit log the status update
        await log_database_operation(
            db=db,
            action=AuditAction.UPDATE,
            table_name="attendance_cards",
            record_id=card_uid,
            old_values={"status": old_status},
            new_values={"status": status_update.status},
            changed_fields=["status"],
            operation_summary=f"Updated card {card_uid} status from {old_status} to {status_update.status}",
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role
        )
        
        return card
        
    except Exception as e:
        # Audit log the failed update
        await log_database_operation(
            db=db,
            action=AuditAction.UPDATE,
            table_name="attendance_cards",
            operation_summary=f"Failed to update card {card_uid} status",
            operation_details={"error": str(e)},
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role
        )
        raise


@router.post("/assignments/bulk", response_model=BulkCardAssignmentResponse)
async def bulk_assign_cards_for_class_endpoint(
    request: BulkCardAssignmentRequest,
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Bulk assign cards to students for a class (Staff/Admin only)."""
    try:
        result = await bulk_assign_cards_for_class(db, request.assignments)
        
        # Audit log the bulk assignment operation
        await log_database_operation(
            db=db,
            action=AuditAction.CREATE,
            table_name="card_assignments",
            operation_summary=f"Bulk assigned {len(result.successful)} cards to students",
            operation_details={
                "total_requested": len(request.assignments),
                "successful_count": len(result.successful),
                "failed_count": len(result.failed),
                "course_id": request.assignments[0].course_id if request.assignments else None
            },
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role
        )
        
        return result
        
    except Exception as e:
        # Audit log the failed operation
        await log_database_operation(
            db=db,
            action=AuditAction.CREATE,
            table_name="card_assignments",
            operation_summary="Bulk card assignment failed",
            operation_details={"error": str(e)},
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role
        )
        raise


@router.post("/assignments/bulk-csv", response_model=BulkCardAssignmentResponse)
async def bulk_assign_cards_from_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Bulk assign cards from CSV file (Staff/Admin only)."""
    try:
        # Read CSV content
        content = await file.read()
        csv_text = content.decode('utf-8')
        
        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(csv_text))
        assignments = []
        
        for row in csv_reader:
            assignments.append(CardAssignmentCreate(
                student_id=int(row['student_id']),
                card_uid=row['card_uid'],
                course_id=int(row.get('course_id', 0)) if row.get('course_id') else None
            ))
        
        # Create assignments
        request = BulkCardAssignmentRequest(assignments=assignments)
        result = await bulk_assign_cards_for_class(db, request)
        
        # Audit log the CSV import operation
        await log_database_operation(
            db=db,
            action=AuditAction.CREATE,
            table_name="card_assignments",
            operation_summary=f"CSV import: Assigned {len(result.successful)} cards to students",
            operation_details={
                "file_name": file.filename,
                "file_size": len(content),
                "total_requested": len(assignments),
                "successful_count": len(result.successful),
                "failed_count": len(result.failed)
            },
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role
        )
        
        return result
        
    except Exception as e:
        # Audit log the failed CSV import
        await log_database_operation(
            db=db,
            action=AuditAction.CREATE,
            table_name="card_assignments",
            operation_summary="CSV import of card assignments failed",
            operation_details={"error": str(e), "file_name": file.filename},
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role
        )
        raise


@router.delete("/assignments/bulk-revoke")
async def bulk_revoke_card_assignments_endpoint(
    student_ids: List[int],
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Bulk revoke card assignments (Staff/Admin only)."""
    try:
        # Get old assignments for audit
        old_assignments = []
        for student_id in student_ids:
            assignment = await get_card_assignment(db, student_id)
            if assignment:
                old_assignments.append(assignment)
        
        # Revoke assignments
        revoked_count = await bulk_revoke_card_assignments(db, student_ids)
        
        # Audit log the bulk revocation
        await log_database_operation(
            db=db,
            action=AuditAction.DELETE,
            table_name="card_assignments",
            operation_summary=f"Bulk revoked {revoked_count} card assignments",
            operation_details={
                "student_ids": student_ids,
                "revoked_count": revoked_count,
                "old_assignments": [
                    {"student_id": a.student_id, "card_uid": a.card_uid, "assigned_at": a.assigned_at.isoformat()}
                    for a in old_assignments
                ]
            },
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role
        )
        
        return {"message": f"Revoked {revoked_count} card assignments", "revoked_count": revoked_count}
        
    except Exception as e:
        # Audit log the failed operation
        await log_database_operation(
            db=db,
            action=AuditAction.DELETE,
            table_name="card_assignments",
            operation_summary="Bulk card assignment revocation failed",
            operation_details={"error": str(e), "student_ids": student_ids},
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role
        )
        raise


@router.post("/records/bulk-import", response_model=BulkAttendanceRecordResponse)
async def bulk_import_attendance_records_endpoint(
    request: BulkAttendanceRecordRequest,
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Bulk import attendance records (Staff/Admin only)."""
    try:
        result = await bulk_import_attendance_records(db, request.records)
        
        # Audit log the bulk import operation
        await log_database_operation(
            db=db,
            action=AuditAction.CREATE,
            table_name="attendance_records",
            operation_summary=f"Bulk imported {len(result.successful)} attendance records",
            operation_details={
                "total_requested": len(request.records),
                "successful_count": len(result.successful),
                "failed_count": len(result.failed),
                "date_range": {
                    "earliest": min(r.swiped_at for r in request.records).isoformat() if request.records else None,
                    "latest": max(r.swiped_at for r in request.records).isoformat() if request.records else None
                }
            },
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role
        )
        
        return result
        
    except Exception as e:
        # Audit log the failed operation
        await log_database_operation(
            db=db,
            action=AuditAction.CREATE,
            table_name="attendance_records",
            operation_summary="Bulk attendance record import failed",
            operation_details={"error": str(e)},
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role
        )
        raise


@router.post("/records/bulk-csv", response_model=BulkAttendanceRecordResponse)
async def bulk_import_attendance_records_from_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Bulk import attendance records from CSV file (Staff/Admin only)."""
    try:
        # Read CSV content
        content = await file.read()
        csv_text = content.decode('utf-8')
        
        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(csv_text))
        records = []
        
        for row in csv_reader:
            records.append(AttendanceRecordCreate(
                student_id=int(row['student_id']),
                swiped_at=datetime.fromisoformat(row['swiped_at']),
                type=int(row['type']),
                card_uid_used=row['card_uid_used']
            ))
        
        # Create records
        request = BulkAttendanceRecordRequest(records=records)
        result = await bulk_import_attendance_records(db, request)
        
        # Audit log the CSV import operation
        await log_database_operation(
            db=db,
            action=AuditAction.CREATE,
            table_name="attendance_records",
            operation_summary=f"CSV import: Imported {len(result.successful)} attendance records",
            operation_details={
                "file_name": file.filename,
                "file_size": len(content),
                "total_requested": len(records),
                "successful_count": len(result.successful),
                "failed_count": len(result.failed)
            },
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role
        )
        
        return result
        
    except Exception as e:
        # Audit log the failed CSV import
        await log_database_operation(
            db=db,
            action=AuditAction.CREATE,
            table_name="attendance_records",
            operation_summary="CSV import of attendance records failed",
            operation_details={"error": str(e), "file_name": file.filename},
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role
        )
        raise


# ============================================================================
# QUERY AND REPORTING (For Staff to view data)
# ============================================================================

@router.get("/records/student/{student_id}", response_model=AttendanceRecordsResponse)
async def get_student_attendance_records(
    student_id: int,
    start_date: Optional[date] = Query(None, description="Start date for filtering"),
    end_date: Optional[date] = Query(None, description="End date for filtering"),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Get attendance records for a specific student (Staff/Admin only)."""
    records = await get_student_attendance_records(
        db=db,
        student_id=student_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    
    return AttendanceRecordsResponse(
        records=records,
        total=len(records)
    )


@router.get("/summary/student/{student_id}", response_model=AttendanceSummaryResponse)
async def get_student_attendance_summary(
    student_id: int,
    start_date: Optional[date] = Query(None, description="Start date for summary"),
    end_date: Optional[date] = Query(None, description="End date for summary"),
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Get attendance summary for a specific student (Staff/Admin only)."""
    summary = await get_student_attendance_summary(
        db=db,
        student_id=student_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return AttendanceSummaryResponse(
        student_id=student_id,
        check_ins=summary['check_ins'],
        check_outs=summary['check_outs'],
        total_records=summary['total_records'],
        period_start=start_date,
        period_end=end_date
    )


@router.get("/summary/class")
async def get_class_attendance_summary(
    course_id: Optional[int] = Query(None, description="Filter by course ID"),
    date: Optional[date] = Query(None, description="Specific date for summary"),
    start_date: Optional[date] = Query(None, description="Start date for summary"),
    end_date: Optional[date] = Query(None, description="End date for summary"),
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Get attendance summary for a class or date range (Staff/Admin only)."""
    # This would need to be implemented in attendance_ops
    # For now, returning mock data
    return {
        "course_id": course_id,
        "date": date,
        "start_date": start_date,
        "end_date": end_date,
        "total_students": 0,
        "present_today": 0,
        "absent_today": 0,
        "attendance_rate": 0.0
    }


# ============================================================================
# STUDENT ENDPOINTS (For viewing own attendance)
# ============================================================================

@router.get("/my-attendance", response_model=AttendanceRecordsResponse)
async def get_my_attendance_records(
    start_date: Optional[date] = Query(None, description="Start date for filtering"),
    end_date: Optional[date] = Query(None, description="End date for filtering"),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's attendance records."""
    if current_user.role not in [UserRole.STUDENT, UserRole.INSTRUCTOR, UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    records = await get_student_attendance_records(
        db=db,
        student_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    
    return AttendanceRecordsResponse(
        records=records,
        total=len(records)
    )


@router.get("/my-summary", response_model=AttendanceSummaryResponse)
async def get_my_attendance_summary(
    start_date: Optional[date] = Query(None, description="Start date for summary"),
    end_date: Optional[date] = Query(None, description="End date for summary"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's attendance summary."""
    if current_user.role not in [UserRole.STUDENT, UserRole.INSTRUCTOR, UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    summary = await get_student_attendance_summary(
        db=db,
        student_id=current_user.id,
        start_date=start_date,
        end_date=end_date
    )
    
    return AttendanceSummaryResponse(
        student_id=current_user.id,
        check_ins=summary['check_ins'],
        check_outs=summary['check_outs'],
        total_records=summary['total_records'],
        period_start=start_date,
        period_end=end_date
    )
