from sqlalchemy import Column, String, DateTime, Text, ForeignKey, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel


class Guardian(BaseModel):
    __tablename__ = "guardians"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    full_name = Column(String(255), nullable=False)
    phone_number = Column(String(50), unique=True, nullable=False)
    notes = Column(Text, nullable=True, comment="Ghi chú cho team sale: công việc, sở thích, thói quen của phụ huynh...")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    student_relationships = relationship("StudentGuardianRelationship", back_populates="guardian")
    
    def __repr__(self):
        return f"<Guardian(id={self.id}, full_name='{self.full_name}', phone_number='{self.phone_number}')>"


class StudentGuardianRelationship(BaseModel):
    __tablename__ = "student_guardian_relationships"
    
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    guardian_id = Column(UUID(as_uuid=True), ForeignKey("guardians.id"), primary_key=True)
    relationship_type = Column(String(50), nullable=True, comment='e.g., "Father", "Mother", "Guardian"')
    
    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    guardian = relationship("Guardian", back_populates="student_relationships")
    
    def __repr__(self):
        return f"<StudentGuardianRelationship(student_id={self.student_id}, guardian_id={self.guardian_id}, relationship_type='{self.relationship_type}')>"