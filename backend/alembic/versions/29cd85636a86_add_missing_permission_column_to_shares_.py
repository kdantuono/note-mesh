"""Add missing permission column to shares table

Revision ID: 29cd85636a86
Revises: 0142f314ad72
Create Date: 2025-09-14 23:42:43.753341

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29cd85636a86'
down_revision: Union[str, Sequence[str], None] = '0142f314ad72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add permission column with default value for existing data."""
    # Add column with default value first to handle existing data
    op.add_column('shares', sa.Column('permission', sa.String(length=20), nullable=False, server_default='read'))

    # Remove server_default after column is created (model handles default)
    op.alter_column('shares', 'permission', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('shares', 'permission')