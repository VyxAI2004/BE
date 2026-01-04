"""
Model cho ProductUser - Product membership & permissions
"""
from typing import TYPE_CHECKING, Optional
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .product import Product
    from .user import User
    from .role import Role


class ProductUser(Base):
    """Model cho bảng product_users - quản lý thành viên của product"""
    __tablename__ = "product_users"

    # Columns
    product_id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[Optional[str]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("roles.id", ondelete="SET NULL"), nullable=True
    )
    permissions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    invited_by: Mapped[Optional[str]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    # Relationships
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="product_users",
        lazy="select"
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="product_memberships",
        foreign_keys=[user_id],
        lazy="select"
    )
    role: Mapped[Optional["Role"]] = relationship(
        "Role",
        lazy="select"
    )
    inviter: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="invited_product_memberships",
        foreign_keys=[invited_by],
        lazy="select"
    )
