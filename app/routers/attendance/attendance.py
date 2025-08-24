from fastapi import Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date, datetime
import csv
import io

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.attendance import (
    AttendanceCardCreate, AttendanceCardResponse, AttendanceCardUpdate,
    CardAssignmentCreate, CardAssignmentResponse,
    AttendanceRecordCreate, AttendanceRecordResponse,
    AttendanceSummaryResponse, AttendanceCardsResponse,
    CardAssignmentsResponse, AttendanceRecordsResponse,
    BulkCardAssignmentRequest, BulkCardAssignmentResponse,
    CardStatusUpdateRequest, AttendanceFilterRequest,
    BulkCardCreateRequest, BulkCardCreateResponse,
    BulkAttendanceRecordRequest, BulkAttendanceRecordResponse
)
from app.core.decorators import csrf_protect
from app.core.deps import get_current_user, require_role
from app.core.operations import attendance as attendance_ops
from app.models.attendance import CardStatus, AttendanceType

# Create router
from fastapi import APIRouter
router = APIRouter(prefix="/attendance", tags=["attendance"])


# ============================================================================
# BULK CARD MANAGEMENT (For Staff to manage physical cards)
# ============================================================================

@router.post("/cards/bulk", response_model=BulkCardCreateResponse, status_code=status.HTTP_201_CREATED)
@csrf_protect
async def bulk_create_attendance_cards(
    cards_data: BulkCardCreateRequest,
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Bulk create multiple attendance cards for a new batch (Staff/Admin only)."""
    successful = []
    failed = []
    
    for card_data in cards_data.cards:
        try:
            # Check if card already exists
            existing_card = await attendance_ops.get_attendance_card(db, card_data.card_uid)
            if existing_card:
                failed.append({
                    "card_uid": card_data.card_uid,
                    "error": "Card already exists"
                })
                continue
            
            card = await attendance_ops.create_attendance_card(
                db=db,
                card_uid=card_data.card_uid,
                status=card_data.status,
                notes=card_data.notes
            )
            
            if card:
                successful.append(card)
            else:
                failed.append({
                    "card_uid": card_data.card_uid,
                    "error": "Failed to create card"
                })
                
        except Exception as e:
            failed.append({
                "card_uid": card_data.card_uid,
                "error": str(e)
            })
    
    return BulkCardCreateResponse(
        cards=successful,
        failed=failed,
        total_requested=len(cards_data.cards),
        total_successful=len(successful),
        total_failed=len(failed)
    )


@router.post("/cards/bulk-csv", response_model=BulkCardCreateResponse, status_code=status.HTTP_201_CREATED)
@csrf_protect
async def bulk_create_attendance_cards_from_csv(
    file: UploadFile = File(..., description="CSV file with card_uid,status,notes columns"),
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Bulk create attendance cards from CSV upload (Staff/Admin only)."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV"
        )
    
    try:
        content = await file.read()
        csv_text = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_text))
        
        cards_data = []
        for row in csv_reader:
            cards_data.append(AttendanceCardCreate(
                card_uid=row['card_uid'],
                status=CardStatus(int(row.get('status', 2))),  # Default to INACTIVE
                notes=row.get('notes')
            ))
        
        # Use the bulk create endpoint
        return await bulk_create_attendance_cards(
            BulkCardCreateRequest(cards=cards_data),
            current_user,
            db
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing CSV: {str(e)}"
        )


@router.get("/cards", response_model=AttendanceCardsResponse)
async def list_attendance_cards(
    status: Optional[CardStatus] = Query(None, description="Filter by card status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """List attendance cards with optional filtering (Staff/Admin only)."""
    # This would need to be implemented in attendance_ops
    # For now, returning empty response
    return AttendanceCardsResponse(cards=[], total=0)


@router.get("/cards/{card_uid}", response_model=AttendanceCardResponse)
async def get_attendance_card(
    card_uid: str,
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Get attendance card by UID (Staff/Admin only)."""
    card = await attendance_ops.get_attendance_card(db, card_uid)
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance card not found"
        )
    return card


@router.put("/cards/{card_uid}", response_model=AttendanceCardResponse)
@csrf_protect
async def update_attendance_card(
    card_uid: str,
    card_update: CardStatusUpdateRequest,
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Update attendance card status (Staff/Admin only)."""
    success = await attendance_ops.update_card_status(
        db=db,
        card_uid=card_uid,
        status=card_update.status,
        notes=card_update.notes
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance card not found"
        )
    
    # Get updated card
    card = await attendance_ops.get_attendance_card(db, card_uid)
    return card


@router.get("/cards/inventory/summary")
async def get_card_inventory_summary(
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Get summary of card inventory by status (Staff/Admin only)."""
    # This would need to be implemented in attendance_ops
    # For now, returning mock data
    return {
        "total_cards": 0,
        "active_cards": 0,
        "inactive_cards": 0,
        "lost_cards": 0,
        "damaged_cards": 0,
        "assigned_cards": 0,
        "available_cards": 0
    }


# ============================================================================
# BULK CARD ASSIGNMENT MANAGEMENT (For Class Rosters)
# ============================================================================

@router.post("/assignments/bulk", response_model=BulkCardAssignmentResponse, status_code=status.HTTP_201_CREATED)
@csrf_protect
async def bulk_assign_cards_for_class(
    bulk_data: BulkCardAssignmentRequest,
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Bulk assign cards to students for a class roster (Staff/Admin only)."""
    successful = []
    failed = []
    
    for assignment_data in bulk_data.assignments:
        try:
            # Check if card exists and is available
            card = await attendance_ops.get_attendance_card(db, assignment_data.card_uid)
            if not card:
                failed.append({
                    "student_id": assignment_data.student_id,
                    "card_uid": assignment_data.card_uid,
                    "error": "Card not found"
                })
                continue
            
            if card.status != CardStatus.ACTIVE:
                failed.append({
                    "student_id": assignment_data.student_id,
                    "card_uid": assignment_data.card_uid,
                    "error": f"Card is {card.status.name} and cannot be assigned"
                })
                continue
            
            assignment = await attendance_ops.assign_card_to_student(
                db=db,
                student_id=assignment_data.student_id,
                card_uid=assignment_data.card_uid
            )
            
            if assignment:
                successful.append(assignment)
            else:
                failed.append({
                    "student_id": assignment_data.student_id,
                    "card_uid": assignment_data.card_uid,
                    "error": "Failed to create assignment"
                })
                
        except Exception as e:
            failed.append({
                "student_id": assignment_data.student_id,
                "card_uid": assignment_data.card_uid,
                "error": str(e)
            })
    
    return BulkCardAssignmentResponse(
        successful=successful,
        failed=failed,
        total_requested=len(bulk_data.assignments),
        total_successful=len(successful),
        total_failed=len(failed)
    )


@router.post("/assignments/bulk-csv", response_model=BulkCardAssignmentResponse, status_code=status.HTTP_201_CREATED)
@csrf_protect
async def bulk_assign_cards_from_csv(
    file: UploadFile = File(..., description="CSV file with student_id,card_uid columns"),
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Bulk assign cards to students from CSV upload (Staff/Admin only)."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV"
        )
    
    try:
        content = await file.read()
        csv_text = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_text))
        
        assignments_data = []
        for row in csv_reader:
            assignments_data.append(CardAssignmentCreate(
                student_id=int(row['student_id']),
                card_uid=row['card_uid']
            ))
        
        # Use the bulk assignment endpoint
        return await bulk_assign_cards_for_class(
            BulkCardAssignmentRequest(assignments=assignments_data),
            current_user,
            db
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing CSV: {str(e)}"
        )


@router.delete("/assignments/bulk")
@csrf_protect
async def bulk_revoke_card_assignments(
    student_ids: List[int],
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Bulk revoke card assignments for multiple students (Staff/Admin only)."""
    successful = []
    failed = []
    
    for student_id in student_ids:
        try:
            success = await attendance_ops.revoke_card_assignment(db=db, student_id=student_id)
            if success:
                successful.append(student_id)
            else:
                failed.append({
                    "student_id": student_id,
                    "error": "No active assignment found"
                })
        except Exception as e:
            failed.append({
                "student_id": student_id,
                "error": str(e)
            })
    
    return {
        "message": "Bulk revocation completed",
        "successful": successful,
        "failed": failed,
        "total_requested": len(student_ids),
        "total_successful": len(successful),
        "total_failed": len(failed)
    }


@router.get("/assignments/student/{student_id}", response_model=CardAssignmentsResponse)
async def get_student_card_assignments(
    student_id: int,
    include_revoked: bool = Query(False, description="Include revoked assignments"),
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Get card assignments for a specific student (Staff/Admin only)."""
    assignments = await attendance_ops.get_card_assignments_by_student(
        db=db,
        student_id=student_id,
        include_revoked=include_revoked
    )
    
    return CardAssignmentsResponse(
        assignments=assignments,
        total=len(assignments)
    )


@router.get("/assignments/class-roster")
async def get_class_card_assignments(
    course_id: Optional[int] = Query(None, description="Filter by course ID"),
    active_only: bool = Query(True, description="Show only active assignments"),
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Get all active card assignments (class roster view) (Staff/Admin only)."""
    # This would need to be implemented in attendance_ops
    # For now, returning empty response
    return {
        "assignments": [],
        "total": 0,
        "course_id": course_id,
        "active_only": active_only
    }


# ============================================================================
# BULK ATTENDANCE RECORD IMPORT (From External Swipe Machines)
# ============================================================================

@router.post("/records/bulk", response_model=BulkAttendanceRecordResponse, status_code=status.HTTP_201_CREATED)
@csrf_protect
async def bulk_import_attendance_records(
    records_data: BulkAttendanceRecordRequest,
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Bulk import attendance records from external swipe machines (Staff/Admin only)."""
    successful = []
    failed = []
    
    for record_data in records_data.records:
        try:
            # Check if card exists
            card = await attendance_ops.get_attendance_card(db, record_data.card_uid_used)
            if not card:
                failed.append({
                    "student_id": record_data.student_id,
                    "card_uid": record_data.card_uid_used,
                    "swiped_at": record_data.swiped_at.isoformat() if hasattr(record_data, 'swiped_at') else None,
                    "error": "Card not found"
                })
                continue
            
            record = await attendance_ops.create_attendance_record(
                db=db,
                student_id=record_data.student_id,
                attendance_type=record_data.type,
                card_uid=record_data.card_uid_used
            )
            
            if record:
                successful.append(record)
            else:
                failed.append({
                    "student_id": record_data.student_id,
                    "card_uid": record_data.card_uid_used,
                    "swiped_at": record_data.swiped_at.isoformat() if hasattr(record_data, 'swiped_at') else None,
                    "error": "Failed to create record"
                })
                
        except Exception as e:
            failed.append({
                "student_id": record_data.student_id,
                "card_uid": record_data.card_uid_used,
                "swiped_at": record_data.swiped_at.isoformat() if hasattr(record_data, 'swiped_at') else None,
                "error": str(e)
            })
    
    return BulkAttendanceRecordResponse(
        records=successful,
        failed=failed,
        total_requested=len(records_data.records),
        total_successful=len(successful),
        total_failed=len(failed)
    )


@router.post("/records/bulk-csv", response_model=BulkAttendanceRecordResponse, status_code=status.HTTP_201_CREATED)
@csrf_protect
async def bulk_import_attendance_records_from_csv(
    file: UploadFile = File(..., description="CSV file with student_id,type,card_uid_used,swiped_at columns"),
    current_user: User = Depends(require_role(UserRole.STAFF)),
    db: AsyncSession = Depends(get_db)
):
    """Bulk import attendance records from CSV upload (Staff/Admin only)."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV"
        )
    
    try:
        content = await file.read()
        csv_text = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_text))
        
        records_data = []
        for row in csv_reader:
            # Parse swiped_at if provided, otherwise use current time
            swiped_at = None
            if row.get('swiped_at'):
                try:
                    swiped_at = datetime.fromisoformat(row['swiped_at'].replace('Z', '+00:00'))
                except:
                    swiped_at = datetime.utcnow()
            else:
                swiped_at = datetime.utcnow()
            
            records_data.append(AttendanceRecordCreate(
                student_id=int(row['student_id']),
                type=AttendanceType(int(row['type'])),
                card_uid_used=row['card_uid_used']
            ))
        
        # Use the bulk import endpoint
        return await bulk_import_attendance_records(
            BulkAttendanceRecordRequest(records=records_data),
            current_user,
            db
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing CSV: {str(e)}"
        )


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
    records = await attendance_ops.get_attendance_records_by_student(
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
    summary = await attendance_ops.get_attendance_summary_by_student(
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
    
    records = await attendance_ops.get_attendance_records_by_student(
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
    
    summary = await attendance_ops.get_attendance_summary_by_student(
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
