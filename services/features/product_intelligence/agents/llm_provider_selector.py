from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from core.llm.factory import AgentFactory
from core.llm.base import BaseAgent
from models.ai_model import AIModel
from services.core.ai_model import AIModelService
from services.core.user_ai_model import UserAIModelService
from repositories.ai_model import AIModelRepository


class LLMProviderSelector:
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_model_service = AIModelService(db)
        self.user_ai_model_service = UserAIModelService(db)
    
    def select_agent(self, user_id: UUID, project_assigned_model_id: Optional[UUID] = None) -> BaseAgent:
        # 1. Try user's custom model first
        user_ai_model = self.user_ai_model_service.get_user_active_model(user_id)
        if user_ai_model:
            ai_model = user_ai_model.ai_model
            kwargs = user_ai_model.config or ai_model.config or {}
            if ai_model.base_url:
                kwargs["base_url"] = ai_model.base_url
            return AgentFactory.create(
                provider=ai_model.provider,
                model=ai_model.model_name,
                api_key=user_ai_model.api_key or ai_model.api_key,
                **kwargs
            )
        
        # 2. Try project assigned model
        if project_assigned_model_id:
            ai_model = self.ai_model_service.get(project_assigned_model_id)
            if ai_model and ai_model.is_active:
                kwargs = ai_model.config or {}
                if ai_model.base_url:
                    kwargs["base_url"] = ai_model.base_url
                return AgentFactory.create(
                    provider=ai_model.provider,
                    model=ai_model.model_name,
                    api_key=ai_model.api_key,
                    **kwargs
                )
        
        # 3. Try system default
        models = self.ai_model_service.search(is_active=True, limit=1)
        if models:
            ai_model = models[0]
            kwargs = ai_model.config or {}
            if ai_model.base_url:
                kwargs["base_url"] = ai_model.base_url
            return AgentFactory.create(
                provider=ai_model.provider,
                model=ai_model.model_name,
                api_key=ai_model.api_key,
                **kwargs
            )
        
        # 4. Fallback to environment
        return AgentFactory.create("google")
