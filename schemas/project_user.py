from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr

from shared.enums import ProjectRoleEnum

class ProjectUserBase(BaseModel):
    """Base schema for ProjectUser model"""
    project_id: UUID
    user_id: UUID
    role_id: Optional[UUID] = None
    permissions: Optional[dict] = None
    is_active: Optional[bool] = True

class ProjectUserCreate(ProjectUserBase):
    """Schema for creating project user membership"""
    invited_by: Optional[UUID] = None

class ProjectUserInviteRequest(BaseModel):
    """Schema for inviting user by email"""
    email: EmailStr
    role: Optional[str] = "member"  # owner, admin, member, viewer

class ProjectUserUpdate(BaseModel):
    """Schema for updating project user membership"""
    role_id: Optional[UUID] = None
    role: Optional[str] = None
    permissions: Optional[dict] = None
    is_active: Optional[bool] = None

class ProjectUserUpdateRoleRequest(BaseModel):
    """Schema for updating project user role"""
    role: str  # owner, admin, member, viewer

class ProjectUserResponse(ProjectUserBase):
    """Schema for project user response"""
    id: UUID
    joined_at: Optional[datetime] = None
    invited_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProjectMemberResponse(BaseModel):
    """Schema for project member info - for task assignment"""
    id: UUID  # User ID, not ProjectUser ID
    name: str
    email: str
    
    class Config:
        from_attributes = True

class ProjectMemberDetailResponse(BaseModel):
    """Schema for detailed project member info"""
    id: UUID  # User ID
    name: str
    email: str
    role: Optional[str] = None
    status: Optional[str] = None
    
    class Config:
        from_attributes = True

class ProjectUserInviteResponse(BaseModel):
    """Schema for invite response"""
    id: UUID
    project_id: UUID
    user_id: UUID
    role: str
    status: str
    invited_at: datetime
    is_active: bool

    class Config:
        from_attributes = True

class ProjectMemberAssignRequest(BaseModel):
    """Schema for assigning multiple users to project"""
    user_ids: List[UUID]
    role_id: Optional[UUID] = None
    permissions: Optional[dict] = None

class ProjectMemberRemoveRequest(BaseModel):
    """Schema for removing users from project"""
    user_ids: List[UUID]