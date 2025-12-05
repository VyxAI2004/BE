from typing import List, Optional, Dict, Union, Any
from uuid import UUID
from pydantic import BaseModel, Field
# Define Pydantic models for Structured Output
class ProductItem(BaseModel):
    name: str = Field(description="Full name of the product")
    price: float = Field(description="Price in VND")
    url: str = Field(description="Direct URL to the product")
    rating: float = Field(description="Product rating (0-5)")
    sold: int = Field(description="Number of items sold")
    shop_type: str = Field(description="Shop type (e.g., Shopee Mall, Shop Yêu Thích+)")
    reason: str = Field(description="Reason for recommending this product")

class PriceRange(BaseModel):
    min: float
    average: float
    max: float

class SearchResponse(BaseModel):
    analysis: str = Field(description="Market analysis and price trends")
    products: List[ProductItem]
    price_range: PriceRange

class RankedProduct(BaseModel):
    name: str
    price: float
    url: str
    rating: float
    sold: int
    reason: str

class RankingResponse(BaseModel):
    analysis: str
    top_products: List[RankedProduct]


# ==================== 2-STEP SEARCH FLOW SCHEMAS ====================

# Step 1: Product Analysis
class AnalyzedProduct(BaseModel):
    """Product from Step 1: Analysis phase"""
    name: str = Field(description="Tên đầy đủ và chính xác của sản phẩm")
    estimated_price: float = Field(description="Giá ước tính (VND)")
    features: List[str] = Field(description="Danh sách tính năng nổi bật")
    reason: str = Field(description="Lý do đề xuất sản phẩm này")

class ProductAnalysisResponse(BaseModel):
    """Response schema for Step 1: Product Analysis"""
    analysis: str = Field(description="Nhận định chung về thị trường và xu hướng")
    products: List[AnalyzedProduct] = Field(description="Danh sách 5-10 sản phẩm nổi bật")


# Step 2: Link Generation (Single Platform)
class ProductWithLink(BaseModel):
    """Product with single platform link (for shopee/lazada/tiki)"""
    name: str = Field(description="Tên sản phẩm")
    estimated_price: float = Field(description="Giá ước tính (VND)")
    url: str = Field(description="Link tìm kiếm trên platform được chọn")

class ProductLinksResponse(BaseModel):
    """Response schema for Step 2: Link Generation (single platform)"""
    products: List[ProductWithLink] = Field(description="Danh sách sản phẩm với links")


# Step 2: Link Generation (Multi-Platform)
class ProductUrls(BaseModel):
    """URLs for all platforms"""
    shopee: str = Field(description="Shopee search link")
    lazada: str = Field(description="Lazada search link")
    tiki: str = Field(description="Tiki search link")

class ProductWithMultiLinks(BaseModel):
    """Product with links for all platforms (for platform='all')"""
    name: str = Field(description="Tên sản phẩm")
    estimated_price: float = Field(description="Giá ước tính (VND)")
    urls: ProductUrls = Field(description="Links cho tất cả các platforms")

class ProductMultiLinksResponse(BaseModel):
    """Response schema for Step 2: Link Generation (all platforms)"""
    products: List[ProductWithMultiLinks] = Field(description="Danh sách sản phẩm với multi-platform links")


# ==================== INTERNAL SCHEMAS ====================

class ProjectInfoInput(BaseModel):
    """Input schema for project information"""
    id: UUID
    name: str
    target_product_name: str
    target_budget_range: Optional[float] = None
    description: Optional[str] = None

class AnalysisResult(BaseModel):
    """Result from Step 1: Product Analysis"""
    analysis: str
    products: List[AnalyzedProduct]

class SearchHandlerResult(BaseModel):
    """Result from SearchHandler.search()"""
    ai_result: Dict[str, Any]  # Can be AnalysisResult or error dict
    shopee_products: List[Union[ProductWithLink, ProductWithMultiLinks]]
    grounding_metadata: Dict[str, Any]  # Will be converted to GroundingMetadataFull


# ==================== FINAL API RESPONSE SCHEMAS ====================

class ProjectInfo(BaseModel):
    """Project information in response"""
    id: str
    name: str
    description: Optional[str] = None
    target_product: str
    budget: Optional[float] = None
    platform: str = "all"

class GroundingMetadata(BaseModel):
    """Metadata from Google Search Grounding"""
    grounding_supports: int = 0
    search_entry_point: Optional[str] = None

class GroundingMetadataFull(BaseModel):
    """Full grounding metadata for both steps"""
    step1_analysis: Optional[GroundingMetadata] = None
    step2_links: Optional[GroundingMetadata] = None

class ProductSearchResponse(BaseModel):
    """Final API response for product search"""
    project_info: ProjectInfo
    ai_analysis: str
    recommended_products: List[Union[ProductWithLink, ProductWithMultiLinks]]
    all_products: List[Union[ProductWithLink, ProductWithMultiLinks]]
    total_found: int
    grounding_metadata: GroundingMetadataFull
    note: str