"""
Schemas for Team and TeamUser
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class UserBaseSchema(BaseModel):
    """Base schema for user info"""
    user_id: uuid.UUID
    username: str
    email: str
    full_name: str

    class Config:
        from_attributes = True


class TeamUserCreate(BaseModel):
    """Schema for creating a TeamUser"""
    team_id: uuid.UUID
    user_id: uuid.UUID
    role: str = Field(default="member", pattern="^(owner|lead|member)$")
    status: str = Field(default="active", pattern="^(active|pending|inactive)$")
    invited_by: Optional[uuid.UUID] = None
    is_active: bool = True
    invited_at: Optional[datetime] = None
    joined_at: Optional[datetime] = None


class TeamUserUpdate(BaseModel):
    """Schema for updating a TeamUser"""
    role: Optional[str] = Field(None, pattern="^(owner|lead|member)$")
    status: Optional[str] = Field(None, pattern="^(active|pending|inactive)$")
    is_active: Optional[bool] = None


class TeamUserResponse(BaseModel):
    """Response schema for TeamUser with user details"""
    id: uuid.UUID
    team_id: uuid.UUID
    user_id: uuid.UUID
    username: str
    email: str
    full_name: str
    role: str  # owner, lead, member
    status: str  # active, pending, inactive
    is_active: bool
    joined_at: datetime
    invited_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TeamCreate(BaseModel):
    """Schema for creating a team"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    created_by: Optional[uuid.UUID] = None  # Set by service, not by user


class TeamUpdate(BaseModel):
    """Schema for updating a team"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)


class TeamResponse(BaseModel):
    """Response schema for Team"""
    id: uuid.UUID
    name: str
    description: Optional[str]
    created_by: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    members: Optional[List[TeamUserResponse]] = []

    class Config:
        from_attributes = True


class TeamInviteRequest(BaseModel):
    """Request schema for inviting a user to team"""
    email: str = Field(..., description="Email of user to invite")
    role: str = Field(default="member", description="Role: owner, lead, member")


class TeamMemberUpdate(BaseModel):
    """Request schema for updating team member role"""
    role: str = Field(..., description="New role: owner, lead, member")


class ListTeamsResponse(BaseModel):
    """Response schema for listing teams"""
    total: int
    items: List[TeamResponse]

    class Config:
        from_attributes = True
