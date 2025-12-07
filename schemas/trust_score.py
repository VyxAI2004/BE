"""
Schemas cho Product Trust Score.
Pydantic Schemas cho Request/Response models.
"""
from typing import Optional, Dict, Any, List, Annotated
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, Field


class ProductTrustScoreBase(BaseModel):
    """Base schema cho ProductTrustScore"""
    trust_score: Annotated[Decimal, Field(ge=0, le=100, description="Trust score 0-100")]
    total_reviews: int = 0
    analyzed_reviews: int = 0
    verified_reviews_count: int = 0
    spam_reviews_count: int = 0
    spam_percentage: Decimal = Decimal("0")
    positive_reviews_count: int = 0
    negative_reviews_count: int = 0
    neutral_reviews_count: int = 0
    average_sentiment_score: Decimal = Decimal("0")
    review_quality_score: Optional[Decimal] = None
    engagement_score: Optional[Decimal] = None


class ProductTrustScoreCreate(ProductTrustScoreBase):
    """Schema để tạo trust score mới"""
    product_id: UUID
    calculation_metadata: Optional[Dict[str, Any]] = None


class ProductTrustScoreUpdate(BaseModel):
    """Schema để cập nhật trust score"""
    trust_score: Optional[Annotated[Decimal, Field(ge=0, le=100)]] = None
    total_reviews: Optional[int] = None
    analyzed_reviews: Optional[int] = None
    verified_reviews_count: Optional[int] = None
    spam_reviews_count: Optional[int] = None
    spam_percentage: Optional[Decimal] = None
    positive_reviews_count: Optional[int] = None
    negative_reviews_count: Optional[int] = None
    neutral_reviews_count: Optional[int] = None
    average_sentiment_score: Optional[Decimal] = None
    review_quality_score: Optional[Decimal] = None
    engagement_score: Optional[Decimal] = None
    calculation_metadata: Optional[Dict[str, Any]] = None


class ProductTrustScoreResponse(ProductTrustScoreBase):
    """Schema cho response của trust score"""
    id: UUID
    product_id: UUID
    calculated_at: datetime
    calculation_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TrustScoreBreakdown(BaseModel):
    """Schema cho breakdown chi tiết của mỗi component"""
    factor: float
    weight: float
    contribution: float
    details: Dict[str, Any]


class TrustScoreDetailResponse(BaseModel):
    """Schema cho response trust score với breakdown chi tiết"""
    product_id: UUID
    trust_score: float
    breakdown: Dict[str, TrustScoreBreakdown]
    total_reviews: int
    analyzed_reviews: int
    calculated_at: datetime

    class Config:
        from_attributes = True


class TrustScoreListResponse(BaseModel):
    """Schema cho list trust scores response"""
    items: List[ProductTrustScoreResponse]
    total: int
    limit: int

    class Config:
        from_attributes = True
