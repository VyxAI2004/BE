import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from sqlalchemy.orm import Session
from core.dependencies.auth import verify_token
from core.dependencies.db import get_db
from schemas.auth import TokenData

from core.dependencies.services import get_user_service
from schemas.user import (
    ListUsersResponse,
    UserResponse,
    UserCreate,
    UserUpdate,
    UserPromoteRequest,
)
from schemas.role import UserRoleCreate
from services.core.user import UserService
from repositories.user import UserFilters
from models.user import User
from middlewares.permissions import check_global_permissions
from shared.enums import GlobalPermissionEnum, RoleEnum
from core.settings import settings

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserResponse)
def create_user(
    *,
    payload: UserCreate,
    user_service: UserService = Depends(get_user_service),
):
    """Create new user"""
    try:
        user = user_service.create_user(payload=payload)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/me", response_model=UserResponse)
def get_my_profile(
    user_from_token: TokenData = Depends(verify_token),
    user_service: UserService = Depends(get_user_service),
):
    """Get current user's profile"""
    user = user_service.get_user(user_id=user_from_token.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@router.patch("/me", response_model=UserResponse)
def update_my_profile(
    *,
    payload: UserUpdate,
    user_from_token: TokenData = Depends(verify_token),
    user_service: UserService = Depends(get_user_service),
):
    """Update current user's profile"""
    user = user_service.update_user(user_id=user_from_token.user_id, payload=payload)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@router.get("/me/permissions", response_model=List[str])
def get_my_permissions(
    user_from_token: TokenData = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get current user's permissions"""
    from services.core.permission import PermissionService
    permission_service = PermissionService(db)
    return permission_service.get_user_permissions(user_id=user_from_token.user_id)

    
@router.get("/", response_model=ListUsersResponse)
def get_list_users(
    *,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    q: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    user_service: UserService = Depends(get_user_service),
    user_from_token: TokenData = Depends(verify_token),
):
    try:
        users = user_service.search(
            q=q,
            username=username,
            email=email,
            skip=skip,
            limit=limit,
        )
        total = user_service.count_users(
            filters=UserFilters(q=q, username=username, email=email)
        )
        return ListUsersResponse(
            total=total,
            items=[UserResponse.model_validate(user) for user in users]
)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    *,
    user_id: uuid.UUID,
    user_service: UserService = Depends(get_user_service),
    user_from_token: TokenData = Depends(verify_token),
):
    user = user_service.get_user(user_id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    *,
    user_id: uuid.UUID,
    payload: UserUpdate,
    user_service: UserService = Depends(get_user_service),
    user_from_token: TokenData = Depends(verify_token),
):
    user = user_service.update_user(user_id=user_id, payload=payload)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    *,
    user_id: uuid.UUID,
    user_service: UserService = Depends(get_user_service),
    user_from_token: TokenData = Depends(verify_token),
):
    try:
        user_service.delete_user(user_id=user_id)
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ROLE MANAGEMENT ENDPOINTS ====================

@router.post("/{user_id}/roles/{role_id}", response_model=UserResponse)
@check_global_permissions(GlobalPermissionEnum.ASSIGN_ROLES)
def assign_role_to_user(
    *,
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    user_service: UserService = Depends(get_user_service),
    token: TokenData = Depends(verify_token),
):
    """Assign a role to a user (Admin only)"""
    try:
        user = user_service.assign_role_to_user(user_id=user_id, role_id=role_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{user_id}/roles/{role_id}", response_model=UserResponse)
@check_global_permissions(GlobalPermissionEnum.ASSIGN_ROLES)
def remove_role_from_user(
    *,
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    user_service: UserService = Depends(get_user_service),
    token: TokenData = Depends(verify_token),
):
    """Remove a role from a user (Admin only)"""
    try:
        user = user_service.remove_role_from_user(user_id=user_id, role_id=role_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{user_id}/promote", response_model=UserResponse)
def promote_user_to_admin(
    *,
    user_id: uuid.UUID,
    payload: UserPromoteRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    user_service: UserService = Depends(get_user_service),
    token: TokenData = Depends(verify_token),
    db: Session = Depends(get_db),
):

    try:
        # 1. Validate Admin Secret Key
        if not settings.validate_admin_secret_key(x_admin_secret):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid admin secret key"
            )
        
        # 2. Check if requester is Super Admin
        from services.core.permission import PermissionService
        permission_service = PermissionService(db)
        user_permissions = permission_service.get_user_permissions(user_id=token.user_id)
        
        # Get user roles to check if super admin
        from models.role import UserRole, Role
        user_roles = db.query(Role).join(UserRole).filter(
            UserRole.user_id == token.user_id
        ).all()
        
        is_super_admin = any(role.slug == RoleEnum.SUPER_ADMIN for role in user_roles)
        
        if not is_super_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Super Admin can promote users to admin/super_admin roles"
            )
        
        # 3. Promote user
        user = user_service.promote_user_to_admin(
            user_id=user_id,
            role_slug=payload.role_slug,
            promoted_by=token.user_id,
            reason=payload.reason
        )
        
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        return user
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
