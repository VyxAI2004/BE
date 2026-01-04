"""
Schemas cho ProductUser - Product membership & invitations
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class ProductUserBase(BaseModel):
    """Base schema for ProductUser"""
    product_id: UUID
    user_id: UUID
    role_id: Optional[UUID] = None
    permissions: Optional[dict] = None
    is_active: Optional[bool] = True


class ProductUserCreate(ProductUserBase):
    """Schema for creating product user membership"""
    invited_by: Optional[UUID] = None


class ProductUserUpdate(BaseModel):
    """Schema for updating product user membership"""
    role_id: Optional[UUID] = None
    permissions: Optional[dict] = None
    is_active: Optional[bool] = None


class ProductUserResponse(ProductUserBase):
    """Schema for product user response"""
    id: UUID
    invited_at: Optional[datetime] = None
    invited_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    role_name: Optional[str] = None

    class Config:
        from_attributes = True


class ProductInviteRequest(BaseModel):
    """Schema for inviting user to product"""
    user_email: str
    role_id: Optional[UUID] = None
    permissions: Optional[dict] = None


class ProductMemberResponse(BaseModel):
    """Schema for product member with user details"""
    id: UUID
    product_id: UUID
    user_id: UUID
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    user_avatar: Optional[str] = None
    role_id: Optional[UUID] = None
    role_name: Optional[str] = None
    is_active: bool
    invited_at: Optional[datetime] = None
    invited_by_name: Optional[str] = None

    class Config:
        from_attributes = True
