import uuid
from typing import List, Optional
from sqlalchemy.orm import Session

from models.role import Role, Permission, UserRole
from schemas.role import (
    RoleCreate, 
    RoleUpdate, 
    PermissionCreate, 
    PermissionUpdate,
)
from repositories.role import RoleRepository, PermissionRepository, RoleFilters, PermissionFilters
from .base import BaseService


class RoleService(BaseService[Role, RoleCreate, RoleUpdate, RoleRepository]):
    def __init__(self, db: Session):
        super().__init__(db, Role, RoleRepository)

    def get_role(self, *, role_id: uuid.UUID) -> Optional[Role]:
        """Get role by ID"""
        return self.get(role_id)

    def get_role_by_slug(self, *, slug: str) -> Optional[Role]:
        """Get role by slug"""
        return self.repository.get_by_slug(slug=slug)

    def get_role_by_name(self, *, name: str) -> Optional[Role]:
        """Get role by name"""
        return self.repository.get_by_name(name=name)

    def search(
        self,
        *,
        q: Optional[str] = None,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_system_role: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Role]:
        """Search roles with filters"""
        filters: Optional[RoleFilters] = None
        filter_dict = {}
        
        if q:
            filter_dict["q"] = q
        if name:
            filter_dict["name"] = name
        if slug:
            filter_dict["slug"] = slug
        if category:
            filter_dict["category"] = category
        if is_active is not None:
            filter_dict["is_active"] = is_active
        if is_system_role is not None:
            filter_dict["is_system_role"] = is_system_role

        if filter_dict:
            filters = RoleFilters(**filter_dict)

        return self.repository.search(filters=filters, skip=skip, limit=limit)

    def create_role(self, payload: RoleCreate) -> Role:
        """Create new role with optional permissions"""
        # Check if role name already exists
        existing_role = self.repository.get_by_name(name=payload.name)
        if existing_role:
            raise ValueError(f"Role with name '{payload.name}' already exists")
        
        # Check if role slug already exists
        existing_slug = self.repository.get_by_slug(slug=payload.slug)
        if existing_slug:
            raise ValueError(f"Role with slug '{payload.slug}' already exists")

        # Create role
        role_data = payload.model_dump(exclude={"permission_ids"})
        role = self.create(payload=RoleCreate(**role_data))

        # Assign permissions if provided
        if payload.permission_ids:
            self.assign_permissions(role_id=role.id, permission_ids=payload.permission_ids)
            self.db.refresh(role)

        return role

    def update_role(
        self,
        role_id: uuid.UUID,
        payload: RoleUpdate,
    ) -> Optional[Role]:
        """Update role"""
        db_role = self.get(role_id)
        if not db_role:
            return None
        
        # Check if trying to update system role
        if db_role.is_system_role and payload.name:
            raise ValueError("Cannot update system role name")

        # Check if new name conflicts
        if payload.name and payload.name != db_role.name:
            existing_role = self.repository.get_by_name(name=payload.name)
            if existing_role:
                raise ValueError(f"Role with name '{payload.name}' already exists")

        # Update permissions if provided
        permission_ids = payload.permission_ids
        update_data = payload.model_dump(exclude={"permission_ids"}, exclude_unset=True)
        
        role = self.update(db_obj=db_role, payload=RoleUpdate(**update_data))
        
        if permission_ids is not None:
            self.assign_permissions(role_id=role.id, permission_ids=permission_ids)
            self.db.refresh(role)

        return role

    def delete_role(self, role_id: uuid.UUID) -> None:
        """Delete role (cannot delete system roles)"""
        db_role = self.get(role_id)
        if not db_role:
            raise ValueError("Role not found")
        
        if db_role.is_system_role:
            raise ValueError("Cannot delete system role")

        self.delete(id=role_id)

    def activate_role(self, role_id: uuid.UUID) -> Optional[Role]:
        """Activate a role"""
        return self.repository.activate_role(role_id)

    def deactivate_role(self, role_id: uuid.UUID) -> Optional[Role]:
        """Deactivate a role (cannot deactivate system roles)"""
        db_role = self.get(role_id)
        if db_role and db_role.is_system_role:
            raise ValueError("Cannot deactivate system role")
        return self.repository.deactivate_role(role_id)

    def assign_permissions(self, role_id: uuid.UUID, permission_ids: List[uuid.UUID]) -> Role:
        """Assign permissions to a role"""
        role = self.get(role_id)
        if not role:
            raise ValueError("Role not found")
        
        # Verify all permissions exist
        for perm_id in permission_ids:
            perm = self.db.query(Permission).filter(Permission.id == perm_id).first()
            if not perm:
                raise ValueError(f"Permission with ID {perm_id} not found")

        return self.repository.assign_permissions(role_id, permission_ids)

    def remove_permissions(self, role_id: uuid.UUID, permission_ids: List[uuid.UUID]) -> Role:
        """Remove specific permissions from a role"""
        role = self.get(role_id)
        if not role:
            raise ValueError("Role not found")

        return self.repository.remove_permissions(role_id, permission_ids)

    def get_role_permissions(self, role_id: uuid.UUID) -> List[uuid.UUID]:
        """Get all permission IDs for a role"""
        return self.repository.get_permission_ids_for_role(role_id)

    def count_roles(self, *, filters: Optional[RoleFilters] = None) -> int:
        """Count roles with filters"""
        return self.repository.count_by_filters(filters=filters)


class PermissionService(BaseService[Permission, PermissionCreate, PermissionUpdate, PermissionRepository]):
    def __init__(self, db: Session):
        super().__init__(db, Permission, PermissionRepository)

    def get_permission(self, *, permission_id: uuid.UUID) -> Optional[Permission]:
        """Get permission by ID"""
        return self.get(permission_id)

    def get_permission_by_slug(self, *, slug: str) -> Optional[Permission]:
        """Get permission by slug"""
        return self.repository.get_by_slug(slug=slug)

    def get_permission_by_name(self, *, name: str) -> Optional[Permission]:
        """Get permission by name"""
        return self.repository.get_by_name(name=name)

    def search(
        self,
        *,
        q: Optional[str] = None,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Permission]:
        """Search permissions with filters"""
        filters: Optional[PermissionFilters] = None
        filter_dict = {}
        
        if q:
            filter_dict["q"] = q
        if name:
            filter_dict["name"] = name
        if slug:
            filter_dict["slug"] = slug
        if category:
            filter_dict["category"] = category
        if is_active is not None:
            filter_dict["is_active"] = is_active

        if filter_dict:
            filters = PermissionFilters(**filter_dict)

        return self.repository.search(filters=filters, skip=skip, limit=limit)

    def get_permissions_by_category(self, category: str) -> List[Permission]:
        """Get all permissions by category"""
        return self.repository.get_by_category(category)

    def create_permission(self, payload: PermissionCreate) -> Permission:
        """Create new permission"""
        # Check if permission name already exists
        existing_perm = self.repository.get_by_name(name=payload.name)
        if existing_perm:
            raise ValueError(f"Permission with name '{payload.name}' already exists")

        # Check if permission slug already exists
        existing_slug = self.repository.get_by_slug(slug=payload.slug)
        if existing_slug:
            raise ValueError(f"Permission with slug '{payload.slug}' already exists")

        return self.create(payload=payload)

    def update_permission(
        self,
        permission_id: uuid.UUID,
        payload: PermissionUpdate,
    ) -> Optional[Permission]:
        """Update permission"""
        db_perm = self.get(permission_id)
        if not db_perm:
            return None

        # Check if trying to update system permission
        if db_perm.is_system_permission:
            raise ValueError("Cannot update system permission")

        # Check if new name conflicts
        if payload.name and payload.name != db_perm.name:
            existing_perm = self.repository.get_by_name(name=payload.name)
            if existing_perm:
                raise ValueError(f"Permission with name '{payload.name}' already exists")

        return self.update(db_obj=db_perm, payload=payload)

    def delete_permission(self, permission_id: uuid.UUID) -> None:
        """Delete permission (cannot delete system permissions)"""
        db_perm = self.get(permission_id)
        if not db_perm:
            raise ValueError("Permission not found")

        if db_perm.is_system_permission:
            raise ValueError("Cannot delete system permission")

        self.delete(id=permission_id)

    def activate_permission(self, permission_id: uuid.UUID) -> Optional[Permission]:
        """Activate a permission"""
        return self.repository.activate_permission(permission_id)

    def deactivate_permission(self, permission_id: uuid.UUID) -> Optional[Permission]:
        """Deactivate a permission (cannot deactivate system permissions)"""
        db_perm = self.get(permission_id)
        if db_perm and db_perm.is_system_permission:
            raise ValueError("Cannot deactivate system permission")
        return self.repository.deactivate_permission(permission_id)

    def count_permissions(self, *, filters: Optional[PermissionFilters] = None) -> int:
        """Count permissions with filters"""
        return self.repository.count_by_filters(filters=filters)
