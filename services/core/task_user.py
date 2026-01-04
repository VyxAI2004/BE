"""
Service cho TaskUser - Business Logic Layer
"""
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from models.task_user import TaskUser
from models.user import User
from models.task import Task
from schemas.task_user import TaskUserCreate, TaskUserUpdate
from repositories.task_user import TaskUserRepository
from .base import BaseService


class TaskUserService(BaseService[TaskUser, TaskUserCreate, TaskUserUpdate, TaskUserRepository]):
    """Service để quản lý TaskUser - Task collaborators & invitations"""

    def __init__(self, db: Session):
        super().__init__(db, TaskUser, TaskUserRepository)

    def invite_collaborator(
        self,
        task_id: UUID,
        user: User,
        role: str = "collaborator",
        permissions: Optional[dict] = None,
        invited_by_id: Optional[UUID] = None,
    ) -> TaskUser:
        """Mời user làm collaborator trên task"""
        # Check if already exists
        existing = self.repository.get_by_task_and_user(task_id, user.id)
        if existing:
            return existing
        
        # Create new task user
        payload = TaskUserCreate(
            task_id=task_id,
            user_id=user.id,
            role=role,
            permissions=permissions,
            invited_by=invited_by_id,
        )
        return self.create(payload)

    def get_task_collaborators(
        self, task_id: UUID, skip: int = 0, limit: int = 100, is_active_only: bool = True
    ) -> list[TaskUser]:
        """Lấy tất cả collaborators của task"""
        return self.repository.get_task_collaborators(task_id, skip, limit, is_active_only)

    def get_user_tasks_as_collaborator(
        self, user_id: UUID, skip: int = 0, limit: int = 100, is_active_only: bool = True
    ) -> list[TaskUser]:
        """Lấy tất cả tasks mà user là collaborator"""
        return self.repository.get_user_tasks_as_collaborator(user_id, skip, limit, is_active_only)

    def set_assignees(self, task_id: UUID, assigned_to_ids: list[UUID], invited_by_id: UUID) -> None:
        """
        Set multiple assignees for a task. Removes old assignees and adds new ones.
        
        Args:
            task_id: Task ID to assign users to
            assigned_to_ids: List of user IDs to assign
            invited_by_id: User ID who is making the assignment
        """
        # Remove all old assignees
        self.repository.remove_all_from_task(task_id)
        
        # Add new assignees
        for user_id in assigned_to_ids:
            payload = TaskUserCreate(
                task_id=task_id,
                user_id=user_id,
                role="assignee",
                invited_by=invited_by_id,
            )
            self.create(payload)

    def update_collaborator_role(
        self, task_id: UUID, user_id: UUID, role: str, permissions: Optional[dict] = None
    ) -> Optional[TaskUser]:
        """Cập nhật role của collaborator trong task"""
        collaborator = self.repository.get_by_task_and_user(task_id, user_id)
        if not collaborator:
            return None
        
        payload = TaskUserUpdate(role=role, permissions=permissions)
        return self.update(db_obj=collaborator, payload=payload)

    def remove_from_task(self, task_id: UUID, user_id: UUID) -> bool:
        """Xoá collaborator khỏi task"""
        return self.repository.remove_from_task(task_id, user_id)

    def is_task_collaborator(self, task_id: UUID, user_id: UUID) -> bool:
        """Kiểm tra user có phải là collaborator của task không"""
        collaborator = self.repository.get_by_task_and_user(task_id, user_id)
        return collaborator is not None and collaborator.is_active

    def can_user_edit_task_as_collaborator(self, task_id: UUID, user_id: UUID) -> bool:
        """Kiểm tra user có thể edit task nếu là collaborator"""
        collaborator = self.repository.get_by_task_and_user(task_id, user_id)
        if not collaborator or not collaborator.is_active:
            return False
        
        # Allowed roles for editing: editor, collaborator (not read_only)
        return collaborator.role in ["editor", "collaborator"]

    def can_user_comment_on_task(self, task_id: UUID, user_id: UUID) -> bool:
        """Kiểm tra user có thể comment trên task"""
        collaborator = self.repository.get_by_task_and_user(task_id, user_id)
        if not collaborator or not collaborator.is_active:
            return False
        
        # All roles can comment
        return True

    def get_collaborators_by_role(self, task_id: UUID, role: str) -> list[TaskUser]:
        """Lấy collaborators theo role cụ thể"""
        return self.repository.get_collaborators_by_role(task_id, role)
