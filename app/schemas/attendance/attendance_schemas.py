from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID
from app.models.attendance import CardStatus, AttendanceType
from app.schemas.common import BaseUUIDModel, PaginatedResponse


class AttendanceCardBase(BaseModel):
    card_uid: str = Field(..., description="Unique ID from the card (RFID/NFC UID, Barcode)")
    status: CardStatus = Field(CardStatus.INACTIVE, description="Current status of the card")
    notes: Optional[str] = Field(None, description="Additional notes about the card")
    branch_id: UUID = Field(..., description="Branch this card belongs to")
    card_uuid: Optional[UUID] = Field(None, description="Optional NFC UUID; may be NULL until synced")


class AttendanceCardCreate(AttendanceCardBase):
    pass


class AttendanceCardUpdate(BaseModel):
    status: Optional[CardStatus] = None
    notes: Optional[str] = None
    branch_id: Optional[UUID] = None
    card_uuid: Optional[UUID] = None


class AttendanceCardResponse(AttendanceCardBase):
    issued_at: datetime
    assigned_to_public_id: Optional[int] = Field(None, description="Public ID of the user currently assigned to this card")
    
    class Config:
        from_attributes = True


class AttendanceCardsResponse(BaseModel):
    cards: List[AttendanceCardResponse]
    total: int


# Paginated list alias (consistent with UsersListResponse)
AttendanceCardsListResponse = PaginatedResponse[AttendanceCardResponse]


# Bulk Card Creation Schemas
class BulkCardCreateRequest(BaseModel):
    cards: List[AttendanceCardCreate] = Field(..., description="List of cards to create")


class BulkCardCreateResponse(BaseModel):
    cards: List[AttendanceCardResponse]
    failed: List[dict]
    total_requested: int
    total_successful: int
    total_failed: int


class CardAssignmentBase(BaseModel):
    student_id: UUID = Field(..., description="ID of the student")
    card_uid: str = Field(..., description="UID of the card to assign")


class CardAssignmentCreate(CardAssignmentBase):
    pass


class CardAssignmentUpdate(BaseModel):
    card_uid: Optional[str] = None
    revoked: Optional[bool] = None


class CardAssignmentResponse(CardAssignmentBase, BaseUUIDModel):
    assigned_at: datetime
    revoked_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CardAssignmentsResponse(BaseModel):
    assignments: List[CardAssignmentResponse]
    total: int


class AttendanceRecordBase(BaseModel):
    student_id: UUID = Field(..., description="ID of the student")
    type: AttendanceType = Field(..., description="Type of attendance record")
    card_uid_used: str = Field(..., description="UID of the card used")


class AttendanceRecordCreate(AttendanceRecordBase):
    pass


class AttendanceRecordResponse(AttendanceRecordBase, BaseUUIDModel):
    swiped_at: datetime
    
    class Config:
        from_attributes = True


class AttendanceRecordsResponse(BaseModel):
    records: List[AttendanceRecordResponse]
    total: int


# Bulk Attendance Record Import Schemas
class BulkAttendanceRecordRequest(BaseModel):
    records: List[AttendanceRecordCreate] = Field(..., description="List of attendance records to import")


class BulkAttendanceRecordResponse(BaseModel):
    records: List[AttendanceRecordResponse]
    failed: List[dict]
    total_requested: int
    total_successful: int
    total_failed: int


class AttendanceSummaryResponse(BaseModel):
    student_id: UUID
    check_ins: int
    check_outs: int
    total_records: int
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class BulkCardAssignmentRequest(BaseModel):
    assignments: List[CardAssignmentCreate]


class BulkCardAssignmentResponse(BaseModel):
    successful: List[CardAssignmentResponse]
    failed: List[dict]
    total_requested: int
    total_successful: int
    total_failed: int


class CardStatusUpdateRequest(BaseModel):
    status: CardStatus
    notes: Optional[str] = None


class AttendanceFilterRequest(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    student_id: Optional[UUID] = None
    course_id: Optional[UUID] = None
    attendance_type: Optional[AttendanceType] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)
