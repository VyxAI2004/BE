from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from typing import Optional
import json

from core.dependencies.auth import verify_token
from core.dependencies.services import get_project_service
from schemas.auth import TokenData
from schemas.product_ai import ProductSearchResponse
from services.core.project import ProjectService
from services.features.product_intelligence.agents import ProductAIAgent 
from shared.enums import PlatformEnum

router = APIRouter(prefix="/products/ai", tags=["Product AI"])

@router.get("/search/{project_id}", response_model=ProductSearchResponse)
def ai_search_products_for_project(
    project_id: UUID,
    limit: int = 10,
    platform: PlatformEnum = Query(
        default=PlatformEnum.ALL,
        description="E-commerce platform: 'shopee', 'lazada', 'tiki', or 'all'",
    ),
    project_service: ProjectService = Depends(get_project_service),
    token: TokenData = Depends(verify_token),
):
    project = project_service.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_info = {
        "id": project.id,
        "name": project.name,
        "target_product_name": project.target_product_name,
        "target_budget_range": project.target_budget_range,
        "description": project.description
    }

    try:
        agent = ProductAIAgent(db=project_service.db)
        return agent.search_products(project_info, token.user_id, limit, platform)
        
    except ImportError as e:
        raise HTTPException(
            status_code=500, 
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"AI search failed: {str(e)}"
        )
