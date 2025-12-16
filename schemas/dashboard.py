"""
Dashboard Schemas - Định nghĩa các schemas cho dashboard statistics
"""
from pydantic import BaseModel
from typing import Optional


class DashboardStatisticsResponse(BaseModel):
    """Response schema cho dashboard statistics"""
    total_reviews: int
    active_projects: int
    average_trust_score: float
    
    class Config:
        from_attributes = True
