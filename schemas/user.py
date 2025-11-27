from datetime import datetime
from typing import Optional, List, Annotated
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from schemas.role import UserRoleResponse

class UserBase(BaseModel):
    """Base schema for User model"""
    username: Annotated[str, Field(min_length=3, max_length=50)]
    email: EmailStr
    full_name: Annotated[str, Field(min_length=2, max_length=100)]
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = True

class UserCreate(BaseModel):
    username: Annotated[str, Field(min_length=3, max_length=50)]
    email: EmailStr
    password_hash: str 
    full_name: Annotated[str, Field(min_length=2, max_length=100)]
    is_active: Optional[bool] = True

class UserUpdate(BaseModel):
    """Schema for updating user information"""
    username: Optional[Annotated[str, Field(min_length=3, max_length=50)]] = None
    email: Optional[EmailStr] = None
    full_name: Optional[Annotated[str, Field(min_length=2, max_length=100)]] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None

class UserChangePassword(BaseModel):
    """Schema for changing password"""
    current_password: str
    new_password: Annotated[str, Field(min_length=8)]

class UserResetPassword(BaseModel):
    """Schema for resetting password"""
    reset_token: str
    new_password: Annotated[str, Field(min_length=8)]

class UserUpdateInternal(UserUpdate):
    """Schema for internal user updates (with hashed password)"""
    password_hash: Optional[str] = None

class UserResponse(UserBase):
    """Schema for user response"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    roles: List[UserRoleResponse] = []

    class Config:
        from_attributes = True


class ListUsersResponse(BaseModel):
    """Schema for list users response"""
    items: List[UserResponse]
    total: int

    class Config:
        from_attributes = True

    
class UserPromoteRequest(BaseModel):
    """Schema for promoting user to admin/super_admin"""
    role_slug: Annotated[str, Field(pattern="^(admin|super_admin)$")]
    reason: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "role_slug": "admin",
                "reason": "Promoted to admin for managing projects"
            }
        }