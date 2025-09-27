"""Reporting and analytics commands for admin CLI."""

import click
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, case
from sqlalchemy.orm import selectinload
import csv

from app.database import AsyncSessionLocal
from app.models import (
    User, UserRole, Course, Enrollment, Payment, PaymentStatus,
    AttendanceRecord, AuditLog, AuditAction
)
from ..utils import (
    async_command, display_table, display_stats,
    format_datetime, parse_date
)


@click.group(name='reports')
def reports_group():
    """📊 Reporting and analytics commands."""
    pass


@reports_group.command()
@async_command
async def dashboard():
    """Show system dashboard with key metrics."""
    async with AsyncSessionLocal() as db:
        click.echo("\n📊 System Dashboard")
        click.echo("=" * 60)
        
        # User statistics
        user_stats = await db.execute(
            select(
                User.role,
                func.count(User.id).label('count')
            ).group_by(User.role)
        )
        user_counts = {role: count for role, count in user_stats}
        
        click.echo("\n👥 User Statistics:")
        total_users = sum(user_counts.values())
        click.echo(f"   Total Users: {total_users:,}")
        for role in UserRole:
            count = user_counts.get(role.value, 0)
            click.echo(f"   {role.name}: {count:,}")
        
        # Course statistics
        total_courses = await db.scalar(select(func.count(Course.id)))
        active_enrollments = await db.scalar(
            select(func.count(Enrollment.id))
            .where(Enrollment.is_active == True)
        )
        
        click.echo("\n📚 Course Statistics:")
        click.echo(f"   Total Courses: {total_courses:,}")
        click.echo(f"   Active Enrollments: {active_enrollments:,}")
        
        # Recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        new_users = await db.scalar(
            select(func.count(User.id))
            .where(User.created_at >= week_ago)
        )
        new_courses = await db.scalar(
            select(func.count(Course.id))
            .where(Course.created_at >= week_ago)
        )
        new_enrollments = await db.scalar(
            select(func.count(Enrollment.id))
            .where(Enrollment.enrolled_at >= week_ago)
        )
        
        click.echo("\n📈 Recent Activity (Last 7 Days):")
        click.echo(f"   New Users: {new_users:,}")
        click.echo(f"   New Courses: {new_courses:,}")
        click.echo(f"   New Enrollments: {new_enrollments:,}")
        
        # System health
        today = datetime.utcnow().date()
        today_logins = await db.scalar(
            select(func.count(AuditLog.id))
            .where(
                AuditLog.action == AuditAction.LOGIN,
                func.date(AuditLog.created_at) == today,
                AuditLog.operation_summary.like('%success%')
            )
        )
        
        click.echo("\n🏥 System Health:")
        click.echo(f"   Logins Today: {today_logins:,}")


@reports_group.command()
@click.option('--start-date', callback=parse_date, help='Start date (YYYY-MM-DD)')
@click.option('--end-date', callback=parse_date, help='End date (YYYY-MM-DD)')
@click.option('--format', type=click.Choice(['summary', 'detailed', 'csv']), default='summary')
@click.option('--output', type=click.File('w'), help='Output file for CSV format')
@async_command
async def user_growth(start_date, end_date, format, output):
    """Analyze user growth over time."""
    async with AsyncSessionLocal() as db:
        # Default date range
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        click.echo(f"\n📈 User Growth Report")
        click.echo(f"📅 Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        click.echo("=" * 60)
        
        # Get daily user registrations
        daily_stats = await db.execute(
            select(
                func.date(User.created_at).label('date'),
                User.role,
                func.count(User.id).label('count')
            )
            .where(User.created_at.between(start_date, end_date))
            .group_by(func.date(User.created_at), User.role)
            .order_by(func.date(User.created_at))
        )
        
        daily_data = {}
        for date, role, count in daily_stats:
            if date not in daily_data:
                daily_data[date] = {}
            role_name = UserRole(role).name
            daily_data[date][role_name] = count
        
        if format == 'csv' and output:
            # Write CSV
            writer = csv.writer(output)
            writer.writerow(['Date', 'Students', 'Instructors', 'Staff', 'Admin', 'Total'])
            
            for date in sorted(daily_data.keys()):
                data = daily_data[date]
                row = [
                    date.strftime('%Y-%m-%d'),
                    data.get('STUDENT', 0),
                    data.get('INSTRUCTOR', 0),
                    data.get('STAFF', 0),
                    data.get('ADMIN', 0),
                    sum(data.values())
                ]
                writer.writerow(row)
            
            click.echo(f"✅ Data exported to {output.name}")
            
        elif format == 'detailed':
            # Detailed view
            for date in sorted(daily_data.keys()):
                data = daily_data[date]
                total = sum(data.values())
                click.echo(f"\n📅 {date.strftime('%Y-%m-%d')}:")
                for role_name, count in sorted(data.items()):
                    click.echo(f"   {role_name}: {count}")
                click.echo(f"   Total: {total}")
                
        else:
            # Summary view
            total_by_role = {}
            for data in daily_data.values():
                for role, count in data.items():
                    total_by_role[role] = total_by_role.get(role, 0) + count
            
            click.echo("\n📊 Summary by Role:")
            for role, count in sorted(total_by_role.items()):
                click.echo(f"   {role}: {count:,}")
            click.echo(f"   Total: {sum(total_by_role.values()):,}")
            
            # Growth rate
            days = (end_date - start_date).days
            if days > 0:
                daily_avg = sum(total_by_role.values()) / days
                click.echo(f"\n📈 Average Growth:")
                click.echo(f"   {daily_avg:.1f} users/day")


@reports_group.command()
@click.option('--top', type=int, default=10, help='Number of top courses to show')
@async_command
async def popular_courses(top: int):
    """Show most popular courses by enrollment."""
    async with AsyncSessionLocal() as db:
        # Get courses with enrollment counts
        popular = await db.execute(
            select(
                Course,
                func.count(Enrollment.id).label('enrollment_count')
            )
            .outerjoin(Enrollment)
            .group_by(Course.id)
            .order_by(func.count(Enrollment.id).desc())
            .limit(top)
        )
        
        click.echo(f"\n🏆 Top {top} Most Popular Courses")
        click.echo("=" * 60)
        
        rows = []
        rank = 1
        for course, count in popular:
            creator_email = 'Unknown'
            if course.creator:
                await db.refresh(course, ['creator'])
                creator_email = course.creator.email
            
            rows.append([
                rank,
                course.title[:40],
                creator_email,
                count,
                f"${course.price}" if course.price else "Free"
            ])
            rank += 1
        
        if rows:
            display_table(
                ['Rank', 'Course Title', 'Creator', 'Enrollments', 'Price'],
                rows
            )
        else:
            click.echo("📭 No courses found.")


@reports_group.command()
@click.option('--period', type=click.Choice(['day', 'week', 'month', 'year']), default='month')
@async_command
async def revenue_report(period: str):
    """Generate revenue report."""
    async with AsyncSessionLocal() as db:
        # Calculate date range
        now = datetime.utcnow()
        if period == 'day':
            start_date = now - timedelta(days=1)
        elif period == 'week':
            start_date = now - timedelta(weeks=1)
        elif period == 'month':
            start_date = now - timedelta(days=30)
        else:
            start_date = now - timedelta(days=365)
        
        click.echo(f"\n💰 Revenue Report (Last {period})")
        click.echo("=" * 60)
        
        # Get payment statistics
        payment_stats = await db.execute(
            select(
                Payment.status,
                func.count(Payment.id).label('count'),
                func.sum(Payment.amount).label('total_amount')
            )
            .where(Payment.created_at >= start_date)
            .group_by(Payment.status)
        )
        
        total_revenue = 0
        pending_revenue = 0
        
        click.echo("\n📊 Payment Summary:")
        for status, count, amount in payment_stats:
            status_name = PaymentStatus(status).name if status else 'UNKNOWN'
            amount = amount or 0
            
            if status == PaymentStatus.COMPLETED:
                total_revenue = amount
            elif status == PaymentStatus.PENDING:
                pending_revenue = amount
            
            click.echo(f"   {status_name}: {count} payments, ${amount:.2f}")
        
        click.echo(f"\n💵 Revenue Summary:")
        click.echo(f"   Completed: ${total_revenue:.2f}")
        click.echo(f"   Pending: ${pending_revenue:.2f}")
        click.echo(f"   Total Potential: ${(total_revenue + pending_revenue):.2f}")
        
        # Top revenue courses
        top_courses = await db.execute(
            select(
                Course,
                func.count(Payment.id).label('payment_count'),
                func.sum(Payment.amount).label('total_revenue')
            )
            .join(Enrollment, Course.id == Enrollment.course_id)
            .join(Payment, Enrollment.id == Payment.enrollment_id)
            .where(
                Payment.created_at >= start_date,
                Payment.status == PaymentStatus.COMPLETED
            )
            .group_by(Course.id)
            .order_by(func.sum(Payment.amount).desc())
            .limit(5)
        )
        
        click.echo("\n🏆 Top Revenue Courses:")
        for course, count, revenue in top_courses:
            revenue = revenue or 0
            click.echo(f"   {course.title[:40]}: ${revenue:.2f} ({count} payments)")


@reports_group.command()
@click.option('--days', type=int, default=30, help='Number of days to analyze')
@async_command
async def attendance_trends(days: int):
    """Analyze attendance trends."""
    async with AsyncSessionLocal() as db:
        since_date = datetime.utcnow() - timedelta(days=days)
        
        click.echo(f"\n📊 Attendance Trends (Last {days} days)")
        click.echo("=" * 60)
        
        # Daily attendance counts
        daily_attendance = await db.execute(
            select(
                func.date(AttendanceRecord.swiped_at).label('date'),
                func.count(func.distinct(AttendanceRecord.student_id)).label('unique_students'),
                func.count(AttendanceRecord.id).label('total_swipes')
            )
            .where(AttendanceRecord.swiped_at >= since_date)
            .group_by(func.date(AttendanceRecord.swiped_at))
            .order_by(func.date(AttendanceRecord.swiped_at).desc())
        )
        
        records = daily_attendance.all()
        
        if not records:
            click.echo("📭 No attendance records found.")
            return
        
        # Calculate averages
        total_days = len(records)
        total_students = sum(r.unique_students for r in records)
        total_swipes = sum(r.total_swipes for r in records)
        
        click.echo("\n📈 Summary:")
        click.echo(f"   Days with attendance: {total_days}")
        click.echo(f"   Average students/day: {total_students/total_days:.1f}")
        click.echo(f"   Average swipes/day: {total_swipes/total_days:.1f}")
        
        # Peak days
        click.echo("\n🏆 Peak Attendance Days:")
        for record in sorted(records, key=lambda x: x.unique_students, reverse=True)[:5]:
            click.echo(f"   {record.date.strftime('%Y-%m-%d')}: {record.unique_students} students, {record.total_swipes} swipes")
        
        # Day of week analysis
        dow_stats = {}
        for record in records:
            dow = record.date.strftime('%A')
            if dow not in dow_stats:
                dow_stats[dow] = {'days': 0, 'students': 0}
            dow_stats[dow]['days'] += 1
            dow_stats[dow]['students'] += record.unique_students
        
        click.echo("\n📅 Average by Day of Week:")
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day in days_order:
            if day in dow_stats:
                stats = dow_stats[day]
                avg = stats['students'] / stats['days'] if stats['days'] > 0 else 0
                click.echo(f"   {day}: {avg:.1f} students/day")


@reports_group.command()
@click.option('--inactive-days', type=int, default=30, help='Days of inactivity to consider')
@async_command
async def inactive_users(inactive_days: int):
    """Find inactive users."""
    async with AsyncSessionLocal() as db:
        cutoff_date = datetime.utcnow() - timedelta(days=inactive_days)
        
        # Find users who haven't logged in
        inactive = await db.execute(
            select(User)
            .options(selectinload(User.profile))
            .where(
                or_(
                    User.last_login_at < cutoff_date,
                    User.last_login_at.is_(None)
                )
            )
            .order_by(User.last_login_at.asc().nullsfirst())
        )
        inactive_users_list = inactive.scalars().all()
        
        if not inactive_users_list:
            click.echo(f"✅ No users inactive for more than {inactive_days} days.")
            return
        
        click.echo(f"\n😴 Inactive Users (No login in {inactive_days}+ days)")
        click.echo("=" * 60)
        
        # Group by role
        by_role = {}
        never_logged_in = []
        
        for user in inactive_users_list:
            if user.last_login_at is None:
                never_logged_in.append(user)
            else:
                role_name = UserRole(user.role).name if user.role else 'UNKNOWN'
                if role_name not in by_role:
                    by_role[role_name] = []
                by_role[role_name].append(user)
        
        # Display never logged in
        if never_logged_in:
            click.echo(f"\n❌ Never Logged In ({len(never_logged_in)}):")
            for user in never_logged_in[:10]:  # Show max 10
                days_since_creation = (datetime.utcnow() - user.created_at).days
                click.echo(f"   {user.email} (created {days_since_creation} days ago)")
            if len(never_logged_in) > 10:
                click.echo(f"   ... and {len(never_logged_in) - 10} more")
        
        # Display by role
        for role, users in sorted(by_role.items()):
            click.echo(f"\n🎭 {role} ({len(users)}):")
            for user in users[:10]:  # Show max 10 per role
                days_inactive = (datetime.utcnow() - user.last_login_at).days
                click.echo(f"   {user.email} (inactive {days_inactive} days)")
            if len(users) > 10:
                click.echo(f"   ... and {len(users) - 10} more")


@reports_group.command()
@click.option('--output', type=click.File('w'), required=True, help='Output file for report')
@async_command
async def generate_summary(output):
    """Generate comprehensive system summary report."""
    async with AsyncSessionLocal() as db:
        click.echo("📝 Generating comprehensive report...")
        
        # Write header
        output.write("Giao Duc Thang Long LMS - System Summary Report\n")
        output.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        output.write("=" * 80 + "\n\n")
        
        # User statistics
        output.write("USER STATISTICS\n")
        output.write("-" * 40 + "\n")
        
        user_stats = await db.execute(
            select(
                User.role,
                func.count(User.id).label('count')
            ).group_by(User.role)
        )
        
        total_users = 0
        for role, count in user_stats:
            role_name = UserRole(role).name if role else 'UNKNOWN'
            output.write(f"{role_name}: {count}\n")
            total_users += count
        output.write(f"Total Users: {total_users}\n\n")
        
        # Course statistics
        output.write("COURSE STATISTICS\n")
        output.write("-" * 40 + "\n")
        
        total_courses = await db.scalar(select(func.count(Course.id)))
        total_enrollments = await db.scalar(select(func.count(Enrollment.id)))
        active_enrollments = await db.scalar(
            select(func.count(Enrollment.id)).where(Enrollment.is_active == True)
        )
        
        output.write(f"Total Courses: {total_courses}\n")
        output.write(f"Total Enrollments: {total_enrollments}\n")
        output.write(f"Active Enrollments: {active_enrollments}\n\n")
        
        # Add more sections as needed...
        
        output.write("\n" + "=" * 80 + "\n")
        output.write("End of Report\n")
        
        click.echo(f"✅ Report generated: {output.name}")