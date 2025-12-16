"""add_task_order_field

Revision ID: g9h0i1j2k3l4
Revises: b2c3d4e5f6a7
Create Date: 2024-12-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g9h0i1j2k3l4'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add task_order field to tasks table"""
    op.add_column('tasks', sa.Column('task_order', sa.Integer(), nullable=True, comment='Thứ tự ưu tiên của task (1-5)'))


def downgrade() -> None:
    """Remove task_order field from tasks table"""
    op.drop_column('tasks', 'task_order')
