"""
Repository cho ProductUser - Data Access Layer
"""
from typing import Optional, Type
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models.product_user import ProductUser
from schemas.product_user import ProductUserCreate, ProductUserUpdate
from .base import BaseRepository


class ProductUserRepository(BaseRepository[ProductUser, ProductUserCreate, ProductUserUpdate]):
    """Repository để quản lý ProductUser"""

    def __init__(self, model: Type[ProductUser], db: Session):
        super().__init__(model, db)

    def get_by_product_and_user(
        self, product_id: UUID, user_id: UUID
    ) -> Optional[ProductUser]:
        """Lấy ProductUser theo product_id và user_id"""
        return self.db.query(ProductUser).filter(
            and_(
                ProductUser.product_id == product_id,
                ProductUser.user_id == user_id
            )
        ).first()

    def get_product_members(
        self, product_id: UUID, skip: int = 0, limit: int = 100, is_active_only: bool = True
    ) -> list[ProductUser]:
        """Lấy tất cả thành viên của product"""
        query = self.db.query(ProductUser).filter(ProductUser.product_id == product_id)
        
        if is_active_only:
            query = query.filter(ProductUser.is_active == True)
        
        return query.offset(skip).limit(limit).all()

    def get_user_products(
        self, user_id: UUID, skip: int = 0, limit: int = 100, is_active_only: bool = True
    ) -> list[ProductUser]:
        """Lấy tất cả products mà user là thành viên"""
        query = self.db.query(ProductUser).filter(ProductUser.user_id == user_id)
        
        if is_active_only:
            query = query.filter(ProductUser.is_active == True)
        
        return query.offset(skip).limit(limit).all()

    def count_product_members(self, product_id: UUID) -> int:
        """Đếm số thành viên của product"""
        return self.db.query(ProductUser).filter(
            ProductUser.product_id == product_id
        ).count()

    def remove_from_product(self, product_id: UUID, user_id: UUID) -> bool:
        """Xoá user khỏi product"""
        result = self.db.query(ProductUser).filter(
            and_(
                ProductUser.product_id == product_id,
                ProductUser.user_id == user_id
            )
        ).delete()
        self.db.commit()
        return result > 0
