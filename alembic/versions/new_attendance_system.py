"""Add attendance tracking system

Revision ID: new_attendance_system
Revises: c1b178ca1950
Create Date: 2025-01-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'new_attendance_system'
down_revision: Union[str, Sequence[str], None] = 'c1b178ca1950'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add attendance tracking system."""
    
    # Add new columns to users table
    op.add_column('users', sa.Column('need_change_email', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('need_change_password', sa.Boolean(), nullable=False, server_default='false'))
    
    # Create attendance_cards table
    op.create_table('attendance_cards',
        sa.Column('card_uid', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Integer(), nullable=False, server_default='2'),  # INACTIVE
        sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('card_uid')
    )
    
    # Create card_assignments table
    op.create_table('card_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('card_uid', sa.String(length=255), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['card_uid'], ['attendance_cards.card_uid'], ),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_card_assignments_id'), 'card_assignments', ['id'], unique=False)
    
    # Create attendance_records table
    op.create_table('attendance_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('swiped_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('type', sa.Integer(), nullable=False),
        sa.Column('card_uid_used', sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(['card_uid_used'], ['attendance_cards.card_uid'], ),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attendance_records_id'), 'attendance_records', ['id'], unique=False)
    
    # Create indexes for attendance system
    op.create_index('ix_card_assignments_student_revoked', 'card_assignments', ['student_id', 'revoked_at'], unique=False)
    op.create_index('ix_card_assignments_card_revoked', 'card_assignments', ['card_uid', 'revoked_at'], unique=False)
    op.create_index('ix_attendance_records_student_swiped', 'attendance_records', ['student_id', 'swiped_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema to remove attendance tracking system."""
    
    # Drop attendance tables
    op.drop_index('ix_attendance_records_student_swiped', table_name='attendance_records')
    op.drop_index('ix_card_assignments_card_revoked', table_name='card_assignments')
    op.drop_index('ix_card_assignments_student_revoked', table_name='card_assignments')
    op.drop_index(op.f('ix_attendance_records_id'), table_name='attendance_records')
    op.drop_table('attendance_records')
    op.drop_index(op.f('ix_card_assignments_id'), table_name='card_assignments')
    op.drop_table('card_assignments')
    op.drop_table('attendance_cards')
    
    # Remove columns from users table
    op.drop_column('users', 'need_change_password')
    op.drop_column('users', 'need_change_email')
