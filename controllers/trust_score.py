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
)
from schemas.auth import TokenData
from schemas.trust_score import (
    ProductTrustScoreResponse,
    TrustScoreDetailResponse,
)
from services.core.product_trust_score import ProductTrustScoreService
from services.core.product import ProductService

router = APIRouter(prefix="/products", tags=["Trust Score"])


# =============================================================================
# TRUST SCORE ENDPOINTS
# =============================================================================

@router.get("/{product_id}/trust-score", response_model=ProductTrustScoreResponse)
def get_trust_score(
    product_id: UUID,
    trust_score_service: ProductTrustScoreService = Depends(get_product_trust_score_service),
    product_service: ProductService = Depends(get_product_service),
    token: TokenData = Depends(verify_token),
):
    """
    Lấy Trust Score của một product.
    
    Returns trust score cơ bản với các thống kê.
    """
    # Verify product exists
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
    """
    Lấy Trust Score với breakdown chi tiết.
    
    Returns:
    - Trust score tổng
    - Breakdown từng component (sentiment, spam, volume, verification)
    - Contribution của mỗi component
    """
    # Verify product exists
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
    token: TokenData = Depends(verify_token),
):
    """
    Tính toán (hoặc tính lại) Trust Score cho một product.
    
    Yêu cầu product phải có reviews và reviews phải được phân tích trước.
    
    Formula:
    - Sentiment Factor: 40%
    - Spam Factor: 30%
    - Volume Factor: 20%
    - Verification Factor: 10%
    """
    # Verify product exists
    product = product_service.get(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    try:
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
    """Xóa Trust Score của một product (để tính lại từ đầu)"""
    product = product_service.get(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    deleted = trust_score_service.delete_trust_score(product_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trust score not found for this product"
        )


# =============================================================================
# TOP TRUSTED PRODUCTS
# =============================================================================

@router.get("/top-trusted", tags=["Trust Score"])
def get_top_trusted_products(
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    limit: int = Query(10, ge=1, le=50, description="Number of products to return"),
    trust_score_service: ProductTrustScoreService = Depends(get_product_trust_score_service),
    token: TokenData = Depends(verify_token),
):
    """
    Lấy danh sách products có Trust Score cao nhất.
    
    - **project_id**: Lọc theo project (optional)
    - **limit**: Số lượng products trả về (max 50)
    """
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
    """
    Lấy danh sách products trong khoảng Trust Score.
    
    Ví dụ: Lấy products có score từ 80-100 (high trust)
    """
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
