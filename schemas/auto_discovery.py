from uuid import UUID
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from schemas.product_filter import ProductFilterCriteria


class AutoDiscoveryRequest(BaseModel):
    """Request schema for automated product discovery"""
    project_id: UUID
    user_input: str = Field(
        ..., 
        description="Natural language input. Examples: 'tìm kiếm cho tôi 2 sản phẩm mẫu dựa trên project của tôi, yêu cầu là có hơn 100 reviews, mall, và trên sàn lazada'"
    )


class AutoDiscoveryRequestLegacy(BaseModel):
    """Legacy request schema (for backward compatibility)"""
    project_id: UUID
    user_query: str = Field(..., description="Product search query (e.g., 'cà phê hòa tan')")
    filter_criteria: Optional[str] = Field(
        None, 
        description="Optional: Natural language filter criteria. Examples: 'rating 4.5+, review 100+, mall, max price 500000'. Leave null if no filtering needed."
    )
    max_products: int = Field(default=20, ge=1, le=100, description="Maximum number of products to import")


class AutoDiscoveryResponse(BaseModel):
    """Response schema for automated product discovery"""
    status: str = Field(..., description="success or error")
    message: str = Field(..., description="Response message")
    filter_criteria: Optional[Dict[str, Any]] = Field(None, description="Extracted filter criteria")
    products_found: int = Field(0, description="Total products found from crawl")
    products_filtered: int = Field(0, description="Products after filtering")
    products_imported: int = Field(0, description="Products successfully imported")
    imported_product_ids: List[UUID] = Field(default_factory=list, description="IDs of imported products")
    error_type: Optional[str] = Field(None, description="Error type if status is error")
    extracted_criteria: Optional[Dict[str, Any]] = Field(None, description="Extracted criteria if validation failed")
    suggested_platforms: Optional[List[str]] = Field(None, description="Suggested platforms if shopee is requested")


class AutoDiscoveryFlowRequest(BaseModel):
    """Request schema for detailed product analysis flow (Phase 2)"""
    project_id: UUID = Field(..., description="Project ID")
    products: List[Dict[str, Any]] = Field(
        ..., 
        description="List of products with review count config. Example: [{'product_id': 'uuid', 'review_count': 100}]"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "550e8400-e29b-41d4-a716-446655440000",
                "products": [
                    {"product_id": "550e8400-e29b-41d4-a716-446655440001", "review_count": 100},
                    {"product_id": "550e8400-e29b-41d4-a716-446655440002", "review_count": 90}
                ]
            }
        }

