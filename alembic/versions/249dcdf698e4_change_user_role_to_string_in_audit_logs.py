"""change_user_role_to_string_in_audit_logs

Revision ID: 249dcdf698e4
Revises: cb41d73c0458
Create Date: 2025-10-25 18:47:28.703053

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '249dcdf698e4'
down_revision: Union[str, Sequence[str], None] = 'cb41d73c0458'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Change user_role column from INTEGER to VARCHAR(50)
    op.alter_column('audit_logs', 'user_role',
                    existing_type=sa.Integer(),
                    type_=sa.String(50),
                    existing_nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Change user_role column back from VARCHAR(50) to INTEGER
    op.alter_column('audit_logs', 'user_role',
                    existing_type=sa.String(50),
                    type_=sa.Integer(),
                    existing_nullable=True)
