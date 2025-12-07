from fastapi import APIRouter
from .user import router as user_router
from .activity_log import router as activity_log_router
from .auth import router as auth_router
from .project import router as project_router
from .ai_model import router as ai_model_router
from .user_ai_model import router as user_ai_model_router
from .role import router as role_router
from .permission import router as permission_router
from .product import router as product_router
from .product_ai import router as product_ai_router
from .product_crawler import router as product_crawler_router
# Trust Score Feature
from .product_review import router as product_review_router
from .review_analysis import router as review_analysis_router
from .trust_score import router as trust_score_router

api_router = APIRouter(prefix="/api/v1")

__all__ = ["api_router"]
api_router.include_router(user_router)
api_router.include_router(activity_log_router)
api_router.include_router(auth_router)
api_router.include_router(project_router)
api_router.include_router(ai_model_router)
api_router.include_router(user_ai_model_router)
api_router.include_router(role_router)
api_router.include_router(permission_router)
api_router.include_router(product_router)
api_router.include_router(product_ai_router)
api_router.include_router(product_crawler_router)
# Trust Score Feature
api_router.include_router(product_review_router)
api_router.include_router(review_analysis_router)
api_router.include_router(trust_score_router)