"""
Schemas cho Review Analysis.
Pydantic Schemas cho Request/Response models.
"""
from typing import Optional, Dict, Any, Annotated
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, Field


class ReviewAnalysisBase(BaseModel):
    """Base schema cho ReviewAnalysis"""
    sentiment_label: Annotated[str, Field(max_length=20, description="positive/negative/neutral")]
    sentiment_score: Annotated[Decimal, Field(ge=0, le=1, description="Score 0.0000 - 1.0000")]
    sentiment_confidence: Annotated[Decimal, Field(ge=0, le=1)]
    is_spam: bool
    spam_score: Annotated[Decimal, Field(ge=0, le=1)]
    spam_confidence: Annotated[Decimal, Field(ge=0, le=1)]
    sentiment_model_version: Optional[Annotated[str, Field(max_length=50)]] = None
    spam_model_version: Optional[Annotated[str, Field(max_length=50)]] = None


class ReviewAnalysisCreate(ReviewAnalysisBase):
    """Schema để tạo analysis mới"""
    review_id: UUID
    analysis_metadata: Optional[Dict[str, Any]] = None


class ReviewAnalysisUpdate(BaseModel):
    """Schema để cập nhật analysis"""
    sentiment_label: Optional[Annotated[str, Field(max_length=20)]] = None
    sentiment_score: Optional[Annotated[Decimal, Field(ge=0, le=1)]] = None
    sentiment_confidence: Optional[Annotated[Decimal, Field(ge=0, le=1)]] = None
    is_spam: Optional[bool] = None
    spam_score: Optional[Annotated[Decimal, Field(ge=0, le=1)]] = None
    spam_confidence: Optional[Annotated[Decimal, Field(ge=0, le=1)]] = None
    sentiment_model_version: Optional[Annotated[str, Field(max_length=50)]] = None
    spam_model_version: Optional[Annotated[str, Field(max_length=50)]] = None
    analysis_metadata: Optional[Dict[str, Any]] = None


class ReviewAnalysisResponse(ReviewAnalysisBase):
    """Schema cho response của analysis"""
    id: UUID
    review_id: UUID
    analyzed_at: datetime
    analysis_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReviewAnalysisListResponse(BaseModel):
    """Schema cho list analyses response với pagination"""
    items: list[ReviewAnalysisResponse]
    total: int
    skip: int
    limit: int

    class Config:
        from_attributes = True


class AnalysisStatisticsResponse(BaseModel):
    """Schema cho thống kê analysis của một product"""
    product_id: UUID
    total_analyzed: int
    sentiment_counts: Dict[str, int]  # {"positive": x, "negative": y, "neutral": z}
    spam_count: int
    spam_percentage: float
    average_sentiment_score: float

    class Config:
        from_attributes = True
