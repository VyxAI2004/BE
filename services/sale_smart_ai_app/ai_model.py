from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session

from models.ai_model import AIModel
from schemas.ai_model import AIModelCreate, AIModelUpdate
from repositories.ai_model import AIModelRepository, AIModelFilters

from .base import BaseService


class AIModelService(
    BaseService[AIModel, AIModelCreate, AIModelUpdate, AIModelRepository]
):
    def __init__(self, db: Session):
        super().__init__(db, AIModel, AIModelRepository)

    def get_ai_model(self, *, model_id: UUID) -> Optional[AIModel]:
        """Get AI model by ID"""
        return self.get(model_id)


    def search(
        self,
        *,
        q: Optional[str] = None,
        model_type: Optional[str] = None,
        provider: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AIModel]:
        """Search AI models with filters (admin or public)"""
        filters: Optional[AIModelFilters] = None
        filter_dict = {}
        if q:
            filter_dict["q"] = q
        if model_type:
            filter_dict["model_type"] = model_type
        if provider:
            filter_dict["provider"] = provider
        if is_active is not None:
            filter_dict["is_active"] = is_active
        if filter_dict:
            filters = AIModelFilters(**filter_dict)
        return self.repository.search(filters=filters, skip=skip, limit=limit)

    def create_ai_model(self, payload: AIModelCreate) -> AIModel:
        """Admin: Create new AI model"""
        # Check if model name already exists (global)
        existing_model = self.repository.get_by_name_provider_model(
            name=payload.name,
            provider=payload.provider,
            model_name=payload.model_name
        )
        if existing_model:
            raise ValueError(f"AI model with name '{payload.name}' and provider '{payload.provider}' already exists")
        return self.create(payload=payload)

    def update_ai_model(
        self,
        model_id: UUID,
        payload: AIModelUpdate,
    ) -> Optional[AIModel]:
        """Admin: Update AI model"""
        db_model = self.get(model_id)
        if not db_model:
            return None
        # Check if new name conflicts with existing models
        if payload.name:
            existing_model = self.repository.get_by_name_provider_model(
                name=payload.name,
                provider=payload.provider or db_model.provider,
                model_name=payload.model_name or db_model.model_name
            )
            if existing_model and existing_model.id != model_id:
                raise ValueError(f"AI model with name '{payload.name}' and provider '{payload.provider or db_model.provider}' already exists")
        return self.update(db_obj=db_model, payload=payload)

    def delete_ai_model(self, model_id: UUID) -> None:
        """Admin: Delete AI model (hard delete)"""
        db_model = self.get(model_id)
        if not db_model:
            raise ValueError("AI model not found")
        self.delete(id=model_id)

    def deactivate_ai_model(self, model_id: UUID) -> Optional[AIModel]:
        """Admin: Deactivate AI model (soft delete)"""
        db_model = self.get(model_id)
        if not db_model:
            return None
        return self.repository.deactivate_model(model_id=model_id)

    def activate_ai_model(self, model_id: UUID) -> Optional[AIModel]:
        """Admin: Activate AI model"""
        db_model = self.get(model_id)
        if not db_model:
            return None
        return self.repository.activate_model(model_id=model_id)



    def increment_usage(self, model_id: UUID) -> Optional[AIModel]:
        """Increment usage count and update last_used_at timestamp"""
        return self.repository.increment_usage_count(model_id=model_id)

    def count_ai_models(self, *, filters: Optional[AIModelFilters] = None) -> int:
        """Count AI models with filters"""
        return self.repository.count_by_filters(filters=filters)




