from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from .base import Base

class UserAIModel(Base):
    __tablename__ = "user_ai_models"

    user_id: Mapped[str] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ai_model_id: Mapped[str] = mapped_column(PGUUID(as_uuid=True), ForeignKey("ai_models.id", ondelete="CASCADE"), nullable=False)
    api_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    user = relationship("User", back_populates="user_ai_models", lazy="select")
    ai_model = relationship("AIModel", back_populates="user_ai_models", lazy="select")
