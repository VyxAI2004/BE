import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from core.dependencies.auth import verify_token
from schemas.auth import TokenData
from core.dependencies.services import get_permission_service
from schemas.role import (
    ListPermissionsResponse,
    PermissionResponse,
    PermissionCreate,
    PermissionUpdate,
)
from services.core.permission import PermissionService
from repositories.permission import PermissionFilters
from middlewares.permissions import check_global_permissions
from shared.enums import GlobalPermissionEnum

router = APIRouter(prefix="/permissions", tags=["permissions"])


# Admin only: Create permission
@router.post("/", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
@check_global_permissions(GlobalPermissionEnum.MANAGE_ROLES)
def create_permission(
    *,
    payload: PermissionCreate,
    permission_service: PermissionService = Depends(get_permission_service),
    token: TokenData = Depends(verify_token),
):
    """Create a new permission (Admin only)"""
    try:
        permission = permission_service.create(payload=payload)
        return permission
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin only: List permissions
@router.get("/", response_model=ListPermissionsResponse)
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
@router.get("/{permission_id}", response_model=PermissionResponse)
@check_global_permissions(GlobalPermissionEnum.MANAGE_ROLES)
def get_permission(
    *,
    permission_id: uuid.UUID,
    permission_service: PermissionService = Depends(get_permission_service),
    token: TokenData = Depends(verify_token),
):
    """Get permission by ID (Admin only)"""
    permission = permission_service.get(id=permission_id)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return permission


# Admin only: Update permission
@router.patch("/{permission_id}", response_model=PermissionResponse)
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
        permission = permission_service.get(id=permission_id)
        if not permission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
            
        updated_permission = permission_service.update(db_obj=permission, payload=payload)
        return updated_permission
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin only: Delete permission
@router.delete("/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
@check_global_permissions(GlobalPermissionEnum.MANAGE_ROLES)
def delete_permission(
    *,
    permission_id: uuid.UUID,
    permission_service: PermissionService = Depends(get_permission_service),
    token: TokenData = Depends(verify_token),
):
    """Delete permission (Admin only, cannot delete system permissions)"""
    try:
        permission = permission_service.get(id=permission_id)
        if not permission:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
             
        if permission.is_system_permission:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete system permission")

        permission_service.delete(id=permission_id)
        return None
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin only: Activate permission
@router.post("/{permission_id}/activate", response_model=PermissionResponse)
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
@router.post("/{permission_id}/deactivate", response_model=PermissionResponse)
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
