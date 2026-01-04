"""add_product_id_to_tasks

Revision ID: h1i2j3k4l5m6
Revises: g9h0i1j2k3l4
Create Date: 2024-12-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'h1i2j3k4l5m6'
down_revision: Union[str, None] = 'g9h0i1j2k3l4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add product_id FK to tasks table"""
    op.add_column('tasks', sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_tasks_product_id', 'tasks', 'products', ['product_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    """Remove product_id FK from tasks table"""
    op.drop_constraint('fk_tasks_product_id', 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'product_id')
