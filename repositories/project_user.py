from typing import List, Optional, Type
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_

from models.project import ProjectUser
from schemas.project_user import ProjectUserCreate, ProjectUserUpdate

from .base import BaseRepository

class ProjectUserRepository(BaseRepository[ProjectUser, ProjectUserCreate, ProjectUserUpdate]):
    def __init__(self, model: Type[ProjectUser], db: Session):
        super().__init__(model, db)

    def get_by_project_and_user(self, project_id: UUID, user_id: UUID) -> Optional[ProjectUser]:
        """Get project user membership by project and user ID"""
        return (
            self.db.query(ProjectUser)
            .filter(
                and_(
                    ProjectUser.project_id == project_id,
                    ProjectUser.user_id == user_id
                )
            )
            .first()
        )

    def get_project_members(self, project_id: UUID, is_active: bool = True) -> List[ProjectUser]:
        """Get all members of a project"""
        query = self.db.query(ProjectUser).filter(ProjectUser.project_id == project_id)
        if is_active is not None:
            query = query.filter(ProjectUser.is_active == is_active)
        return query.all()

    def get_user_projects(self, user_id: UUID, is_active: bool = True) -> List[ProjectUser]:
        """Get all projects a user is member of"""
        query = self.db.query(ProjectUser).filter(ProjectUser.user_id == user_id)
        if is_active is not None:
            query = query.filter(ProjectUser.is_active == is_active)
        return query.all()

    def deactivate_membership(self, project_id: UUID, user_id: UUID) -> Optional[ProjectUser]:
        """Deactivate a user's membership in a project"""
        project_user = self.get_by_project_and_user(project_id, user_id)
        if project_user:
            return self.update(db_obj=project_user, obj_in=ProjectUserUpdate(is_active=False))
        return None

    def remove_membership(self, project_id: UUID, user_id: UUID) -> None:
        """Remove a user's membership from a project"""
        project_user = self.get_by_project_and_user(project_id, user_id)
        if project_user:
            self.db.delete(project_user)
            self.db.commit()

    def bulk_create_memberships(self, memberships: List[ProjectUserCreate]) -> List[ProjectUser]:
        """Create multiple project memberships at once"""
        project_users = []
        for membership_data in memberships:
            db_obj = ProjectUser(**membership_data.model_dump())
            self.db.add(db_obj)
            project_users.append(db_obj)
        
        self.db.commit()
        for obj in project_users:
            self.db.refresh(obj)
        
        return project_users