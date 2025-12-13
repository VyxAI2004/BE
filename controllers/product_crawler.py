from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.dependencies.db import get_db
from core.dependencies.auth import verify_token
from core.dependencies.services import get_crawler_service
from schemas.auth import TokenData
from schemas.product_crawler import CrawlSearchRequest, CrawlReviewsRequest
from services.features.product_intelligence.crawler.crawler_service import CrawlerService

router = APIRouter(prefix="/products/crawler", tags=["Product Crawler"])

@router.post("/search")
def crawl_search_results(
    request: CrawlSearchRequest,
    service: CrawlerService = Depends(get_crawler_service),
    token: TokenData = Depends(verify_token),
) -> List[str]:
    """
    Step 1: Crawl product list from search URL.
    Returns list of product URLs found.
    """
    try:
        result = service.crawl_search_page(
            project_id=request.project_id,
            search_url=request.search_url,
            max_products=request.max_products
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search crawl failed: {str(e)}")

@router.post("/reviews")
def crawl_product_reviews(
    request: CrawlReviewsRequest,
    service: CrawlerService = Depends(get_crawler_service),
    token: TokenData = Depends(verify_token),
):
    """
    Step 2: Crawl reviews for a specific product.
    """
    try:
        result = service.crawl_product_reviews(
            product_id=request.product_id,
            review_limit=request.review_limit
        )
        if result.status == "failed":
            raise HTTPException(status_code=400, detail=result.message)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review crawl failed: {str(e)}")
