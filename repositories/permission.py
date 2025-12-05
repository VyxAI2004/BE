from typing import Optional, List, Dict, TypedDict, Type
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func

from repositories.base import BaseRepository
from models.role import Permission, RolePermission, Role, UserRole
from models.project import ProjectUser, Project
from schemas.role import PermissionCreate, PermissionUpdate


class PermissionFilters(TypedDict, total=False):
    """Permission filters for comprehensive search"""
    q: Optional[str]
    name: Optional[str]
    slug: Optional[str]
    category: Optional[str]
    is_active: Optional[bool]


class PermissionRepository(BaseRepository[Permission, PermissionCreate, PermissionUpdate]):
    """Repository for permission-related database operations"""

    def __init__(self, db: Session):
        super().__init__(Permission, db)

    # ------------------------------
    # Internal helper methods
    # ------------------------------

    def _build_permission_query(self):
        """Base SELECT for Permission with Role and RolePermission."""
        return (
            select(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .where(Role.is_active == True, Permission.is_active == True)
        )

    def _query_global_permissions(self, user_id: UUID) -> List[str]:
        """Get permissions through global system roles."""
        stmt = (
            self._build_permission_query()
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        return self.db.execute(stmt).scalars().all()

    def _query_project_permissions(self, user_id: UUID, project_id: UUID) -> List[str]:
        """Get permissions through project-specific roles."""
        stmt = (
            self._build_permission_query()
            .join(ProjectUser, ProjectUser.role_id == Role.id)
            .where(ProjectUser.user_id == user_id, ProjectUser.project_id == project_id)
        )
        return self.db.execute(stmt).scalars().all()

    # ------------------------------
    # Public methods
    # ------------------------------

    def get_user_permissions(
        self, 
        user_id: UUID, 
        project_id: Optional[UUID] = None
    ) -> tuple[List[str], Dict[str, List[str]]]:
        """
        Get all permissions for a user.
        
        Returns:
            tuple: (global_permissions, project_permissions_dict)
        """
        global_permissions = set(self._query_global_permissions(user_id))
        project_permissions: Dict[str, List[str]] = {}

        if project_id:
            # Only specific project
            perms = self._query_project_permissions(user_id, project_id)
            if perms:
                project_permissions[str(project_id)] = list(perms)
        else:
            # All project permissions
            stmt = (
                select(ProjectUser.project_id, Permission.name)
                .join(Role, Role.id == ProjectUser.role_id)
                .join(RolePermission, RolePermission.role_id == Role.id)
                .join(Permission, Permission.id == RolePermission.permission_id)
                .where(ProjectUser.user_id == user_id)
                .where(Role.is_active == True, Permission.is_active == True)
            )
            rows = self.db.execute(stmt).all()

            for pid, perm in rows:
                pid = str(pid)
                project_permissions.setdefault(pid, []).append(perm)

        return list(global_permissions), project_permissions

    def has_permission(
        self, 
        user_id: UUID, 
        permission_name: str, 
        project_id: Optional[UUID] = None
    ) -> bool:
        """
        Check if user has a specific permission.
        """
        # Check global roles
        stmt = (
            select(Permission.id)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                UserRole.user_id == user_id,
                Permission.name == permission_name,
                Role.is_active == True,
                Permission.is_active == True,
            )
        )
        if self.db.execute(stmt).first():
            return True

        # Check project roles
        if project_id:
            stmt = (
                select(Permission.id)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .join(Role, Role.id == RolePermission.role_id)
                .join(ProjectUser, ProjectUser.role_id == Role.id)
                .where(
                    ProjectUser.user_id == user_id,
                    ProjectUser.project_id == project_id,
                    Permission.name == permission_name,
                    Role.is_active == True,
                    Permission.is_active == True,
                )
            )
            if self.db.execute(stmt).first():
                return True

        return False

    def is_project_owner_or_assignee(self, user_id: UUID, project_id: UUID) -> bool:
        """
        Check if user is the creator or assignee of the project.
        """
        stmt = select(Project.id).where(
            Project.id == project_id,
            (Project.created_by == user_id) | (Project.assigned_to == user_id)
        )
        return self.db.execute(stmt).first() is not None

    def search(
        self,
        *,
        filters: Optional[PermissionFilters] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Permission]:
        """Search permissions with filters"""
        db_query = self.db.query(Permission)

        if filters:
            filter_conditions = []
            
            if filters.get("q"):
                query = filters.get("q")
                filter_conditions.append(
                    or_(
                        Permission.name.ilike(f"%{query}%"),
                        Permission.slug.ilike(f"%{query}%"),
                        Permission.description.ilike(f"%{query}%"),
                    )
                )
            
            if filters.get("name"):
                filter_conditions.append(Permission.name.ilike(f"%{filters.get('name')}%"))
            
            if filters.get("slug"):
                filter_conditions.append(Permission.slug == filters.get("slug"))
            
            if filters.get("category"):
                filter_conditions.append(Permission.category == filters.get("category"))
            
            if filters.get("is_active") is not None:
                filter_conditions.append(Permission.is_active == filters.get("is_active"))
            
            if filter_conditions:
                db_query = db_query.filter(and_(*filter_conditions))

        return db_query.order_by(Permission.category, Permission.name).offset(skip).limit(limit).all()

    def get_by_slug(self, *, slug: str) -> Optional[Permission]:
        """Get permission by slug"""
        return self.db.query(Permission).filter(Permission.slug == slug).first()

    def get_by_name(self, *, name: str) -> Optional[Permission]:
        """Get permission by name"""
        return self.db.query(Permission).filter(Permission.name == name).first()

    def get_by_category(self, category: str) -> List[Permission]:
        """Get all permissions by category"""
        return self.db.query(Permission).filter(
            Permission.category == category,
            Permission.is_active == True
        ).order_by(Permission.name).all()

    def count_by_filters(self, *, filters: Optional[PermissionFilters] = None) -> int:
        """Count permissions with filters"""
        db_query = self.db.query(func.count(Permission.id))

        if filters:
            filter_conditions = []
            
            if filters.get("q"):
                query = filters.get("q")
                filter_conditions.append(
                    or_(
                        Permission.name.ilike(f"%{query}%"),
                        Permission.slug.ilike(f"%{query}%"),
                        Permission.description.ilike(f"%{query}%"),
                    )
                )
            
            if filters.get("name"):
                filter_conditions.append(Permission.name.ilike(f"%{filters.get('name')}%"))
            
            if filters.get("slug"):
                filter_conditions.append(Permission.slug == filters.get("slug"))
            
            if filters.get("category"):
                filter_conditions.append(Permission.category == filters.get("category"))
            
            if filters.get("is_active") is not None:
                filter_conditions.append(Permission.is_active == filters.get("is_active"))
            
            if filter_conditions:
                db_query = db_query.filter(and_(*filter_conditions))

        return db_query.scalar() or 0

    def activate_permission(self, permission_id: str) -> Optional[Permission]:
        """Activate a permission"""
        perm = self.get(permission_id)
        if perm and not perm.is_system_permission:
            perm.is_active = True
            self.db.commit()
            self.db.refresh(perm)
        return perm

    def deactivate_permission(self, permission_id: str) -> Optional[Permission]:
        """Deactivate a permission (system permissions cannot be deactivated)"""
        perm = self.get(permission_id)
        if perm and not perm.is_system_permission:
            perm.is_active = False
            self.db.commit()
            self.db.refresh(perm)
        return perm
