"""
Model cho TeamUser - Team membership & permissions
"""
from typing import TYPE_CHECKING, Optional
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func, Enum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .base import Base
from shared.enums import TeamRoleEnum

if TYPE_CHECKING:
    from .team import Team
    from .user import User


class TeamUser(Base):
    """Model cho bảng team_users - quản lý thành viên của team"""
    __tablename__ = "team_users"

    # Columns
    team_id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(
        String(20), server_default=TeamRoleEnum.MEMBER.value, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), server_default="active", nullable=False  # active, pending, inactive
    )
    invited_by: Mapped[Optional[str]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    
    # Timestamps (specific to TeamUser)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    invited_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    team: Mapped["Team"] = relationship(
        "Team",
        back_populates="members",
        lazy="select"
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="team_memberships",
        lazy="select",
        foreign_keys=[user_id]
    )
    invited_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[invited_by],
        lazy="select"
    )
