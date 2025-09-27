"""Course management commands for admin CLI."""

import click
from typing import Optional
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from decimal import Decimal

from app.database import AsyncSessionLocal
from app.models import Course, User, UserRole, Enrollment
from app.core.operations import course as course_ops
from ..utils import (
    async_command, display_course_info, display_table, 
    validate_email, parse_date, validate_positive_number
)


@click.group(name='courses')
def courses_group():
    """📚 Course management commands."""
    pass


@courses_group.command(name='list')
@click.option('--limit', type=int, default=50, help='Maximum number of courses to display')
@click.option('--offset', type=int, default=0, help='Number of courses to skip')
@click.option('--search', help='Search in title and description')
@click.option('--creator-email', callback=validate_email, help='Filter by creator email')
@click.option('--format', type=click.Choice(['detailed', 'table']), default='table', help='Output format')
@async_command
async def list_courses(limit: int, offset: int, search: str, creator_email: str, format: str):
    """List courses in the system."""
    async with AsyncSessionLocal() as db:
        # Build query
        query = select(Course).options(selectinload(Course.creator))
        
        # Filter by creator
        if creator_email:
            creator = await db.scalar(
                select(User).where(User.email == creator_email)
            )
            if not creator:
                click.echo(f"❌ Creator with email '{creator_email}' not found!")
                return
            query = query.where(Course.creator_id == creator.id)
        
        # Search filter
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Course.title.ilike(search_pattern),
                    Course.description.ilike(search_pattern),
                    Course.teacher_name.ilike(search_pattern)
                )
            )
        
        # Count total
        count_query = select(func.count()).select_from(Course)
        if creator_email and creator:
            count_query = count_query.where(Course.creator_id == creator.id)
        if search:
            count_query = count_query.where(
                or_(
                    Course.title.ilike(search_pattern),
                    Course.description.ilike(search_pattern),
                    Course.teacher_name.ilike(search_pattern)
                )
            )
        
        total_count = await db.scalar(count_query)
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        result = await db.execute(query)
        courses = result.scalars().all()
        
        if not courses:
            click.echo("📭 No courses found.")
            return
        
        click.echo(f"\n📚 Found {total_count} courses (showing {len(courses)}):")
        
        if format == 'table':
            rows = []
            for course in courses:
                # Get enrollment count
                enrollment_count = await db.scalar(
                    select(func.count()).select_from(Enrollment)
                    .where(Enrollment.course_id == course.id)
                )
                
                rows.append([
                    course.id,
                    course.title[:30],
                    course.creator.email if course.creator else 'Unknown',
                    course.teacher_name or 'N/A',
                    enrollment_count,
                    f"${course.price}" if course.price else 'Free',
                    course.created_at.strftime("%Y-%m-%d")
                ])
            
            display_table(
                ['ID', 'Title', 'Creator', 'Teacher', 'Students', 'Price', 'Created'],
                rows
            )
        else:
            click.echo("=" * 80)
            for course in courses:
                display_course_info(course, detailed=True)
                click.echo("-" * 40)


@courses_group.command()
@click.option('--course-id', type=int, prompt='Course ID', help='ID of the course')
@async_command
async def info(course_id: int):
    """Show detailed information about a specific course."""
    async with AsyncSessionLocal() as db:
        course = await db.get(Course, course_id)
        if not course:
            click.echo(f"❌ Course with ID '{course_id}' not found!")
            return
        
        # Load creator
        await db.refresh(course, ['creator'])
        
        click.echo(f"\n📋 Course Information")
        click.echo("=" * 60)
        
        display_course_info(course, detailed=True)
        
        # Additional info
        click.echo("\n👨‍🏫 Creator Information:")
        if course.creator:
            click.echo(f"   Email: {course.creator.email}")
            if course.creator.profile:
                click.echo(f"   Name: {course.creator.profile.first_name} {course.creator.profile.last_name}")
        
        # Get enrollment statistics
        enrollment_count = await db.scalar(
            select(func.count()).select_from(Enrollment)
            .where(Enrollment.course_id == course.id)
        )
        
        click.echo(f"\n📊 Statistics:")
        click.echo(f"   Total Enrollments: {enrollment_count}")
        
        # Get recent enrollments
        recent_enrollments = await db.execute(
            select(Enrollment)
            .options(selectinload(Enrollment.student))
            .where(Enrollment.course_id == course.id)
            .order_by(Enrollment.enrolled_at.desc())
            .limit(5)
        )
        recent = recent_enrollments.scalars().all()
        
        if recent:
            click.echo(f"\n🆕 Recent Enrollments:")
            for enrollment in recent:
                student = enrollment.student
                student_name = f"{student.email}"
                if student.profile:
                    student_name = f"{student.profile.first_name} {student.profile.last_name} ({student.email})"
                click.echo(f"   - {student_name} on {enrollment.enrolled_at.strftime('%Y-%m-%d')}")


@courses_group.command()
@click.option('--title', prompt='Course title', help='Title of the course')
@click.option('--creator-email', prompt='Creator email', callback=validate_email, help='Email of the course creator')
@click.option('--description', help='Course description')
@click.option('--teacher-name', help='Teacher name')
@click.option('--location', help='Course location')
@click.option('--price', type=float, callback=validate_positive_number, help='Course price')
@click.option('--start-date', callback=parse_date, help='Course start date (YYYY-MM-DD)')
@async_command
async def create(title: str, creator_email: str, description: str, teacher_name: str, 
                location: str, price: float, start_date):
    """Create a new course."""
    async with AsyncSessionLocal() as db:
        # Find creator
        creator = await db.scalar(
            select(User).where(User.email == creator_email)
        )
        if not creator:
            click.echo(f"❌ User with email '{creator_email}' not found!")
            return
        
        if creator.role == UserRole.STUDENT:
            click.echo(f"❌ Students cannot create courses!")
            return
        
        # Show summary
        click.echo("\n📋 Course Summary:")
        click.echo(f"   Title: {title}")
        click.echo(f"   Creator: {creator_email}")
        if description:
            click.echo(f"   Description: {description[:50]}...")
        if teacher_name:
            click.echo(f"   Teacher: {teacher_name}")
        if location:
            click.echo(f"   Location: {location}")
        if price:
            click.echo(f"   Price: ${price}")
        if start_date:
            click.echo(f"   Start Date: {start_date.strftime('%Y-%m-%d')}")
        
        if not click.confirm("\n✅ Create this course?"):
            click.echo("❌ Operation cancelled.")
            return
        
        try:
            course = Course(
                title=title,
                creator_id=creator.id,
                description=description,
                teacher_name=teacher_name or creator.profile.first_name + " " + creator.profile.last_name if creator.profile else None,
                location=location,
                price=Decimal(str(price)) if price else None,
                start_date=start_date
            )
            
            db.add(course)
            await db.commit()
            await db.refresh(course)
            
            click.echo(f"\n🎉 Course created successfully!")
            display_course_info(course, detailed=True)
            
        except SQLAlchemyError as e:
            click.echo(f"❌ Failed to create course: {e}")


@courses_group.command()
@click.option('--course-id', type=int, prompt='Course ID', help='ID of the course to delete')
@click.option('--force', is_flag=True, help='Skip confirmation prompts')
@async_command
async def delete(course_id: int, force: bool):
    """Delete a course from the system."""
    async with AsyncSessionLocal() as db:
        course = await db.get(Course, course_id)
        if not course:
            click.echo(f"❌ Course with ID '{course_id}' not found!")
            return
        
        # Check enrollments
        enrollment_count = await db.scalar(
            select(func.count()).select_from(Enrollment)
            .where(Enrollment.course_id == course.id)
        )
        
        click.echo(f"\n⚠️  Course to delete:")
        display_course_info(course)
        
        if enrollment_count > 0:
            click.echo(f"\n⚠️  This course has {enrollment_count} enrolled students!")
        
        if not force:
            click.echo("\n⚠️  WARNING: This action cannot be undone!")
            if not click.confirm("🗑️  Are you sure you want to delete this course?"):
                click.echo("❌ Operation cancelled.")
                return
        
        try:
            await db.delete(course)
            await db.commit()
            click.echo(f"✅ Course '{course.title}' deleted successfully!")
        except Exception as e:
            click.echo(f"❌ Error deleting course: {e}")


@courses_group.command()
@click.option('--course-id', type=int, prompt='Course ID', help='ID of the course')
@click.option('--student-email', prompt='Student email', callback=validate_email, help='Email of the student to enroll')
@async_command
async def enroll_student(course_id: int, student_email: str):
    """Manually enroll a student in a course."""
    async with AsyncSessionLocal() as db:
        # Check course exists
        course = await db.get(Course, course_id)
        if not course:
            click.echo(f"❌ Course with ID '{course_id}' not found!")
            return
        
        # Check student exists
        student = await db.scalar(
            select(User).where(User.email == student_email)
        )
        if not student:
            click.echo(f"❌ User with email '{student_email}' not found!")
            return
        
        # Check if already enrolled
        existing = await db.scalar(
            select(Enrollment).where(
                Enrollment.course_id == course_id,
                Enrollment.student_id == student.id
            )
        )
        if existing:
            click.echo(f"ℹ️  Student is already enrolled in this course!")
            return
        
        try:
            enrollment = Enrollment(
                course_id=course_id,
                student_id=student.id,
                is_active=True
            )
            db.add(enrollment)
            await db.commit()
            
            click.echo(f"✅ Successfully enrolled {student_email} in '{course.title}'!")
            
        except Exception as e:
            click.echo(f"❌ Error enrolling student: {e}")


@courses_group.command()
@click.option('--course-id', type=int, prompt='Course ID', help='ID of the course')
@click.option('--format', type=click.Choice(['list', 'table']), default='table', help='Output format')
@async_command
async def list_students(course_id: int, format: str):
    """List all students enrolled in a course."""
    async with AsyncSessionLocal() as db:
        # Check course exists
        course = await db.get(Course, course_id)
        if not course:
            click.echo(f"❌ Course with ID '{course_id}' not found!")
            return
        
        # Get enrollments
        enrollments = await db.execute(
            select(Enrollment)
            .options(selectinload(Enrollment.student).selectinload(User.profile))
            .where(Enrollment.course_id == course_id)
            .order_by(Enrollment.enrolled_at.desc())
        )
        enrollments = enrollments.scalars().all()
        
        if not enrollments:
            click.echo(f"📭 No students enrolled in '{course.title}'.")
            return
        
        click.echo(f"\n👥 Students enrolled in '{course.title}': {len(enrollments)}")
        
        if format == 'table':
            rows = []
            for enrollment in enrollments:
                student = enrollment.student
                name = "N/A"
                if student.profile:
                    name = f"{student.profile.first_name} {student.profile.last_name}"
                
                rows.append([
                    student.id,
                    student.email,
                    name,
                    enrollment.enrolled_at.strftime("%Y-%m-%d"),
                    "Active" if enrollment.is_active else "Inactive"
                ])
            
            display_table(
                ['ID', 'Email', 'Name', 'Enrolled', 'Status'],
                rows
            )
        else:
            click.echo("=" * 60)
            for enrollment in enrollments:
                student = enrollment.student
                click.echo(f"\n📧 {student.email}")
                if student.profile:
                    click.echo(f"👤 {student.profile.first_name} {student.profile.last_name}")
                click.echo(f"📅 Enrolled: {enrollment.enrolled_at.strftime('%Y-%m-%d')}")
                click.echo(f"✅ Status: {'Active' if enrollment.is_active else 'Inactive'}")


@courses_group.command()
@click.option('--days', type=int, default=7, help='Number of days to look back')
@async_command
async def recent_activity(days: int):
    """Show recent course activity."""
    async with AsyncSessionLocal() as db:
        from datetime import datetime, timedelta
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Recent courses created
        recent_courses = await db.execute(
            select(Course)
            .options(selectinload(Course.creator))
            .where(Course.created_at >= since_date)
            .order_by(Course.created_at.desc())
            .limit(10)
        )
        recent_courses = recent_courses.scalars().all()
        
        # Recent enrollments
        recent_enrollments = await db.execute(
            select(Enrollment)
            .options(
                selectinload(Enrollment.course),
                selectinload(Enrollment.student)
            )
            .where(Enrollment.enrolled_at >= since_date)
            .order_by(Enrollment.enrolled_at.desc())
            .limit(10)
        )
        recent_enrollments = recent_enrollments.scalars().all()
        
        click.echo(f"\n📊 Course Activity (Last {days} days)")
        click.echo("=" * 60)
        
        if recent_courses:
            click.echo(f"\n🆕 New Courses ({len(recent_courses)}):")
            for course in recent_courses:
                creator_email = course.creator.email if course.creator else 'Unknown'
                click.echo(f"   - {course.title} by {creator_email} on {course.created_at.strftime('%Y-%m-%d')}")
        else:
            click.echo("\n🆕 No new courses created.")
        
        if recent_enrollments:
            click.echo(f"\n📝 Recent Enrollments ({len(recent_enrollments)}):")
            for enrollment in recent_enrollments:
                student_email = enrollment.student.email if enrollment.student else 'Unknown'
                course_title = enrollment.course.title if enrollment.course else 'Unknown'
                click.echo(f"   - {student_email} enrolled in '{course_title}' on {enrollment.enrolled_at.strftime('%Y-%m-%d')}")
        else:
            click.echo("\n📝 No recent enrollments.")