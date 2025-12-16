"""add product analytics table

Revision ID: b2c3d4e5f6a7
Revises: f7a8b9c0d1e2
Create Date: 2025-12-16 16:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create product_analytics table
    op.create_table('product_analytics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Analytics Data
        sa.Column('analysis_data', postgresql.JSONB(), nullable=False, comment='Kết quả phân tích từ LLM'),
        
        # Metadata
        sa.Column('model_used', sa.String(length=100), nullable=False, comment='LLM model được sử dụng'),
        sa.Column('total_reviews_analyzed', sa.Integer(), nullable=False, comment='Tổng số reviews đã phân tích'),
        sa.Column('sample_reviews_count', sa.Integer(), nullable=False, comment='Số reviews mẫu được sử dụng'),
        
        # Timestamps
        sa.Column('analyzed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('product_id', name='uq_product_analytics_product_id'),
    )
    
    # Create indexes
    op.create_index('ix_product_analytics_product_id', 'product_analytics', ['product_id'], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_product_analytics_product_id', table_name='product_analytics')
    
    # Drop table
    op.drop_table('product_analytics')
