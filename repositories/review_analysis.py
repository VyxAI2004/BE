"""
Repository cho Review Analysis - Data Access Layer.
Chịu trách nhiệm tương tác trực tiếp với Database.
"""
from typing import List, Optional, Type, TypedDict
from uuid import UUID

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from models.product import ReviewAnalysis, ProductReview
from schemas.review_analysis import ReviewAnalysisCreate, ReviewAnalysisUpdate

from .base import BaseRepository


class ReviewAnalysisFilters(TypedDict, total=False):
    """Filters cho ReviewAnalysis"""
    review_id: Optional[UUID]
    sentiment_label: Optional[str]
    is_spam: Optional[bool]


class ReviewAnalysisRepository(BaseRepository[ReviewAnalysis, ReviewAnalysisCreate, ReviewAnalysisUpdate]):
    """Repository để quản lý ReviewAnalysis"""
    
    def __init__(self, model: Type[ReviewAnalysis], db: Session):
        super().__init__(model, db)

    def get_by_review(self, review_id: UUID) -> Optional[ReviewAnalysis]:
        """Lấy analysis của một review (1-1 relationship)"""
        return (
            self.db.query(ReviewAnalysis)
            .filter(ReviewAnalysis.review_id == review_id)
            .first()
        )

    def get_by_product(
        self, 
        product_id: UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[ReviewAnalysis]:
        """Lấy tất cả analyses của reviews thuộc một product"""
        return (
            self.db.query(ReviewAnalysis)
            .join(ProductReview)
            .filter(ProductReview.product_id == product_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_by_sentiment(self, product_id: UUID) -> dict:
        """Đếm số analyses theo sentiment label cho một product"""
        results = (
            self.db.query(ReviewAnalysis.sentiment_label, func.count(ReviewAnalysis.id))
            .join(ProductReview)
            .filter(ProductReview.product_id == product_id)
            .group_by(ReviewAnalysis.sentiment_label)
            .all()
        )
        return {label: count for label, count in results}

    def count_spam(self, product_id: UUID) -> int:
        """Đếm số spam reviews cho một product"""
        return (
            self.db.query(func.count(ReviewAnalysis.id))
            .join(ProductReview)
            .filter(
                and_(
                    ProductReview.product_id == product_id,
                    ReviewAnalysis.is_spam == True
                )
            )
            .scalar()
        )

    def get_statistics(self, product_id: UUID) -> dict:
        """
        Lấy thống kê tổng hợp cho một product.
        Returns: {
            "total_analyzed": int,
            "sentiment_counts": {"positive": x, "negative": y, "neutral": z},
            "spam_count": int,
            "average_sentiment_score": float
        }
        """
        # Count by sentiment
        sentiment_counts = self.count_by_sentiment(product_id)
        
        # Count spam
        spam_count = self.count_spam(product_id)
        
        # Calculate average sentiment score
        avg_sentiment = (
            self.db.query(func.avg(ReviewAnalysis.sentiment_score))
            .join(ProductReview)
            .filter(ProductReview.product_id == product_id)
            .scalar()
        )
        
        # Total analyzed
        total_analyzed = sum(sentiment_counts.values())
        
        return {
            "total_analyzed": total_analyzed,
            "sentiment_counts": sentiment_counts,
            "spam_count": spam_count,
            "average_sentiment_score": float(avg_sentiment) if avg_sentiment else 0.0
        }

    def bulk_create(self, analyses: List[ReviewAnalysisCreate]) -> List[ReviewAnalysis]:
        """Tạo nhiều analyses cùng lúc"""
        db_analyses = [ReviewAnalysis(**analysis.model_dump()) for analysis in analyses]
        
        self.db.add_all(db_analyses)
        self.db.commit()
        for analysis in db_analyses:
            self.db.refresh(analysis)
        
        return db_analyses

    def upsert(self, analysis: ReviewAnalysisCreate) -> ReviewAnalysis:
        """
        Insert or update analysis cho một review.
        Vì 1 review chỉ có 1 analysis (unique review_id).
        """
        existing = self.get_by_review(analysis.review_id)
        
        if existing:
            # Update existing
            for field, value in analysis.model_dump(exclude_unset=True).items():
                if field != "review_id" and hasattr(existing, field):
                    setattr(existing, field, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new
            return self.create(obj_in=analysis)
