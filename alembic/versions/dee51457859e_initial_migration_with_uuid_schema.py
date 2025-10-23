"""Initial migration with UUID schema

Revision ID: dee51457859e
Revises: 
Create Date: 2025-10-23 13:52:22.052547

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'dee51457859e'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    
    # Create enums
    op.execute("CREATE TYPE userrole AS ENUM ('STUDENT', 'INSTRUCTOR', 'STAFF', 'ADMIN')")
    op.execute("CREATE TYPE invoicestatus AS ENUM ('DUE', 'PAID', 'OVERDUE', 'CANCELLED')")
    op.execute("CREATE TYPE paymentstatus AS ENUM ('PENDING', 'SUCCESSFUL', 'FAILED')")
    op.execute("CREATE TYPE cardstatus AS ENUM ('ACTIVE', 'INACTIVE', 'LOST', 'DAMAGED')")
    op.execute("CREATE TYPE attendancetype AS ENUM ('CHECK_IN', 'CHECK_OUT')")
    op.execute("CREATE TYPE dayofweek AS ENUM ('MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY')")
    
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', postgresql.ENUM('STUDENT', 'INSTRUCTOR', 'STAFF', 'ADMIN', name='userrole', create_type=False), nullable=False),
        sa.Column('need_change_email', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('need_change_password', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    
    # Create user_profiles table
    op.create_table('user_profiles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('avatar', sa.String(length=255), nullable=True),
        sa.Column('current_school', sa.String(length=255), nullable=True),
        sa.Column('current_grade', sa.String(length=50), nullable=True),
        sa.Column('default_discount_percentage', sa.DECIMAL(precision=5, scale=2), nullable=True, server_default='0'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('user_id')
    )
    
    # Create courses table
    op.create_table('courses',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('teacher_name', sa.String(length=255), nullable=True),
        sa.Column('price', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('preview_picture_path', sa.String(length=500), nullable=True),
        sa.Column('group_chat_link', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_courses_id'), 'courses', ['id'], unique=False)
    op.create_index(op.f('ix_courses_title'), 'courses', ['title'], unique=False)
    
    # Create enrollments table
    op.create_table('enrollments',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('enrolled_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('discount_percentage', sa.DECIMAL(precision=5, scale=2), nullable=False, server_default='0'),
        sa.Column('discount_reason', sa.Text(), nullable=True),
        sa.Column('discount_approved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
        sa.ForeignKeyConstraint(['discount_approved_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id', 'course_id', name='unique_student_course')
    )
    op.create_index(op.f('ix_enrollments_id'), 'enrollments', ['id'], unique=False)
    
    # Create course_edit_permissions table
    op.create_table('course_edit_permissions',
        sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instructor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['instructor_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('course_id', 'instructor_id')
    )
    
    # Create course_payment_period table
    op.create_table('course_payment_period',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_course_payment_period_id'), 'course_payment_period', ['id'], unique=False)
    
    # Create invoices table
    op.create_table('invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('enrollment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_period_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', postgresql.ENUM('DUE', 'PAID', 'OVERDUE', 'CANCELLED', name='invoicestatus', create_type=False), nullable=False, server_default='DUE'),
        sa.Column('amount_due', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['enrollment_id'], ['enrollments.id'], ),
        sa.ForeignKeyConstraint(['payment_period_id'], ['course_payment_period.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('enrollment_id', 'payment_period_id', name='unique_enrollment_payment_period')
    )
    op.create_index(op.f('ix_invoices_id'), 'invoices', ['id'], unique=False)
    
    # Create payments table
    op.create_table('payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', postgresql.ENUM('PENDING', 'SUCCESSFUL', 'FAILED', name='paymentstatus', create_type=False), nullable=False, server_default='PENDING'),
        sa.Column('amount', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('provider_reference', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider_reference')
    )
    op.create_index(op.f('ix_payments_id'), 'payments', ['id'], unique=False)
    
    # Create course_documents table
    op.create_table('course_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_path', sa.String(length=500), nullable=True),
        sa.Column('document_name', sa.String(length=255), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=True),
        sa.Column('document_size', sa.Integer(), nullable=True),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_course_documents_course_active', 'course_documents', ['course_id', 'is_active'], unique=False)
    op.create_index(op.f('ix_course_documents_id'), 'course_documents', ['id'], unique=False)
    
    # Create attendance_cards table
    op.create_table('attendance_cards',
        sa.Column('card_uid', sa.String(length=255), nullable=False),
        sa.Column('status', postgresql.ENUM('ACTIVE', 'INACTIVE', 'LOST', 'DAMAGED', name='cardstatus', create_type=False), nullable=False, server_default='INACTIVE'),
        sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('card_uid')
    )
    
    # Create card_assignments table
    op.create_table('card_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('card_uid', sa.String(length=255), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['card_uid'], ['attendance_cards.card_uid'], ),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_card_assignments_card_revoked', 'card_assignments', ['card_uid', 'revoked_at'], unique=False)
    op.create_index(op.f('ix_card_assignments_id'), 'card_assignments', ['id'], unique=False)
    op.create_index('ix_card_assignments_student_revoked', 'card_assignments', ['student_id', 'revoked_at'], unique=False)
    
    # Create attendance_records table
    op.create_table('attendance_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('swiped_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('type', postgresql.ENUM('CHECK_IN', 'CHECK_OUT', name='attendancetype', create_type=False), nullable=False),
        sa.Column('card_uid_used', sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attendance_records_id'), 'attendance_records', ['id'], unique=False)
    
    # Create guardians table
    op.create_table('guardians',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('phone_number', sa.String(length=50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone_number')
    )
    op.create_index(op.f('ix_guardians_id'), 'guardians', ['id'], unique=False)
    
    # Create student_guardian_relationships table
    op.create_table('student_guardian_relationships',
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('guardian_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('relationship_type', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['guardian_id'], ['guardians.id'], ),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('student_id', 'guardian_id')
    )
    
    # Create branches table
    op.create_table('branches',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('address', sa.String(length=500), nullable=False),
        sa.Column('contact_info', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_branches_id'), 'branches', ['id'], unique=False)
    
    # Create rooms table
    op.create_table('rooms',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('room_number', sa.String(length=50), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('branch_id', 'room_number', name='unique_branch_room')
    )
    op.create_index(op.f('ix_rooms_id'), 'rooms', ['id'], unique=False)
    
    # Create course_schedules table
    op.create_table('course_schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('room_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('day_of_week', postgresql.ENUM('MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY', name='dayofweek', create_type=False), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
        sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('course_id', 'day_of_week', 'start_time', name='unique_course_schedule')
    )
    op.create_index(op.f('ix_course_schedules_id'), 'course_schedules', ['id'], unique=False)
    
    # Create audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_email', sa.String(length=255), nullable=True),
        sa.Column('user_role', sa.Integer(), nullable=True),
        sa.Column('action', sa.Integer(), nullable=False),
        sa.Column('resource_type', sa.Integer(), nullable=False),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('resource_name', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('request_method', sa.String(length=10), nullable=True),
        sa.Column('request_path', sa.String(length=500), nullable=True),
        sa.Column('request_query', sa.Text(), nullable=True),
        sa.Column('request_body_size', sa.Integer(), nullable=True),
        sa.Column('response_status_code', sa.Integer(), nullable=True),
        sa.Column('response_size', sa.Integer(), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('database_queries', sa.Integer(), nullable=True),
        sa.Column('database_time_ms', sa.Integer(), nullable=True),
        sa.Column('operation_summary', sa.Text(), nullable=False),
        sa.Column('operation_details', sa.JSON(), nullable=True),
        sa.Column('old_values', sa.JSON(), nullable=True),
        sa.Column('new_values', sa.JSON(), nullable=True),
        sa.Column('changed_fields', sa.JSON(), nullable=True),
        sa.Column('table_name', sa.String(length=255), nullable=True),
        sa.Column('record_id', sa.String(length=255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_traceback', sa.Text(), nullable=True),
        sa.Column('severity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('correlation_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('request_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('request_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)


def downgrade() -> None:
    # Drop all tables
    op.drop_table('audit_logs')
    op.drop_table('course_schedules')
    op.drop_table('rooms')
    op.drop_table('branches')
    op.drop_table('student_guardian_relationships')
    op.drop_table('guardians')
    op.drop_table('attendance_records')
    op.drop_table('card_assignments')
    op.drop_table('attendance_cards')
    op.drop_table('course_documents')
    op.drop_table('payments')
    op.drop_table('invoices')
    op.drop_table('course_payment_period')
    op.drop_table('course_edit_permissions')
    op.drop_table('enrollments')
    op.drop_table('courses')
    op.drop_table('user_profiles')
    op.drop_table('users')
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS dayofweek")
    op.execute("DROP TYPE IF EXISTS attendancetype")
    op.execute("DROP TYPE IF EXISTS cardstatus")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
    op.execute("DROP TYPE IF EXISTS invoicestatus")
    op.execute("DROP TYPE IF EXISTS userrole")