"""Add created_at and updated_at to team_users table

Revision ID: l5m6n7o8p9q0
Revises: k4l5m6n7o8p9
Create Date: 2026-01-05 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'l5m6n7o8p9q0'
down_revision: Union[str, Sequence[str], None] = 'k4l5m6n7o8p9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add created_at column to team_users
    op.add_column('team_users', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    
    # Add updated_at column to team_users
    op.add_column('team_users', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))


def downgrade() -> None:
    # Remove updated_at column
    op.drop_column('team_users', 'updated_at')
    
    # Remove created_at column
    op.drop_column('team_users', 'created_at')
