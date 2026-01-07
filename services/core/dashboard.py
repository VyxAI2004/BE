"""
Dashboard Service - Business Logic Layer cho dashboard statistics
"""
from typing import Optional
from uuid import UUID
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.project import Project
from models.product import Product, ProductReview, ProductTrustScore
from shared.enums import ProjectStatusEnum
from repositories.project import ProjectRepository
from repositories.product import ProductRepository
from repositories.product_review import ProductReviewRepository
from repositories.product_trust_score import ProductTrustScoreRepository


class DashboardService:
    """Service để tính toán dashboard statistics"""
    
    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(Project, db)
        self.product_repo = ProductRepository(Product, db)
        self.review_repo = ProductReviewRepository(ProductReview, db)
        self.trust_score_repo = ProductTrustScoreRepository(ProductTrustScore, db)
    
    def get_statistics(self, user_id: UUID) -> dict:
        """
        Lấy thống kê dashboard cho user:
        - Tổng số reviews (tổng đánh giá)
        - Số dự án đang hoạt động (active projects)
        - Điểm tin cậy trung bình (average trust score)
        """
        # 1. Lấy tất cả projects của user
        user_projects = self.project_repo.get_all_user_projects(user_id)
        project_ids = [p.id for p in user_projects]
        
        if not project_ids:
            return {
                "total_reviews": 0,
                "active_projects": 0,
                "average_trust_score": 0.0
            }
        
        # 2. Đếm số dự án đang hoạt động (RUNNING status)
        active_projects = sum(
            1 for p in user_projects 
            if p.status == ProjectStatusEnum.RUNNING
        )
        
        # 3. Đếm tổng số reviews từ tất cả products trong các projects của user
        # Sử dụng repository method để tính toán
        total_reviews = self.review_repo.count_by_projects(project_ids)
        
        # 4. Tính điểm tin cậy trung bình từ tất cả products trong các projects của user
        average_trust_score = self.trust_score_repo.avg_trust_score_by_projects(project_ids)
        
        return {
            "total_reviews": total_reviews,
            "active_projects": active_projects,
            "average_trust_score": average_trust_score
        }

