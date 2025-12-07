"""
Schemas cho Product Review.
Pydantic Schemas cho Request/Response models.
"""
from typing import Optional, Dict, Any, List, Annotated, TYPE_CHECKING
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .review_analysis import ReviewAnalysisResponse


class ProductReviewBase(BaseModel):
    """Base schema cho ProductReview"""
    reviewer_name: Optional[Annotated[str, Field(max_length=200)]] = None
    reviewer_id: Optional[Annotated[str, Field(max_length=100)]] = None
    rating: Annotated[int, Field(ge=1, le=5, description="Điểm đánh giá 1-5")]
    content: Optional[str] = None
    review_date: Optional[datetime] = None
    platform: Annotated[str, Field(max_length=50, description="shopee/lazada/tiki")]
    source_url: Optional[Annotated[str, Field(max_length=500)]] = None
    is_verified_purchase: bool = False
    helpful_count: Optional[int] = 0
    images: Optional[Dict[str, Any]] = None


class ProductReviewCreate(ProductReviewBase):
    """Schema để tạo review mới"""
    product_id: UUID
    crawl_session_id: Optional[UUID] = None
    raw_data: Optional[Dict[str, Any]] = None


class ProductReviewUpdate(BaseModel):
    """Schema để cập nhật review"""
    reviewer_name: Optional[Annotated[str, Field(max_length=200)]] = None
    reviewer_id: Optional[Annotated[str, Field(max_length=100)]] = None
    rating: Optional[Annotated[int, Field(ge=1, le=5)]] = None
    content: Optional[str] = None
    review_date: Optional[datetime] = None
    is_verified_purchase: Optional[bool] = None
    helpful_count: Optional[int] = None
    images: Optional[Dict[str, Any]] = None


class ProductReviewResponse(ProductReviewBase):
    """Schema cho response của review"""
    id: UUID
    product_id: UUID
    crawl_session_id: Optional[UUID] = None
    crawled_at: datetime
    created_at: datetime
    updated_at: datetime
    # Include analysis if loaded (forward reference)
    analysis: Optional["ReviewAnalysisResponse"] = None

    class Config:
        from_attributes = True


class ProductReviewListResponse(BaseModel):
    """Schema cho list reviews response với pagination"""
    items: List[ProductReviewResponse]
    total: int
    skip: int
    limit: int

    class Config:
        from_attributes = True


# Forward reference update - will be called after ReviewAnalysisResponse is imported
def _rebuild_models():
    from .review_analysis import ReviewAnalysisResponse
    ProductReviewResponse.model_rebuild()

_rebuild_models()
