"""
Controller cho Task Collaborator Management & Invitations
"""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.dependencies.db import get_db
from core.dependencies.auth import verify_token, TokenData
from services.core.task_user import TaskUserService
from services.core.task import TaskService
from services.core.user import UserService
from schemas.task_user import (
    TaskUserResponse,
    TaskInviteRequest,
    TaskCollaboratorResponse,
    TaskUserUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Task Collaborators"])


def get_task_user_service(db: Session = Depends(get_db)) -> TaskUserService:
    """Dependency để get TaskUserService"""
    return TaskUserService(db)


def get_task_service(db: Session = Depends(get_db)) -> TaskService:
    """Dependency để get TaskService"""
    return TaskService(db)


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Dependency để get UserService"""
    return UserService(db)


@router.post("/{task_id}/invite", response_model=TaskCollaboratorResponse, status_code=status.HTTP_201_CREATED)
def invite_collaborator(
    task_id: UUID,
    payload: TaskInviteRequest,
    token: TokenData = Depends(verify_token),
    task_user_service: TaskUserService = Depends(get_task_user_service),
    task_service: TaskService = Depends(get_task_service),
    user_service: UserService = Depends(get_user_service),
):
    """Mời user làm collaborator trên task - chỉ task creator/assigned được"""
    try:
        # Get task
        task = task_service.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Check authorization - only creator or assigned can invite
        is_creator = task.created_by == token.user_id
        is_assigned = task.assigned_to == token.user_id
        
        if not (is_creator or is_assigned):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only task creator or assigned user can invite collaborators"
            )
        
        # Find target user by email
        target_user = user_service.get_by_email(payload.user_email)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with email {payload.user_email} not found"
            )
        
        # Check if already invited
        existing = task_user_service.repository.get_by_task_and_user(task_id, target_user.id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a collaborator on this task"
            )
        
        # Create invitation
        task_user = task_user_service.invite_collaborator(
            task_id=task_id,
            user=target_user,
            role=payload.role,
            invited_by_id=token.user_id,
        )
        
        # Build response
        return TaskCollaboratorResponse(
            id=task_user.id,
            task_id=task_user.task_id,
            user_id=task_user.user_id,
            user_name=target_user.full_name,
            user_email=target_user.email,
            user_avatar=target_user.avatar_url,
            role=task_user.role,
            is_active=task_user.is_active,
            invited_at=task_user.invited_at,
            invited_by_name=token.user_id,
            can_view=True,
            can_edit=task_user.role in ["editor", "collaborator"],
            can_comment=True,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inviting collaborator: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error inviting collaborator: {str(e)}"
        )


@router.get("/{task_id}/collaborators", response_model=List[TaskCollaboratorResponse])
def get_task_collaborators(
    task_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    token: TokenData = Depends(verify_token),
    task_user_service: TaskUserService = Depends(get_task_user_service),
):
    """Lấy danh sách collaborators của task"""
    try:
        collaborators = task_user_service.get_task_collaborators(
            task_id=task_id,
            skip=skip,
            limit=limit,
            is_active_only=True
        )
        
        # Build response with user details
        result = []
        for collab in collaborators:
            user = collab.user
            result.append(
                TaskCollaboratorResponse(
                    id=collab.id,
                    task_id=collab.task_id,
                    user_id=collab.user_id,
                    user_name=user.full_name if user else None,
                    user_email=user.email if user else None,
                    user_avatar=user.avatar_url if user else None,
                    role=collab.role,
                    is_active=collab.is_active,
                    invited_at=collab.invited_at,
                    invited_by_name=collab.inviter.full_name if collab.inviter else None,
                    can_view=True,
                    can_edit=collab.role in ["editor", "collaborator"],
                    can_comment=True,
                )
            )
        
        return result
    except Exception as e:
        logger.error(f"Error getting task collaborators: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching collaborators"
        )


@router.patch("/{task_id}/collaborators/{user_id}", response_model=TaskCollaboratorResponse)
def update_collaborator_role(
    task_id: UUID,
    user_id: UUID,
    payload: TaskUserUpdate,
    token: TokenData = Depends(verify_token),
    task_user_service: TaskUserService = Depends(get_task_user_service),
    task_service: TaskService = Depends(get_task_service),
):
    """Cập nhật role của collaborator trên task"""
    try:
        # Get task for authorization
        task = task_service.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Check authorization
        is_creator = task.created_by == token.user_id
        is_assigned = task.assigned_to == token.user_id
        
        if not (is_creator or is_assigned):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only task creator or assigned user can update collaborators"
            )
        
        collaborator = task_user_service.update_collaborator_role(
            task_id=task_id,
            user_id=user_id,
            role=payload.role or "collaborator",
            permissions=payload.permissions,
        )
        
        if not collaborator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collaborator not found"
            )
        
        user = collaborator.user
        return TaskCollaboratorResponse(
            id=collaborator.id,
            task_id=collaborator.task_id,
            user_id=collaborator.user_id,
            user_name=user.full_name if user else None,
            user_email=user.email if user else None,
            user_avatar=user.avatar_url if user else None,
            role=collaborator.role,
            is_active=collaborator.is_active,
            invited_at=collaborator.invited_at,
            can_view=True,
            can_edit=collaborator.role in ["editor", "collaborator"],
            can_comment=True,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating collaborator: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error updating collaborator"
        )


@router.delete("/{task_id}/collaborators/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_collaborator(
    task_id: UUID,
    user_id: UUID,
    token: TokenData = Depends(verify_token),
    task_user_service: TaskUserService = Depends(get_task_user_service),
    task_service: TaskService = Depends(get_task_service),
):
    """Xoá collaborator khỏi task"""
    try:
        # Get task for authorization
        task = task_service.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # Check authorization
        is_creator = task.created_by == token.user_id
        is_assigned = task.assigned_to == token.user_id
        
        if not (is_creator or is_assigned):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only task creator or assigned user can remove collaborators"
            )
        
        success = task_user_service.remove_from_task(
            task_id=task_id,
            user_id=user_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collaborator not found"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing collaborator: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error removing collaborator"
        )
