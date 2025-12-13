from typing import List, Optional, Type, TypedDict
from uuid import UUID

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from models.product import ReviewAnalysis, ProductReview
from schemas.review_analysis import ReviewAnalysisCreate, ReviewAnalysisUpdate

from .base import BaseRepository


class ReviewAnalysisFilters(TypedDict, total=False):
    review_id: Optional[UUID]
    sentiment_label: Optional[str]
    is_spam: Optional[bool]


class ReviewAnalysisRepository(BaseRepository[ReviewAnalysis, ReviewAnalysisCreate, ReviewAnalysisUpdate]):
    def __init__(self, model: Type[ReviewAnalysis], db: Session):
        super().__init__(model, db)

    def get_by_review(self, review_id: UUID) -> Optional[ReviewAnalysis]:
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
        return (
            self.db.query(ReviewAnalysis)
            .join(ProductReview)
            .filter(ProductReview.product_id == product_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_by_sentiment(self, product_id: UUID) -> dict:
        results = (
            self.db.query(ReviewAnalysis.sentiment_label, func.count(ReviewAnalysis.id))
            .join(ProductReview)
            .filter(ProductReview.product_id == product_id)
            .group_by(ReviewAnalysis.sentiment_label)
            .all()
        )
        return {label: count for label, count in results}

    def count_spam(self, product_id: UUID) -> int:
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
        sentiment_counts = self.count_by_sentiment(product_id)
        
        spam_count = self.count_spam(product_id)
        
        avg_sentiment = (
            self.db.query(func.avg(ReviewAnalysis.sentiment_score))
            .join(ProductReview)
            .filter(ProductReview.product_id == product_id)
            .scalar()
        )
        
        avg_spam = (
            self.db.query(func.avg(ReviewAnalysis.spam_score))
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
            "average_sentiment_score": float(avg_sentiment) if avg_sentiment else 0.0,
            "average_spam_score": float(avg_spam) if avg_spam else 0.0
        }

    def bulk_create(self, analyses: List[ReviewAnalysisCreate]) -> List[ReviewAnalysis]:
        db_analyses = [ReviewAnalysis(**analysis.model_dump()) for analysis in analyses]
        
        self.db.add_all(db_analyses)
        self.db.commit()
        for analysis in db_analyses:
            self.db.refresh(analysis)
        
        return db_analyses

    def upsert(self, analysis: ReviewAnalysisCreate) -> ReviewAnalysis:
        existing = self.get_by_review(analysis.review_id)
        
        if existing:
            for field, value in analysis.model_dump(exclude_unset=True).items():
                if field != "review_id" and hasattr(existing, field):
                    setattr(existing, field, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new
            return self.create(obj_in=analysis)
    
    def get_reviews_with_fallback_scores(self, product_id: UUID) -> List[ReviewAnalysis]:
        from decimal import Decimal
        
        all_analyses = self.get_by_product(product_id=product_id, skip=0, limit=10000)
        
        fallback_analyses = [
            analysis for analysis in all_analyses
            if analysis.sentiment_score == Decimal("0.5") and analysis.spam_score == Decimal("0.5")
        ]
        
        return fallback_analyses
