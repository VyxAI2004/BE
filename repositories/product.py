from typing import List, Optional, Type, TypedDict
from uuid import UUID

from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from models.product import Product
from schemas.product import ProductCreate, ProductUpdate

from .base import BaseRepository


class ProductFilters(TypedDict, total=False):
    """Product filters for comprehensive search"""
    q: Optional[str]
    name: Optional[str]
    project_id: Optional[UUID]
    platform: Optional[str]
    brand: Optional[str]
    category: Optional[str]
    min_price: Optional[float]
    max_price: Optional[float]


class ProductRepository(BaseRepository[Product, ProductCreate, ProductUpdate]):
    def __init__(self, model: Type[Product], db: Session):
        super().__init__(model, db)

    def apply_filters(self, query, filters: Optional[ProductFilters] = None):
        # Initialize filter conditions list
        filter_conditions = []
        
        # Create a copy to avoid modifying the original filters
        if filters is None:
            filters_copy = {}
        else:
            filters_copy = filters.copy()

        # Full-text search
        if filters_copy.get("q"):
            q = filters_copy.pop("q")
            filter_conditions.append(
                or_(
                    Product.name.ilike(f"%{q}%"),
                    Product.brand.ilike(f"%{q}%"),
                    Product.category.ilike(f"%{q}%"),
                    Product.subcategory.ilike(f"%{q}%"),
                )
            )

        # Handle specific filters and remove them from the copy
        if filters_copy.get("name"):
            filter_conditions.append(Product.name.ilike(f"%{filters_copy.pop('name')}%"))

        if filters_copy.get("project_id"):
            filter_conditions.append(Product.project_id == filters_copy.pop("project_id"))

        if filters_copy.get("platform"):
            filter_conditions.append(Product.platform == filters_copy.pop("platform"))

        if filters_copy.get("brand"):
            filter_conditions.append(Product.brand.ilike(f"%{filters_copy.pop('brand')}%"))

        if filters_copy.get("category"):
            filter_conditions.append(Product.category.ilike(f"%{filters_copy.pop('category')}%"))

        # Filter by price range
        if filters_copy.get("min_price") is not None:
            filter_conditions.append(Product.current_price >= filters_copy.pop("min_price"))
        
        if filters_copy.get("max_price") is not None:
            filter_conditions.append(Product.current_price <= filters_copy.pop("max_price"))

        # Apply custom filter conditions
        if filter_conditions:
            query = query.filter(and_(*filter_conditions))

        # Pass remaining filters to BaseRepository
        if filters_copy:
            query = super().apply_filters(query, filters_copy)

        return query

    def get_by_project(self, project_id: UUID, skip: int = 0, limit: int = 100) -> List[Product]:
        """Get products by project"""
        return (
            self.db.query(Product)
            .filter(Product.project_id == project_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
