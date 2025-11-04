from datetime import datetime
from typing import Optional, List, Annotated
from uuid import UUID
from pydantic import BaseModel, Field


class AIModelBase(BaseModel):
    """Base schema for AIModel model"""
    name: Annotated[str, Field(min_length=1, max_length=100)]
    model_type: Annotated[str, Field(min_length=1, max_length=50)]  # llm, crawler, analyzer
    provider: Annotated[str, Field(min_length=1, max_length=50)]    # openai, anthropic, gemini, custom
    model_name: Annotated[str, Field(min_length=1, max_length=100)] # gpt-4, claude-3, etc.
    base_url: Optional[Annotated[str, Field(max_length=500)]] = None # For custom endpoints
    config: Optional[dict] = None  # Model configuration
    is_active: Optional[bool] = True


class AIModelCreate(BaseModel):
    """Schema for creating AI model"""
    name: Annotated[str, Field(min_length=1, max_length=100)]
    model_type: Annotated[str, Field(min_length=1, max_length=50)]
    provider: Annotated[str, Field(min_length=1, max_length=50)]
    model_name: Annotated[str, Field(min_length=1, max_length=100)]
    base_url: Optional[Annotated[str, Field(max_length=500)]] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = True


class AIModelUpdate(BaseModel):
    """Schema for updating AI model information"""
    name: Optional[Annotated[str, Field(min_length=1, max_length=100)]] = None
    model_type: Optional[Annotated[str, Field(min_length=1, max_length=50)]] = None
    provider: Optional[Annotated[str, Field(min_length=1, max_length=50)]] = None
    model_name: Optional[Annotated[str, Field(min_length=1, max_length=100)]] = None
    base_url: Optional[Annotated[str, Field(max_length=500)]] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None


class AIModelResponse(AIModelBase):
    """Schema for AI model response"""
    id: UUID
    usage_count: int
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ListAIModelsResponse(BaseModel):
    """Schema for list AI models response"""
    items: List[AIModelResponse]
    total: int

    class Config:
        from_attributes = True
