from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from models.project import Project
from repositories.permission import PermissionRepository

class PermissionService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = PermissionRepository(db)

    def get_user_permissions(self, user_id: UUID, project_id: Optional[UUID] = None) -> List[str]:
        """
        Get all permissions for a user, optionally scoped to a project.
        Returns a list of permission slugs/names.
        """
        global_perms, project_perms_dict = self.repository.get_user_permissions(user_id, project_id)
        
        if project_id:
            # Return global + specific project permissions
            project_perms = project_perms_dict.get(str(project_id), [])
            return list(set(global_perms + project_perms))
        else:
            # Return only global permissions
            return global_perms

    def get_all_user_permissions(self, user_id: UUID) -> tuple[List[str], dict[str, List[str]]]:
        """
        Get global and all project permissions for a user.
        Used for JWT token generation.
        
        Returns:
            tuple: (global_permissions, project_permissions_dict)
        """
        return self.repository.get_user_permissions(user_id, project_id=None)

    def has_permission(self, user_id: UUID, permission_name: str, project_id: Optional[UUID] = None) -> bool:
        """
        Check if user has a specific permission.
        """
        # Use repository for role-based permissions
        if self.repository.has_permission(user_id, permission_name, project_id):
            return True
            
        # Check if user is Project Owner (Implicit Permission) or Assignee
        if project_id:
            project = self.db.get(Project, project_id)
            if project:
                if project.created_by == user_id:
                    return True
                if project.assigned_to == user_id:
                    return True

        return False

    def enforce_permission(self, user_id: UUID, permission_name: str, project_id: Optional[UUID] = None):
        """
        Raise exception if user does not have permission.
        """
        if not self.has_permission(user_id, permission_name, project_id):
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission: {permission_name}"
            )

