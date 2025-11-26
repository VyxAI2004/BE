import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
)
from services.sale_smart_ai_app.user import UserService
from repositories.user import UserFilters

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

@router.get("/me/permissions", response_model=List[str])
def get_my_permissions(
    user_from_token: TokenData = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get current user's permissions"""
    from services.sale_smart_ai_app.permission import PermissionService
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
