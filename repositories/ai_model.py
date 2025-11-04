from typing import List, Optional, Type, TypedDict
from uuid import UUID

from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from models.ai_model import AIModel
from schemas.ai_model import AIModelCreate, AIModelUpdate

from .base import BaseRepository


class AIModelFilters(TypedDict, total=False):
    """AI Model filters for comprehensive search (global, no user filter)"""
    q: Optional[str]
    model_type: Optional[str]
    provider: Optional[str]
    is_active: Optional[bool]


class AIModelRepository(BaseRepository[AIModel, AIModelCreate, AIModelUpdate]):
    def __init__(self, model: Type[AIModel], db: Session):
        super().__init__(model, db)

    def search(
        self,
        *,
        filters: Optional[AIModelFilters] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AIModel]:
        """Search AI models with comprehensive filters"""
        db_query = self.db.query(AIModel)

        if filters:
            filter_conditions = []
            
            if filters.get("q"):
                query = filters.get("q")
                filter_conditions.append(
                    or_(
                        AIModel.name.ilike(f"%{query}%"),
                        AIModel.model_name.ilike(f"%{query}%"),
                        AIModel.provider.ilike(f"%{query}%"),
                    )
                )
            
            if filters.get("model_type"):
                filter_conditions.append(AIModel.model_type == filters.get("model_type"))
            
            if filters.get("provider"):
                filter_conditions.append(AIModel.provider == filters.get("provider"))
            
            if filters.get("is_active") is not None:
                filter_conditions.append(AIModel.is_active == filters.get("is_active"))
            
            if filter_conditions:
                db_query = db_query.filter(and_(*filter_conditions))

        return db_query.offset(skip).limit(limit).all()

    def get_by_name_provider_model(self, *, name: str, provider: str, model_name: str) -> Optional[AIModel]:
        """Get AI model by name+provider+model_name (global uniqueness)"""
        return (
            self.db.query(AIModel)
            .filter(
                and_(
                    AIModel.name == name,
                    AIModel.provider == provider,
                    AIModel.model_name == model_name
                )
            )
            .first()
        )

    def increment_usage_count(self, *, model_id: UUID) -> Optional[AIModel]:
        """Increment usage count and update last_used_at"""
        from datetime import datetime
        
        ai_model = self.get(model_id)
        if ai_model:
            ai_model.usage_count = (ai_model.usage_count or 0) + 1
            ai_model.last_used_at = datetime.utcnow()
            self.db.add(ai_model)
            self.db.commit()
            self.db.refresh(ai_model)
        return ai_model

    def count_by_filters(self, *, filters: Optional[AIModelFilters] = None) -> int:
        """Count AI models with filters"""
        db_query = self.db.query(AIModel)

        if filters:
            filter_conditions = []
            
            if filters.get("q"):
                query = filters.get("q")
                filter_conditions.append(
                    or_(
                        AIModel.name.ilike(f"%{query}%"),
                        AIModel.model_name.ilike(f"%{query}%"),
                        AIModel.provider.ilike(f"%{query}%"),
                    )
                )
            
            if filters.get("model_type"):
                filter_conditions.append(AIModel.model_type == filters.get("model_type"))
            
            if filters.get("provider"):
                filter_conditions.append(AIModel.provider == filters.get("provider"))
            
            if filters.get("is_active") is not None:
                filter_conditions.append(AIModel.is_active == filters.get("is_active"))
            
            if filter_conditions:
                db_query = db_query.filter(and_(*filter_conditions))

        return db_query.count()

    def deactivate_model(self, *, model_id: UUID) -> Optional[AIModel]:
        """Deactivate an AI model instead of deleting"""
        ai_model = self.get(model_id)
        if ai_model:
            ai_model.is_active = False
            self.db.add(ai_model)
            self.db.commit()
            self.db.refresh(ai_model)
        return ai_model

    def activate_model(self, *, model_id: UUID) -> Optional[AIModel]:
        """Activate an AI model"""
        ai_model = self.get(model_id)
        if ai_model:
            ai_model.is_active = True
            self.db.add(ai_model)
            self.db.commit()
            self.db.refresh(ai_model)
        return ai_model
