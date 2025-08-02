"""Add text extraction fields to documents.

Revision ID: 20250802_0003
Revises: 20250802_0002
Create Date: 2025-08-02 03:09:30.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250802_0003'
down_revision = '20250802_0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add text extraction fields to documents table."""
    # Add text extraction fields
    op.add_column('documents', sa.Column('extracted_text', sa.Text(), nullable=True))
    op.add_column('documents', sa.Column('extracted_text_path', sa.String(length=1000), nullable=True))
    op.add_column('documents', sa.Column('ocr_text', sa.Text(), nullable=True))
    op.add_column('documents', sa.Column('ocr_confidence', sa.JSON(), nullable=True))
    op.add_column('documents', sa.Column('extracted_metadata', sa.JSON(), nullable=True))
    op.add_column('documents', sa.Column('text_extraction_status', sa.String(length=20), nullable=False, server_default='pending'))
    op.add_column('documents', sa.Column('ocr_status', sa.String(length=20), nullable=False, server_default='pending'))


def downgrade() -> None:
    """Remove text extraction fields from documents table."""
    op.drop_column('documents', 'ocr_status')
    op.drop_column('documents', 'text_extraction_status')
    op.drop_column('documents', 'extracted_metadata')
    op.drop_column('documents', 'ocr_confidence')
    op.drop_column('documents', 'ocr_text')
    op.drop_column('documents', 'extracted_text_path')
    op.drop_column('documents', 'extracted_text')