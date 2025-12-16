"""
Controller cho Trust Score - API Endpoints.
Quản lý tính toán và truy vấn Trust Score của products.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from core.dependencies.auth import verify_token
from core.dependencies.services import (
    get_product_trust_score_service,
    get_product_service,
    get_product_review_service,
    get_review_analysis_service,
    get_product_analytics_service,
    get_product_analytics_cache_service,
)
from schemas.auth import TokenData
from schemas.trust_score import (
    ProductTrustScoreResponse,
    TrustScoreDetailResponse,
)
from schemas.product_analytics import ProductAnalyticsResponse
from services.core.product_trust_score import ProductTrustScoreService
from services.core.product import ProductService
from services.core.product_review import ProductReviewService
from services.core.review_analysis import ReviewAnalysisService
from services.core.product_analytics import ProductAnalyticsService
from services.core.product_analytics_service import ProductAnalyticsCacheService

router = APIRouter(prefix="/products", tags=["Trust Score"])

@router.get("/{product_id}/trust-score", response_model=ProductTrustScoreResponse)
def get_trust_score(
    product_id: UUID,
    trust_score_service: ProductTrustScoreService = Depends(get_product_trust_score_service),
    product_service: ProductService = Depends(get_product_service),
    token: TokenData = Depends(verify_token),
):

    product = product_service.get(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    trust_score = trust_score_service.get_by_product(product_id)
    if not trust_score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Trust score not calculated yet. Call POST /trust-score/calculate first."
        )
    
    return trust_score


@router.get("/{product_id}/trust-score/detail", response_model=TrustScoreDetailResponse)
def get_trust_score_detail(
    product_id: UUID,
    trust_score_service: ProductTrustScoreService = Depends(get_product_trust_score_service),
    product_service: ProductService = Depends(get_product_service),
    token: TokenData = Depends(verify_token),
):

    product = product_service.get(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    detail = trust_score_service.get_trust_score_detail(product_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Trust score not calculated yet. Call POST /trust-score/calculate first."
        )
    
    return detail


@router.post("/{product_id}/trust-score/calculate", response_model=ProductTrustScoreResponse)
def calculate_trust_score(
    product_id: UUID,
    trust_score_service: ProductTrustScoreService = Depends(get_product_trust_score_service),
    product_service: ProductService = Depends(get_product_service),
    review_service: ProductReviewService = Depends(get_product_review_service),
    analysis_service: ReviewAnalysisService = Depends(get_review_analysis_service),
    token: TokenData = Depends(verify_token),
):

    product = product_service.get(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    try:
        # Auto-analyze unanalyzed reviews before calculating trust score
        unanalyzed = review_service.get_unanalyzed_reviews(product_id=product_id, limit=1000)
        
        if unanalyzed:
            # Analyze unanalyzed reviews
            analyses = analysis_service.analyze_product_reviews(product_id)
        
        # Re-analyze reviews with fallback scores (0.5) - indicates model error
        fallback_analyses = analysis_service.reanalyze_fallback_reviews(product_id)
        
        # Calculate trust score
        trust_score = trust_score_service.calculate_trust_score(product_id)
        if not trust_score:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot calculate trust score. Product has no reviews."
            )
        return trust_score
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating trust score: {str(e)}"
        )


@router.delete("/{product_id}/trust-score", status_code=status.HTTP_204_NO_CONTENT)
def delete_trust_score(
    product_id: UUID,
    trust_score_service: ProductTrustScoreService = Depends(get_product_trust_score_service),
    product_service: ProductService = Depends(get_product_service),
    token: TokenData = Depends(verify_token),
):
    product = product_service.get(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    deleted = trust_score_service.delete_trust_score(product_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trust score not found for this product"
        )

@router.get("/top-trusted", tags=["Trust Score"])
def get_top_trusted_products(
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    limit: int = Query(10, ge=1, le=50, description="Number of products to return"),
    trust_score_service: ProductTrustScoreService = Depends(get_product_trust_score_service),
    token: TokenData = Depends(verify_token),
):

    top_products = trust_score_service.get_top_trusted(
        project_id=project_id,
        limit=limit
    )
    
    return {
        "items": top_products,
        "total": len(top_products),
        "limit": limit
    }


@router.get("/by-score-range", tags=["Trust Score"])
def get_products_by_score_range(
    min_score: float = Query(0, ge=0, le=100, description="Minimum trust score"),
    max_score: float = Query(100, ge=0, le=100, description="Maximum trust score"),
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    trust_score_service: ProductTrustScoreService = Depends(get_product_trust_score_service),
    token: TokenData = Depends(verify_token),
):
    products = trust_score_service.get_by_score_range(
        min_score=min_score,
        max_score=max_score,
        project_id=project_id,
        skip=skip,
        limit=limit
    )
    
    return {
        "items": products,
        "total": len(products),
        "min_score": min_score,
        "max_score": max_score,
        "skip": skip,
        "limit": limit
    }


@router.get("/{product_id}/analytics", response_model=ProductAnalyticsResponse, tags=["Product Analytics"])
def get_product_analytics(
    product_id: UUID,
    refresh: bool = Query(False, description="Force refresh analytics (bypass cache)"),
    analytics_cache_service: ProductAnalyticsCacheService = Depends(get_product_analytics_cache_service),
    product_service: ProductService = Depends(get_product_service),
    token: TokenData = Depends(verify_token),
):
    """
    Phân tích sản phẩm bằng LLM dựa trên reviews và trust score.
    Yêu cầu trust score đã được tính toán trước.
    
    - Nếu đã có analytics trong cache, trả về từ cache (tránh tốn chi phí LLM)
    - Nếu chưa có hoặc refresh=True, phân tích mới và lưu vào cache
    """
    import logging
    logger = logging.getLogger(__name__)
    
    product = product_service.get(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    try:
        # Get project to get assigned_model_id
        project_assigned_model_id = None
        try:
            project = getattr(product, 'project', None)
            if project:
                project_assigned_model_id = getattr(project, 'assigned_model_id', None)
                logger.info(f"Project assigned_model_id: {project_assigned_model_id} for product {product_id}")
        except Exception as e:
            logger.warning(f"Could not load project relationship for product {product_id}: {e}")
        
        # Get user_id from token
        user_id = token.user_id
        
        # Get from cache or analyze
        analytics = analytics_cache_service.get_or_analyze(
            product_id=product_id,
            user_id=user_id,
            project_assigned_model_id=project_assigned_model_id,
            force_refresh=refresh
        )
        
        logger.info(f"Analytics {'from cache' if analytics.get('from_cache') else 'generated'} for product {product_id}")
        return ProductAnalyticsResponse(**analytics)
    except ValueError as e:
        logger.warning(f"Validation error for product {product_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error analyzing product {product_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing product: {str(e)}"
        )
