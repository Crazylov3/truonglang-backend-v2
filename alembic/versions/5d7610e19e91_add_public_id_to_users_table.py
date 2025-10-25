"""add_public_id_to_users_table

Revision ID: 5d7610e19e91
Revises: 249dcdf698e4
Create Date: 2025-10-25 19:28:06.457413

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d7610e19e91'
down_revision: Union[str, Sequence[str], None] = '249dcdf698e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Add public_id column as nullable first
    op.add_column('users', sa.Column('public_id', sa.Integer(), nullable=True, comment='Human-readable ID for support, URLs, etc.'))
    
    # Step 2: Populate public_id for existing users
    # This will assign sequential numbers to existing users
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE users 
        SET public_id = subquery.row_number 
        FROM (
            SELECT id, ROW_NUMBER() OVER (ORDER BY created_at) as row_number 
            FROM users 
            WHERE public_id IS NULL
        ) AS subquery 
        WHERE users.id = subquery.id
    """))
    
    # Step 3: Make public_id NOT NULL after populating existing data
    op.alter_column('users', 'public_id', nullable=False)
    
    # Step 4: Create sequence for auto-increment (PostgreSQL specific)
    op.execute(sa.text("""
        CREATE SEQUENCE IF NOT EXISTS users_public_id_seq;
        SELECT setval('users_public_id_seq', COALESCE(MAX(public_id), 0)) FROM users;
        ALTER TABLE users ALTER COLUMN public_id SET DEFAULT nextval('users_public_id_seq');
    """))
    
    # Step 5: Create unique index for public_id
    op.create_index('ix_users_public_id', 'users', ['public_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the index first
    op.drop_index('ix_users_public_id', table_name='users')
    
    # Drop the sequence
    op.execute(sa.text("DROP SEQUENCE IF EXISTS users_public_id_seq"))
    
    # Drop the public_id column
    op.drop_column('users', 'public_id')
