"""add_created_by_to_tasks

Revision ID: i2j3k4l5m6n7
Revises: h1i2j3k4l5m6
Create Date: 2024-12-20 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'i2j3k4l5m6n7'
down_revision: Union[str, None] = 'h1i2j3k4l5m6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add created_by FK to tasks table"""
    op.add_column('tasks', sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_tasks_created_by', 'tasks', 'users', ['created_by'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Remove created_by FK from tasks table"""
    op.drop_constraint('fk_tasks_created_by', 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'created_by')
