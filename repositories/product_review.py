"""
Repository cho Product Review - Data Access Layer.
Chịu trách nhiệm tương tác trực tiếp với Database.
"""
from typing import List, Optional, Type, TypedDict
from uuid import UUID

from sqlalchemy import and_, func
from sqlalchemy.orm import Session, joinedload

from models.product import ProductReview
from schemas.product_review import ProductReviewCreate, ProductReviewUpdate

from .base import BaseRepository


class ProductReviewFilters(TypedDict, total=False):
    """Filters cho ProductReview"""
    product_id: Optional[UUID]
    platform: Optional[str]
    rating: Optional[int]
    rating__gte: Optional[int]
    rating__lte: Optional[int]
    is_verified_purchase: Optional[bool]
    crawl_session_id: Optional[UUID]


class ProductReviewRepository(BaseRepository[ProductReview, ProductReviewCreate, ProductReviewUpdate]):
    """Repository để quản lý ProductReview"""
    
    def __init__(self, model: Type[ProductReview], db: Session):
        super().__init__(model, db)

    def get_by_product(
        self, 
        product_id: UUID, 
        skip: int = 0, 
        limit: int = 100,
        include_analysis: bool = False
    ) -> List[ProductReview]:
        """Lấy reviews theo product_id"""
        query = self.db.query(ProductReview).filter(ProductReview.product_id == product_id)
        
        if include_analysis:
            query = query.options(joinedload(ProductReview.analysis))
        
        return query.order_by(ProductReview.review_date.desc()).offset(skip).limit(limit).all()

    def get_by_product_and_platform(
        self,
        product_id: UUID,
        platform: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[ProductReview]:
        """Lấy reviews theo product và platform"""
        return (
            self.db.query(ProductReview)
            .filter(
                and_(
                    ProductReview.product_id == product_id,
                    ProductReview.platform == platform
                )
            )
            .order_by(ProductReview.review_date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_unanalyzed_reviews(
        self, 
        product_id: Optional[UUID] = None,
        limit: int = 100
    ) -> List[ProductReview]:
        """Lấy reviews chưa được phân tích (không có analysis)"""
        query = (
            self.db.query(ProductReview)
            .outerjoin(ProductReview.analysis)
            .filter(ProductReview.analysis == None)
        )
        
        if product_id:
            query = query.filter(ProductReview.product_id == product_id)
        
        return query.limit(limit).all()

    def get_analyzed_reviews(
        self,
        product_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[ProductReview]:
        """Lấy reviews đã được phân tích (có analysis)"""
        return (
            self.db.query(ProductReview)
            .options(joinedload(ProductReview.analysis))
            .filter(ProductReview.product_id == product_id)
            .filter(ProductReview.analysis != None)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_by_product(self, product_id: UUID) -> int:
        """Đếm số reviews của một product"""
        return (
            self.db.query(func.count(ProductReview.id))
            .filter(ProductReview.product_id == product_id)
            .scalar()
        )

    def count_by_rating(self, product_id: UUID) -> dict:
        """Đếm số reviews theo rating cho một product"""
        results = (
            self.db.query(ProductReview.rating, func.count(ProductReview.id))
            .filter(ProductReview.product_id == product_id)
            .group_by(ProductReview.rating)
            .all()
        )
        return {rating: count for rating, count in results}

    def count_verified_purchases(self, product_id: UUID) -> int:
        """Đếm số verified purchase reviews"""
        return (
            self.db.query(func.count(ProductReview.id))
            .filter(
                and_(
                    ProductReview.product_id == product_id,
                    ProductReview.is_verified_purchase == True
                )
            )
            .scalar()
        )

    def get_with_analysis(self, review_id: UUID) -> Optional[ProductReview]:
        """Lấy review kèm analysis"""
        return (
            self.db.query(ProductReview)
            .options(joinedload(ProductReview.analysis))
            .filter(ProductReview.id == review_id)
            .first()
        )

    def bulk_create(self, reviews: List[ProductReviewCreate]) -> List[ProductReview]:
        """Tạo nhiều reviews cùng lúc"""
        db_reviews = [ProductReview(**review.model_dump()) for review in reviews]
        
        self.db.add_all(db_reviews)
        self.db.commit()
        for review in db_reviews:
            self.db.refresh(review)
        
        return db_reviews
