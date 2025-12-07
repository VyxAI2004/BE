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

# Scraper Output Schemas
class CrawledProductItem(BaseModel):
    name: str
    price: Any # Can be float or str depending on scraper, consumer should clean
    link: str
    img: Optional[str] = None
    sold: Optional[Any] = None # Can be str "1.2k" or int
    rating: Optional[float] = None
    platform: Optional[str] = None # Added for convenience

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
