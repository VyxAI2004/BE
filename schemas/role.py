from datetime import datetime
from typing import Optional, List, Annotated
from uuid import UUID
from pydantic import BaseModel, Field


class PermissionBase(BaseModel):
    """Base schema for Permission model"""
    name: Annotated[str, Field(min_length=1, max_length=100)]
    slug: Annotated[str, Field(min_length=1, max_length=100)]
    description: Optional[str] = None
    category: Annotated[str, Field(min_length=1, max_length=50)]
    is_active: Optional[bool] = True


class PermissionCreate(PermissionBase):
    """Schema for creating a permission"""
    is_system_permission: Optional[bool] = False


class PermissionUpdate(BaseModel):
    """Schema for updating a permission"""
    name: Optional[Annotated[str, Field(min_length=1, max_length=100)]] = None
    slug: Optional[Annotated[str, Field(min_length=1, max_length=100)]] = None
    description: Optional[str] = None
    category: Optional[Annotated[str, Field(min_length=1, max_length=50)]] = None
    is_active: Optional[bool] = None


class PermissionResponse(PermissionBase):
    """Schema for permission response"""
    id: UUID
    is_system_permission: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    """Base schema for Role model"""
    name: Annotated[str, Field(min_length=1, max_length=50)]
    slug: Annotated[str, Field(min_length=1, max_length=50)]
    description: Optional[str] = None
    priority: Optional[int] = 100
    is_active: Optional[bool] = True


class RoleCreate(RoleBase):
    """Schema for creating a role"""
    is_system_role: Optional[bool] = False
    permission_ids: Optional[List[UUID]] = None


class RoleUpdate(BaseModel):
    """Schema for updating a role"""
    name: Optional[Annotated[str, Field(min_length=1, max_length=50)]] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    permission_ids: Optional[List[UUID]] = None


class RolePermissionResponse(BaseModel):
    """Schema for role-permission relationship"""
    permission: PermissionResponse
    is_explicitly_granted: bool

    class Config:
        from_attributes = True


class RoleResponse(RoleBase):
    """Schema for role response (without permissions)"""
    id: UUID
    is_system_role: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoleDetailResponse(RoleResponse):
    """Schema for detailed role response (with permissions)"""
    permissions: List[RolePermissionResponse] = []

    class Config:
        from_attributes = True


class ListRolesResponse(BaseModel):
    """Schema for list roles response"""
    items: List[RoleResponse]
    total: int

    class Config:
        from_attributes = True


class ListRoleDetailsResponse(BaseModel):
    """Schema for list detailed roles response"""
    items: List[RoleDetailResponse]
    total: int

    class Config:
        from_attributes = True


class ListPermissionsResponse(BaseModel):
    """Schema for list permissions response"""
    items: List[PermissionResponse]
    total: int

    class Config:
        from_attributes = True


class UserRoleCreate(BaseModel):
    """Schema for assigning a role to a user"""
    role_id: UUID
    assigned_reason: Optional[str] = None


class UserRoleResponse(BaseModel):
    """Schema for user-role relationship"""
    id: UUID
    user_id: UUID
    role: RoleResponse
    assigned_at: Optional[str] = None
    assigned_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BulkAssignRoleRequest(BaseModel):
    """Schema for bulk assigning roles to users"""
    user_ids: List[UUID] = Field(..., min_items=1)
    role_id: UUID
    reason: Optional[str] = None


class BulkAssignRoleResponse(BaseModel):
    """Schema for bulk assign response"""
    message: str
    assigned_count: int


class RolePermissionAssignRequest(BaseModel):
    """Schema for assigning permissions to role"""
    permission_ids: List[UUID] = Field(..., min_items=1)


class RolePermissionRemoveRequest(BaseModel):
    """Schema for removing permissions from role"""
    permission_ids: List[UUID] = Field(..., min_items=1)