"""Add consolidated audit logging system

Revision ID: audit_system_001
Revises: new_attendance_system
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'audit_system_001'
down_revision = 'new_attendance_system'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
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
        sa.Column('operation_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('old_values', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('new_values', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('changed_fields', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('table_name', sa.String(length=255), nullable=True),
        sa.Column('record_id', sa.String(length=255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_traceback', sa.Text(), nullable=True),
        sa.Column('severity', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('correlation_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('request_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('request_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better query performance
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_resource_type'), 'audit_logs', ['resource_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_audit_logs_table_name'), 'audit_logs', ['table_name'], unique=False)
    op.create_index(op.f('ix_audit_logs_correlation_id'), 'audit_logs', ['correlation_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_ip_address'), 'audit_logs', ['ip_address'], unique=False)
    op.create_index(op.f('ix_audit_logs_request_path'), 'audit_logs', ['request_path'], unique=False)
    op.create_index(op.f('ix_audit_logs_response_status_code'), 'audit_logs', ['response_status_code'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_audit_logs_response_status_code'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_request_path'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_ip_address'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_correlation_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_table_name'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_resource_type'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_id'), table_name='audit_logs')
    
    # Drop table
    op.drop_table('audit_logs')
