from typing import Optional, List
from pydantic import BaseModel, Field


class ProductFilterCriteria(BaseModel):
    """Structured filter criteria extracted from user input"""
    
    # Rating filters
    min_rating: Optional[float] = Field(None, ge=0, le=5, description="Minimum rating score")
    max_rating: Optional[float] = Field(None, ge=0, le=5, description="Maximum rating score")
    
    # Review count filters
    min_review_count: Optional[int] = Field(None, ge=0, description="Minimum number of reviews")
    max_review_count: Optional[int] = Field(None, ge=0, description="Maximum number of reviews")
    
    # Price filters
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price in VND")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price in VND")
    
    # Platform & Seller filters
    platforms: Optional[List[str]] = Field(None, description="Filter by platforms: shopee, lazada, tiki")
    is_mall: Optional[bool] = Field(None, description="Only mall sellers")
    is_verified_seller: Optional[bool] = Field(None, description="Only verified sellers")
    
    # Keyword filters
    required_keywords: Optional[List[str]] = Field(None, description="Keywords that must appear in product name")
    excluded_keywords: Optional[List[str]] = Field(None, description="Keywords to exclude")
    
    # Sales & Trust filters
    min_sales_count: Optional[int] = Field(None, ge=0, description="Minimum sales count")
    min_trust_score: Optional[float] = Field(None, ge=0, le=100, description="Minimum trust score")
    
    # Trust badge filters
    trust_badge_types: Optional[List[str]] = Field(None, description="Trust badge types: TikiNOW, Yêu thích, etc.")
    
    # Brand filters
    required_brands: Optional[List[str]] = Field(None, description="Required brands")
    excluded_brands: Optional[List[str]] = Field(None, description="Excluded brands")
    
    # Location filters
    seller_locations: Optional[List[str]] = Field(None, description="Seller locations")

