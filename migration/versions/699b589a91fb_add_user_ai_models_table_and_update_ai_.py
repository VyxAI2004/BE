"""Add user_ai_models table and update ai_models table to match enterprise design

Revision ID: 699b589a91fb
Revises: add_user_ai_models_and_update_ai_models
Create Date: 2025-11-02 18:29:32.885802

"""
from typing import Sequence, Union


from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '699b589a91fb'
down_revision: Union[str, Sequence[str], None] = 'e9087d7591a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop user_id, api_key from ai_models, make user-independent
    with op.batch_alter_table('ai_models') as batch_op:
        batch_op.drop_constraint('uq_user_model_name', type_='unique')
        batch_op.drop_column('user_id')
        batch_op.drop_column('api_key')
        batch_op.create_unique_constraint('uq_model_name_provider', ['name', 'provider', 'model_name'])

    # 2. Create user_ai_models table
    op.create_table('user_ai_models',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ai_model_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('api_key', sa.String(length=500), nullable=True),  # API key riêng của user cho model này
        sa.Column('config', postgresql.JSONB(), nullable=True),      # config riêng nếu cần
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'ai_model_id', name='uq_user_ai_model'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ai_model_id'], ['ai_models.id'], ondelete='CASCADE')
    )

def downgrade() -> None:
    # 1. Drop user_ai_models table
    op.drop_table('user_ai_models')
    # 2. Add user_id, api_key back to ai_models, restore old unique constraint
    with op.batch_alter_table('ai_models') as batch_op:
        batch_op.drop_constraint('uq_model_name_provider', type_='unique')
        batch_op.add_column(sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False))
        batch_op.add_column(sa.Column('api_key', sa.String(length=500), nullable=True))
        batch_op.create_unique_constraint('uq_user_model_name', ['user_id', 'name'])
