"""
Service cho Review Analysis - Business Logic Layer.
Xử lý logic nghiệp vụ liên quan đến phân tích reviews.
"""
from typing import List, Optional
from uuid import UUID
from decimal import Decimal

from sqlalchemy.orm import Session

from models.product import ReviewAnalysis, ProductReview
from repositories.review_analysis import ReviewAnalysisRepository
from schemas.review_analysis import ReviewAnalysisCreate, ReviewAnalysisUpdate
from services.ai.spam_detection_service import get_spam_detection_service

from .base import BaseService


class ReviewAnalysisService(BaseService[ReviewAnalysis, ReviewAnalysisCreate, ReviewAnalysisUpdate, ReviewAnalysisRepository]):
    """Service để quản lý ReviewAnalysis"""

    def __init__(self, db: Session):
        super().__init__(db, ReviewAnalysis, ReviewAnalysisRepository)

    def get_by_review(self, review_id: UUID) -> Optional[ReviewAnalysis]:
        """Lấy analysis của một review"""
        return self.repository.get_by_review(review_id)

    def get_by_product(
        self,
        product_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[ReviewAnalysis]:
        """Lấy tất cả analyses của reviews thuộc một product"""
        return self.repository.get_by_product(
            product_id=product_id,
            skip=skip,
            limit=limit
        )

    def create_analysis(self, payload: ReviewAnalysisCreate) -> ReviewAnalysis:
        """
        Tạo analysis mới.
        Nếu review đã có analysis, sẽ update thay vì tạo mới.
        """
        return self.repository.upsert(payload)

    def bulk_create_analyses(self, analyses: List[ReviewAnalysisCreate]) -> List[ReviewAnalysis]:
        """Tạo nhiều analyses cùng lúc (cho batch processing)"""
        return self.repository.bulk_create(analyses)

    def update_analysis(
        self,
        analysis_id: UUID,
        payload: ReviewAnalysisUpdate
    ) -> Optional[ReviewAnalysis]:
        """Cập nhật analysis"""
        db_analysis = self.get(analysis_id)
        if not db_analysis:
            return None
        return self.update(db_obj=db_analysis, payload=payload)

    def get_sentiment_distribution(self, product_id: UUID) -> dict:
        """
        Lấy phân bố sentiment cho một product.
        Returns: {"positive": x, "negative": y, "neutral": z}
        """
        counts = self.repository.count_by_sentiment(product_id)
        # Ensure all labels are present
        return {
            "positive": counts.get("positive", 0),
            "negative": counts.get("negative", 0),
            "neutral": counts.get("neutral", 0)
        }

    def get_spam_count(self, product_id: UUID) -> int:
        """Đếm số spam reviews cho một product"""
        return self.repository.count_spam(product_id)

    def get_statistics(self, product_id: UUID) -> dict:
        """
        Lấy thống kê tổng hợp analyses cho một product.
        Returns: {
            "total_analyzed": int,
            "sentiment_counts": {"positive": x, "negative": y, "neutral": z},
            "spam_count": int,
            "spam_percentage": float,
            "average_sentiment_score": float
        }
        """
        stats = self.repository.get_statistics(product_id)
        
        # Calculate spam percentage
        total = stats["total_analyzed"]
        spam_percentage = (stats["spam_count"] / total * 100) if total > 0 else 0.0
        
        return {
            **stats,
            "spam_percentage": round(spam_percentage, 2)
        }

    def has_analysis(self, review_id: UUID) -> bool:
        """Kiểm tra review đã có analysis chưa"""
        return self.repository.get_by_review(review_id) is not None
    
    def analyze_review(self, review_id: UUID) -> Optional[ReviewAnalysis]:
        """
        Phân tích một review với spam detection.
        Chỉ dùng spam detection, sentiment sẽ được thêm sau.
        """
        from repositories.product_review import ProductReviewRepository
        
        # Get review
        review_repo = ProductReviewRepository(ProductReview, self.db)
        review = review_repo.get(review_id)
        
        if not review:
            return None
        
        # Check if already analyzed
        existing = self.get_by_review(review_id)
        if existing:
            return existing
        
        # Get spam detection service
        spam_service = get_spam_detection_service()
        
        # Analyze spam
        review_text = review.content or ""
        spam_result = spam_service.predict(review_text)
        
        # Create analysis (sentiment defaults to neutral for now)
        analysis_data = ReviewAnalysisCreate(
            review_id=review_id,
            sentiment_label="neutral",  # Will be added later
            sentiment_score=Decimal("0.5"),
            sentiment_confidence=Decimal("0.5"),
            is_spam=spam_result["is_spam"],
            spam_score=Decimal(str(spam_result["spam_score"])),
            spam_confidence=Decimal(str(spam_result["spam_confidence"])),
            spam_model_version=spam_result.get("model_version", "1.0"),
            sentiment_model_version=None,  # Will be added later
            analysis_metadata={
                "spam_detection": spam_result,
                "review_length": len(review_text),
                "has_content": bool(review_text.strip())
            }
        )
        
        return self.create_analysis(analysis_data)
    
    def analyze_product_reviews(self, product_id: UUID) -> List[ReviewAnalysis]:
        """
        Phân tích tất cả reviews của một product.
        Returns list of analyses created/updated.
        """
        from .product_review import ProductReviewService
        
        review_service = ProductReviewService(self.db)
        unanalyzed = review_service.get_unanalyzed_reviews(product_id=product_id, limit=1000)
        
        analyses = []
        for review in unanalyzed:
            analysis = self.analyze_review(review.id)
            if analysis:
                analyses.append(analysis)
        
        return analyses
