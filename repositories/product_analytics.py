"""
Repository cho Product Analytics.
"""
from typing import Optional, Type
from uuid import UUID

from sqlalchemy.orm import Session

from models.product import ProductAnalytics
from repositories.base import BaseRepository
from schemas.product_analytics import ProductAnalyticsCreate, ProductAnalyticsUpdate


class ProductAnalyticsRepository(BaseRepository[ProductAnalytics, ProductAnalyticsCreate, ProductAnalyticsUpdate]):
    """Repository để quản lý ProductAnalytics"""

    def __init__(self, model: Type[ProductAnalytics], db: Session):
        super().__init__(model, db)

    def get_by_product(self, product_id: UUID) -> Optional[ProductAnalytics]:
        """Lấy analytics của một product"""
        return (
            self.db.query(ProductAnalytics)
            .filter(ProductAnalytics.product_id == product_id)
            .first()
        )

    def upsert(self, analytics_data: ProductAnalyticsCreate) -> ProductAnalytics:
        """Tạo mới hoặc cập nhật analytics"""
        existing = self.get_by_product(analytics_data.product_id)
        
        if existing:
            # Update existing
            for field, value in analytics_data.model_dump(exclude_unset=True).items():
                if field != "product_id" and hasattr(existing, field):
                    setattr(existing, field, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new
            return self.create(obj_in=analytics_data)

    def delete_by_product(self, product_id: UUID) -> bool:
        """Xóa analytics của một product"""
        analytics = self.get_by_product(product_id)
        if not analytics:
            return False
        self.delete(id=analytics.id)
        return True
