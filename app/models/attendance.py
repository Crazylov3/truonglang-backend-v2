from sqlalchemy import Column, String, DateTime, Text, ForeignKey, func, Enum as SQLAEnum, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from enum import Enum
from .base import BaseModel


class CardStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    LOST = "LOST"
    DAMAGED = "DAMAGED"


class AttendanceType(str, Enum):
    CHECK_IN = "CHECK_IN"
    CHECK_OUT = "CHECK_OUT"


class AttendanceCard(BaseModel):
    __tablename__ = "attendance_cards"
    
    card_uid = Column(String(255), primary_key=True, comment="Unique ID from the card (RFID/NFC UID, Barcode). This is the physical identifier.")
    status = Column(SQLAEnum(CardStatus), nullable=False, default=CardStatus.INACTIVE)
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes = Column(Text, nullable=True)
    
    # Relationships
    card_assignments = relationship("CardAssignment", back_populates="card")
    
    def __repr__(self):
        return f"<AttendanceCard(card_uid='{self.card_uid}', status={self.status})>"


class CardAssignment(BaseModel):
    __tablename__ = "card_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    card_uid = Column(String(255), ForeignKey("attendance_cards.card_uid"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True, comment="NULL if currently active.")
    
    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    card = relationship("AttendanceCard", back_populates="card_assignments")
    
    # Indexes
    __table_args__ = (
        Index('ix_card_assignments_student_revoked', 'student_id', 'revoked_at'),
        Index('ix_card_assignments_card_revoked', 'card_uid', 'revoked_at'),
    )
    
    def __repr__(self):
        return f"<CardAssignment(id={self.id}, student_id={self.student_id}, card_uid='{self.card_uid}')>"


class AttendanceRecord(BaseModel):
    __tablename__ = "attendance_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    swiped_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    type = Column(SQLAEnum(AttendanceType), nullable=False)
    card_uid_used = Column(String(255), nullable=False, comment="Which card UID was used for this specific swipe")
    
    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    
    def __repr__(self):
        return f"<AttendanceRecord(id={self.id}, student_id={self.student_id}, type={self.type}, swiped_at={self.swiped_at})>"