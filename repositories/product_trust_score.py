"""
Repository cho Product Trust Score - Data Access Layer.
Chịu trách nhiệm tương tác trực tiếp với Database.
"""
from typing import List, Optional, Type
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from models.product import ProductTrustScore
from schemas.trust_score import ProductTrustScoreCreate, ProductTrustScoreUpdate

from .base import BaseRepository


class ProductTrustScoreRepository(BaseRepository[ProductTrustScore, ProductTrustScoreCreate, ProductTrustScoreUpdate]):
    """Repository để quản lý ProductTrustScore"""
    
    def __init__(self, model: Type[ProductTrustScore], db: Session):
        super().__init__(model, db)

    def get_by_product(self, product_id: UUID) -> Optional[ProductTrustScore]:
        """Lấy trust score của một product (1-1 relationship)"""
        return (
            self.db.query(ProductTrustScore)
            .filter(ProductTrustScore.product_id == product_id)
            .first()
        )

    def get_top_trusted(
        self,
        project_id: Optional[UUID] = None,
        limit: int = 10
    ) -> List[ProductTrustScore]:
        """
        Lấy danh sách products có trust score cao nhất.
        Nếu có project_id thì lọc theo project.
        """
        from models.product import Product
        
        query = (
            self.db.query(ProductTrustScore)
            .join(Product)
            .order_by(desc(ProductTrustScore.trust_score))
        )
        
        if project_id:
            query = query.filter(Product.project_id == project_id)
        
        return query.limit(limit).all()

    def get_by_score_range(
        self,
        min_score: float = 0,
        max_score: float = 100,
        project_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ProductTrustScore]:
        """Lấy trust scores trong khoảng điểm nhất định"""
        from models.product import Product
        
        query = (
            self.db.query(ProductTrustScore)
            .join(Product)
            .filter(ProductTrustScore.trust_score >= min_score)
            .filter(ProductTrustScore.trust_score <= max_score)
        )
        
        if project_id:
            query = query.filter(Product.project_id == project_id)
        
        return query.offset(skip).limit(limit).all()

    def upsert(self, trust_score: ProductTrustScoreCreate) -> ProductTrustScore:
        """
        Insert or update trust score cho một product.
        Vì 1 product chỉ có 1 trust score (unique product_id).
        """
        existing = self.get_by_product(trust_score.product_id)
        
        if existing:
            # Update existing
            for field, value in trust_score.model_dump(exclude_unset=True).items():
                if field != "product_id" and hasattr(existing, field):
                    setattr(existing, field, value)
            # Update calculated_at
            from datetime import datetime, timezone
            existing.calculated_at = datetime.now(timezone.utc)
            
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new
            return self.create(obj_in=trust_score)

    def delete_by_product(self, product_id: UUID) -> bool:
        """Xóa trust score của một product"""
        existing = self.get_by_product(product_id)
        if existing:
            self.delete(id=existing.id)
            return True
        return False
