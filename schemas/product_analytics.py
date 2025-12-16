"""
Schemas cho Product Analytics.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class TrustScoreAnalysis(BaseModel):
    """Phân tích trust score"""
    interpretation: str = Field(..., description="Giải thích ý nghĩa của trust score")
    strengths: List[str] = Field(default_factory=list, description="Điểm mạnh")
    weaknesses: List[str] = Field(default_factory=list, description="Điểm yếu")


class ReviewInsights(BaseModel):
    """Insights từ reviews"""
    sentiment_overview: str = Field(..., description="Tổng quan sentiment")
    key_positive_themes: List[str] = Field(default_factory=list, description="Chủ đề tích cực")
    key_negative_themes: List[str] = Field(default_factory=list, description="Chủ đề tiêu cực")
    spam_concerns: str = Field(..., description="Đánh giá về spam")


class RiskAssessment(BaseModel):
    """Đánh giá rủi ro"""
    overall_risk: str = Field(..., description="Mức độ rủi ro: low|medium|high")
    risk_factors: List[str] = Field(default_factory=list, description="Các yếu tố rủi ro")
    confidence_level: str = Field(..., description="Độ tin cậy của phân tích")


class ProductAnalyticsAnalysis(BaseModel):
    """Kết quả phân tích từ LLM"""
    summary: str = Field(..., description="Tóm tắt tổng quan")
    trust_score_analysis: TrustScoreAnalysis
    review_insights: ReviewInsights
    recommendations: List[str] = Field(default_factory=list, description="Khuyến nghị")
    risk_assessment: RiskAssessment


class ProductAnalyticsMetadata(BaseModel):
    """Metadata của phân tích"""
    model_used: str = Field(..., description="Model LLM được sử dụng")
    total_reviews_analyzed: int = Field(..., description="Tổng số reviews được phân tích")
    sample_reviews_count: int = Field(..., description="Số reviews mẫu")
    error: Optional[str] = Field(None, description="Lỗi nếu có")


class ProductAnalyticsBase(BaseModel):
    """Base schema cho ProductAnalytics"""
    product_id: UUID
    analysis_data: Dict[str, Any] = Field(..., description="Kết quả phân tích từ LLM")
    model_used: str = Field(..., description="LLM model được sử dụng")
    total_reviews_analyzed: int = Field(..., description="Tổng số reviews được phân tích")
    sample_reviews_count: int = Field(..., description="Số reviews mẫu")


class ProductAnalyticsCreate(ProductAnalyticsBase):
    """Schema để tạo analytics mới"""
    pass


class ProductAnalyticsUpdate(BaseModel):
    """Schema để cập nhật analytics"""
    analysis_data: Optional[Dict[str, Any]] = None
    model_used: Optional[str] = None
    total_reviews_analyzed: Optional[int] = None
    sample_reviews_count: Optional[int] = None


class ProductAnalyticsResponse(BaseModel):
    """Response schema cho product analytics"""
    product_id: UUID
    analysis: Dict[str, Any] = Field(..., description="Kết quả phân tích từ LLM")
    metadata: ProductAnalyticsMetadata
    generated_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Thời gian tạo")

    class Config:
        from_attributes = True
