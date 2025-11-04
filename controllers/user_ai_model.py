import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from core.dependencies.auth import verify_token
from schemas.auth import TokenData
from schemas.user_ai_model import UserAIModelCreate, UserAIModelUpdate, UserAIModelResponse
from services.sale_smart_ai_app.user_ai_model import UserAIModelService
from core.dependencies.db import get_db

router = APIRouter(prefix="/user-ai-models", tags=["user-ai-models"])

@router.get("/", response_model=list[UserAIModelResponse])
def get_user_ai_models(
    db = Depends(get_db),
    user_from_token: TokenData = Depends(verify_token),
):
    service = UserAIModelService(db)
    user_models = service.get_user_models(user_from_token.user_id)
    return user_models

@router.post("/", response_model=UserAIModelResponse, status_code=status.HTTP_201_CREATED)
def create_or_update_user_ai_model(
    payload: UserAIModelCreate,
    db = Depends(get_db),
    user_from_token: TokenData = Depends(verify_token),
):
    service = UserAIModelService(db)
    user_ai_model = service.create_or_update(user_from_token.user_id, payload)
    return user_ai_model

@router.delete("/{ai_model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_ai_model(
    ai_model_id: uuid.UUID,
    db = Depends(get_db),
    user_from_token: TokenData = Depends(verify_token),
):
    service = UserAIModelService(db)
    service.delete(user_from_token.user_id, ai_model_id)
    return None
