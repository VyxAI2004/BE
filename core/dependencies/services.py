from fastapi import Depends
from sqlalchemy.orm import Session

from core.dependencies.db import get_db

def get_user_service(db: Session = Depends(get_db)):
    from services.core.user import UserService
    return UserService(db)

def get_activity_log_service(db: Session = Depends(get_db)):
    from services.core.activity_log import ActivityLogService
    return ActivityLogService(db)

def get_auth_service(db: Session = Depends(get_db)):
    from services.core.auth import AuthService
    return AuthService(db)

def get_project_service(db: Session = Depends(get_db)):
    from services.core.project import ProjectService
    return ProjectService(db)

def get_project_user_service(db: Session = Depends(get_db)):
    from services.core.project_user import ProjectUserService
    return ProjectUserService(db)

def get_ai_model_service(db: Session = Depends(get_db)):
    from services.core.ai_model import AIModelService
    return AIModelService(db)

def get_role_service(db: Session = Depends(get_db)):
    from services.core.role import RoleService
    return RoleService(db)

def get_permission_service(db: Session = Depends(get_db)):
    from services.core.role import PermissionService
    return PermissionService(db)

def get_product_service(db: Session = Depends(get_db)):
    from services.core.product import ProductService
    return ProductService(db)

def get_product_review_service(db: Session = Depends(get_db)):
    from services.core.product_review import ProductReviewService
    return ProductReviewService(db)

def get_review_analysis_service(db: Session = Depends(get_db)):
    from services.core.review_analysis import ReviewAnalysisService
    return ReviewAnalysisService(db)

def get_product_trust_score_service(db: Session = Depends(get_db)):
    from services.core.product_trust_score import ProductTrustScoreService
    return ProductTrustScoreService(db)

def get_crawler_service(db: Session = Depends(get_db)):
    from services.features.product_intelligence.crawler.crawler_service import CrawlerService
    return CrawlerService(db)