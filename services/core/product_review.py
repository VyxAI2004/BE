"""
Service cho Product Review - Business Logic Layer.
Xử lý logic nghiệp vụ liên quan đến reviews.
"""
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from models.product import ProductReview
from repositories.product_review import ProductReviewRepository, ProductReviewFilters
from schemas.product_review import ProductReviewCreate, ProductReviewUpdate

from .base import BaseService


class ProductReviewService(BaseService[ProductReview, ProductReviewCreate, ProductReviewUpdate, ProductReviewRepository]):
    """Service để quản lý ProductReview"""

    def __init__(self, db: Session):
        super().__init__(db, ProductReview, ProductReviewRepository)

    def get_product_reviews(
        self,
        product_id: UUID,
        skip: int = 0,
        limit: int = 100,
        include_analysis: bool = False
    ) -> Tuple[List[ProductReview], int]:
        """
        Lấy danh sách reviews của một product với pagination.
        Returns: (reviews, total_count)
        """
        reviews = self.repository.get_by_product(
            product_id=product_id,
            skip=skip,
            limit=limit,
            include_analysis=include_analysis
        )
        total = self.repository.count_by_product(product_id)
        return reviews, total

    def get_reviews_by_platform(
        self,
        product_id: UUID,
        platform: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[ProductReview]:
        """Lấy reviews theo product và platform"""
        return self.repository.get_by_product_and_platform(
            product_id=product_id,
            platform=platform,
            skip=skip,
            limit=limit
        )

    def get_unanalyzed_reviews(
        self,
        product_id: Optional[UUID] = None,
        limit: int = 100
    ) -> List[ProductReview]:
        """Lấy reviews chưa được AI phân tích"""
        return self.repository.get_unanalyzed_reviews(
            product_id=product_id,
            limit=limit
        )

    def get_analyzed_reviews(
        self,
        product_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[ProductReview]:
        """Lấy reviews đã được AI phân tích"""
        return self.repository.get_analyzed_reviews(
            product_id=product_id,
            skip=skip,
            limit=limit
        )

    def get_review_with_analysis(self, review_id: UUID) -> Optional[ProductReview]:
        """Lấy review kèm kết quả phân tích"""
        return self.repository.get_with_analysis(review_id)

    def get_rating_distribution(self, product_id: UUID) -> dict:
        """
        Lấy phân bố rating của một product.
        Returns: {1: count, 2: count, 3: count, 4: count, 5: count}
        """
        rating_counts = self.repository.count_by_rating(product_id)
        # Ensure all ratings 1-5 are present
        return {i: rating_counts.get(i, 0) for i in range(1, 6)}

    def get_verified_purchase_count(self, product_id: UUID) -> int:
        """Đếm số verified purchase reviews"""
        return self.repository.count_verified_purchases(product_id)

    def create_review(self, payload: ProductReviewCreate) -> ProductReview:
        """Tạo review mới"""
        return self.create(payload=payload)

    def bulk_create_reviews(self, reviews: List[ProductReviewCreate]) -> List[ProductReview]:
        """
        Tạo nhiều reviews cùng lúc (cho batch crawling).
        """
        return self.repository.bulk_create(reviews)

    def update_review(
        self,
        review_id: UUID,
        payload: ProductReviewUpdate
    ) -> Optional[ProductReview]:
        """Cập nhật review"""
        db_review = self.get(review_id)
        if not db_review:
            return None
        return self.update(db_obj=db_review, payload=payload)

    def delete_review(self, review_id: UUID) -> bool:
        """Xóa review"""
        db_review = self.get(review_id)
        if not db_review:
            return False
        self.delete(id=review_id)
        return True

    def get_review_statistics(self, product_id: UUID) -> dict:
        """
        Lấy thống kê reviews cho một product.
        Returns: {
            "total_reviews": int,
            "verified_purchases": int,
            "rating_distribution": {1: x, 2: y, ...},
            "average_rating": float
        }
        """
        total = self.repository.count_by_product(product_id)
        verified = self.repository.count_verified_purchases(product_id)
        rating_dist = self.get_rating_distribution(product_id)
        
        # Calculate average rating
        total_rating = sum(rating * count for rating, count in rating_dist.items())
        avg_rating = total_rating / total if total > 0 else 0.0
        
        return {
            "total_reviews": total,
            "verified_purchases": verified,
            "rating_distribution": rating_dist,
            "average_rating": round(avg_rating, 2)
        }
