from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, HTTPException, status
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.deps import get_db, get_current_user, require_role
from app.core.decorators import csrf_protect
from app.core.operations import course_data as course_data_ops
from app.core.operations import course as course_ops
from app.models.user import UserRole
from app.schemas.courses import (
    CourseDocumentCreate,
    CourseDocumentUpdate,
    CourseDocumentResponse,
    CourseDocumentsResponse
)
import os
import aiofiles
from datetime import datetime

from .courses import router, logger

# Configure upload settings
UPLOAD_DIR = "uploads/course_documents"
ALLOWED_DOCUMENT_TYPES = {
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-powerpoint": "ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "text/plain": "txt"
}
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp"
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.get("/{course_id}/documents", response_model=CourseDocumentsResponse)
async def get_course_documents(
    course_id: int,
    only_active: bool = Query(True, description="Only return active documents"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get all documents for a course.
    
    - Students can only see documents for courses they're enrolled in
    - Instructors can see documents for courses they teach
    - Staff and Admin can see all documents
    """
    # Check access permissions
    if current_user.role == UserRole.STUDENT:
        # Check if student is enrolled
        enrollment = await course_ops.check_enrollment(db, current_user.id, course_id)
        if not enrollment:
            raise HTTPException(status_code=403, detail="You are not enrolled in this course")
    
    elif current_user.role == UserRole.INSTRUCTOR:
        # Check if instructor teaches this course
        has_permission = await course_ops.check_instructor_permission(db, current_user.id, course_id)
        if not has_permission:
            raise HTTPException(status_code=403, detail="You don't have permission to access this course")
    
    # Staff and Admin have full access
    
    return await course_data_ops.get_course_documents(db, course_id, only_active)


@router.post("/{course_id}/documents/upload", response_model=CourseDocumentResponse)
async def upload_course_document(
    course_id: int,
    file: UploadFile = File(...),
    document_name: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR))
):
    """
    Upload a document for a course.
    
    - Only instructors (with permission), staff, and admin can upload
    - Supported formats: PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT
    - Max file size: 50MB
    """
    # Check instructor permission if instructor role
    if current_user.role == UserRole.INSTRUCTOR:
        has_permission = await course_ops.check_instructor_permission(db, current_user.id, course_id)
        if not has_permission:
            raise HTTPException(status_code=403, detail="You don't have permission to manage this course")
    
    # Validate file type
    content_type = file.content_type
    if content_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Allowed types: {list(ALLOWED_DOCUMENT_TYPES.values())}")
    
    # Check file size
    file_size = 0
    content = await file.read()
    file_size = len(content)
    await file.seek(0)  # Reset file pointer
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB")
    
    # Create upload directory if it doesn't exist
    course_dir = os.path.join(UPLOAD_DIR, str(course_id))
    os.makedirs(course_dir, exist_ok=True)
    
    # Generate unique filename
    file_extension = ALLOWED_DOCUMENT_TYPES[content_type]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"doc_{timestamp}_{current_user.id}.{file_extension}"
    file_path = os.path.join(course_dir, safe_filename)
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    # Create database entry
    course_document = CourseDocumentCreate(
        course_id=course_id,
        document_name=document_name or file.filename,
        document_type=file_extension.upper(),
        document_size=file_size,
        document_path=file_path,
        is_active=True
    )
    
    return await course_data_ops.create_course_document(db, course_id, course_document, current_user.id)


@router.post("/{course_id}/documents/preview")
async def upload_course_preview(
    course_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR))
):
    """
    Upload a preview picture for a course.
    
    - Only instructors (with permission), staff, and admin can upload
    - Supported formats: JPG, PNG, GIF, WEBP
    - Max file size: 10MB
    - Only one active preview per course (previous ones are deactivated)
    """
    # Check instructor permission if instructor role
    if current_user.role == UserRole.INSTRUCTOR:
        has_permission = await course_ops.check_instructor_permission(db, current_user.id, course_id)
        if not has_permission:
            raise HTTPException(status_code=403, detail="You don't have permission to manage this course")
    
    # Validate file type
    content_type = file.content_type
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Allowed types: {list(ALLOWED_IMAGE_TYPES.values())}")
    
    # Check file size (10MB for images)
    max_image_size = 10 * 1024 * 1024
    content = await file.read()
    file_size = len(content)
    await file.seek(0)
    
    if file_size > max_image_size:
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size: {max_image_size // (1024*1024)}MB")
    
    # Create upload directory
    preview_dir = os.path.join(UPLOAD_DIR, str(course_id), "previews")
    os.makedirs(preview_dir, exist_ok=True)
    
    # Generate unique filename
    file_extension = ALLOWED_IMAGE_TYPES[content_type]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"preview_{timestamp}.{file_extension}"
    file_path = os.path.join(preview_dir, safe_filename)
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    # Set as course preview
    course = await course_data_ops.set_course_preview_picture(db, course_id, file_path)
    
    return {"message": "Preview picture uploaded successfully", "preview_picture_path": course.preview_picture_path}


@router.patch("/{course_id}/documents/{document_id}", response_model=CourseDocumentResponse)
async def update_course_document(
    course_id: int,
    document_id: int,
    update_data: CourseDocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR))
):
    """Update course document metadata."""
    # Check instructor permission if instructor role
    if current_user.role == UserRole.INSTRUCTOR:
        has_permission = await course_ops.check_instructor_permission(db, current_user.id, course_id)
        if not has_permission:
            raise HTTPException(status_code=403, detail="You don't have permission to manage this course")
    
    return await course_data_ops.update_course_document(db, document_id, update_data)


@router.delete("/{course_id}/documents/{document_id}")
async def delete_course_document(
    course_id: int,
    document_id: int,
    permanent: bool = Query(False, description="Permanently delete the document"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.INSTRUCTOR))
):
    """
    Delete or deactivate a course document.
    
    - By default, performs soft delete (sets is_active=False)
    - Set permanent=true for hard delete
    """
    # Check instructor permission if instructor role
    if current_user.role == UserRole.INSTRUCTOR:
        has_permission = await course_ops.check_instructor_permission(db, current_user.id, course_id)
        if not has_permission:
            raise HTTPException(status_code=403, detail="You don't have permission to manage this course")
    
    await course_data_ops.delete_course_document(db, document_id, soft_delete=not permanent)
    
    return {"message": "Document deleted successfully"}