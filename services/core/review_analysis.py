from typing import List, Optional
from uuid import UUID
from decimal import Decimal

from sqlalchemy.orm import Session

from models.product import ReviewAnalysis, ProductReview
from repositories.review_analysis import ReviewAnalysisRepository
from schemas.review_analysis import ReviewAnalysisCreate, ReviewAnalysisUpdate
from services.features.product_intelligence.ai.spam_detection_service import (
    get_spam_detection_service,
)

from .base import BaseService


class ReviewAnalysisService(
    BaseService[
        ReviewAnalysis,
        ReviewAnalysisCreate,
        ReviewAnalysisUpdate,
        ReviewAnalysisRepository,
    ]
):
    def __init__(self, db: Session):
        super().__init__(db, ReviewAnalysis, ReviewAnalysisRepository)

    def get_by_review(self, review_id: UUID) -> Optional[ReviewAnalysis]:
        return self.repository.get_by_review(review_id)

    def get_by_product(
        self, product_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[ReviewAnalysis]:
        return self.repository.get_by_product(
            product_id=product_id, skip=skip, limit=limit
        )

    def create_analysis(self, payload: ReviewAnalysisCreate) -> ReviewAnalysis:
        return self.repository.upsert(payload)

    def bulk_create_analyses(
        self, analyses: List[ReviewAnalysisCreate]
    ) -> List[ReviewAnalysis]:
        return self.repository.bulk_create(analyses)

    def update_analysis(
        self, analysis_id: UUID, payload: ReviewAnalysisUpdate
    ) -> Optional[ReviewAnalysis]:
        db_analysis = self.get(analysis_id)
        if not db_analysis:
            return None
        return self.update(db_obj=db_analysis, payload=payload)

    def get_sentiment_distribution(self, product_id: UUID) -> dict:
        counts = self.repository.count_by_sentiment(product_id)
        return {
            "positive": counts.get("positive", 0),
            "negative": counts.get("negative", 0),
            "neutral": counts.get("neutral", 0),
        }

    def get_spam_count(self, product_id: UUID) -> int:
        return self.repository.count_spam(product_id)

    def get_statistics(self, product_id: UUID) -> dict:
        stats = self.repository.get_statistics(product_id)
        total = stats["total_analyzed"]
        spam_percentage = (stats["spam_count"] / total * 100) if total > 0 else 0.0
        return {**stats, "spam_percentage": round(spam_percentage, 2)}

    def get_sentiment_scores_detail(self, product_id: UUID) -> dict:
        analyses = self.get_by_product(product_id=product_id, limit=10000)

        sentiment_distribution = {"positive": 0, "negative": 0, "neutral": 0}
        sentiment_scores = []
        total_sentiment_score = 0.0

        for analysis in analyses:
            sentiment_distribution[analysis.sentiment_label] += 1
            score = float(analysis.sentiment_score)
            sentiment_scores.append(
                {
                    "review_id": str(analysis.review_id),
                    "sentiment_label": analysis.sentiment_label,
                    "sentiment_score": score,
                    "sentiment_confidence": float(
                        analysis.sentiment_confidence
                    ),
                }
            )
            total_sentiment_score += score

        total_count = len(analyses)
        average_sentiment = (
            total_sentiment_score / total_count if total_count > 0 else 0.0
        )

        return {
            "product_id": str(product_id),
            "total_analyzed": total_count,
            "average_sentiment_score": round(average_sentiment, 4),
            "sentiment_distribution": sentiment_distribution,
            "sentiment_breakdown": {
                "positive_percentage": round(
                    sentiment_distribution["positive"] / total_count * 100,
                    2,
                )
                if total_count > 0
                else 0,
                "negative_percentage": round(
                    sentiment_distribution["negative"] / total_count * 100,
                    2,
                )
                if total_count > 0
                else 0,
                "neutral_percentage": round(
                    sentiment_distribution["neutral"] / total_count * 100,
                    2,
                )
                if total_count > 0
                else 0,
            },
            "reviews": sentiment_scores,
        }

    def get_spam_scores_detail(self, product_id: UUID) -> dict:
        analyses = self.get_by_product(product_id=product_id, limit=10000)

        spam_count = 0
        spam_scores = []
        total_spam_score = 0.0

        for analysis in analyses:
            if analysis.is_spam:
                spam_count += 1
            score = float(analysis.spam_score)
            spam_scores.append(
                {
                    "review_id": str(analysis.review_id),
                    "is_spam": analysis.is_spam,
                    "spam_score": score,
                    "spam_confidence": float(analysis.spam_confidence),
                }
            )
            total_spam_score += score

        total_count = len(analyses)
        average_spam_score = (
            total_spam_score / total_count if total_count > 0 else 0.0
        )
        spam_percentage = (
            spam_count / total_count * 100 if total_count > 0 else 0.0
        )

        return {
            "product_id": str(product_id),
            "total_analyzed": total_count,
            "spam_detected": spam_count,
            "spam_percentage": round(spam_percentage, 2),
            "average_spam_score": round(average_spam_score, 4),
            "clean_reviews": total_count - spam_count,
            "clean_percentage": round(100 - spam_percentage, 2),
            "reviews": spam_scores,
        }

    def has_analysis(self, review_id: UUID) -> bool:
        return self.repository.get_by_review(review_id) is not None

    def analyze_review(self, review_id: UUID) -> Optional[ReviewAnalysis]:
        from repositories.product_review import ProductReviewRepository
        from services.features.product_intelligence.ai.sentiment_analysis_service import (
            get_sentiment_analysis_service,
        )

        review_repo = ProductReviewRepository(ProductReview, self.db)
        review = review_repo.get(review_id)
        if not review:
            return None

        existing = self.get_by_review(review_id)
        if existing:
            return existing

        spam_service = get_spam_detection_service()
        sentiment_service = get_sentiment_analysis_service()

        review_text = review.content or ""
        spam_result = spam_service.predict(review_text)
        sentiment_result = sentiment_service.predict(review_text)

        analysis_data = ReviewAnalysisCreate(
            review_id=review_id,
            sentiment_label=sentiment_result.get("sentiment_label", "neutral"),
            sentiment_score=Decimal(
                str(sentiment_result.get("sentiment_score", 0.5))
            ),
            sentiment_confidence=Decimal(
                str(sentiment_result.get("sentiment_confidence", 0.5))
            ),
            is_spam=spam_result["is_spam"],
            spam_score=Decimal(str(spam_result["spam_score"])),
            spam_confidence=Decimal(str(spam_result["spam_confidence"])),
            spam_model_version=spam_result.get("model_version", "1.0"),
            sentiment_model_version=sentiment_result.get("model_version", "1.0"),
            analysis_metadata={
                "spam_detection": spam_result,
                "sentiment_analysis": {
                    "probabilities": sentiment_result.get(
                        "probabilities", {}
                    ),
                    "error": sentiment_result.get("error"),
                },
                "review_length": len(review_text),
                "has_content": bool(review_text.strip()),
            },
        )

        return self.create_analysis(analysis_data)

    def analyze_product_reviews(self, product_id: UUID) -> List[ReviewAnalysis]:
        from .product_review import ProductReviewService

        review_service = ProductReviewService(self.db)
        unanalyzed = review_service.get_unanalyzed_reviews(
            product_id=product_id, limit=1000
        )

        analyses = []
        for review in unanalyzed:
            analysis = self.analyze_review(review.id)
            if analysis:
                analyses.append(analysis)

        return analyses

    def reanalyze_fallback_reviews(
        self, product_id: UUID
    ) -> List[ReviewAnalysis]:
        fallback_analyses = self.repository.get_reviews_with_fallback_scores(
            product_id
        )
        if not fallback_analyses:
            return []

        from .product_review import ProductReviewService
        from services.features.product_intelligence.ai.sentiment_analysis_service import (
            get_sentiment_analysis_service,
        )

        review_service = ProductReviewService(self.db)
        analyses = []

        for analysis in fallback_analyses:
            review = review_service.get(analysis.review_id)
            if not review:
                continue

            spam_service = get_spam_detection_service()
            sentiment_service = get_sentiment_analysis_service()

            review_text = review.content or ""
            spam_result = spam_service.predict(review_text)
            sentiment_result = sentiment_service.predict(review_text)

            analysis_data = ReviewAnalysisCreate(
                review_id=analysis.review_id,
                sentiment_label=sentiment_result.get(
                    "sentiment_label", "neutral"
                ),
                sentiment_score=Decimal(
                    str(sentiment_result.get("sentiment_score", 0.5))
                ),
                sentiment_confidence=Decimal(
                    str(sentiment_result.get("sentiment_confidence", 0.5))
                ),
                is_spam=spam_result["is_spam"],
                spam_score=Decimal(str(spam_result["spam_score"])),
                spam_confidence=Decimal(str(spam_result["spam_confidence"])),
                spam_model_version=spam_result.get("model_version", "1.0"),
                sentiment_model_version=sentiment_result.get(
                    "model_version", "1.0"
                ),
                analysis_metadata={
                    "spam_detection": spam_result,
                    "sentiment_analysis": {
                        "probabilities": sentiment_result.get(
                            "probabilities", {}
                        ),
                        "error": sentiment_result.get("error"),
                    },
                    "review_length": len(review_text),
                    "has_content": bool(review_text.strip()),
                },
            )

            updated = self.create_analysis(analysis_data)
            if updated:
                analyses.append(updated)

        return analyses
