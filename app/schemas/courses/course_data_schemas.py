from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.schemas.common import BaseUUIDModel


class CourseDocumentBase(BaseModel):
    document_name: str = Field(..., min_length=1, max_length=255, description="Document file name")
    document_type: Optional[str] = Field(None, max_length=50, description="File type: PDF, DOCX, etc.")
    document_size: Optional[int] = Field(None, ge=0, description="File size in bytes")
    is_active: bool = Field(True, description="Whether the document is active")


class CourseDocumentCreate(CourseDocumentBase):
    course_id: UUID = Field(..., description="Course ID this data belongs to")
    document_path: Optional[str] = Field(None, max_length=500, description="Path to document file")


class CourseDocumentUpdate(BaseModel):
    document_name: Optional[str] = Field(None, min_length=1, max_length=255)
    document_type: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = Field(None)


class CourseDocumentResponse(CourseDocumentBase, BaseUUIDModel):
    course_id: UUID
    document_path: Optional[str]
    uploaded_by: UUID
    uploaded_at: datetime
    uploader_name: Optional[str] = Field(None, description="Name of the user who uploaded")

    class Config:
        from_attributes = True


class CourseDocumentsResponse(BaseModel):
    documents: List[CourseDocumentResponse]
    total: int = Field(..., description="Total number of documents for the course")