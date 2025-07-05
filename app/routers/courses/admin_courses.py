from fastapi import Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import UserRole
from app.core.decorators import csrf_protect, authentication_required
from app.schemas.courses.course_schemas import DeleteCourseResponse
from app.core.operations import course as course_ops
from .courses import router


@router.delete("/{course_id}", response_model=DeleteCourseResponse)
@authentication_required(allowed_role=UserRole.STAFF)
@csrf_protect
async def delete_course(
    course_id: int = Path(..., description="Course ID"),
    db: AsyncSession = Depends(get_db)
):
    """Delete a course (Staff and Admin only)."""
    # Get course title before deletion
    course_title = await course_ops.get_course_title(db, course_id)
    
    if not course_title:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Delete course
    if not await course_ops.delete_course(db, course_id):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete course"
        )
    
    return DeleteCourseResponse(message=f"Course '{course_title}' deleted successfully") 