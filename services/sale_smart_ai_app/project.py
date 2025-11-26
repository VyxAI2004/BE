import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from models.project import Project
from repositories.project import ProjectFilters, ProjectRepository
from schemas.project import ProjectCreate, ProjectUpdate
from schemas.project_user import ProjectMemberAssignRequest
from shared.enums import ProjectStatusEnum
from .base import BaseService
from .permission import PermissionService

class ProjectService(BaseService[Project, ProjectCreate, ProjectUpdate, ProjectRepository]):
    def __init__(self, db: Session):
        super().__init__(db, Project, ProjectRepository)

    def update_project(self, project_id: uuid.UUID, payload: ProjectUpdate, user_id: uuid.UUID) -> Optional[Project]:
        """Update project"""
        db_project = self.get(project_id)
        if not db_project:
            return None
        
        # Check permission
        permission_service = PermissionService(self.db)
        if not permission_service.has_permission(user_id, "project:update", project_id):
            raise ValueError("You don't have permission to update this project")
        
        return self.update(db_obj=db_project, payload=payload)

    def delete_project(self, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Delete project"""
        db_project = self.get(project_id)
        if not db_project:
            raise ValueError("Project not found")
        
        # Check permission
        permission_service = PermissionService(self.db)
        if not permission_service.has_permission(user_id, "project:delete", project_id):
            raise ValueError("You don't have permission to delete this project")
        
        # Actually delete the project
        self.delete(id=project_id)

    def get_user_projects(self, user_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Project]:
        """Get projects created by or assigned to a specific user"""
        return self.repository.get_by_user(user_id=user_id, skip=skip, limit=limit)

    def get_my_projects(self, user_id: uuid.UUID, skip: int = 0, limit: int = 100) -> tuple[List[Project], int]:
        """Get all projects related to user: created, assigned, or member of
        
        Returns:
            tuple: (paginated_projects, total_count)
        """
        # Get all projects related to user (repository handles the complex query)
        all_projects = self.repository.get_all_user_projects(user_id=user_id)
        
        # Calculate total
        total = len(all_projects)
        
        # Apply pagination
        paginated_projects = all_projects[skip:skip + limit]
        
        return paginated_projects, total

    def assign_project(self, project_id: uuid.UUID, assigned_to: uuid.UUID, user_id: uuid.UUID) -> Optional[Project]:
        """Assign project to a single user (legacy method)"""
        db_project = self.get(project_id)
        if not db_project:
            return None
        
        # Check permission
        permission_service = PermissionService(self.db)
        if not permission_service.has_permission(user_id, "project:assign", project_id):
            raise ValueError("You don't have permission to assign this project")
        
        update_payload = ProjectUpdate(assigned_to=assigned_to)
        return self.update(db_obj=db_project, payload=update_payload)

    def assign_multiple_users_to_project(
        self, 
        project_id: uuid.UUID, 
        request: ProjectMemberAssignRequest, 
        user_id: uuid.UUID
    ) -> Optional[Project]:
        """Assign multiple users to project as members"""
        from .project_user import ProjectUserService
        
        db_project = self.get(project_id)
        if not db_project:
            return None
        
        # Check permission
        permission_service = PermissionService(self.db)
        if not permission_service.has_permission(user_id, "project:manage_members", project_id):
            raise ValueError("You don't have permission to assign users to this project")
        
        # Use ProjectUserService to assign multiple users
        project_user_service = ProjectUserService(self.db)
        project_user_service.assign_users_to_project(
            project_id=project_id,
            request=request,
            invited_by=user_id
        )
        
        return db_project

    def remove_users_from_project(
        self, 
        project_id: uuid.UUID, 
        user_ids: List[uuid.UUID], 
        user_id: uuid.UUID
    ) -> Optional[Project]:
        """Remove multiple users from project"""
        from .project_user import ProjectUserService
        
        db_project = self.get(project_id)
        if not db_project:
            return None
        
        # Check permission
        permission_service = PermissionService(self.db)
        if not permission_service.has_permission(user_id, "project:manage_members", project_id):
            raise ValueError("You don't have permission to remove users from this project")
        
        # Use ProjectUserService to remove users
        project_user_service = ProjectUserService(self.db)
        project_user_service.remove_users_from_project(
            project_id=project_id,
            user_ids=user_ids
        )
        
        return db_project

    def get_project_members(self, project_id: uuid.UUID) -> List:
        """Get all active members of a project"""
        from .project_user import ProjectUserService
        
        project_user_service = ProjectUserService(self.db)
        return project_user_service.get_project_members(project_id=project_id, is_active=True)

    def update_project_status(self, project_id: uuid.UUID, status: ProjectStatusEnum, user_id: uuid.UUID) -> Optional[Project]:
        """Update project status"""
        db_project = self.get(project_id)
        if not db_project:
            return None
        
        # Check permission
        permission_service = PermissionService(self.db)
        if not permission_service.has_permission(user_id, "project:update_status", project_id):
            raise ValueError("You don't have permission to update this project status")
        
        from datetime import datetime
        
        # If marking as completed, set completed_at
        if status == ProjectStatusEnum.COMPLETED:
            update_payload = ProjectUpdate(status=status, completed_at=datetime.utcnow())
        else:
            update_payload = ProjectUpdate(status=status)
        
        return self.update(db_obj=db_project, payload=update_payload)