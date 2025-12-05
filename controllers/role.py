import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from core.dependencies.auth import verify_token
from schemas.auth import TokenData
from core.dependencies.services import get_role_service
from schemas.role import (
    ListRolesResponse,
    RoleResponse,
    RoleDetailResponse,
    RoleCreate,
    RoleUpdate,
    RolePermissionAssignRequest,
    RolePermissionRemoveRequest,
)
from services.core.role import RoleService
from repositories.role import RoleFilters
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



