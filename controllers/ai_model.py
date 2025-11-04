import uuid
from typing import Optional


from fastapi import APIRouter, Depends, HTTPException, Query, status
from core.dependencies.auth import verify_token
from schemas.auth import TokenData
from core.dependencies.services import get_ai_model_service
from schemas.ai_model import (
    ListAIModelsResponse,
    AIModelResponse,
    AIModelCreate,
    AIModelUpdate,
)
from services.sale_smart_ai_app.ai_model import AIModelService
from repositories.ai_model import AIModelFilters
from middlewares.permissions import check_global_permissions
from shared.enums import GlobalPermissionEnum, RoleEnum

router = APIRouter(prefix="/ai-models", tags=["ai-models"])



# Admin only: create AI model
@router.post("/", response_model=AIModelResponse, status_code=status.HTTP_201_CREATED)
@check_global_permissions(GlobalPermissionEnum.MANAGE_AI_MODELS)
async def create_ai_model(
    *,
    payload: AIModelCreate,
    ai_model_service: AIModelService = Depends(get_ai_model_service),
    token: TokenData = Depends(verify_token),
):
    try:
        ai_model = ai_model_service.create_ai_model(payload=payload)
        return ai_model
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))



# Public: list all AI models (no user filter)
@router.get("/", response_model=ListAIModelsResponse)
def get_list_ai_models(
    *,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    q: Optional[str] = Query(None, description="Search in name, model_name, provider"),
    model_type: Optional[str] = Query(None, description="Filter by model type (llm, crawler, analyzer)"),
    provider: Optional[str] = Query(None, description="Filter by provider (openai, anthropic, gemini, custom)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    ai_model_service: AIModelService = Depends(get_ai_model_service),
):
    try:
        ai_models = ai_model_service.search(
            q=q,
            model_type=model_type,
            provider=provider,
            is_active=is_active,
            skip=skip,
            limit=limit,
        )
        filters_dict = {}
        if q:
            filters_dict["q"] = q
        if model_type:
            filters_dict["model_type"] = model_type
        if provider:
            filters_dict["provider"] = provider
        if is_active is not None:
            filters_dict["is_active"] = is_active
        filters = AIModelFilters(**filters_dict) if filters_dict else None
        total = ai_model_service.count_ai_models(filters=filters)
        return ListAIModelsResponse(
            total=total,
            items=[AIModelResponse.model_validate(ai_model) for ai_model in ai_models]
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Removed user-scoped endpoints: /my, /my/active, /types/{model_type}, /providers/{provider}



# Public: get AI model by ID
@router.get("/{ai_model_id}", response_model=AIModelResponse)
def get_ai_model(
    *,
    ai_model_id: uuid.UUID,
    ai_model_service: AIModelService = Depends(get_ai_model_service),
):
    ai_model = ai_model_service.get_ai_model(model_id=ai_model_id)
    if not ai_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI model not found")
    return ai_model


# Statistics endpoint removed or can be reimplemented later if needed



# Admin only: update AI model
@router.patch("/{ai_model_id}", response_model=AIModelResponse)
@check_global_permissions(GlobalPermissionEnum.MANAGE_AI_MODELS)
async def update_ai_model(
    *,
    ai_model_id: uuid.UUID,
    payload: AIModelUpdate,
    ai_model_service: AIModelService = Depends(get_ai_model_service),
    token: TokenData = Depends(verify_token),
):
    try:
        ai_model = ai_model_service.update_ai_model(
            model_id=ai_model_id,
            payload=payload
        )
        if not ai_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI model not found")
        return ai_model
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{ai_model_id}/deactivate", response_model=AIModelResponse)
@check_global_permissions(GlobalPermissionEnum.MANAGE_AI_MODELS)
async def deactivate_ai_model(
    *,
    ai_model_id: uuid.UUID,
    ai_model_service: AIModelService = Depends(get_ai_model_service),
    token: TokenData = Depends(verify_token),
):
    try:
        ai_model = ai_model_service.deactivate_ai_model(model_id=ai_model_id)
        if not ai_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI model not found")
        return ai_model
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{ai_model_id}/activate", response_model=AIModelResponse)
@check_global_permissions(GlobalPermissionEnum.MANAGE_AI_MODELS)
async def activate_ai_model(
    *,
    ai_model_id: uuid.UUID,
    ai_model_service: AIModelService = Depends(get_ai_model_service),
    token: TokenData = Depends(verify_token),
):
    try:
        ai_model = ai_model_service.activate_ai_model(model_id=ai_model_id)
        if not ai_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI model not found")
        return ai_model
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{ai_model_id}/increment-usage", response_model=AIModelResponse)
def increment_ai_model_usage(
    *,
    ai_model_id: uuid.UUID,
    ai_model_service: AIModelService = Depends(get_ai_model_service),
    token: TokenData = Depends(verify_token),
):
    try:
        ai_model = ai_model_service.increment_usage(model_id=ai_model_id)
        if not ai_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI model not found")
        return ai_model
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))



# Admin only: delete AI model
@router.delete("/{ai_model_id}", status_code=status.HTTP_204_NO_CONTENT)
@check_global_permissions(GlobalPermissionEnum.MANAGE_AI_MODELS)
async def delete_ai_model(
    *,
    ai_model_id: uuid.UUID,
    ai_model_service: AIModelService = Depends(get_ai_model_service),
    token: TokenData = Depends(verify_token),
):
    try:
        ai_model_service.delete_ai_model(model_id=ai_model_id)
        return None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin-only endpoints
@router.get("/admin/all", response_model=ListAIModelsResponse)
@check_global_permissions(GlobalPermissionEnum.VIEW_ALL_AI_MODELS)
async def admin_get_all_ai_models(
    *,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    q: Optional[str] = Query(None),
    model_type: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    ai_model_service: AIModelService = Depends(get_ai_model_service),
    token: TokenData = Depends(verify_token),
):
    """
    Admin: Get all AI models across all users.
    
    Requires: VIEW_ALL_AI_MODELS permission (Admin or Super Admin only)
    """
    try:
        ai_models = ai_model_service.search(
            q=q,
            model_type=model_type,
            provider=provider,
            is_active=is_active,
            skip=skip,
            limit=limit,
        )
        
        filters_dict = {}
        if q:
            filters_dict["q"] = q
        if model_type:
            filters_dict["model_type"] = model_type
        if provider:
            filters_dict["provider"] = provider
        if is_active is not None:
            filters_dict["is_active"] = is_active
        
        filters = AIModelFilters(**filters_dict) if filters_dict else None
        total = ai_model_service.count_ai_models(filters=filters)
        
        return ListAIModelsResponse(
            total=total,
            items=[AIModelResponse.model_validate(ai_model) for ai_model in ai_models]
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
