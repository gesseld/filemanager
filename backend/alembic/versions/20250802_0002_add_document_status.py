"""Add status column to documents table.

Revision ID: 20250802_0002
Revises: 20250802_0001
Create Date: 2025-08-02 02:51:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250802_0002'
down_revision = '20250802_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add status column to documents table."""
    op.add_column(
        'documents',
        sa.Column('status', sa.String(20), nullable=False, server_default='pending')
    )


def downgrade() -> None:
    """Remove status column from documents table."""
    op.drop_column('documents', 'status')