from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Text, Boolean, DateTime, Date, Integer, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .project import Project
    from .crawl_session import CrawlSession
    from .user import User
    from .ai_model import AIModel
    from .attachment import Attachment
    from .comment import Comment


class Task(Base):
    """Model cho bảng tasks"""
    __tablename__ = "tasks"
    
    # Columns
    project_id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    crawl_session_id: Mapped[Optional[str]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("crawl_sessions.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    pipeline_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    stage_order: Mapped[int] = mapped_column(Integer, nullable=False)
    task_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Thứ tự ưu tiên của task (1-5)")

    task_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(20), server_default="pending", nullable=True)
    priority: Mapped[Optional[str]] = mapped_column(String(20), server_default="medium", nullable=True)

    assigned_to: Mapped[Optional[str]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_model_id: Mapped[Optional[str]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ai_models.id", ondelete="SET NULL"), nullable=True
    )

    due_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    completed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_hours: Mapped[Optional[Numeric]] = mapped_column(Numeric(5, 2), nullable=True)
    actual_hours: Mapped[Optional[Numeric]] = mapped_column(Numeric(5, 2), nullable=True)
    stage_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="tasks", lazy="select")
    crawl_session: Mapped[Optional["CrawlSession"]] = relationship("CrawlSession", back_populates="tasks", lazy="select")
    assignee: Mapped[Optional["User"]] = relationship("User", back_populates="assigned_tasks", lazy="select")
    assigned_model: Mapped[Optional["AIModel"]] = relationship("AIModel", back_populates="assigned_tasks", lazy="select")

    subtasks: Mapped[list["Subtask"]] = relationship(
        "Subtask", back_populates="task", cascade="all, delete-orphan", lazy="select"
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        "Attachment", back_populates="task", cascade="all, delete-orphan", lazy="select"
    )
    comments: Mapped[list["Comment"]] = relationship(
        "Comment", back_populates="task", cascade="all, delete-orphan", lazy="select"
    )


class Subtask(Base):
    """Model cho bảng subtasks"""
    __tablename__ = "subtasks"
    
    # Columns
    task_id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    completed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    due_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    
    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="subtasks", lazy="select")
