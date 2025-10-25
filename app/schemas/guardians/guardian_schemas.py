from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.schemas.common import BaseUUIDModel, PaginatedResponse


class GuardianBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255, description="Guardian's full name")
    phone_number: str = Field(..., min_length=1, max_length=50, description="Guardian's phone number")
    notes: Optional[str] = Field(None, description="Additional notes about the guardian")


class GuardianCreate(GuardianBase):
    pass


class GuardianUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone_number: Optional[str] = Field(None, min_length=1, max_length=50)
    notes: Optional[str] = None


class GuardianResponse(GuardianBase, BaseUUIDModel):
    created_at: datetime
    
    class Config:
        from_attributes = True


GuardiansListResponse = PaginatedResponse[GuardianResponse]


class StudentGuardianRelationshipBase(BaseModel):
    student_id: UUID = Field(..., description="Student ID")
    guardian_id: UUID = Field(..., description="Guardian ID")
    relationship_type: Optional[str] = Field(None, max_length=50, description="Relationship type (e.g., parent, guardian)")


class StudentGuardianRelationshipCreate(BaseModel):
    guardian_id: UUID = Field(..., description="Guardian ID")
    relationship_type: Optional[str] = Field(None, max_length=50, description="Relationship type")


class StudentGuardianRelationshipResponse(StudentGuardianRelationshipBase):
    guardian: GuardianResponse
    
    class Config:
        from_attributes = True


class StudentGuardiansResponse(BaseModel):
    student_id: UUID
    guardians: List[StudentGuardianRelationshipResponse]
    total: int