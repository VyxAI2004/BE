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
from .task_user import TaskUserService


class TaskService(BaseService[Task, TaskCreate, TaskUpdate, TaskRepository]):
    """Service để quản lý Task"""

    def __init__(self, db: Session):
        super().__init__(db, Task, TaskRepository)

    def update(self, db_obj: Task, payload: TaskUpdate, **kwargs) -> Task:
        """Override update to handle assigned_to_ids for multiple assignees"""
        # Extract assigned_to_ids if provided
        assigned_to_ids = payload.assigned_to_ids
        current_user_id = kwargs.get("current_user_id")
        
        # If assigned_to_ids provided, use TaskUserService to manage assignees
        if assigned_to_ids is not None and len(assigned_to_ids) > 0:
            task_user_service = TaskUserService(self.db)
            task_user_service.set_assignees(db_obj.id, assigned_to_ids, current_user_id)
            
            # Set assigned_to to first user for backward compatibility
            payload.assigned_to = assigned_to_ids[0]
        elif assigned_to_ids is not None and len(assigned_to_ids) == 0:
            # Empty list means remove all assignees
            task_user_service = TaskUserService(self.db)
            task_user_service.repository.remove_all_from_task(db_obj.id)
            payload.assigned_to = None
        
        # Call parent update with remaining fields
        return super().update(db_obj=db_obj, payload=payload)

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

    def get_by_product(
        self, product_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        """Lấy tasks theo product_id"""
        return self.repository.get_by_product(product_id=product_id, skip=skip, limit=limit)

    def get_user_accessible_tasks(self, user_id: UUID) -> List[Task]:
        """Lấy tất cả tasks mà user có access (creator, assigned, or project member)"""
        return self.repository.get_user_accessible_tasks(user_id=user_id)

    def can_user_access_task(self, user_id: UUID, task: Task) -> bool:
        """Check nếu user có access tới task (creator, assigned, or project member)"""
        from models.project_user import ProjectUser
        
        # Check if creator
        if task.created_by == user_id:
            return True
        
        # Check if assigned
        if task.assigned_to == user_id:
            return True
        
        # Check if project member
        project_member = self.db.query(ProjectUser).filter(
            ProjectUser.project_id == task.project_id,
            ProjectUser.user_id == user_id,
            ProjectUser.is_active == True
        ).first()
        
        if project_member:
            return True
        
        # Check if project creator or assigned
        project = self.db.query(type(task.project)).filter_by(id=task.project_id).first()
        if project and (project.created_by == user_id or project.assigned_to == user_id):
            return True
        
        return False

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
