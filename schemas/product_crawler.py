from uuid import UUID
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# Request Schemas
class CrawlSearchRequest(BaseModel):
    project_id: UUID
    search_url: str = Field(..., description="URL to crawl products from (e.g. Shopee search URL)")
    max_products: int = Field(default=10, ge=1, le=50)

class CrawlReviewsRequest(BaseModel):
    product_id: UUID
    review_limit: int = Field(default=30, ge=0, le=100)

# Respone Schemas
class CrawlProductReviewsResponse(BaseModel):
    product_id: Optional[UUID] = None
    reviews_crawled: int = 0
    status: str
    message: Optional[str] = None

# Scraper Output Schemas
class CrawledProductItem(BaseModel):
    name: str
    price: Any # Can be float or str depending on scraper, consumer should clean
    link: str
    img: Optional[str] = None
    sold: Optional[Any] = None # Can be str "1.2k" or int
    rating: Optional[float] = None
    platform: Optional[str] = None # Added for convenience
    review_count: Optional[int] = None # Number of reviews

class CrawledReview(BaseModel):
    author: str
    rating: int
    content: str
    time: Optional[str] = None
    helpful_count: int = 0
    images: List[str] = []
    seller_respond: Optional[str] = None

class CrawledProductDetail(BaseModel):
    link: str
    category: str = ""
    description: str = ""
    detailed_rating: Dict[str, Any] = {} # e.g. {"5_star": 100}
    total_rating: int = 0
    comments: List[CrawledReview] = []


class CrawledProductItemExtended(BaseModel):
    """Extended product data from crawler with all fields"""
    
    # Basic Info
    platform: str  # tiki, lazada, shopee
    product_name: str
    product_url: str
    
    # Pricing
    price_current: float
    price_original: Optional[float] = None
    discount_rate: Optional[float] = None
    
    # Ratings & Reviews
    rating_score: Optional[float] = None  # 0-5
    review_count: Optional[int] = None
    sales_count: Optional[int] = None
    
    # Seller Info
    is_mall: bool = False
    is_verified_seller: bool = False
    seller_location: Optional[str] = None
    brand: Optional[str] = None
    
    # Trust & Quality
    trust_badge_type: Optional[str] = None  # TikiNOW, Yêu thích, etc.
    trust_score: Optional[float] = None  # 0-100
    
    # Keywords & Metadata
    keywords_in_title: List[str] = []
    category: Optional[str] = None
    subcategory: Optional[str] = None
    
    # Images
    image_urls: List[str] = []
    
    # Additional metadata
    metadata: Dict[str, Any] = {}