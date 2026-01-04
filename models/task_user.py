"""
Model cho TaskUser - Task collaborators & permissions
"""
from typing import TYPE_CHECKING, Optional
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .task import Task
    from .user import User


class TaskUser(Base):
    """Model cho bảng task_users - quản lý collaborators của task"""
    __tablename__ = "task_users"

    # Columns
    task_id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="collaborator"
    )  # read_only, editor, collaborator
    permissions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    invited_by: Mapped[Optional[str]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    # Relationships
    task: Mapped["Task"] = relationship(
        "Task",
        back_populates="task_users",
        lazy="select"
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="task_memberships",
        foreign_keys=[user_id],
        lazy="select"
    )
    inviter: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="invited_task_memberships",
        foreign_keys=[invited_by],
        lazy="select"
    )
