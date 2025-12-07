"""
Controller cho Review Analysis - API Endpoints.
Quản lý phân tích AI của reviews.
"""
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from core.dependencies.auth import verify_token
from core.dependencies.services import (
    get_review_analysis_service,
    get_product_review_service,
    get_product_service,
)
from schemas.auth import TokenData
from schemas.review_analysis import (
    ReviewAnalysisCreate,
    ReviewAnalysisUpdate,
    ReviewAnalysisResponse,
    ReviewAnalysisListResponse,
    AnalysisStatisticsResponse,
)
from services.core.review_analysis import ReviewAnalysisService
from services.core.product_review import ProductReviewService
from services.core.product import ProductService

router = APIRouter(prefix="/products/{product_id}/analyses", tags=["Review Analysis"])


# =============================================================================
# REVIEW ANALYSIS CRUD
# =============================================================================

@router.get("/", response_model=ReviewAnalysisListResponse)
def get_product_analyses(
    product_id: UUID,
    sentiment_label: Optional[str] = Query(None, description="Filter by sentiment: positive, negative, neutral"),
    is_spam: Optional[bool] = Query(None, description="Filter by spam status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    analysis_service: ReviewAnalysisService = Depends(get_review_analysis_service),
    product_service: ProductService = Depends(get_product_service),
    token: TokenData = Depends(verify_token),
):
    """
    Lấy danh sách AI analyses của tất cả reviews thuộc một product.
    
    - **sentiment_label**: Lọc theo sentiment (positive/negative/neutral)
    - **is_spam**: Lọc theo trạng thái spam
    """
    # Verify product exists
    product = product_service.get(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    analyses = analysis_service.get_by_product(
        product_id=product_id,
        skip=skip,
        limit=limit
    )
    
    # Apply additional filters if needed
    if sentiment_label:
        analyses = [a for a in analyses if a.sentiment_label == sentiment_label]
    if is_spam is not None:
        analyses = [a for a in analyses if a.is_spam == is_spam]
    
    return {
        "items": analyses,
        "total": len(analyses),
        "skip": skip,
        "limit": limit
    }


@router.get("/statistics", response_model=AnalysisStatisticsResponse)
def get_analysis_statistics(
    product_id: UUID,
    analysis_service: ReviewAnalysisService = Depends(get_review_analysis_service),
    product_service: ProductService = Depends(get_product_service),
    token: TokenData = Depends(verify_token),
):
    """
    Lấy thống kê AI analysis của một product.
    
    Returns:
    - Tổng số reviews đã phân tích
    - Phân bố sentiment (positive/negative/neutral)
    - Số lượng và tỷ lệ spam
    - Điểm sentiment trung bình
    """
    # Verify product exists
    product = product_service.get(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    stats = analysis_service.get_statistics(product_id)
    
    return {
        "product_id": product_id,
        "total_analyzed": stats["total_analyzed"],
        "sentiment_counts": stats["sentiment_counts"],
        "spam_count": stats["spam_count"],
        "spam_percentage": stats["spam_percentage"],
        "average_sentiment_score": stats["average_sentiment_score"]
    }


@router.get("/{analysis_id}", response_model=ReviewAnalysisResponse)
def get_analysis_detail(
    product_id: UUID,
    analysis_id: UUID,
    analysis_service: ReviewAnalysisService = Depends(get_review_analysis_service),
    product_service: ProductService = Depends(get_product_service),
    token: TokenData = Depends(verify_token),
):
    """Lấy chi tiết một analysis"""
    # Verify product exists
    product = product_service.get(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    analysis = analysis_service.get(analysis_id)
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    
    return analysis


@router.post("/", response_model=ReviewAnalysisResponse, status_code=status.HTTP_201_CREATED)
def create_analysis(
    product_id: UUID,
    payload: ReviewAnalysisCreate,
    analysis_service: ReviewAnalysisService = Depends(get_review_analysis_service),
    review_service: ProductReviewService = Depends(get_product_review_service),
    product_service: ProductService = Depends(get_product_service),
    token: TokenData = Depends(verify_token),
):
    """
    Tạo AI analysis cho một review.
    
    Nếu review đã có analysis, sẽ update thay vì tạo mới (upsert).
    Thường được gọi từ AI service, không phải user trực tiếp.
    """
    # Verify product exists
    product = product_service.get(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    # Verify review exists and belongs to product
    review = review_service.get(payload.review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    
    if review.product_id != product_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Review does not belong to this product"
        )
    
    return analysis_service.create_analysis(payload)


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def bulk_create_analyses(
    product_id: UUID,
    payload: List[ReviewAnalysisCreate],
    analysis_service: ReviewAnalysisService = Depends(get_review_analysis_service),
    product_service: ProductService = Depends(get_product_service),
    token: TokenData = Depends(verify_token),
):
    """
    Tạo nhiều AI analyses cùng lúc (batch processing).
    
    Dùng cho việc phân tích hàng loạt reviews sau khi crawl.
    """
    # Verify product exists
    product = product_service.get(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    try:
        analyses = analysis_service.bulk_create_analyses(payload)
        return {
            "created": len(analyses),
            "items": analyses
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating analyses: {str(e)}"
        )


@router.put("/{analysis_id}", response_model=ReviewAnalysisResponse)
def update_analysis(
    product_id: UUID,
    analysis_id: UUID,
    payload: ReviewAnalysisUpdate,
    analysis_service: ReviewAnalysisService = Depends(get_review_analysis_service),
    product_service: ProductService = Depends(get_product_service),
    token: TokenData = Depends(verify_token),
):
    """Cập nhật một analysis"""
    # Verify product exists
    product = product_service.get(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    analysis = analysis_service.get(analysis_id)
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    
    updated = analysis_service.update_analysis(analysis_id, payload)
    return updated


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(
    product_id: UUID,
    analysis_id: UUID,
    analysis_service: ReviewAnalysisService = Depends(get_review_analysis_service),
    product_service: ProductService = Depends(get_product_service),
    token: TokenData = Depends(verify_token),
):
    """Xóa một analysis"""
    # Verify product exists
    product = product_service.get(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    analysis = analysis_service.get(analysis_id)
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    
    analysis_service.repository.delete(id=analysis_id)
