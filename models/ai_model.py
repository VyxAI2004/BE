from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User
    from .project import Project
    from .product_source import ProductSource
    from .crawl_session import CrawlSession
    from .task import Task
    from .activity_log import ActivityLog
    from .product import PriceAnalysis

class AIModel(Base):
    # Quan hệ với user_ai_models (nhiều user_ai_model cho 1 model)
    user_ai_models = relationship(
        "UserAIModel",
        back_populates="ai_model",
        cascade="all, delete-orphan",
        lazy="select"
    )
    """Model cho bảng ai_models"""
    __tablename__ = "ai_models"
    
    # Columns
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)  # llm, crawler, analyzer
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # openai, anthropic, gemini, custom
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)  # gpt-4, claude-3, etc.
    base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # For custom endpoints
    config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Model configuration
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, server_default='true', nullable=True)
    last_used_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    usage_count: Mapped[Optional[int]] = mapped_column(Integer, server_default='0', nullable=True)
    assigned_projects: Mapped[list["Project"]] = relationship(
        "Project", 
        back_populates="assigned_model",
        lazy="select"
    )
    assigned_sources: Mapped[list["ProductSource"]] = relationship(
        "ProductSource", 
        back_populates="assigned_model",
        lazy="select"
    )
    crawl_sessions: Mapped[list["CrawlSession"]] = relationship(
        "CrawlSession", 
        back_populates="assigned_model",
        lazy="select"
    )
    assigned_tasks: Mapped[list["Task"]] = relationship(
        "Task", 
        back_populates="assigned_model",
        lazy="select"
    )
    activity_logs: Mapped[list["ActivityLog"]] = relationship(
        "ActivityLog", 
        back_populates="model",
        lazy="select"
    )
    price_analyses: Mapped[list["PriceAnalysis"]] = relationship(
        "PriceAnalysis", 
        back_populates="model",
        lazy="select"
    )
