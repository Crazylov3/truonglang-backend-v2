from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload

from app.models.course import CourseDocument, Course
from app.models.user import User
from app.schemas.courses import (
    CourseDocumentCreate, 
    CourseDocumentUpdate,
    CourseDocumentResponse,
    CourseDocumentsResponse
)
from fastapi import HTTPException, status


async def create_course_document(
    db: AsyncSession,
    course_id: int,
    data: CourseDocumentCreate,
    uploaded_by: int
) -> CourseDocument:
    """Create new course document entry."""
    # Verify course exists
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    db_course_document = CourseDocument(
        course_id=course_id,
        document_path=data.document_path,
        document_name=data.document_name,
        document_type=data.document_type,
        document_size=data.document_size,
        uploaded_by=uploaded_by,
        is_active=data.is_active
    )
    
    db.add(db_course_document)
    await db.commit()
    await db.refresh(db_course_document)
    
    return db_course_document


async def get_course_documents(
    db: AsyncSession,
    course_id: int,
    only_active: bool = True
) -> CourseDocumentsResponse:
    """Get all documents for a course."""
    # Build query
    query = select(CourseDocument).where(CourseDocument.course_id == course_id)
    
    if only_active:
        query = query.where(CourseDocument.is_active == True)
    
    query = query.options(joinedload(CourseDocument.uploader))
    query = query.order_by(CourseDocument.uploaded_at.desc())
    
    result = await db.execute(query)
    documents = result.scalars().all()
    
    # Format response
    document_responses = []
    for doc in documents:
        uploader_name = None
        if doc.uploader:
            profile = await db.execute(
                select(User).where(User.id == doc.uploader.id).options(joinedload(User.profile))
            )
            user = profile.scalar_one_or_none()
            if user and user.profile:
                uploader_name = f"{user.profile.first_name} {user.profile.last_name}"
        
        document_responses.append(CourseDocumentResponse(
            id=doc.id,
            course_id=doc.course_id,
            document_name=doc.document_name,
            document_type=doc.document_type,
            document_size=doc.document_size,
            document_path=doc.document_path,
            uploaded_by=doc.uploaded_by,
            uploaded_at=doc.uploaded_at,
            is_active=doc.is_active,
            uploader_name=uploader_name
        ))
    
    return CourseDocumentsResponse(
        documents=document_responses,
        total=len(document_responses)
    )


async def update_course_document(
    db: AsyncSession,
    document_id: int,
    update_data: CourseDocumentUpdate
) -> CourseDocument:
    """Update course document entry."""
    # Get existing document
    db_document = await db.get(CourseDocument, document_id)
    if not db_document:
        raise HTTPException(status_code=404, detail="Course document not found")
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(db_document, field, value)
    
    await db.commit()
    await db.refresh(db_document)
    
    return db_document


async def delete_course_document(
    db: AsyncSession,
    document_id: int,
    soft_delete: bool = True
) -> None:
    """Delete or deactivate course document."""
    db_document = await db.get(CourseDocument, document_id)
    if not db_document:
        raise HTTPException(status_code=404, detail="Course document not found")
    
    if soft_delete:
        db_document.is_active = False
        await db.commit()
    else:
        await db.delete(db_document)
        await db.commit()


async def set_course_preview_picture(
    db: AsyncSession,
    course_id: int,
    preview_path: str
) -> Course:
    """Set or update the preview picture for a course."""
    # Get the course
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Update the preview picture path
    course.preview_picture_path = preview_path
    
    await db.commit()
    await db.refresh(course)
    
    return course