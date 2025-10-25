"""Attendance management commands for admin CLI."""

import click
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
import csv
import io

from app.database import AsyncSessionLocal
from app.models import (
    AttendanceCard, CardAssignment, AttendanceRecord,
    CardStatus, AttendanceType, User
)
from ..utils import (
    async_command, display_table, validate_email,
    format_datetime, display_stats, validate_uuid
)


@click.group(name='attendance')
def attendance_group():
    """✅ Attendance management commands."""
    pass


@attendance_group.command(name='cards')
@click.option('--status', type=click.Choice(['all', 'active', 'inactive', 'lost', 'damaged']), default='all', help='Filter by status')
@click.option('--limit', type=int, default=50, help='Number of cards to display')
@click.option('--unassigned', is_flag=True, help='Show only unassigned cards')
@async_command
async def list_cards(status: str, limit: int, unassigned: bool):
    """List attendance cards."""
    async with AsyncSessionLocal() as db:
        # Build query
        query = select(AttendanceCard)
        
        # Filter by status
        if status != 'all':
            status_map = {
                'active': CardStatus.ACTIVE,
                'inactive': CardStatus.INACTIVE,
                'lost': CardStatus.LOST,
                'damaged': CardStatus.DAMAGED
            }
            query = query.where(AttendanceCard.status == status_map[status])
        
        # Filter unassigned
        if unassigned:
            # Subquery to find assigned cards
            assigned_cards = select(CardAssignment.card_uid).where(
                CardAssignment.revoked_at.is_(None)
            )
            query = query.where(AttendanceCard.card_uid.notin_(assigned_cards))
        
        query = query.limit(limit)
        result = await db.execute(query)
        cards = result.scalars().all()
        
        if not cards:
            click.echo("📭 No cards found.")
            return
        
        click.echo(f"\n💳 Attendance Cards (showing {len(cards)}):")
        
        rows = []
        for card in cards:
            # Get current assignment
            assignment = await db.scalar(
                select(CardAssignment)
                .options(selectinload(CardAssignment.student))
                .where(
                    CardAssignment.card_uid == card.card_uid,
                    CardAssignment.revoked_at.is_(None)
                )
            )
            
            assigned_to = "Unassigned"
            if assignment and assignment.student:
                assigned_to = assignment.student.email
            
            status_name = CardStatus(card.status).name
            
            rows.append([
                card.card_uid,
                status_name,
                assigned_to,
                format_datetime(card.issued_at),
                card.notes or ""
            ])
        
        display_table(
            ['Card UID', 'Status', 'Assigned To', 'Issued', 'Notes'],
            rows
        )


@attendance_group.command()
@click.option('--card-uid', prompt='Card UID', help='UID of the card')
@click.option('--notes', help='Notes about the card')
@async_command
async def create_card(card_uid: str, notes: str):
    """Create a new attendance card."""
    async with AsyncSessionLocal() as db:
        # Check if card exists
        existing = await db.scalar(
            select(AttendanceCard).where(AttendanceCard.card_uid == card_uid)
        )
        if existing:
            click.echo(f"❌ Card '{card_uid}' already exists!")
            return
        
        try:
            card = AttendanceCard(
                card_uid=card_uid,
                status=CardStatus.INACTIVE,
                notes=notes
            )
            db.add(card)
            await db.commit()
            
            click.echo(f"✅ Card '{card_uid}' created successfully!")
            
        except Exception as e:
            click.echo(f"❌ Error creating card: {e}")


@attendance_group.command()
@click.option('--card-uid', prompt='Card UID', help='UID of the card')
@click.option('--student-email', prompt='Student email', callback=validate_email, help='Email of the student')
@async_command
async def assign_card(card_uid: str, student_email: str):
    """Assign a card to a student."""
    async with AsyncSessionLocal() as db:
        # Check card exists
        card = await db.scalar(
            select(AttendanceCard).where(AttendanceCard.card_uid == card_uid)
        )
        if not card:
            click.echo(f"❌ Card '{card_uid}' not found!")
            return
        
        # Check student exists
        student = await db.scalar(
            select(User).where(User.email == student_email)
        )
        if not student:
            click.echo(f"❌ User '{student_email}' not found!")
            return
        
        # Check if already assigned
        existing = await db.scalar(
            select(CardAssignment).where(
                CardAssignment.card_uid == card_uid,
                CardAssignment.revoked_at.is_(None)
            )
        )
        if existing:
            click.echo(f"❌ Card is already assigned!")
            return
        
        try:
            # Create assignment
            assignment = CardAssignment(
                student_id=student.id,
                card_uid=card_uid
            )
            db.add(assignment)
            
            # Activate card
            card.status = CardStatus.ACTIVE
            
            await db.commit()
            click.echo(f"✅ Card '{card_uid}' assigned to {student_email}!")
            
        except Exception as e:
            click.echo(f"❌ Error assigning card: {e}")


@attendance_group.command()
@click.option('--card-uid', prompt='Card UID', help='UID of the card')
@async_command
async def revoke_card(card_uid: str):
    """Revoke a card assignment."""
    async with AsyncSessionLocal() as db:
        # Find active assignment
        assignment = await db.scalar(
            select(CardAssignment)
            .options(selectinload(CardAssignment.student))
            .where(
                CardAssignment.card_uid == card_uid,
                CardAssignment.revoked_at.is_(None)
            )
        )
        
        if not assignment:
            click.echo(f"❌ No active assignment found for card '{card_uid}'!")
            return
        
        student_email = assignment.student.email if assignment.student else "Unknown"
        
        if click.confirm(f"Revoke card '{card_uid}' from {student_email}?"):
            try:
                assignment.revoked_at = datetime.utcnow()
                
                # Deactivate card
                card = await db.scalar(
                    select(AttendanceCard).where(AttendanceCard.card_uid == card_uid)
                )
                if card:
                    card.status = CardStatus.INACTIVE
                
                await db.commit()
                click.echo(f"✅ Card '{card_uid}' revoked successfully!")
                
            except Exception as e:
                click.echo(f"❌ Error revoking card: {e}")


@attendance_group.command()
@click.option('--student-email', callback=validate_email, help='Filter by student email')
@click.option('--days', type=int, default=30, help='Number of days to show')
@click.option('--format', type=click.Choice(['table', 'detailed']), default='table', help='Output format')
@async_command
async def records(student_email: str, days: int, format: str):
    """View attendance records."""
    async with AsyncSessionLocal() as db:
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Build query
        query = select(AttendanceRecord).options(
            selectinload(AttendanceRecord.student),
            selectinload(AttendanceRecord.card)
        ).where(AttendanceRecord.swiped_at >= since_date)
        
        # Filter by student
        if student_email:
            student = await db.scalar(
                select(User).where(User.email == student_email)
            )
            if not student:
                click.echo(f"❌ User '{student_email}' not found!")
                return
            query = query.where(AttendanceRecord.student_id == student.id)
        
        query = query.order_by(AttendanceRecord.swiped_at.desc()).limit(100)
        
        result = await db.execute(query)
        records = result.scalars().all()
        
        if not records:
            click.echo("📭 No attendance records found.")
            return
        
        click.echo(f"\n📋 Attendance Records (Last {days} days, showing {len(records)}):")
        
        if format == 'table':
            rows = []
            for record in records:
                student_name = record.student.email if record.student else 'Unknown'
                type_name = AttendanceType(record.type).name
                
                rows.append([
                    str(record.id)[:8] + "...",  # Show first 8 chars of UUID
                    format_datetime(record.swiped_at),
                    student_name,
                    type_name,
                    record.card_uid_used
                ])
            
            display_table(
                ['ID', 'Timestamp', 'Student', 'Type', 'Card Used'],
                rows
            )
        else:
            for record in records:
                click.echo(f"\n🆔 Record ID: {str(record.id)}")
                click.echo(f"⏰ Time: {format_datetime(record.swiped_at)}")
                if record.student:
                    click.echo(f"👤 Student: {record.student.email}")
                click.echo(f"🔄 Type: {AttendanceType(record.type).name}")
                click.echo(f"💳 Card: {record.card_uid_used}")
                click.echo("-" * 40)


@attendance_group.command()
@click.option('--student-email', prompt='Student email', callback=validate_email, help='Student email')
@click.option('--month', type=int, help='Month (1-12)')
@click.option('--year', type=int, help='Year')
@async_command
async def student_report(student_email: str, month: int, year: int):
    """Generate attendance report for a student."""
    async with AsyncSessionLocal() as db:
        # Find student
        student = await db.scalar(
            select(User).where(User.email == student_email)
        )
        if not student:
            click.echo(f"❌ User '{student_email}' not found!")
            return
        
        # Default to current month/year
        now = datetime.now()
        if not month:
            month = now.month
        if not year:
            year = now.year
        
        # Calculate date range
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        # Get attendance records
        records = await db.execute(
            select(AttendanceRecord)
            .where(
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.swiped_at >= start_date,
                AttendanceRecord.swiped_at < end_date
            )
            .order_by(AttendanceRecord.swiped_at)
        )
        records = records.scalars().all()
        
        click.echo(f"\n📊 Attendance Report: {student_email}")
        click.echo(f"📅 Period: {start_date.strftime('%B %Y')}")
        click.echo("=" * 60)
        
        if not records:
            click.echo("📭 No attendance records for this period.")
            return
        
        # Process records by day
        daily_records = {}
        for record in records:
            date_key = record.swiped_at.date()
            if date_key not in daily_records:
                daily_records[date_key] = {
                    'check_ins': [],
                    'check_outs': []
                }
            
            if record.type == AttendanceType.CHECK_IN:
                daily_records[date_key]['check_ins'].append(record.swiped_at)
            else:
                daily_records[date_key]['check_outs'].append(record.swiped_at)
        
        # Display summary
        total_days = len(daily_records)
        click.echo(f"\n📈 Summary:")
        click.echo(f"   Days with attendance: {total_days}")
        click.echo(f"   Total swipes: {len(records)}")
        
        # Display daily records
        click.echo(f"\n📅 Daily Records:")
        for date in sorted(daily_records.keys()):
            day_data = daily_records[date]
            check_ins = sorted(day_data['check_ins'])
            check_outs = sorted(day_data['check_outs'])
            
            click.echo(f"\n   {date.strftime('%Y-%m-%d (%A)')}:")
            if check_ins:
                click.echo(f"      First Check-in: {check_ins[0].strftime('%H:%M:%S')}")
            if check_outs:
                click.echo(f"      Last Check-out: {check_outs[-1].strftime('%H:%M:%S')}")
            
            # Calculate duration if both check-in and check-out exist
            if check_ins and check_outs and check_outs[-1] > check_ins[0]:
                duration = check_outs[-1] - check_ins[0]
                hours, remainder = divmod(duration.total_seconds(), 3600)
                minutes = remainder // 60
                click.echo(f"      Duration: {int(hours)}h {int(minutes)}m")


@attendance_group.command()
@click.option('--output', type=click.File('w'), required=True, help='Output CSV file')
@click.option('--days', type=int, default=30, help='Export records from last N days')
@async_command
async def export_records(output, days: int):
    """Export attendance records to CSV."""
    async with AsyncSessionLocal() as db:
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Get records
        records = await db.execute(
            select(AttendanceRecord)
            .options(
                selectinload(AttendanceRecord.student).selectinload(User.profile),
                selectinload(AttendanceRecord.card)
            )
            .where(AttendanceRecord.swiped_at >= since_date)
            .order_by(AttendanceRecord.swiped_at.desc())
        )
        records = records.scalars().all()
        
        if not records:
            click.echo("📭 No records to export.")
            return
        
        # Write CSV
        writer = csv.writer(output)
        writer.writerow([
            'Record ID', 'Timestamp', 'Student ID', 'Student Email',
            'Student Name', 'Type', 'Card UID'
        ])
        
        for record in records:
            student_name = ""
            if record.student and record.student.profile:
                student_name = f"{record.student.profile.first_name} {record.student.profile.last_name}"
            
            writer.writerow([
                record.id,
                record.swiped_at.strftime('%Y-%m-%d %H:%M:%S'),
                record.student_id,
                record.student.email if record.student else '',
                student_name,
                AttendanceType(record.type).name,
                record.card_uid_used
            ])
        
        click.echo(f"✅ Exported {len(records)} records to {output.name}")


@attendance_group.command()
@click.option('--force', is_flag=True, help='Skip confirmation')
@async_command
async def fix_orphaned_cards(force: bool):
    """Find and fix orphaned card assignments."""
    async with AsyncSessionLocal() as db:
        # Find assignments where card doesn't exist
        orphaned = await db.execute(
            select(CardAssignment)
            .outerjoin(AttendanceCard, CardAssignment.card_uid == AttendanceCard.card_uid)
            .where(AttendanceCard.card_uid.is_(None))
        )
        orphaned = orphaned.scalars().all()
        
        if not orphaned:
            click.echo("✅ No orphaned card assignments found.")
            return
        
        click.echo(f"\n⚠️  Found {len(orphaned)} orphaned card assignments:")
        for assignment in orphaned:
            click.echo(f"   - Assignment ID: {assignment.id}, Card UID: {assignment.card_uid}")
        
        if not force and not click.confirm("\nRevoke these orphaned assignments?"):
            click.echo("❌ Operation cancelled.")
            return
        
        try:
            for assignment in orphaned:
                assignment.revoked_at = datetime.utcnow()
            
            await db.commit()
            click.echo(f"✅ Revoked {len(orphaned)} orphaned assignments.")
            
        except Exception as e:
            click.echo(f"❌ Error fixing orphaned assignments: {e}")