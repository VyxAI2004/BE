from typing import Optional, Dict, Any, List, Annotated
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class ProductBase(BaseModel):
    """Base schema for Product model"""
    name: Annotated[str, Field(min_length=1, max_length=500)]
    company: Optional[Annotated[str, Field(max_length=200)]] = None
    brand: Optional[Annotated[str, Field(max_length=100)]] = None
    category: Optional[Annotated[str, Field(max_length=100)]] = None
    subcategory: Optional[Annotated[str, Field(max_length=100)]] = None
    platform: Annotated[str, Field(max_length=50)]
    current_price: float
    original_price: Optional[float] = None
    discount_rate: Optional[float] = None
    currency: Optional[Annotated[str, Field(max_length=10)]] = "VND"
    specifications: Optional[Dict[str, Any]] = None
    features: Optional[str] = None
    images: Optional[Dict[str, Any]] = None
    url: str
    is_verified: Optional[bool] = False
    data_source: Optional[str] = None

class ProductCreate(ProductBase):
    """Schema for creating product"""
    project_id: UUID
    product_source_id: Optional[UUID] = None
    crawl_session_id: Optional[UUID] = None
    # Allow minimal creation
    platform: Optional[Annotated[str, Field(max_length=50)]] = None
    current_price: Optional[float] = 0.0

class ProductUpdate(BaseModel):
    """Schema for updating product information"""
    name: Optional[Annotated[str, Field(min_length=1, max_length=500)]] = None
    company: Optional[Annotated[str, Field(max_length=200)]] = None
    brand: Optional[Annotated[str, Field(max_length=100)]] = None
    category: Optional[Annotated[str, Field(max_length=100)]] = None
    subcategory: Optional[Annotated[str, Field(max_length=100)]] = None
    platform: Optional[Annotated[str, Field(max_length=50)]] = None
    current_price: Optional[float] = None
    original_price: Optional[float] = None
    discount_rate: Optional[float] = None
    currency: Optional[Annotated[str, Field(max_length=10)]] = None
    specifications: Optional[Dict[str, Any]] = None
    features: Optional[str] = None
    images: Optional[Dict[str, Any]] = None
    url: Optional[str] = None
    is_verified: Optional[bool] = None
    data_source: Optional[str] = None
    trust_score: Optional[float] = None

class ProductResponse(ProductBase):
    """Schema for product response"""
    id: UUID
    project_id: UUID
    product_source_id: Optional[UUID] = None
    crawl_session_id: Optional[UUID] = None
    average_rating: Optional[float] = None
    review_count: Optional[int] = None
    sold_count: Optional[int] = None
    collected_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    trust_score: Optional[float] = None

    class Config:
        from_attributes = True

class ProductListResponse(BaseModel):
    """Schema for list products response"""
    items: List[ProductResponse]
    total: int
    skip: int
    limit: int

    class Config:
        from_attributes = True
