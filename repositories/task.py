from typing import List, Optional, Type
from uuid import UUID

from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session, joinedload, Query
from sqlalchemy.sql import literal_column

from models.task import Task
from models.product import Product
from schemas.task import TaskCreate, TaskUpdate

from .base import BaseRepository


class TaskRepository(BaseRepository[Task, TaskCreate, TaskUpdate]):
    def __init__(self, model: Type[Task], db: Session):
        super().__init__(model, db)
    
    def _with_product(self, query: Query) -> Query:
        """Helper to eager load product relationship"""
        return query.options(joinedload(self.model.product))

    def get_by_project(
        self, project_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        """Lấy tasks theo project"""
        return self._with_product(
            self.db.query(self.model)
            .filter(self.model.project_id == project_id)
            .offset(skip)
            .limit(limit)
        ).all()

    def get_by_assigned_to(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        """Lấy tasks được assign cho user"""
        return self._with_product(
            self.db.query(self.model)
            .filter(self.model.assigned_to == user_id)
            .offset(skip)
            .limit(limit)
        ).all()

    def get_by_product(
        self, product_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        """Lấy tasks theo product_id"""
        return self._with_product(
            self.db.query(self.model)
            .filter(self.model.product_id == product_id)
            .offset(skip)
            .limit(limit)
        ).all()

    def get_by_status(
        self, status: str, project_id: Optional[UUID] = None, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        """Lấy tasks theo status"""
        query = self.db.query(self.model).filter(self.model.status == status)
        if project_id:
            query = query.filter(self.model.project_id == project_id)
        return self._with_product(query).offset(skip).limit(limit).all()

    def get_by_product_id(self, product_id: UUID) -> List[Task]:
        """Lấy tasks theo product_id"""
        return (
            self.db.query(self.model)
            .filter(self.model.product_id == product_id)
            .all()
        )

    def delete_by_product_id(self, product_id: UUID) -> int:
        """Xóa tất cả tasks của một product"""
        from sqlalchemy.exc import SQLAlchemyError
        try:
            deleted_count = (
                self.db.query(self.model)
                .filter(self.model.product_id == product_id)
                .delete(synchronize_session=False)
            )
            self.db.commit()
            return deleted_count
        except SQLAlchemyError:
            self.db.rollback()
            raise

    def get_user_accessible_tasks(self, user_id: UUID) -> List[Task]:
        """Lấy tất cả tasks mà user có access (creator, assigned, or project member)"""
        from models.project_user import ProjectUser
        
        # Build query with product join
        query = (
            self.db.query(self.model)
            .outerjoin(Product, self.model.product_id == Product.id)
            .filter(
                or_(
                    self.model.created_by == user_id,  # Creator can always see
                    self.model.assigned_to == user_id,  # Assigned users can see
                    self.model.project_id.in_(  # Project members can see
                        self.db.query(ProjectUser.project_id).filter(
                            and_(
                                ProjectUser.user_id == user_id,
                                ProjectUser.is_active == True
                            )
                        )
                    )
                )
            )
            .distinct()
        )
        
        results = query.all()
        
        # Manually set product_name from product relationship for serialization
        for task in results:
            if not hasattr(task, 'product_name') or task.product_name is None:
                if hasattr(task, 'product') and task.product:
                    # Set as attribute so Pydantic can access it
                    object.__setattr__(task, 'product_name', task.product.name)
        
        return results
