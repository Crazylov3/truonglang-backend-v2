from fastapi import Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.course import Course
from app.models.user import UserRole
from app.core.decorators import csrf_protect, authentication_required
from app.schemas.courses.course_schemas import DeleteCourseResponse
from .courses import router, logger


@router.delete("/{course_id}", response_model=DeleteCourseResponse)
@authentication_required(allowed_role=UserRole.STAFF)
@csrf_protect
async def delete_course(
    course_id: int = Path(..., description="Course ID"),
    db: AsyncSession = Depends(get_db)
):
    """Delete a course (Staff and Admin only)."""
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    course_title = course.title
    await db.delete(course)
    await db.commit()
    
    return DeleteCourseResponse(message=f"Course '{course_title}' deleted successfully") 