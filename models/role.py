from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Text, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User
    from .project import ProjectUser


class Role(Base):
    """Model cho bảng roles (quản lý vai trò người dùng)"""
    __tablename__ = "roles"
    
    # Columns
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_system_role: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, server_default="100", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    
    # Relationships
    users: Mapped[list["UserRole"]] = relationship(
        "UserRole", 
        back_populates="role", 
        cascade="all, delete-orphan",
        lazy="select"
    )
    permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission", 
        back_populates="role", 
        cascade="all, delete-orphan",
        lazy="select"
    )
    project_users: Mapped[list["ProjectUser"]] = relationship(
        "ProjectUser",
        back_populates="role",
        lazy="select",
    )


class Permission(Base):
    """Model cho bảng permissions (quản lý quyền hạn)"""
    __tablename__ = "permissions"
    
    # Columns
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    is_system_permission: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    
    # Relationships
    roles: Mapped[list["RolePermission"]] = relationship(
        "RolePermission", 
        back_populates="permission", 
        cascade="all, delete-orphan",
        lazy="select"
    )


class UserRole(Base):
    """Junction table cho User-Role many-to-many relationship"""
    __tablename__ = "user_roles"
    
    # Columns
    user_id: Mapped[str] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id: Mapped[str] = mapped_column(PGUUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    assigned_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User", 
        back_populates="roles",
        lazy="select"
    )
    role: Mapped["Role"] = relationship(
        "Role", 
        back_populates="users",
        lazy="select"
    )


class RolePermission(Base):
    """Junction table cho Role-Permission many-to-many relationship"""
    __tablename__ = "role_permissions"
    
    # Columns
    role_id: Mapped[str] = mapped_column(PGUUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id: Mapped[str] = mapped_column(PGUUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)
    is_explicitly_granted: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    
    # Relationships
    role: Mapped["Role"] = relationship(
        "Role", 
        back_populates="permissions",
        lazy="select"
    )
    permission: Mapped["Permission"] = relationship(
        "Permission", 
        back_populates="roles",
        lazy="select"
    )
