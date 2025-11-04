from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID

class UserAIModelBase(BaseModel):
    ai_model_id: UUID
    api_key: Optional[str] = None
    config: Optional[dict] = None

class UserAIModelCreate(UserAIModelBase):
    pass

class UserAIModelUpdate(BaseModel):
    api_key: Optional[str] = None
    config: Optional[dict] = None

class UserAIModelResponse(UserAIModelBase):
    id: UUID
    user_id: UUID
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        orm_mode = True
