from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from models.task import Task
from models.task_user import TaskUser
from models.project import Project
from repositories.task import TaskRepository
from repositories.task_user import TaskUserRepository
from repositories.project_user import ProjectUserRepository
from schemas.task import TaskCreate, TaskUpdate
from models.project_user import ProjectUser
from .base import BaseService
from .task_user import TaskUserService


class TaskService(BaseService[Task, TaskCreate, TaskUpdate, TaskRepository]):
    def __init__(self, db: Session):
        super().__init__(db, Task, TaskRepository)
        self.task_user_repository = TaskUserRepository(model=TaskUser, db=db)
        self.project_user_repository = ProjectUserRepository(model=ProjectUser, db=db)
    
    def _build_assigned_to_list(self, task: Task) -> Optional[List[UUID]]:
        assigned_ids = set()
        if task.id:
            task_users = self.task_user_repository.get_multi(
                filters={'task_id': task.id, 'is_active': True},
                skip=0,
                limit=1000
            )
            task_users = [tu for tu in task_users if tu.role in ['assignee', 'editor']]
            for tu in task_users:
                assigned_ids.add(UUID(str(tu.user_id)) if isinstance(tu.user_id, str) else tu.user_id)

        if not assigned_ids and task.assigned_to:
            assigned_ids.add(UUID(str(task.assigned_to)) if isinstance(task.assigned_to, str) else task.assigned_to)
        
        return list(assigned_ids) if assigned_ids else None

    def update(self, db_obj: Task, payload: TaskUpdate, **kwargs) -> Task:
        assigned_to_ids = payload.assigned_to_ids
        current_user_id = kwargs.get("current_user_id")

        if assigned_to_ids is not None:
            task_user_service = TaskUserService(self.db)
            
            if len(assigned_to_ids) > 0:
                task_user_service.set_assignees(db_obj.id, assigned_to_ids, current_user_id)
                db_obj.assigned_to = assigned_to_ids[0]
            else:
                task_user_service.repository.remove_all_from_task(db_obj.id)
                db_obj.assigned_to = None
        payload_dict = payload.model_dump(exclude={'assigned_to_ids'}, exclude_none=True)
        if payload_dict:
            payload = TaskUpdate(**payload_dict)
            return super().update(db_obj=db_obj, payload=payload)
        else:
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj

    def get_by_project(
        self, project_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        return self.repository.get_by_project(project_id=project_id, skip=skip, limit=limit)

    def get_by_assigned_to(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        return self.repository.get_by_assigned_to(user_id=user_id, skip=skip, limit=limit)

    def get_by_product(
        self, product_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        return self.repository.get_by_product(product_id=product_id, skip=skip, limit=limit)

    def get_user_accessible_tasks(self, user_id: UUID) -> List[Task]:
        return self.repository.get_user_accessible_tasks(user_id=user_id)

    def can_user_access_task(self, user_id: UUID, task: Task) -> bool:
        if task.created_by == user_id:
            return True
        if task.assigned_to:
            if isinstance(task.assigned_to, list):
                if user_id in task.assigned_to:
                    return True
            else:
                if task.assigned_to == user_id:
                    return True

        project_member = self.project_user_repository.get_by_project_and_user(
            task.project_id, user_id
        )
        
        if project_member and project_member.is_active:
            return True
        
        return False

    def get_by_status(
        self, status: str, project_id: Optional[UUID] = None, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        return self.repository.get_by_status(
            status=status, project_id=project_id, skip=skip, limit=limit
        )

    def get_by_product_id(self, product_id: UUID) -> List[Task]:
        return self.repository.get_by_product_id(product_id=product_id)

    def delete_by_product_id(self, product_id: UUID) -> int:
        return self.repository.delete_by_product_id(product_id=product_id)
