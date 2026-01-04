"""
Schemas cho TaskUser - Task collaborators & invitations
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class TaskUserBase(BaseModel):
    """Base schema for TaskUser"""
    task_id: UUID
    user_id: UUID
    role: str = "collaborator"  # read_only, editor, collaborator
    permissions: Optional[dict] = None
    is_active: Optional[bool] = True


class TaskUserCreate(TaskUserBase):
    """Schema for creating task user (collaborator)"""
    invited_by: Optional[UUID] = None
    message: Optional[str] = None


class TaskUserUpdate(BaseModel):
    """Schema for updating task user"""
    role: Optional[str] = None
    permissions: Optional[dict] = None
    is_active: Optional[bool] = None


class TaskUserResponse(TaskUserBase):
    """Schema for task user response"""
    id: UUID
    invited_at: Optional[datetime] = None
    invited_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskInviteRequest(BaseModel):
    """Schema for inviting user to task"""
    user_email: str
    role: str = "collaborator"  # read_only, editor, collaborator
    message: Optional[str] = None


class TaskCollaboratorResponse(BaseModel):
    """Schema for task collaborator with user details"""
    id: UUID
    task_id: UUID
    user_id: UUID
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    user_avatar: Optional[str] = None
    role: str
    is_active: bool
    invited_at: Optional[datetime] = None
    invited_by_name: Optional[str] = None
    can_view: bool = True
    can_edit: bool = False
    can_comment: bool = True

    class Config:
        from_attributes = True
