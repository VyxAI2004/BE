from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import json

from services.core.base import BaseService
from models.role import Permission
from schemas.role import PermissionCreate, PermissionUpdate
from repositories.permission import PermissionRepository, PermissionFilters
from core.cache import get_cache

class PermissionService(BaseService[Permission, PermissionCreate, PermissionUpdate, PermissionRepository]):
    def __init__(self, db: Session):
        # Call super().__init__() to properly initialize BaseService
        super().__init__(db, Permission, PermissionRepository)
        self.cache = get_cache()
        self.CACHE_TTL = 300  # 5 minutes

    def _get_cache_key(self, user_id: UUID) -> str:
        return f"user:perms:{user_id}"

    def get_user_permissions(self, user_id: UUID, project_id: Optional[UUID] = None) -> List[str]:
        """
        Get all permissions for a user, optionally scoped to a project.
        Returns a list of permission slugs/names.
        """
        # Try to get from cache first
        cache_key = self._get_cache_key(user_id)
        cached_data = self.cache.get(cache_key)
        
        if cached_data:
            try:
                data = json.loads(cached_data)
                global_perms = data.get("global", [])
                project_perms_dict = data.get("project", {})
            except json.JSONDecodeError:
                # If cache is corrupted, fallback to DB
                global_perms, project_perms_dict = self.repository.get_user_permissions(user_id, project_id)
        else:
            # Cache miss - fetch from DB
            global_perms, project_perms_dict = self.repository.get_user_permissions(user_id, project_id)
            
            # Cache the result
            cache_data = {
                "global": global_perms,
                "project": project_perms_dict
            }
            self.cache.setex(cache_key, self.CACHE_TTL, json.dumps(cache_data))
        
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
        """
        # Reuse caching logic
        cache_key = self._get_cache_key(user_id)
        cached_data = self.cache.get(cache_key)
        
        if cached_data:
            try:
                data = json.loads(cached_data)
                return data.get("global", []), data.get("project", {})
            except json.JSONDecodeError:
                pass
                
        global_perms, project_perms_dict = self.repository.get_user_permissions(user_id, project_id=None)
        
        # Cache the result
        cache_data = {
            "global": global_perms,
            "project": project_perms_dict
        }
        self.cache.setex(cache_key, self.CACHE_TTL, json.dumps(cache_data))
        
        return global_perms, project_perms_dict

    def invalidate_user_cache(self, user_id: UUID):
        """Invalidate permission cache for a user"""
        self.cache.delete(self._get_cache_key(user_id))

    def has_permission(self, user_id: UUID, permission_name: str, project_id: Optional[UUID] = None) -> bool:
        """
        Check if user has a specific permission.
        """
        # 1. Check cached permissions first (Fastest)
        user_perms = self.get_user_permissions(user_id, project_id)
        if permission_name in user_perms:
            return True
            
        # 2. Check implicit permissions (Owner/Assignee) - Not cached as it depends on Project state
        if project_id and self.repository.is_project_owner_or_assignee(user_id, project_id):
            return True

        return False

    def is_project_owner_or_assignee(self, user_id: UUID, project_id: UUID) -> bool:
        """
        Check if user is the creator or assignee of the project.
        """
        return self.repository.is_project_owner_or_assignee(user_id, project_id)

    def enforce_permission(self, user_id: UUID, permission_name: str, project_id: Optional[UUID] = None):
        """
        Raise exception if user does not have permission.
        """
        if not self.has_permission(user_id, permission_name, project_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission: {permission_name}"
            )

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

    def count_permissions(self, *, filters: Optional[PermissionFilters] = None) -> int:
        """Count permissions with filters"""
        return self.repository.count_by_filters(filters=filters)

    def activate_permission(self, permission_id: UUID) -> Optional[Permission]:
        """Activate a permission"""
        return self.repository.activate_permission(str(permission_id))

    def deactivate_permission(self, permission_id: UUID) -> Optional[Permission]:
        """Deactivate a permission"""
        perm = self.get(permission_id)
        if perm and perm.is_system_permission:
            raise ValueError("Cannot deactivate system permission")
        return self.repository.deactivate_permission(str(permission_id))
