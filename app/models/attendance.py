from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from enum import IntEnum
from .base import BaseModel


class CardStatus(IntEnum):
    ACTIVE = 1
    INACTIVE = 2
    LOST = 3
    DAMAGED = 4


class AttendanceType(IntEnum):
    CHECK_IN = 1
    CHECK_OUT = 2


class AttendanceCard(BaseModel):
    __tablename__ = "attendance_cards"
    
    card_uid = Column(String(255), primary_key=True, comment="Unique ID from the card (RFID/NFC UID, Barcode)")
    status = Column(Integer, nullable=False, default=CardStatus.INACTIVE)
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes = Column(Text, nullable=True)
    
    # Relationships
    card_assignments = relationship("CardAssignment", back_populates="card")
    attendance_records = relationship("AttendanceRecord", back_populates="card")
    
    def __repr__(self):
        return f"<AttendanceCard(card_uid='{self.card_uid}', status={self.status})>"


class CardAssignment(BaseModel):
    __tablename__ = "card_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    card_uid = Column(String(255), ForeignKey("attendance_cards.card_uid"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    student = relationship("User", back_populates="card_assignments")
    card = relationship("AttendanceCard", back_populates="card_assignments")
    
    def __repr__(self):
        return f"<CardAssignment(id={self.id}, student_id={self.student_id}, card_uid='{self.card_uid}')>"


class AttendanceRecord(BaseModel):
    __tablename__ = "attendance_records"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    swiped_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    type = Column(Integer, nullable=False)
    card_uid_used = Column(String(255), ForeignKey("attendance_cards.card_uid"), nullable=False)
    
    # Relationships
    student = relationship("User", back_populates="attendance_records")
    card = relationship("AttendanceCard", back_populates="attendance_records")
    
    def __repr__(self):
        return f"<AttendanceRecord(id={self.id}, student_id={self.student_id}, type={self.type}, swiped_at={self.swiped_at})>"
