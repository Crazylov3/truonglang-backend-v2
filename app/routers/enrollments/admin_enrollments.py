from fastapi import Depends, HTTPException, status, Path, Query, Body, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.database import get_db
from app.core.deps import get_current_user
from app.core.decorators import authentication_required, csrf_protect
from app.core.validators import validate_uuid
from app.models.user import User, UserRole
from app.core.operations import enrollment as enrollment_ops
from app.core.operations import user as user_ops
from app.core.operations import course as course_ops
from app.schemas.courses.course_schemas import EnrollmentResponse
from app.schemas.enrollments.enrollments_schemas import BulkEnrollmentRequest, BulkEnrollmentResponse, Enrollment, Enrollments
from .enrollments import router, logger
from uuid import UUID
import csv
import io
from typing import Tuple


@router.post("/admin/course/{course_id}/enroll", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
@authentication_required(allowed_role=UserRole.ADMIN)
@csrf_protect
async def admin_enroll_student(
    course_id: str = Path(..., description="Course ID"),
    student_id: Optional[str] = Query(None, description="Student UUID"),
    email: Optional[str] = Query(None, description="Student email"),
    public_id: Optional[int] = Query(None, description="Student public ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin endpoint to manually enroll a student in a course by student ID, email, or public ID."""
    
    # Validate course
    course_uuid = validate_uuid(course_id)
    course = await course_ops.get_course_by_id(db, course_uuid)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Must provide exactly one identifier
    if not student_id and not email and not public_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide exactly one of: student_id, email, or public_id"
        )
    
    if sum([bool(student_id), bool(email), bool(public_id)]) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide exactly one of: student_id, email, or public_id"
        )
    
    # Find student by identifier
    student = None
    if student_id:
        student_uuid = validate_uuid(student_id)
        student = await user_ops.get_user_by_id(db, student_uuid)
    elif email:
        student = await user_ops.get_user_by_email(db, email)
    elif public_id:
        student = await user_ops.get_user_by_public_id(db, public_id)
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Check if student is actually a student role
    if student.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is not a student (role: {student.role})"
        )
    
    # Check if already enrolled
    if await enrollment_ops.check_enrollment_exists(db, student.id, course_uuid):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student is already enrolled in this course"
        )
    
    # Create enrollment
    enrollment = await enrollment_ops.create_enrollment(
        db=db,
        student_id=student.id,
        course_id=course_uuid
    )
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create enrollment"
        )
    
    return EnrollmentResponse(
        message=f"Student {student.full_name} ({student.email}) enrolled in course {course.title} successfully"
    )


async def _process_enrollments(course_uuid, identifiers, db):
    """Helper function to process enrollments from a list of identifiers."""
    successful = []
    failed = []
    
    for identifier in identifiers:
        try:
            # Skip empty or None identifiers
            if not identifier or not str(identifier).strip():
                failed.append({
                    'identifier': identifier,
                    'reason': 'Empty identifier'
                })
                continue
            
            # Try to determine if it's a UUID, email, or public_id
            student = None
            
            # Try UUID first
            try:
                student_uuid = UUID(identifier)
                student = await user_ops.get_user_by_id(db, student_uuid)
            except (ValueError, TypeError):
                # Not a valid UUID, try public_id
                try:
                    public_id = int(identifier)
                    student = await user_ops.get_user_by_public_id(db, public_id)
                except (ValueError, TypeError):
                    # Assume it's an email
                    student = await user_ops.get_user_by_email(db, identifier)
            
            if not student:
                failed.append({
                    'identifier': identifier,
                    'reason': 'Student not found'
                })
                continue
            
            # Check if student is actually a student role
            if student.role != UserRole.STUDENT:
                failed.append({
                    'identifier': identifier,
                    'reason': f'User is not a student (role: {student.role})',
                    'user_email': student.email
                })
                continue
            
            # Check if already enrolled
            if await enrollment_ops.check_enrollment_exists(db, student.id, course_uuid):
                failed.append({
                    'identifier': identifier,
                    'reason': 'Already enrolled',
                    'user_email': student.email
                })
                continue
            
            # Create enrollment
            enrollment = await enrollment_ops.create_enrollment(
                db=db,
                student_id=student.id,
                course_id=course_uuid
            )
            
            if enrollment:
                successful.append({
                    'identifier': identifier,
                    'user_id': str(student.id),
                    'email': student.email,
                    'full_name': student.full_name
                })
            else:
                failed.append({
                    'identifier': identifier,
                    'reason': 'Failed to create enrollment',
                    'user_email': student.email
                })
        
        except Exception as e:
            failed.append({
                'identifier': identifier,
                'reason': f'Error: {str(e)}'
            })
    
    return successful, failed


@router.post("/admin/course/{course_id}/bulk-enroll", response_model=BulkEnrollmentResponse, status_code=status.HTTP_201_CREATED)
@authentication_required(allowed_role=UserRole.ADMIN)
@csrf_protect
async def admin_bulk_enroll_students(
    course_id: str = Path(..., description="Course ID"),
    bulk_request: BulkEnrollmentRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin endpoint to bulk enroll multiple students in a course by student IDs, emails, or public IDs.
    
    Accepts JSON body with list of student identifiers.
    """
    
    # Validate course
    course_uuid = validate_uuid(course_id)
    course = await course_ops.get_course_by_id(db, course_uuid)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    if not bulk_request.student_identifiers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No student identifiers provided"
        )
    
    successful, failed = await _process_enrollments(course_uuid, bulk_request.student_identifiers, db)
    
    return BulkEnrollmentResponse(
        success_count=len(successful),
        failure_count=len(failed),
        successful=successful,
        failed=failed
    )


@router.post("/admin/course/{course_id}/bulk-enroll-csv", response_model=BulkEnrollmentResponse, status_code=status.HTTP_201_CREATED)
@authentication_required(allowed_role=UserRole.ADMIN)
@csrf_protect
async def admin_bulk_enroll_students_csv(
    course_id: str = Path(..., description="Course ID"),
    csv_file: UploadFile = File(..., description="CSV file with student identifiers (one per line or comma-separated in first column)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin endpoint to bulk enroll multiple students in a course from a CSV file.
    
    CSV format: Each row should contain a student identifier (UUID, email, or public_id).
    The first column should contain the identifier. Headers are optional.
    
    Example CSV:
        student@example.com
        12345
        550e8400-e29b-41d4-a716-446655440000
    """
    
    # Validate course
    course_uuid = validate_uuid(course_id)
    course = await course_ops.get_course_by_id(db, course_uuid)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Read and parse CSV file
    try:
        contents = await csv_file.read()
        file_content = io.StringIO(contents.decode('utf-8'))
        csv_reader = csv.reader(file_content)
        
        identifiers = []
        for row in csv_reader:
            if row and row[0].strip():  # Skip empty rows
                # Take the first column as the identifier
                identifier = row[0].strip()
                # Skip header row if it looks like a header
                if identifier.lower() in ['email', 'student_id', 'public_id', 'identifier', 'student_email', 'id']:
                    continue
                identifiers.append(identifier)
        
        if not identifiers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid student identifiers found in CSV file"
            )
        
        # Process enrollments
        successful, failed = await _process_enrollments(course_uuid, identifiers, db)
        
        return BulkEnrollmentResponse(
            success_count=len(successful),
            failure_count=len(failed),
            successful=successful,
            failed=failed
        )
        
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file must be UTF-8 encoded"
        )
    except Exception as e:
        logger.error(f"Error processing CSV file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing CSV file: {str(e)}"
        )


@router.get("/admin/student/{student_id}/enrollments", response_model=Enrollments, status_code=status.HTTP_200_OK)
@authentication_required(allowed_role=UserRole.STAFF)
async def get_student_enrollments(
    student_id: str = Path(..., description="Student ID (UUID, email, or public_id)"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    active_only: bool = Query(True, description="Show only active enrollments"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get enrollments for a specific student by student ID, email, or public_id.
    
    Accessible by STAFF and ADMIN roles.
    """
    
    # Find student by identifier
    student = None
    try:
        # Try as UUID first
        try:
            student_uuid = UUID(student_id)
            student = await user_ops.get_user_by_id(db, student_uuid)
        except (ValueError, TypeError, AttributeError):
            # Not a valid UUID, try public_id
            try:
                public_id = int(student_id)
                student = await user_ops.get_user_by_public_id(db, public_id)
            except (ValueError, TypeError):
                # Assume it's an email
                student = await user_ops.get_user_by_email(db, student_id)
    except Exception as e:
        logger.error(f"Error finding student: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error while searching for student"
        )
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Get enrollments
    enrollments, total = await enrollment_ops.get_user_enrollments(
        db=db,
        student_id=student.id,
        active_only=active_only,
        page=page,
        per_page=per_page
    )
    
    enrollment_list = [
        Enrollment(
            id=enrollment.id,
            student_id=enrollment.student_id,
            course_id=enrollment.course_id,
            enrolled_at=enrollment.enrolled_at,
            is_active=enrollment.is_active,
            discount_percentage=float(enrollment.discount_percentage) if enrollment.discount_percentage else 0.0,
            discount_reason=enrollment.discount_reason,
            discount_approved_by=enrollment.discount_approved_by
        )
        for enrollment in enrollments
    ]
    
    return Enrollments.create(
        items=enrollment_list,
        total=total,
        page=page,
        per_page=per_page
    )


@router.delete("/admin/course/{course_id}/unenroll", response_model=EnrollmentResponse, status_code=status.HTTP_200_OK)
@authentication_required(allowed_role=UserRole.ADMIN)
@csrf_protect
async def admin_unenroll_student(
    course_id: str = Path(..., description="Course ID"),
    student_id: Optional[str] = Query(None, description="Student UUID"),
    email: Optional[str] = Query(None, description="Student email"),
    public_id: Optional[int] = Query(None, description="Student public ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin endpoint to unenroll a student from a course by student ID, email, or public ID."""
    
    # Validate course
    course_uuid = validate_uuid(course_id)
    course = await course_ops.get_course_by_id(db, course_uuid)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Must provide exactly one identifier
    if not student_id and not email and not public_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide exactly one of: student_id, email, or public_id"
        )
    
    if sum([bool(student_id), bool(email), bool(public_id)]) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide exactly one of: student_id, email, or public_id"
        )
    
    # Find student by identifier
    student = None
    if student_id:
        student_uuid = validate_uuid(student_id)
        student = await user_ops.get_user_by_id(db, student_uuid)
    elif email:
        student = await user_ops.get_user_by_email(db, email)
    elif public_id:
        student = await user_ops.get_user_by_public_id(db, public_id)
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Check if student is actually a student role
    if student.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is not a student (role: {student.role})"
        )
    
    # Check if enrolled
    if not await enrollment_ops.check_enrollment_exists(db, student.id, course_uuid):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student is not enrolled in this course"
        )
    
    # Deactivate enrollment
    success = await enrollment_ops.deactivate_enrollment(
        db=db,
        student_id=student.id,
        course_id=course_uuid
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unenroll student"
        )
    
    return EnrollmentResponse(
        message=f"Student {student.full_name} ({student.email}) has been unenrolled from course {course.title}"
    )


async def _process_unenrollments(course_uuid, identifiers, db):
    """Helper function to process unenrollments from a list of identifiers."""
    successful = []
    failed = []
    
    for identifier in identifiers:
        try:
            # Skip empty or None identifiers
            if not identifier or not str(identifier).strip():
                failed.append({
                    'identifier': identifier,
                    'reason': 'Empty identifier'
                })
                continue
            
            # Try to determine if it's a UUID, email, or public_id
            student = None
            
            # Try UUID first
            try:
                student_uuid = UUID(identifier)
                student = await user_ops.get_user_by_id(db, student_uuid)
            except (ValueError, TypeError):
                # Not a valid UUID, try public_id
                try:
                    public_id = int(identifier)
                    student = await user_ops.get_user_by_public_id(db, public_id)
                except (ValueError, TypeError):
                    # Assume it's an email
                    student = await user_ops.get_user_by_email(db, identifier)
            
            if not student:
                failed.append({
                    'identifier': identifier,
                    'reason': 'Student not found'
                })
                continue
            
            # Check if student is actually a student role
            if student.role != UserRole.STUDENT:
                failed.append({
                    'identifier': identifier,
                    'reason': f'User is not a student (role: {student.role})',
                    'user_email': student.email
                })
                continue
            
            # Check if enrolled
            if not await enrollment_ops.check_enrollment_exists(db, student.id, course_uuid):
                failed.append({
                    'identifier': identifier,
                    'reason': 'Not enrolled in this course',
                    'user_email': student.email
                })
                continue
            
            # Deactivate enrollment
            success = await enrollment_ops.deactivate_enrollment(
                db=db,
                student_id=student.id,
                course_id=course_uuid
            )
            
            if success:
                successful.append({
                    'identifier': identifier,
                    'user_id': str(student.id),
                    'email': student.email,
                    'full_name': student.full_name
                })
            else:
                failed.append({
                    'identifier': identifier,
                    'reason': 'Failed to unenroll',
                    'user_email': student.email
                })
        
        except Exception as e:
            failed.append({
                'identifier': identifier,
                'reason': f'Error: {str(e)}'
            })
    
    return successful, failed


@router.post("/admin/course/{course_id}/bulk-unenroll", response_model=BulkEnrollmentResponse, status_code=status.HTTP_200_OK)
@authentication_required(allowed_role=UserRole.ADMIN)
@csrf_protect
async def admin_bulk_unenroll_students(
    course_id: str = Path(..., description="Course ID"),
    bulk_request: BulkEnrollmentRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin endpoint to bulk unenroll multiple students from a course by student IDs, emails, or public IDs.
    
    Accepts JSON body with list of student identifiers.
    """
    
    # Validate course
    course_uuid = validate_uuid(course_id)
    course = await course_ops.get_course_by_id(db, course_uuid)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    if not bulk_request.student_identifiers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No student identifiers provided"
        )
    
    successful, failed = await _process_unenrollments(course_uuid, bulk_request.student_identifiers, db)
    
    return BulkEnrollmentResponse(
        success_count=len(successful),
        failure_count=len(failed),
        successful=successful,
        failed=failed
    )

