from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from models.user_ai_model import UserAIModel
from models.ai_model import AIModel
from schemas.user_ai_model import UserAIModelCreate, UserAIModelUpdate
from repositories.user_ai_model import UserAIModelRepository

class UserAIModelService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = UserAIModelRepository(db)

    def get_user_models(self, user_id: UUID) -> List[UserAIModel]:
        return self.repository.get_all_by_user(user_id)

    def get_by_user_and_model(self, user_id: UUID, ai_model_id: UUID) -> Optional[UserAIModel]:
        return self.repository.get_by_user_and_model(user_id, ai_model_id)

    def create_or_update(self, user_id: UUID, obj_in: UserAIModelCreate) -> UserAIModel:
        db_obj = self.repository.get_by_user_and_model(user_id, obj_in.ai_model_id)
        if db_obj:
            return self.repository.update(db_obj, UserAIModelUpdate(api_key=obj_in.api_key, config=obj_in.config))
        return self.repository.create(user_id, obj_in)

    def delete(self, user_id: UUID, ai_model_id: UUID):
        db_obj = self.repository.get_by_user_and_model(user_id, ai_model_id)
        if db_obj:
            self.repository.delete(db_obj)

    def get_runtime_config(self, user_id: UUID, ai_model_id: UUID) -> Optional[Dict[str, Any]]:
        """Return merged runtime config for calling AI: config from ai_models + api_key/config from user_ai_models"""
        ai_model: Optional[AIModel] = self.db.get(AIModel, ai_model_id)
        if not ai_model:
            return None
        user_link = self.repository.get_by_user_and_model(user_id, ai_model_id)
        if not user_link:
            return None
        return {
            "provider": ai_model.provider,
            "model_name": ai_model.model_name,
            "base_url": ai_model.base_url,
            "model_config": ai_model.config or {},
            "api_key": user_link.api_key,
            "user_config": user_link.config or {},
        }
