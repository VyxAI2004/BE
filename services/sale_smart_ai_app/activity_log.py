from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from models.activity_log import ActivityLog
from schemas.activity_log import ActivityLogCreate, ActivityLogUpdate
from repositories.activity_log import ActivityLogRepository, ActivityLogFilters

from .base import BaseService


class ActivityLogService(
    BaseService[ActivityLog, ActivityLogCreate, ActivityLogUpdate, ActivityLogRepository]
):
    def __init__(self, db: Session):
        super().__init__(db, ActivityLog, ActivityLogRepository)

    def create_log(
        self,
        *,
        user_id: UUID,
        action: str,
        target_id: Optional[UUID] = None,
        target_type: Optional[str] = None,
        log_metadata: Optional[dict] = None,
    ) -> ActivityLog:
        """Ghi lại 1 log mới"""
        payload = ActivityLogCreate(
            user_id=user_id,
            action=action,
            target_id=target_id,
            target_type=target_type,
            log_metadata=log_metadata,
        )
        return self.create(payload=payload)

    def search(
        self,
        *,
        filters: Optional[ActivityLogFilters] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ActivityLog]:
        """Tìm log với filter linh hoạt"""
        return self.repository.search(filters=filters, skip=skip, limit=limit)

    def count(self, filters: Optional[ActivityLogFilters] = None) -> int:
        """Đếm số log theo filters"""
        return self.repository.count(filters=filters)

    def get_by_user(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[ActivityLog]:
        """Lấy log theo user"""
        filters: ActivityLogFilters = {"user_id": user_id}
        return self.repository.search(filters=filters, skip=skip, limit=limit)

    def get_by_action(
        self, action: str, skip: int = 0, limit: int = 100
    ) -> List[ActivityLog]:
        """Lấy log theo action"""
        filters: ActivityLogFilters = {"action": action}
        return self.repository.search(filters=filters, skip=skip, limit=limit)

    def get_by_target(
        self, target_id: UUID, target_type: Optional[str] = None, skip: int = 0, limit: int = 100
    ) -> List[ActivityLog]:
        """Lấy log theo đối tượng (target)"""
        filters: ActivityLogFilters = {"target_id": target_id}
        if target_type:
            filters["target_type"] = target_type
        return self.repository.search(filters=filters, skip=skip, limit=limit)
