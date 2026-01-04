"""add project_users columns

Revision ID: 2024_01_04_1
Revises: j3k4l5m6n7o8
Create Date: 2026-01-04 16:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2024_01_04_1'
down_revision: Union[str, Sequence[str], None] = 'j3k4l5m6n7o8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to project_users table
    op.add_column('project_users', sa.Column('role', sa.String(length=20), server_default='member', nullable=False))
    op.add_column('project_users', sa.Column('status', sa.String(length=20), server_default='pending', nullable=False))
    op.add_column('project_users', sa.Column('invited_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('project_users', sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Drop the columns
    op.drop_column('project_users', 'accepted_at')
    op.drop_column('project_users', 'invited_at')
    op.drop_column('project_users', 'status')
    op.drop_column('project_users', 'role')
