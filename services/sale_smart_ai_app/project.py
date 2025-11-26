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

    def get_project(self, *, project_id: uuid.UUID) -> Optional[Project]:
        """Get project by ID"""
        return self.get(project_id)

    def search(
        self,
        *,
        q: Optional[str] = None,
        name: Optional[str] = None,
        status: Optional[ProjectStatusEnum] = None,
        created_by: Optional[uuid.UUID] = None,
        assigned_to: Optional[uuid.UUID] = None,
        pipeline_type: Optional[str] = None,
        target_product_category: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Project]:
        """Search projects with filters"""
        filters: Optional[ProjectFilters] = None

        filter_dict = {}
        if q:
            filter_dict["q"] = q
        if name:
            filter_dict["name"] = name
        if status:
            filter_dict["status"] = status
        if created_by:
            filter_dict["created_by"] = created_by
        if assigned_to:
            filter_dict["assigned_to"] = assigned_to
        if pipeline_type:
            filter_dict["pipeline_type"] = pipeline_type
        if target_product_category:
            filter_dict["target_product_category"] = target_product_category

        if filter_dict:
            filters = ProjectFilters(**filter_dict)

        return self.repository.search(filters=filters, skip=skip, limit=limit)

    def create_project(self, payload: ProjectCreate, created_by: uuid.UUID) -> Project:
        """Create new project"""
        # Add the created_by field to the payload
        payload_dict = payload.model_dump() if hasattr(payload, 'model_dump') else payload.dict()
        payload_dict["created_by"] = created_by
        return self.create(payload=ProjectCreate(**payload_dict))

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