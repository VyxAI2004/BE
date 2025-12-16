from typing import TYPE_CHECKING, Optional
from datetime import date
from sqlalchemy import String, Boolean, Date, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .role import UserRole
    from .ai_model import AIModel
    from .project import Project, ProjectUser   
    from .task import Task
    from .activity_log import ActivityLog
    from .attachment import Attachment
    from .comment import Comment


class User(Base):
    """Model cho bảng users"""
    __tablename__ = "users"
    
    # Columns
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, server_default="true", nullable=True)
    # Settings fields
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, default="en")
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    urls: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Store as JSON array of URLs
    
    # Relationships
    roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", 
        back_populates="user", 
        cascade="all, delete-orphan",
        lazy="select"
    )
    # Quan hệ với user_ai_models (nhiều user_ai_model cho 1 user)
    user_ai_models = relationship(
        "UserAIModel",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select"
    )
    created_projects: Mapped[list["Project"]] = relationship(
        "Project", 
        back_populates="creator", 
        foreign_keys="[Project.created_by]",
        lazy="select"
    )
    assigned_projects: Mapped[list["Project"]] = relationship(
        "Project", 
        back_populates="assignee", 
        foreign_keys="[Project.assigned_to]",
        lazy="select"
    )
    project_memberships: Mapped[list["ProjectUser"]] = relationship(
        "ProjectUser", 
        back_populates="user",
        foreign_keys="[ProjectUser.user_id]", 
        lazy="select"
    )
    invited_project_memberships: Mapped[list["ProjectUser"]] = relationship(
        "ProjectUser",
        back_populates="inviter",
        foreign_keys="[ProjectUser.invited_by]",
        lazy="select"
    )
    assigned_tasks: Mapped[list["Task"]] = relationship(
        "Task", 
        back_populates="assignee",
        lazy="select"
    )
    activity_logs: Mapped[list["ActivityLog"]] = relationship(
        "ActivityLog", 
        back_populates="user",
        lazy="select"
    )
    uploaded_attachments: Mapped[list["Attachment"]] = relationship(
        "Attachment", 
        back_populates="uploader",
        lazy="select"
    )
    comments: Mapped[list["Comment"]] = relationship(
        "Comment", 
        back_populates="user",
        lazy="select"
    )
