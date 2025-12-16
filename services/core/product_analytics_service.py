"""
Service cho Product Analytics - Business Logic Layer.
Quản lý cache và phân tích analytics.
"""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from models.product import ProductAnalytics
from repositories.product_analytics import ProductAnalyticsRepository
from schemas.product_analytics import ProductAnalyticsCreate, ProductAnalyticsUpdate
from services.core.product_analytics import ProductAnalyticsService as AnalyticsService

from .base import BaseService


class ProductAnalyticsCacheService(
    BaseService[ProductAnalytics, ProductAnalyticsCreate, ProductAnalyticsUpdate, ProductAnalyticsRepository]
):
    """Service để quản lý cache analytics"""

    def __init__(self, db: Session):
        super().__init__(db, ProductAnalytics, ProductAnalyticsRepository)
        self.analytics_service = AnalyticsService(db)

    def get_by_product(self, product_id: UUID) -> Optional[ProductAnalytics]:
        """Lấy analytics từ cache"""
        return self.repository.get_by_product(product_id)

    def get_or_analyze(
        self,
        product_id: UUID,
        user_id: UUID,
        project_assigned_model_id: Optional[UUID] = None,
        force_refresh: bool = False
    ) -> dict:
        """
        Lấy analytics từ cache hoặc phân tích mới nếu chưa có.
        
        Args:
            product_id: ID của product
            user_id: ID của user
            project_assigned_model_id: ID của model được assign cho project
            force_refresh: Nếu True, bỏ qua cache và phân tích lại
        
        Returns:
            Dict chứa kết quả phân tích
        """
        # Check cache first (unless force refresh)
        if not force_refresh:
            cached = self.get_by_product(product_id)
            if cached:
                return {
                    "product_id": str(product_id),
                    "analysis": cached.analysis_data,
                    "metadata": {
                        "model_used": cached.model_used,
                        "total_reviews_analyzed": cached.total_reviews_analyzed,
                        "sample_reviews_count": cached.sample_reviews_count,
                    },
                    "generated_at": cached.analyzed_at,
                    "from_cache": True,
                }

        # Analyze and save to cache
        analytics_result = self.analytics_service.analyze_product(
            product_id=product_id,
            user_id=user_id,
            project_assigned_model_id=project_assigned_model_id
        )

        # Save to database
        analytics_data = ProductAnalyticsCreate(
            product_id=product_id,
            analysis_data=analytics_result["analysis"],
            model_used=analytics_result["metadata"]["model_used"],
            total_reviews_analyzed=analytics_result["metadata"]["total_reviews_analyzed"],
            sample_reviews_count=analytics_result["metadata"]["sample_reviews_count"],
        )

        self.repository.upsert(analytics_data)

        # Get the saved record to get generated_at
        saved = self.get_by_product(product_id)
        
        return {
            "product_id": str(product_id),
            "analysis": analytics_result["analysis"],
            "metadata": analytics_result["metadata"],
            "generated_at": saved.analyzed_at if saved else None,
            "from_cache": False,
        }

    def delete_by_product(self, product_id: UUID) -> bool:
        """Xóa analytics cache của một product"""
        return self.repository.delete_by_product(product_id)
