"""
Model cho Team - Team/Department level
"""
from typing import TYPE_CHECKING, Optional
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, func, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User
    from .project import Project
    from .team_user import TeamUser


class Team(Base):
    """Model cho bảng teams - Team/Department level management"""
    __tablename__ = "teams"

    # Columns
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now()
    )

    # Relationships
    creator: Mapped["User"] = relationship(
        "User",
        back_populates="created_teams",
        foreign_keys=[created_by],
        lazy="select"
    )
    members: Mapped[list["TeamUser"]] = relationship(
        "TeamUser",
        back_populates="team",
        cascade="all, delete-orphan",
        lazy="noload"
    )
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="team",
        cascade="all, delete-orphan",
        lazy="select"
    )
