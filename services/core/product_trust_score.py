"""
Service cho Product Trust Score - Business Logic Layer.
Xử lý logic nghiệp vụ liên quan đến tính toán và quản lý trust score.
"""
import math
from typing import List, Optional
from uuid import UUID
from decimal import Decimal

from sqlalchemy.orm import Session

from models.product import ProductTrustScore, Product
from repositories.product_trust_score import ProductTrustScoreRepository
from schemas.trust_score import (
    ProductTrustScoreCreate, 
    ProductTrustScoreUpdate,
    TrustScoreBreakdown,
    TrustScoreDetailResponse
)

from .base import BaseService


class ProductTrustScoreService(BaseService[ProductTrustScore, ProductTrustScoreCreate, ProductTrustScoreUpdate, ProductTrustScoreRepository]):
    """Service để quản lý ProductTrustScore"""

    # Weights for trust score calculation (spam only for now)
    SPAM_WEIGHT = 0.5  # Increased since we only use spam
    VOLUME_WEIGHT = 0.3
    VERIFICATION_WEIGHT = 0.2
    # SENTIMENT_WEIGHT = 0.0  # Will be added later

    def __init__(self, db: Session):
        super().__init__(db, ProductTrustScore, ProductTrustScoreRepository)

    def get_by_product(self, product_id: UUID) -> Optional[ProductTrustScore]:
        """Lấy trust score của một product"""
        return self.repository.get_by_product(product_id)

    def get_top_trusted(
        self,
        project_id: Optional[UUID] = None,
        limit: int = 10
    ) -> List[ProductTrustScore]:
        """Lấy danh sách products có trust score cao nhất"""
        return self.repository.get_top_trusted(
            project_id=project_id,
            limit=limit
        )

    def get_by_score_range(
        self,
        min_score: float = 0,
        max_score: float = 100,
        project_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ProductTrustScore]:
        """Lấy trust scores trong khoảng điểm"""
        return self.repository.get_by_score_range(
            min_score=min_score,
            max_score=max_score,
            project_id=project_id,
            skip=skip,
            limit=limit
        )

    def calculate_trust_score(self, product_id: UUID) -> Optional[ProductTrustScore]:
        """
        Tính toán trust score cho một product dựa trên reviews và analyses.
        Chỉ dùng spam detection, sentiment sẽ được thêm sau.
        
        Formula (spam only):
        Trust Score = (
            spam_factor * 0.5 +
            volume_factor * 0.3 +
            verification_factor * 0.2
        ) * 100
        """
        from .product_review import ProductReviewService
        from .review_analysis import ReviewAnalysisService
        
        review_service = ProductReviewService(self.db)
        analysis_service = ReviewAnalysisService(self.db)
        
        # Get statistics
        review_stats = review_service.get_review_statistics(product_id)
        analysis_stats = analysis_service.get_statistics(product_id)
        
        total_reviews = review_stats["total_reviews"]
        
        if total_reviews == 0:
            # No reviews, cannot calculate
            return None
        
        # 1. Spam Factor (0-1) - Higher is better (less spam)
        spam_factor = self._calculate_spam_factor(analysis_stats)
        
        # 2. Volume Factor (0-1) - Logarithmic scale
        volume_factor = self._calculate_volume_factor(total_reviews)
        
        # 3. Verification Factor (0-1)
        verification_factor = self._calculate_verification_factor(
            review_stats["verified_purchases"],
            total_reviews
        )
        
        # Calculate final trust score (spam only for now)
        trust_score = (
            spam_factor * self.SPAM_WEIGHT +
            volume_factor * self.VOLUME_WEIGHT +
            verification_factor * self.VERIFICATION_WEIGHT
        ) * 100
        
        # Prepare trust score data
        sentiment_counts = analysis_stats.get("sentiment_counts", {})
        
        trust_score_data = ProductTrustScoreCreate(
            product_id=product_id,
            trust_score=Decimal(str(round(trust_score, 2))),
            total_reviews=total_reviews,
            analyzed_reviews=analysis_stats["total_analyzed"],
            verified_reviews_count=review_stats["verified_purchases"],
            spam_reviews_count=analysis_stats["spam_count"],
            spam_percentage=Decimal(str(analysis_stats["spam_percentage"])),
            positive_reviews_count=sentiment_counts.get("positive", 0),
            negative_reviews_count=sentiment_counts.get("negative", 0),
            neutral_reviews_count=sentiment_counts.get("neutral", 0),
            average_sentiment_score=Decimal(str(analysis_stats.get("average_sentiment_score", 0.5))),
            calculation_metadata={
                "formula_version": "1.0-spam-only",
                "weights": {
                    "spam_factor": self.SPAM_WEIGHT,
                    "volume_factor": self.VOLUME_WEIGHT,
                    "verification_factor": self.VERIFICATION_WEIGHT
                },
                "component_scores": {
                    "spam_factor": round(spam_factor, 4),
                    "volume_factor": round(volume_factor, 4),
                    "verification_factor": round(verification_factor, 4)
                }
            }
        )
        
        # Upsert trust score
        result = self.repository.upsert(trust_score_data)
        
        # Update denormalized trust_score in Product table
        self._update_product_trust_score(product_id, trust_score)
        
        return result

    def _calculate_sentiment_factor(self, analysis_stats: dict) -> float:
        """
        Calculate sentiment component (0-1).
        Based on average sentiment score.
        NOTE: Not used in current formula (spam only), but kept for future use.
        """
        avg_score = analysis_stats.get("average_sentiment_score", 0.5)
        return float(avg_score)

    def _calculate_spam_factor(self, analysis_stats: dict) -> float:
        """
        Calculate spam component (0-1).
        Less spam = higher score.
        """
        total = analysis_stats.get("total_analyzed", 0)
        if total == 0:
            return 1.0  # No data, assume no spam
        
        spam_count = analysis_stats.get("spam_count", 0)
        spam_ratio = spam_count / total
        return 1 - spam_ratio  # Invert: less spam = higher score

    def _calculate_volume_factor(self, total_reviews: int) -> float:
        """
        Calculate volume component (0-1).
        Logarithmic scale:
        - 0 reviews = 0.0
        - 10 reviews = ~0.33
        - 100 reviews = ~0.67
        - 1000+ reviews = 1.0
        """
        if total_reviews == 0:
            return 0.0
        
        score = math.log(total_reviews + 1) / math.log(1001)
        return min(score, 1.0)

    def _calculate_verification_factor(self, verified_count: int, total_reviews: int) -> float:
        """
        Calculate verification component (0-1).
        Ratio of verified purchases.
        """
        if total_reviews == 0:
            return 0.0
        
        return verified_count / total_reviews

    def _update_product_trust_score(self, product_id: UUID, trust_score: float) -> None:
        """Update denormalized trust_score field in Product table"""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if product:
            product.trust_score = Decimal(str(round(trust_score, 2)))
            self.db.commit()

    def get_trust_score_detail(self, product_id: UUID) -> Optional[TrustScoreDetailResponse]:
        """
        Lấy trust score với breakdown chi tiết.
        """
        trust_score = self.get_by_product(product_id)
        if not trust_score:
            return None
        
        metadata = trust_score.calculation_metadata or {}
        weights = metadata.get("weights", {})
        component_scores = metadata.get("component_scores", {})
        
        breakdown = {}
        
        # Sentiment breakdown
        if "sentiment_factor" in component_scores:
            factor = component_scores["sentiment_factor"]
            weight = weights.get("sentiment_factor", self.SENTIMENT_WEIGHT)
            breakdown["sentiment"] = TrustScoreBreakdown(
                factor=factor,
                weight=weight,
                contribution=factor * weight * 100,
                details={
                    "positive": trust_score.positive_reviews_count,
                    "negative": trust_score.negative_reviews_count,
                    "neutral": trust_score.neutral_reviews_count,
                    "average_score": float(trust_score.average_sentiment_score)
                }
            )
        
        # Spam breakdown
        if "spam_factor" in component_scores:
            factor = component_scores["spam_factor"]
            weight = weights.get("spam_factor", self.SPAM_WEIGHT)
            breakdown["spam"] = TrustScoreBreakdown(
                factor=factor,
                weight=weight,
                contribution=factor * weight * 100,
                details={
                    "total_reviews": trust_score.total_reviews,
                    "spam_detected": trust_score.spam_reviews_count,
                    "spam_percentage": float(trust_score.spam_percentage)
                }
            )
        
        # Volume breakdown
        if "volume_factor" in component_scores:
            factor = component_scores["volume_factor"]
            weight = weights.get("volume_factor", self.VOLUME_WEIGHT)
            breakdown["volume"] = TrustScoreBreakdown(
                factor=factor,
                weight=weight,
                contribution=factor * weight * 100,
                details={
                    "total_reviews": trust_score.total_reviews,
                    "analyzed_reviews": trust_score.analyzed_reviews
                }
            )
        
        # Verification breakdown
        if "verification_factor" in component_scores:
            factor = component_scores["verification_factor"]
            weight = weights.get("verification_factor", self.VERIFICATION_WEIGHT)
            verification_rate = (
                trust_score.verified_reviews_count / trust_score.total_reviews * 100
                if trust_score.total_reviews > 0 else 0
            )
            breakdown["verification"] = TrustScoreBreakdown(
                factor=factor,
                weight=weight,
                contribution=factor * weight * 100,
                details={
                    "verified_purchases": trust_score.verified_reviews_count,
                    "total_reviews": trust_score.total_reviews,
                    "verification_rate": round(verification_rate, 2)
                }
            )
        
        return TrustScoreDetailResponse(
            product_id=product_id,
            trust_score=float(trust_score.trust_score),
            breakdown=breakdown,
            total_reviews=trust_score.total_reviews,
            analyzed_reviews=trust_score.analyzed_reviews,
            calculated_at=trust_score.calculated_at
        )

    def recalculate_trust_score(self, product_id: UUID) -> Optional[ProductTrustScore]:
        """Tính lại trust score cho một product"""
        return self.calculate_trust_score(product_id)

    def delete_trust_score(self, product_id: UUID) -> bool:
        """Xóa trust score của một product"""
        return self.repository.delete_by_product(product_id)
