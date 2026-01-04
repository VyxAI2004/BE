"""add_product_users_and_task_users_tables

Revision ID: j3k4l5m6n7o8
Revises: i2j3k4l5m6n7
Create Date: 2026-01-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'j3k4l5m6n7o8'
down_revision = 'i2j3k4l5m6n7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ProductUser table
    op.create_table(
        'product_users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('invited_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_id', 'user_id'),
    )
    op.create_index('idx_product_users_product_id', 'product_users', ['product_id'])
    op.create_index('idx_product_users_user_id', 'product_users', ['user_id'])

    # Create TaskUser table
    op.create_table(
        'task_users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='collaborator'),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('invited_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id', 'user_id'),
    )
    op.create_index('idx_task_users_task_id', 'task_users', ['task_id'])
    op.create_index('idx_task_users_user_id', 'task_users', ['user_id'])


def downgrade() -> None:
    op.drop_index('idx_task_users_user_id', table_name='task_users')
    op.drop_index('idx_task_users_task_id', table_name='task_users')
    op.drop_table('task_users')

    op.drop_index('idx_product_users_user_id', table_name='product_users')
    op.drop_index('idx_product_users_product_id', table_name='product_users')
    op.drop_table('product_users')
