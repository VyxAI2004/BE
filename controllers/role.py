import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from core.dependencies.auth import verify_token
from schemas.auth import TokenData
from core.dependencies.services import get_role_service, get_permission_service
from schemas.role import (
    ListRolesResponse,
    RoleResponse,
    RoleDetailResponse,
    ListRoleDetailsResponse,
    RoleCreate,
    RoleUpdate,
    ListPermissionsResponse,
    PermissionResponse,
    PermissionCreate,
    PermissionUpdate,
    BulkAssignRoleRequest,
    BulkAssignRoleResponse,
    RolePermissionAssignRequest,
    RolePermissionRemoveRequest,
)
from services.sale_smart_ai_app.role import RoleService, PermissionService
from repositories.role import RoleFilters, PermissionFilters
from middlewares.permissions import check_global_permissions
from shared.enums import GlobalPermissionEnum

router = APIRouter(prefix="/roles", tags=["roles"])


# Admin only: Create role
@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
@check_global_permissions(GlobalPermissionEnum.MANAGE_ROLES)
def create_role(
    *,
    payload: RoleCreate,
    role_service: RoleService = Depends(get_role_service),
    token: TokenData = Depends(verify_token),
):
    """Create a new role (Admin only)"""
    try:
        role = role_service.create_role(payload=payload)
        return role
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin only: List roles
@router.get("/", response_model=ListRolesResponse)
@check_global_permissions(GlobalPermissionEnum.MANAGE_ROLES)
def list_roles(
    *,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    q: Optional[str] = Query(None, description="Search by name, slug, or description"),
    name: Optional[str] = Query(None, description="Filter by name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_system_role: Optional[bool] = Query(None, description="Filter by system role flag"),
    role_service: RoleService = Depends(get_role_service),
    token: TokenData = Depends(verify_token),
):
    """List all roles (Admin only)"""
    try:
        roles = role_service.search(
            q=q,
            name=name,
            is_active=is_active,
            is_system_role=is_system_role,
            skip=skip,
            limit=limit,
        )
        
        filters_dict = {}
        if q:
            filters_dict["q"] = q
        if name:
            filters_dict["name"] = name
        if is_active is not None:
            filters_dict["is_active"] = is_active
        if is_system_role is not None:
            filters_dict["is_system_role"] = is_system_role
        
        filters = RoleFilters(**filters_dict) if filters_dict else None
        total = role_service.count_roles(filters=filters)
        
        return ListRolesResponse(
            total=total,
            items=[RoleResponse.model_validate(role) for role in roles]
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin only: Get role by ID (with permissions)
@router.get("/{role_id}", response_model=RoleDetailResponse)
@check_global_permissions(GlobalPermissionEnum.MANAGE_ROLES)
def get_role(
    *,
    role_id: uuid.UUID,
    role_service: RoleService = Depends(get_role_service),
    token: TokenData = Depends(verify_token),
):
    """Get role by ID with all permissions (Admin only)"""
    role = role_service.get_role(role_id=role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


# Admin only: Update role
@router.patch("/{role_id}", response_model=RoleResponse)
@check_global_permissions(GlobalPermissionEnum.MANAGE_ROLES)
def update_role(
    *,
    role_id: uuid.UUID,
    payload: RoleUpdate,
    role_service: RoleService = Depends(get_role_service),
    token: TokenData = Depends(verify_token),
):
    """Update role (Admin only)"""
    try:
        role = role_service.update_role(role_id=role_id, payload=payload)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return role
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin only: Delete role
@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
@check_global_permissions(GlobalPermissionEnum.MANAGE_ROLES)
def delete_role(
    *,
    role_id: uuid.UUID,
    role_service: RoleService = Depends(get_role_service),
    token: TokenData = Depends(verify_token),
):
    """Delete role (Admin only, cannot delete system roles)"""
    try:
        role_service.delete_role(role_id=role_id)
        return None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin only: Activate role
@router.post("/{role_id}/activate", response_model=RoleResponse)
@check_global_permissions(GlobalPermissionEnum.MANAGE_ROLES)
def activate_role(
    *,
    role_id: uuid.UUID,
    role_service: RoleService = Depends(get_role_service),
    token: TokenData = Depends(verify_token),
):
    """Activate a role (Admin only)"""
    try:
        role = role_service.activate_role(role_id=role_id)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return role
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin only: Deactivate role
@router.post("/{role_id}/deactivate", response_model=RoleResponse)
@check_global_permissions(GlobalPermissionEnum.MANAGE_ROLES)
def deactivate_role(
    *,
    role_id: uuid.UUID,
    role_service: RoleService = Depends(get_role_service),
    token: TokenData = Depends(verify_token),
):
    """Deactivate a role (Admin only, cannot deactivate system roles)"""
    try:
        role = role_service.deactivate_role(role_id=role_id)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return role
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin only: Assign permissions to role
@router.post("/{role_id}/permissions", response_model=RoleDetailResponse)
@check_global_permissions(GlobalPermissionEnum.MANAGE_ROLES)
def assign_permissions_to_role(
    *,
    role_id: uuid.UUID,
    payload: RolePermissionAssignRequest,
    role_service: RoleService = Depends(get_role_service),
    token: TokenData = Depends(verify_token),
):
    """Assign permissions to a role (Admin only)"""
    try:
        role = role_service.assign_permissions(role_id=role_id, permission_ids=payload.permission_ids)
        return role
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin only: Remove permissions from role
@router.delete("/{role_id}/permissions", response_model=RoleDetailResponse)
@check_global_permissions(GlobalPermissionEnum.MANAGE_ROLES)
def remove_permissions_from_role(
    *,
    role_id: uuid.UUID,
    payload: RolePermissionRemoveRequest,
    role_service: RoleService = Depends(get_role_service),
    token: TokenData = Depends(verify_token),
):
    """Remove permissions from a role (Admin only)"""
    try:
        role = role_service.remove_permissions(role_id=role_id, permission_ids=payload.permission_ids)
        return role
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ==================== PERMISSION ENDPOINTS ====================

# Admin only: Create permission
@router.post("/permissions/", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
@check_global_permissions(GlobalPermissionEnum.MANAGE_ROLES)
def create_permission(
    *,
    payload: PermissionCreate,
    permission_service: PermissionService = Depends(get_permission_service),
    token: TokenData = Depends(verify_token),
):
    """Create a new permission (Admin only)"""
    try:
        permission = permission_service.create_permission(payload=payload)
        return permission
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin only: List permissions
@router.get("/permissions/", response_model=ListPermissionsResponse)
@check_global_permissions(GlobalPermissionEnum.MANAGE_ROLES)
def list_permissions(
    *,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    q: Optional[str] = Query(None, description="Search by name or slug"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    permission_service: PermissionService = Depends(get_permission_service),
    token: TokenData = Depends(verify_token),
):
    """List all permissions (Admin only)"""
    try:
        permissions = permission_service.search(
            q=q,
            category=category,
            is_active=is_active,
            skip=skip,
            limit=limit,
        )
        
        filters_dict = {}
        if q:
            filters_dict["q"] = q
        if category:
            filters_dict["category"] = category
        if is_active is not None:
            filters_dict["is_active"] = is_active
        
        filters = PermissionFilters(**filters_dict) if filters_dict else None
        total = permission_service.count_permissions(filters=filters)
        
        return ListPermissionsResponse(
            total=total,
            items=[PermissionResponse.model_validate(perm) for perm in permissions]
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin only: Get permission by ID
@router.get("/permissions/{permission_id}", response_model=PermissionResponse)
@check_global_permissions(GlobalPermissionEnum.MANAGE_ROLES)
def get_permission(
    *,
    permission_id: uuid.UUID,
    permission_service: PermissionService = Depends(get_permission_service),
    token: TokenData = Depends(verify_token),
):
    """Get permission by ID (Admin only)"""
    permission = permission_service.get_permission(permission_id=permission_id)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return permission


# Admin only: Update permission
@router.patch("/permissions/{permission_id}", response_model=PermissionResponse)
@check_global_permissions(GlobalPermissionEnum.MANAGE_ROLES)
def update_permission(
    *,
    permission_id: uuid.UUID,
    payload: PermissionUpdate,
    permission_service: PermissionService = Depends(get_permission_service),
    token: TokenData = Depends(verify_token),
):
    """Update permission (Admin only)"""
    try:
        permission = permission_service.update_permission(permission_id=permission_id, payload=payload)
        if not permission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
        return permission
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin only: Delete permission
@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
@check_global_permissions(GlobalPermissionEnum.MANAGE_ROLES)
def delete_permission(
    *,
    permission_id: uuid.UUID,
    permission_service: PermissionService = Depends(get_permission_service),
    token: TokenData = Depends(verify_token),
):
    """Delete permission (Admin only, cannot delete system permissions)"""
    try:
        permission_service.delete_permission(permission_id=permission_id)
        return None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin only: Activate permission
@router.post("/permissions/{permission_id}/activate", response_model=PermissionResponse)
@check_global_permissions(GlobalPermissionEnum.MANAGE_ROLES)
def activate_permission(
    *,
    permission_id: uuid.UUID,
    permission_service: PermissionService = Depends(get_permission_service),
    token: TokenData = Depends(verify_token),
):
    """Activate a permission (Admin only)"""
    try:
        permission = permission_service.activate_permission(permission_id=permission_id)
        if not permission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
        return permission
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin only: Deactivate permission
@router.post("/permissions/{permission_id}/deactivate", response_model=PermissionResponse)
@check_global_permissions(GlobalPermissionEnum.MANAGE_ROLES)
def deactivate_permission(
    *,
    permission_id: uuid.UUID,
    permission_service: PermissionService = Depends(get_permission_service),
    token: TokenData = Depends(verify_token),
):
    """Deactivate a permission (Admin only, cannot deactivate system permissions)"""
    try:
        permission = permission_service.deactivate_permission(permission_id=permission_id)
        if not permission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
        return permission
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin only: Get permissions by category
@router.get("/permissions/categories/{category}", response_model=ListPermissionsResponse)
@check_global_permissions(GlobalPermissionEnum.MANAGE_ROLES)
def get_permissions_by_category(
    *,
    category: str,
    permission_service: PermissionService = Depends(get_permission_service),
    token: TokenData = Depends(verify_token),
):
    """Get all permissions by category (Admin only)"""
    try:
        permissions = permission_service.get_permissions_by_category(category=category)
        return ListPermissionsResponse(
            total=len(permissions),
            items=[PermissionResponse.model_validate(perm) for perm in permissions]
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
