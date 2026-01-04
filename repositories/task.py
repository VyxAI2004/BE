from typing import List, Optional, Type
from uuid import UUID

from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from models.task import Task
from schemas.task import TaskCreate, TaskUpdate

from .base import BaseRepository


class TaskRepository(BaseRepository[Task, TaskCreate, TaskUpdate]):
    def __init__(self, model: Type[Task], db: Session):
        super().__init__(model, db)

    def get_by_project(
        self, project_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        """Lấy tasks theo project"""
        return (
            self.db.query(self.model)
            .filter(self.model.project_id == project_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_assigned_to(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        """Lấy tasks được assign cho user"""
        return (
            self.db.query(self.model)
            .filter(self.model.assigned_to == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_product(
        self, product_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        """Lấy tasks theo product_id"""
        return (
            self.db.query(self.model)
            .filter(self.model.product_id == product_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_status(
        self, status: str, project_id: Optional[UUID] = None, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        """Lấy tasks theo status"""
        query = self.db.query(self.model).filter(self.model.status == status)
        if project_id:
            query = query.filter(self.model.project_id == project_id)
        return query.offset(skip).limit(limit).all()

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
        from models.project import ProjectUser
        
        query = (
            self.db.query(self.model)
            .outerjoin(ProjectUser, self.model.project_id == ProjectUser.project_id)
            .filter(
                or_(
                    self.model.created_by == user_id,  # User is creator
                    self.model.assigned_to == user_id,  # User is assigned
                    and_(
                        ProjectUser.user_id == user_id,  # User is project member
                        ProjectUser.is_active == True,
                    ),
                )
            )
            .distinct()
        )
        
        return query.all()
