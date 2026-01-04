"""
Model cho ProjectUser - Project membership & permissions
"""
from typing import TYPE_CHECKING, Optional
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func, Enum
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .base import Base

if TYPE_CHECKING:
    from .project import Project
    from .user import User
    from .role import Role


class ProjectUserRole(str, enum.Enum):
    """Enum cho roles của project user"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class ProjectUser(Base):
    """Model cho bảng project_users - quản lý thành viên của project"""
    __tablename__ = "project_users"

    # Columns
    project_id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(
        String(20), server_default=ProjectUserRole.MEMBER.value, nullable=False
    )
    role_id: Mapped[Optional[str]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("roles.id", ondelete="SET NULL"), nullable=True
    )
    permissions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    invited_by: Mapped[Optional[str]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), server_default="pending", nullable=False  # pending, accepted, declined
    )
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="members",
        lazy="select"
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="project_memberships",
        foreign_keys=[user_id],
        lazy="select"
    )
    inviter: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="invited_project_memberships",
        foreign_keys=[invited_by],
        lazy="select"
    )
    role_obj: Mapped[Optional["Role"]] = relationship(
        "Role",
        lazy="select",
        foreign_keys=[role_id]
    )
