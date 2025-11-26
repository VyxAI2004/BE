from typing import List, Optional, Type, TypedDict
from uuid import UUID

from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from models.project import Project
from schemas.project import ProjectCreate, ProjectUpdate
from shared.enums import ProjectStatusEnum

from .base import BaseRepository


class ProjectFilters(TypedDict, total=False):
    """Project filters for comprehensive search"""
    q: Optional[str]
    name: Optional[str]
    status: Optional[ProjectStatusEnum]
    created_by: Optional[UUID]
    assigned_to: Optional[UUID]
    pipeline_type: Optional[str]
    target_product_category: Optional[str]


class ProjectRepository(BaseRepository[Project, ProjectCreate, ProjectUpdate]):
    def __init__(self, model: Type[Project], db: Session):
        super().__init__(model, db)

    def apply_filters(self, query, filters: Optional[ProjectFilters] = None):
        if not filters:
            return query

        filter_conditions = []

        # Full-text search
        if filters.get("q"):
            q = filters["q"]
            filter_conditions.append(
                or_(
                    Project.name.ilike(f"%{q}%"),
                    Project.description.ilike(f"%{q}%"),
                    Project.target_product_name.ilike(f"%{q}%"),
                    Project.target_product_category.ilike(f"%{q}%"),
                )
            )

        # Filter by name
        if filters.get("name"):
            filter_conditions.append(
                Project.name.ilike(f"%{filters['name']}%")
            )

        # Filter by product category
        if filters.get("target_product_category"):
            filter_conditions.append(
                Project.target_product_category.ilike(
                    f"%{filters['target_product_category']}%"
                )
            )

        # Apply custom filter conditions
        if filter_conditions:
            query = query.filter(and_(*filter_conditions))

        # Standard filters passed to BaseRepository
        standard_filters = {
            key: value
            for key, value in filters.items()
            if key not in ["q", "name", "target_product_category"]
            and value is not None
        }

        if standard_filters:
            query = super().apply_filters(query, standard_filters)

        return query

    def get_by_user(self, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Project]:
        """Get projects created by or assigned to a specific user"""
        return (
            self.db.query(Project)
            .filter(
                or_(
                    Project.created_by == user_id,
                    Project.assigned_to == user_id
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_all_user_projects(self, user_id: UUID) -> List[Project]:
        """Get all projects related to a user: creator, assignee, or member"""
        from models.project import ProjectUser

        query = (
            self.db.query(Project)
            .outerjoin(ProjectUser, Project.id == ProjectUser.project_id)
            .filter(
                or_(
                    Project.created_by == user_id,
                    Project.assigned_to == user_id,
                    and_(
                        ProjectUser.user_id == user_id,
                        ProjectUser.is_active == True,
                    ),
                )
            )
            .distinct()
        )

        return query.all()
