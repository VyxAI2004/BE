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

    def _apply_filters(self, query, filters: Optional[ProjectFilters] = None):
        if not filters:
            return query

        filter_conditions = []
        
        # Text search across multiple fields
        if filters.get("q"):
            q = filters.get("q")
            filter_conditions.append(
                or_(
                    Project.name.ilike(f"%{q}%"),
                    Project.description.ilike(f"%{q}%"),
                    Project.target_product_name.ilike(f"%{q}%"),
                    Project.target_product_category.ilike(f"%{q}%"),
                )
            )
        
        # Specific field filters
        if filters.get("name"):
            filter_conditions.append(
                Project.name.ilike(f"%{filters.get('name')}%")
            )
        
        if filters.get("status"):
            filter_conditions.append(
                Project.status == filters.get("status")
            )
        
        if filters.get("created_by"):
            filter_conditions.append(
                Project.created_by == filters.get("created_by")
            )
        
        if filters.get("assigned_to"):
            filter_conditions.append(
                Project.assigned_to == filters.get("assigned_to")
            )
        
        if filters.get("pipeline_type"):
            filter_conditions.append(
                Project.pipeline_type == filters.get("pipeline_type")
            )
        
        if filters.get("target_product_category"):
            filter_conditions.append(
                Project.target_product_category.ilike(f"%{filters.get('target_product_category')}%")
            )

        if filter_conditions:
            query = query.filter(and_(*filter_conditions))
            
        return query

    def search(
        self,
        *,
        filters: Optional[ProjectFilters] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Project]:
        db_query = self.db.query(Project)
        db_query = self._apply_filters(db_query, filters)
        return db_query.offset(skip).limit(limit).all()

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

    def count(self, filters: Optional[ProjectFilters] = None) -> int:
        """Count projects with filters applied"""
        query = self.db.query(Project)
        query = self._apply_filters(query, filters)
        return query.count()