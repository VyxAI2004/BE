from typing import List, Optional, Type, TypedDict
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_

from models.activity_log import ActivityLog
from schemas.activity_log import ActivityLogCreate, ActivityLogUpdate

from .base import BaseRepository


class ActivityLogFilters(TypedDict, total=False):
    """Filters for activity logs"""
    q: Optional[str]
    action: Optional[str]
    user_id: Optional[UUID]
    target_id: Optional[UUID]
    target_type: Optional[str]


class ActivityLogRepository(BaseRepository[ActivityLog, ActivityLogCreate, ActivityLogUpdate]):
    def __init__(self, model: Type[ActivityLog], db: Session):
        super().__init__(model, db)

    def _apply_filters(self, query, filters: Optional[ActivityLogFilters] = None):
        if not filters:
            return query

        filter_conditions = []

        if filters.get("q"):
            q = filters.get("q")
            filter_conditions.append(
                or_(
                    ActivityLog.action.ilike(f"%{q}%"),
                    ActivityLog.target_type.ilike(f"%{q}%"),
                )
            )

        if filters.get("action"):
            filter_conditions.append(ActivityLog.action == filters.get("action"))
        if filters.get("user_id"):
            filter_conditions.append(ActivityLog.user_id == filters.get("user_id"))
        if filters.get("target_id"):
            filter_conditions.append(ActivityLog.target_id == filters.get("target_id"))
        if filters.get("target_type"):
            filter_conditions.append(ActivityLog.target_type == filters.get("target_type"))

        if filter_conditions:
            query = query.filter(*filter_conditions)
            
        return query

    def search(
        self,
        *,
        filters: Optional[ActivityLogFilters] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ActivityLog]:
        db_query = self.db.query(ActivityLog)
        db_query = self._apply_filters(db_query, filters)
        return db_query.offset(skip).limit(limit).all()

    def count(self, filters: Optional[ActivityLogFilters] = None) -> int:
        db_query = self.db.query(ActivityLog)
        db_query = self._apply_filters(db_query, filters)
        return db_query.count()
