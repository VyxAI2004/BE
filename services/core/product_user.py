"""
Service cho ProductUser - Business Logic Layer
"""
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from models.product_user import ProductUser
from models.user import User
from models.product import Product
from schemas.product_user import ProductUserCreate, ProductUserUpdate
from repositories.product_user import ProductUserRepository
from .base import BaseService


class ProductUserService(BaseService[ProductUser, ProductUserCreate, ProductUserUpdate, ProductUserRepository]):
    """Service để quản lý ProductUser - Product membership & invitations"""

    def __init__(self, db: Session):
        super().__init__(db, ProductUser, ProductUserRepository)

    def invite_to_product(
        self,
        product_id: UUID,
        user: User,
        role_id: Optional[UUID] = None,
        permissions: Optional[dict] = None,
        invited_by_id: Optional[UUID] = None,
    ) -> ProductUser:
        """Mời user vào product"""
        # Check if already exists
        existing = self.repository.get_by_product_and_user(product_id, user.id)
        if existing:
            return existing
        
        # Create new product user
        payload = ProductUserCreate(
            product_id=product_id,
            user_id=user.id,
            role_id=role_id,
            permissions=permissions,
            invited_by=invited_by_id,
        )
        return self.create(payload)

    def get_product_members(
        self, product_id: UUID, skip: int = 0, limit: int = 100, is_active_only: bool = True
    ) -> list[ProductUser]:
        """Lấy tất cả thành viên của product"""
        return self.repository.get_product_members(product_id, skip, limit, is_active_only)

    def get_user_products(
        self, user_id: UUID, skip: int = 0, limit: int = 100, is_active_only: bool = True
    ) -> list[ProductUser]:
        """Lấy tất cả products mà user là thành viên"""
        return self.repository.get_user_products(user_id, skip, limit, is_active_only)

    def update_member_role(
        self, product_id: UUID, user_id: UUID, role_id: Optional[UUID], permissions: Optional[dict] = None
    ) -> Optional[ProductUser]:
        """Cập nhật role của thành viên trong product"""
        member = self.repository.get_by_product_and_user(product_id, user_id)
        if not member:
            return None
        
        payload = ProductUserUpdate(role_id=role_id, permissions=permissions)
        return self.update(db_obj=member, payload=payload)

    def remove_from_product(self, product_id: UUID, user_id: UUID) -> bool:
        """Xoá user khỏi product"""
        return self.repository.remove_from_product(product_id, user_id)

    def is_product_member(self, product_id: UUID, user_id: UUID) -> bool:
        """Kiểm tra user có phải là thành viên của product không"""
        member = self.repository.get_by_product_and_user(product_id, user_id)
        return member is not None and member.is_active

    def can_user_manage_product_members(self, product_id: UUID, user_id: UUID) -> bool:
        """Kiểm tra user có thể quản lý thành viên của product không (phải là owner)"""
        member = self.repository.get_by_product_and_user(product_id, user_id)
        if not member or not member.is_active:
            return False
        
        # Check if user is product owner by role or permissions
        # For now, simple check - can extend with role-based logic
        return member.role_id is not None  # Has some role assigned
