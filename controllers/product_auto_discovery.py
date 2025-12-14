from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.dependencies.db import get_db
from core.dependencies.auth import verify_token
from core.dependencies.services import get_project_service
from schemas.auth import TokenData
from schemas.auto_discovery import AutoDiscoveryRequest, AutoDiscoveryRequestLegacy, AutoDiscoveryResponse
from services.features.product_intelligence.orchestration.auto_discovery_service import AutoDiscoveryService
from services.core.project import ProjectService

router = APIRouter(prefix="/products/auto-discovery", tags=["Auto Discovery"])


def get_auto_discovery_service(db: Session = Depends(get_db)) -> AutoDiscoveryService:
    """Dependency injection for AutoDiscoveryService"""
    return AutoDiscoveryService(db)


@router.post("/execute", response_model=AutoDiscoveryResponse, status_code=status.HTTP_200_OK)
def execute_auto_discovery(
    request: AutoDiscoveryRequest,
    service: AutoDiscoveryService = Depends(get_auto_discovery_service),
    token: TokenData = Depends(verify_token),
):
    """
    Execute automated product discovery and import flow from natural language input
    
    **Input:**
    - `project_id`: Project to import products to
    - `user_input`: Natural language input. Examples:
      - "tìm kiếm cho tôi 2 sản phẩm mẫu dựa trên project của tôi, yêu cầu là có hơn 100 reviews, mall, và trên sàn lazada"
      - "tìm 5 sản phẩm cà phê hòa tan, rating 4.5+, max price 500000"
      - "tìm kiếm sản phẩm mẫu, lazada, tiki, mall"
    
    **Workflow:**
    1. AI parses natural language input → extracts: user_query, filter_criteria, max_products
    2. Gets project info for context (target_product_name, budget, etc.)
    3. Parses filter criteria (if any)
    4. Validates criteria with AI (if any)
    5. Searches for products using AI
    6. Crawls products from search links (max 20 products)
    7. Filters products based on criteria (if any)
    8. AI ranks and selects best products if too many
    9. Imports filtered products to database
    """
    
    result = service.execute_auto_discovery_from_natural_language(
        project_id=request.project_id,
        user_id=token.user_id,
        user_input=request.user_input
    )
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return AutoDiscoveryResponse(**result)


@router.post("/execute-legacy", response_model=AutoDiscoveryResponse, status_code=status.HTTP_200_OK)
def execute_auto_discovery_legacy(
    request: AutoDiscoveryRequestLegacy,
    service: AutoDiscoveryService = Depends(get_auto_discovery_service),
    project_service: ProjectService = Depends(get_project_service),
    token: TokenData = Depends(verify_token),
):
    """
    Legacy endpoint for backward compatibility
    
    Use /execute with natural language input instead
    """
    
    # Get project to retrieve assigned_model_id
    project = project_service.get(request.project_id)
    project_assigned_model_id = project.assigned_model_id if project else None
    
    result = service.execute_auto_discovery(
        project_id=request.project_id,
        user_id=token.user_id,
        user_query=request.user_query,
        filter_criteria_text=request.filter_criteria,
        max_products=request.max_products,
        project_assigned_model_id=project_assigned_model_id
    )
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return AutoDiscoveryResponse(**result)

