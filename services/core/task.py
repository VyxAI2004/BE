"""
Service cho Task - Business Logic Layer.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from models.task import Task
from repositories.task import TaskRepository
from schemas.task import TaskCreate, TaskUpdate

from .base import BaseService


class TaskService(BaseService[Task, TaskCreate, TaskUpdate, TaskRepository]):
    """Service để quản lý Task"""

    def __init__(self, db: Session):
        super().__init__(db, Task, TaskRepository)

    def get_by_project(
        self, project_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        """Lấy tasks theo project"""
        return self.repository.get_by_project(project_id=project_id, skip=skip, limit=limit)

    def get_by_assigned_to(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        """Lấy tasks được assign cho user"""
        return self.repository.get_by_assigned_to(user_id=user_id, skip=skip, limit=limit)

    def get_by_status(
        self, status: str, project_id: Optional[UUID] = None, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        """Lấy tasks theo status"""
        return self.repository.get_by_status(
            status=status, project_id=project_id, skip=skip, limit=limit
        )

    def get_by_product_id(self, product_id: UUID) -> List[Task]:
        """Lấy tasks theo product_id"""
        return self.repository.get_by_product_id(product_id=product_id)

    def delete_by_product_id(self, product_id: UUID) -> int:
        """Xóa tất cả tasks của một product"""
        return self.repository.delete_by_product_id(product_id=product_id)
