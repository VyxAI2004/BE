from typing import Optional, List, Dict
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select

from models.role import Permission, RolePermission, Role, UserRole
from models.project import ProjectUser


class PermissionRepository:
    """Repository for permission-related database operations"""
    
    def __init__(self, db: Session):
        self.db = db

    def get_user_permissions(
        self, 
        user_id: UUID, 
        project_id: Optional[UUID] = None
    ) -> tuple[List[str], Dict[str, List[str]]]:
        """
        Get all permissions for a user.
        
        Returns:
            tuple: (global_permissions, project_permissions_dict)
                - global_permissions: List of global permission names
                - project_permissions_dict: Dict[project_id, List[permission_names]]
        """
        global_permissions = set()
        project_permissions = {}

        # 1. Get Global Permissions via User Roles
        # Join: UserRole -> Role -> RolePermission -> Permission
        stmt = (
            select(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
            .where(Role.is_active == True)
            .where(Permission.is_active == True)
        )
        global_perms = self.db.execute(stmt).scalars().all()
        global_permissions.update(global_perms)

        # 2. Get Project Permissions
        if project_id:
            # Get permissions for specific project
            stmt = (
                select(Permission.name)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .join(Role, Role.id == RolePermission.role_id)
                .join(ProjectUser, ProjectUser.role_id == Role.id)
                .where(ProjectUser.user_id == user_id)
                .where(ProjectUser.project_id == project_id)
                .where(Role.is_active == True)
                .where(Permission.is_active == True)
            )
            project_perms = self.db.execute(stmt).scalars().all()
            if project_perms:
                project_permissions[str(project_id)] = list(project_perms)
        else:
            # Get permissions for all projects user is member of
            stmt = (
                select(ProjectUser.project_id, Permission.name)
                .join(Role, Role.id == ProjectUser.role_id)
                .join(RolePermission, RolePermission.role_id == Role.id)
                .join(Permission, Permission.id == RolePermission.permission_id)
                .where(ProjectUser.user_id == user_id)
                .where(Role.is_active == True)
                .where(Permission.is_active == True)
            )
            results = self.db.execute(stmt).all()
            
            # Group permissions by project_id
            for project_id_result, perm_name in results:
                project_id_str = str(project_id_result)
                if project_id_str not in project_permissions:
                    project_permissions[project_id_str] = []
                project_permissions[project_id_str].append(perm_name)

        return list(global_permissions), project_permissions

    def has_permission(
        self, 
        user_id: UUID, 
        permission_name: str, 
        project_id: Optional[UUID] = None
    ) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            user_id: User ID
            permission_name: Permission name to check
            project_id: Optional project ID for project-scoped permissions
            
        Returns:
            bool: True if user has the permission
        """
        # Check Global Roles first
        stmt = (
            select(Permission.id)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
            .where(Permission.name == permission_name)
            .where(Role.is_active == True)
            .where(Permission.is_active == True)
        )
        if self.db.execute(stmt).first():
            return True

        # Check Project Roles if project_id is provided
        if project_id:
            stmt = (
                select(Permission.id)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .join(Role, Role.id == RolePermission.role_id)
                .join(ProjectUser, ProjectUser.role_id == Role.id)
                .where(ProjectUser.user_id == user_id)
                .where(ProjectUser.project_id == project_id)
                .where(Permission.name == permission_name)
                .where(Role.is_active == True)
                .where(Permission.is_active == True)
            )
            if self.db.execute(stmt).first():
                return True

        return False
