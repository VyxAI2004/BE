"""
Repository cho TaskUser - Data Access Layer
"""
from typing import Optional, Type
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models.task_user import TaskUser
from schemas.task_user import TaskUserCreate, TaskUserUpdate
from .base import BaseRepository


class TaskUserRepository(BaseRepository[TaskUser, TaskUserCreate, TaskUserUpdate]):
    """Repository để quản lý TaskUser"""

    def __init__(self, model: Type[TaskUser], db: Session):
        super().__init__(model, db)

    def get_by_task_and_user(
        self, task_id: UUID, user_id: UUID
    ) -> Optional[TaskUser]:
        """Lấy TaskUser theo task_id và user_id"""
        return self.db.query(TaskUser).filter(
            and_(
                TaskUser.task_id == task_id,
                TaskUser.user_id == user_id
            )
        ).first()

    def get_task_collaborators(
        self, task_id: UUID, skip: int = 0, limit: int = 100, is_active_only: bool = True
    ) -> list[TaskUser]:
        """Lấy tất cả collaborators của task"""
        query = self.db.query(TaskUser).filter(TaskUser.task_id == task_id)
        
        if is_active_only:
            query = query.filter(TaskUser.is_active == True)
        
        return query.offset(skip).limit(limit).all()

    def get_user_tasks_as_collaborator(
        self, user_id: UUID, skip: int = 0, limit: int = 100, is_active_only: bool = True
    ) -> list[TaskUser]:
        """Lấy tất cả tasks mà user là collaborator"""
        query = self.db.query(TaskUser).filter(TaskUser.user_id == user_id)
        
        if is_active_only:
            query = query.filter(TaskUser.is_active == True)
        
        return query.offset(skip).limit(limit).all()

    def count_task_collaborators(self, task_id: UUID) -> int:
        """Đếm số collaborators của task"""
        return self.db.query(TaskUser).filter(
            TaskUser.task_id == task_id
        ).count()

    def remove_from_task(self, task_id: UUID, user_id: UUID) -> bool:
        """Xoá collaborator khỏi task"""
        result = self.db.query(TaskUser).filter(
            and_(
                TaskUser.task_id == task_id,
                TaskUser.user_id == user_id
            )
        ).delete()
        self.db.commit()
        return result > 0
    
    def remove_all_from_task(self, task_id: UUID) -> int:
        """Xoá tất cả collaborators khỏi task"""
        result = self.db.query(TaskUser).filter(
            TaskUser.task_id == task_id
        ).delete()
        self.db.flush()  # Flush to ensure delete is applied before next operations
        return result

    def get_collaborators_by_role(
        self, task_id: UUID, role: str
    ) -> list[TaskUser]:
        """Lấy collaborators theo role"""
        return self.db.query(TaskUser).filter(
            and_(
                TaskUser.task_id == task_id,
                TaskUser.role == role,
                TaskUser.is_active == True
            )
        ).all()
