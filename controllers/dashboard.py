"""
Dashboard Controller - API endpoints cho dashboard statistics
"""
from fastapi import APIRouter, Depends

from core.dependencies.auth import verify_token
from core.dependencies.services import get_dashboard_service
from schemas.auth import TokenData
from schemas.dashboard import DashboardStatisticsResponse
from services.core.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/statistics", response_model=DashboardStatisticsResponse)
def get_dashboard_statistics(
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    user_from_token: TokenData = Depends(verify_token),
):
    """
    Lấy thống kê dashboard:
    - Tổng số reviews (tổng đánh giá)
    - Số dự án đang hoạt động (active projects)
    - Điểm tin cậy trung bình (average trust score)
    """
    stats = dashboard_service.get_statistics(user_from_token.user_id)
    return DashboardStatisticsResponse(**stats)
