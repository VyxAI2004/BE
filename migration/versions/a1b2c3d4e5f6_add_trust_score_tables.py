"""Add product reviews, review analyses, and product trust scores tables for Trust Score feature

Revision ID: a1b2c3d4e5f6
Revises: 699b589a91fb
Create Date: 2025-12-05 13:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '91f8afb91564'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add trust_score column to products table
    op.add_column('products', sa.Column(
        'trust_score', 
        sa.Numeric(precision=5, scale=2), 
        nullable=True,
        comment='Denormalized trust score (0-100)'
    ))
    
    # 2. Create product_reviews table
    op.create_table('product_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('crawl_session_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Reviewer Information
        sa.Column('reviewer_name', sa.String(length=200), nullable=True),
        sa.Column('reviewer_id', sa.String(length=100), nullable=True, comment='ID của reviewer trên platform gốc'),
        
        # Review Content
        sa.Column('rating', sa.Integer(), nullable=False, comment='Điểm đánh giá 1-5'),
        sa.Column('content', sa.Text(), nullable=True, comment='Nội dung review'),
        sa.Column('review_date', sa.DateTime(timezone=True), nullable=True, comment='Ngày đăng review trên platform'),
        
        # Platform Information
        sa.Column('platform', sa.String(length=50), nullable=False, comment='shopee/lazada/tiki'),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        
        # Review Metadata
        sa.Column('is_verified_purchase', sa.Boolean(), nullable=False, server_default='false', comment='Đã mua hàng verified'),
        sa.Column('helpful_count', sa.Integer(), nullable=True, server_default='0', comment='Số lượt thấy hữu ích'),
        sa.Column('images', postgresql.JSONB(), nullable=True, comment='Danh sách URL ảnh review'),
        
        # Crawl Metadata
        sa.Column('crawled_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('raw_data', postgresql.JSONB(), nullable=True, comment='Dữ liệu thô từ crawler để backup'),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['crawl_session_id'], ['crawl_sessions.id'], ondelete='SET NULL'),
    )
    
    # Create indexes for product_reviews
    op.create_index('ix_product_reviews_product_id', 'product_reviews', ['product_id'])
    op.create_index('ix_product_reviews_platform', 'product_reviews', ['platform'])
    op.create_index('ix_product_reviews_review_date', 'product_reviews', ['review_date'])
    op.create_index('ix_product_reviews_product_platform', 'product_reviews', ['product_id', 'platform'])
    
    # 3. Create review_analyses table
    op.create_table('review_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('review_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        
        # Sentiment Analysis Results
        sa.Column('sentiment_label', sa.String(length=20), nullable=False, comment='positive/negative/neutral'),
        sa.Column('sentiment_score', sa.Numeric(precision=5, scale=4), nullable=False, comment='Score 0.0000 - 1.0000'),
        sa.Column('sentiment_confidence', sa.Numeric(precision=5, scale=4), nullable=False, comment='Độ tin cậy dự đoán'),
        
        # Spam Detection Results
        sa.Column('is_spam', sa.Boolean(), nullable=False, comment='True nếu là spam'),
        sa.Column('spam_score', sa.Numeric(precision=5, scale=4), nullable=False, comment='Score 0.0000 - 1.0000'),
        sa.Column('spam_confidence', sa.Numeric(precision=5, scale=4), nullable=False, comment='Độ tin cậy dự đoán spam'),
        
        # Model Information
        sa.Column('sentiment_model_version', sa.String(length=50), nullable=True, comment='Version của sentiment model'),
        sa.Column('spam_model_version', sa.String(length=50), nullable=True, comment='Version của spam model'),
        
        # Analysis Metadata
        sa.Column('analyzed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('analysis_metadata', postgresql.JSONB(), nullable=True, 
                  comment='Chi tiết: sentiment_raw_output, spam_features, processing_time_ms'),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['review_id'], ['product_reviews.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for review_analyses
    op.create_index('ix_review_analyses_review_id', 'review_analyses', ['review_id'], unique=True)
    op.create_index('ix_review_analyses_sentiment_label', 'review_analyses', ['sentiment_label'])
    op.create_index('ix_review_analyses_is_spam', 'review_analyses', ['is_spam'])
    
    # 4. Create product_trust_scores table
    op.create_table('product_trust_scores',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        
        # Trust Score
        sa.Column('trust_score', sa.Numeric(precision=5, scale=2), nullable=False, comment='Trust score 0.00 - 100.00'),
        
        # Review Statistics
        sa.Column('total_reviews', sa.Integer(), nullable=False, server_default='0', comment='Tổng số reviews'),
        sa.Column('analyzed_reviews', sa.Integer(), nullable=False, server_default='0', comment='Số reviews đã phân tích'),
        sa.Column('verified_reviews_count', sa.Integer(), nullable=False, server_default='0', comment='Reviews đã xác thực mua hàng'),
        
        # Spam Statistics
        sa.Column('spam_reviews_count', sa.Integer(), nullable=False, server_default='0', comment='Số reviews spam'),
        sa.Column('spam_percentage', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0', comment='% spam'),
        
        # Sentiment Statistics
        sa.Column('positive_reviews_count', sa.Integer(), nullable=False, server_default='0', comment='Reviews tích cực'),
        sa.Column('negative_reviews_count', sa.Integer(), nullable=False, server_default='0', comment='Reviews tiêu cực'),
        sa.Column('neutral_reviews_count', sa.Integer(), nullable=False, server_default='0', comment='Reviews trung lập'),
        sa.Column('average_sentiment_score', sa.Numeric(precision=5, scale=4), nullable=False, server_default='0', comment='Điểm cảm xúc trung bình'),
        
        # Quality Metrics
        sa.Column('review_quality_score', sa.Numeric(precision=5, scale=2), nullable=True, comment='Điểm chất lượng reviews (0-100)'),
        sa.Column('engagement_score', sa.Numeric(precision=5, scale=2), nullable=True, comment='Điểm tương tác (0-100)'),
        
        # Calculation Details
        sa.Column('calculated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('calculation_metadata', postgresql.JSONB(), nullable=True,
                  comment='Chi tiết công thức: formula_version, weights, component_scores'),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for product_trust_scores
    op.create_index('ix_product_trust_scores_product_id', 'product_trust_scores', ['product_id'], unique=True)
    op.create_index('ix_product_trust_scores_trust_score', 'product_trust_scores', ['trust_score'])


def downgrade() -> None:
    # Drop tables in reverse order (due to foreign key dependencies)
    
    # 1. Drop product_trust_scores table and its indexes
    op.drop_index('ix_product_trust_scores_trust_score', table_name='product_trust_scores')
    op.drop_index('ix_product_trust_scores_product_id', table_name='product_trust_scores')
    op.drop_table('product_trust_scores')
    
    # 2. Drop review_analyses table and its indexes
    op.drop_index('ix_review_analyses_is_spam', table_name='review_analyses')
    op.drop_index('ix_review_analyses_sentiment_label', table_name='review_analyses')
    op.drop_index('ix_review_analyses_review_id', table_name='review_analyses')
    op.drop_table('review_analyses')
    
    # 3. Drop product_reviews table and its indexes
    op.drop_index('ix_product_reviews_product_platform', table_name='product_reviews')
    op.drop_index('ix_product_reviews_review_date', table_name='product_reviews')
    op.drop_index('ix_product_reviews_platform', table_name='product_reviews')
    op.drop_index('ix_product_reviews_product_id', table_name='product_reviews')
    op.drop_table('product_reviews')
    
    # 4. Remove trust_score column from products table
    op.drop_column('products', 'trust_score')
