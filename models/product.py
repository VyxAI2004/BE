from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Text, Boolean, DateTime, Integer, Numeric, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .project import Project
    from .product_source import ProductSource
    from .crawl_session import CrawlSession
    from .task import Task
    from .ai_model import AIModel


class Product(Base):
    """Model cho bảng products"""
    __tablename__ = "products"
    
    # Columns
    project_id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    product_source_id: Mapped[Optional[str]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("product_sources.id", ondelete="SET NULL"), nullable=True
    )
    crawl_session_id: Mapped[Optional[str]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("crawl_sessions.id", ondelete="SET NULL"), nullable=True
    )
    company: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    brand: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    subcategory: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    current_price: Mapped[Numeric] = mapped_column(Numeric(precision=15, scale=2), nullable=False)
    original_price: Mapped[Optional[Numeric]] = mapped_column(Numeric(precision=15, scale=2), nullable=True)
    discount_rate: Mapped[Optional[Numeric]] = mapped_column(Numeric(precision=5, scale=2), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), server_default='VND', nullable=True)
    specifications: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    features: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    images: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    average_rating: Mapped[Optional[Numeric]] = mapped_column(Numeric(precision=3, scale=2), nullable=True)
    review_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sold_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    collected_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), server_default='now()', nullable=True)
    is_verified: Mapped[Optional[bool]] = mapped_column(Boolean, server_default='false', nullable=True)
    data_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # NEW: Denormalized trust score for quick access & sorting
    trust_score: Mapped[Optional[Numeric]] = mapped_column(
        Numeric(precision=5, scale=2), nullable=True, comment="Denormalized trust score (0-100)"
    )
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="products", lazy="select")
    product_source: Mapped["ProductSource"] = relationship("ProductSource", back_populates="products", lazy="select")
    crawl_session: Mapped["CrawlSession"] = relationship("CrawlSession", back_populates="products", lazy="select")
    price_history: Mapped[list["PriceHistory"]] = relationship(
        "PriceHistory", back_populates="product", cascade="all, delete-orphan", lazy="select"
    )
    product_comparisons: Mapped[list["ProductComparison"]] = relationship(
        "ProductComparison", back_populates="competitor_product", lazy="select"
    )
    # NEW: Relationships for reviews and trust score
    reviews: Mapped[list["ProductReview"]] = relationship(
        "ProductReview", back_populates="product", cascade="all, delete-orphan", lazy="select"
    )
    trust_score_detail: Mapped[Optional["ProductTrustScore"]] = relationship(
        "ProductTrustScore", back_populates="product", uselist=False, cascade="all, delete-orphan", lazy="select"
    )


class PriceHistory(Base):
    """Model cho bảng price_history"""
    __tablename__ = "price_history"
    
    # Columns
    product_id: Mapped[str] = mapped_column(PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    price: Mapped[Numeric] = mapped_column(Numeric(precision=15, scale=2), nullable=False)
    currency: Mapped[Optional[str]] = mapped_column(String(10), server_default='VND', nullable=True)
    discount_rate: Mapped[Optional[Numeric]] = mapped_column(Numeric(precision=5, scale=2), nullable=True)
    stock_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    recorded_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), server_default='now()', nullable=True)
    
    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="price_history", lazy="select")


class PriceAnalysis(Base):
    """Model cho bảng price_analysis"""
    __tablename__ = "price_analysis"
    
    # Columns
    project_id: Mapped[str] = mapped_column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    task_id: Mapped[Optional[str]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    model_id: Mapped[Optional[str]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ai_models.id", ondelete="SET NULL"), nullable=True)
    avg_market_price: Mapped[Optional[Numeric]] = mapped_column(Numeric(precision=15, scale=2), nullable=True)
    min_price: Mapped[Optional[Numeric]] = mapped_column(Numeric(precision=15, scale=2), nullable=True)
    max_price: Mapped[Optional[Numeric]] = mapped_column(Numeric(precision=15, scale=2), nullable=True)
    price_std_dev: Mapped[Optional[Numeric]] = mapped_column(Numeric(precision=15, scale=2), nullable=True)
    recommended_price: Mapped[Optional[Numeric]] = mapped_column(Numeric(precision=15, scale=2), nullable=True)
    confidence_score: Mapped[Optional[Numeric]] = mapped_column(Numeric(precision=5, scale=4), nullable=True)
    price_by_brand: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    price_by_features: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    analysis_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    llm_analysis_result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    insights: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="price_analyses", lazy="select")
    task: Mapped["Task"] = relationship("Task", lazy="select")
    model: Mapped["AIModel"] = relationship("AIModel", back_populates="price_analyses", lazy="select")


class ProductComparison(Base):
    """Model cho bảng product_comparisons"""
    __tablename__ = "product_comparisons"
    
    # Columns
    project_id: Mapped[str] = mapped_column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    target_product_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    competitor_product_id: Mapped[Optional[str]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    similarity_score: Mapped[Optional[Numeric]] = mapped_column(Numeric(precision=5, scale=4), nullable=True)
    price_difference: Mapped[Optional[Numeric]] = mapped_column(Numeric(precision=15, scale=2), nullable=True)
    competitive_advantage: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    disadvantage: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="product_comparisons", lazy="select")
    competitor_product: Mapped["Product"] = relationship("Product", back_populates="product_comparisons", lazy="select")


# =============================================================================
# NEW MODELS FOR TRUST SCORE FEATURE (Phase 1)
# =============================================================================

class ProductReview(Base):
    """
    Model lưu trữ reviews được crawl từ các sàn TMĐT (Shopee, Lazada, Tiki).
    Mỗi review thuộc về một product.
    """
    __tablename__ = "product_reviews"
    
    # Foreign Keys
    product_id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey("products.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    crawl_session_id: Mapped[Optional[str]] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey("crawl_sessions.id", ondelete="SET NULL"), 
        nullable=True
    )
    
    # Reviewer Information
    reviewer_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    reviewer_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="ID của reviewer trên platform gốc"
    )
    
    # Review Content
    rating: Mapped[int] = mapped_column(Integer, nullable=False, comment="Điểm đánh giá 1-5")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Nội dung review")
    review_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Ngày đăng review trên platform"
    )
    
    # Platform Information
    platform: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="shopee/lazada/tiki"
    )
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Review Metadata
    is_verified_purchase: Mapped[bool] = mapped_column(
        Boolean, server_default='false', nullable=False, comment="Đã mua hàng verified"
    )
    helpful_count: Mapped[Optional[int]] = mapped_column(
        Integer, server_default='0', nullable=True, comment="Số lượt thấy hữu ích"
    )
    images: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="Danh sách URL ảnh review"
    )
    
    # Crawl Metadata
    crawled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default='now()', nullable=False
    )
    raw_data: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="Dữ liệu thô từ crawler để backup"
    )
    
    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="reviews", lazy="select")
    crawl_session: Mapped[Optional["CrawlSession"]] = relationship("CrawlSession", lazy="select")
    analysis: Mapped[Optional["ReviewAnalysis"]] = relationship(
        "ReviewAnalysis", back_populates="review", uselist=False, cascade="all, delete-orphan", lazy="select"
    )
    
    # Indexes
    __table_args__ = (
        Index('ix_product_reviews_review_date', 'review_date'),
        Index('ix_product_reviews_product_platform', 'product_id', 'platform'),
    )


class ReviewAnalysis(Base):
    """
    Model lưu kết quả phân tích từ AI models service.
    Mỗi review có tối đa 1 analysis (1-1 relationship).
    """
    __tablename__ = "review_analyses"
    
    # Foreign Key - 1:1 với ProductReview
    review_id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey("product_reviews.id", ondelete="CASCADE"), 
        nullable=False,
        unique=True,
        index=True
    )
    
    # Sentiment Analysis Results
    sentiment_label: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True, comment="positive/negative/neutral"
    )
    sentiment_score: Mapped[Numeric] = mapped_column(
        Numeric(precision=5, scale=4), nullable=False, comment="Score 0.0000 - 1.0000"
    )
    sentiment_confidence: Mapped[Numeric] = mapped_column(
        Numeric(precision=5, scale=4), nullable=False, comment="Độ tin cậy dự đoán"
    )
    
    # Spam Detection Results
    is_spam: Mapped[bool] = mapped_column(
        Boolean, nullable=False, index=True, comment="True nếu là spam"
    )
    spam_score: Mapped[Numeric] = mapped_column(
        Numeric(precision=5, scale=4), nullable=False, comment="Score 0.0000 - 1.0000"
    )
    spam_confidence: Mapped[Numeric] = mapped_column(
        Numeric(precision=5, scale=4), nullable=False, comment="Độ tin cậy dự đoán spam"
    )
    
    # Model Information
    sentiment_model_version: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="Version của sentiment model"
    )
    spam_model_version: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="Version của spam model"
    )
    
    # Analysis Metadata
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default='now()', nullable=False
    )
    analysis_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, 
        comment="Chi tiết: sentiment_raw_output, spam_features, processing_time_ms"
    )
    
    # Relationships
    review: Mapped["ProductReview"] = relationship("ProductReview", back_populates="analysis", lazy="select")


class ProductTrustScore(Base):
    """
    Model lưu chi tiết tính toán trust score cho mỗi product.
    Mỗi product có tối đa 1 trust score detail (1-1 relationship).
    """
    __tablename__ = "product_trust_scores"
    
    # Foreign Key - 1:1 với Product
    product_id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey("products.id", ondelete="CASCADE"), 
        nullable=False,
        unique=True,
        index=True
    )
    
    # Trust Score (0-100)
    trust_score: Mapped[Numeric] = mapped_column(
        Numeric(precision=5, scale=2), nullable=False, index=True, comment="Trust score 0.00 - 100.00"
    )
    
    # Review Statistics
    total_reviews: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default='0', comment="Tổng số reviews"
    )
    analyzed_reviews: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default='0', comment="Số reviews đã phân tích"
    )
    verified_reviews_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default='0', comment="Reviews đã xác thực mua hàng"
    )
    
    # Spam Statistics
    spam_reviews_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default='0', comment="Số reviews spam"
    )
    spam_percentage: Mapped[Numeric] = mapped_column(
        Numeric(precision=5, scale=2), nullable=False, server_default='0', comment="% spam"
    )
    
    # Sentiment Statistics
    positive_reviews_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default='0', comment="Reviews tích cực"
    )
    negative_reviews_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default='0', comment="Reviews tiêu cực"
    )
    neutral_reviews_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default='0', comment="Reviews trung lập"
    )
    average_sentiment_score: Mapped[Numeric] = mapped_column(
        Numeric(precision=5, scale=4), nullable=False, server_default='0', comment="Điểm cảm xúc trung bình"
    )
    
    # Quality Metrics
    review_quality_score: Mapped[Optional[Numeric]] = mapped_column(
        Numeric(precision=5, scale=2), nullable=True, comment="Điểm chất lượng reviews (0-100)"
    )
    engagement_score: Mapped[Optional[Numeric]] = mapped_column(
        Numeric(precision=5, scale=2), nullable=True, comment="Điểm tương tác (0-100)"
    )
    
    # Calculation Details
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default='now()', nullable=False
    )
    calculation_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        comment="Chi tiết công thức: formula_version, weights, component_scores"
    )
    
    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="trust_score_detail", lazy="select")
