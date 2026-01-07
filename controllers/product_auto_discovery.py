from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json

from core.dependencies.db import get_db
from core.dependencies.auth import verify_token
from core.dependencies.services import get_project_service
from schemas.auth import TokenData
from schemas.auto_discovery import AutoDiscoveryRequest, AutoDiscoveryRequestLegacy, AutoDiscoveryResponse, AutoDiscoveryFlowRequest
from services.features.product_intelligence.orchestration.auto_discovery_service import AutoDiscoveryService
from services.features.product_intelligence.orchestration.auto_discovery_streaming_service import AutoDiscoveryStreamingService
from services.features.product_intelligence.orchestration.auto_discovery_flow_service import AutoDiscoveryFlowService
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


@router.post("/execute-stream")
async def execute_auto_discovery_stream(
    request: AutoDiscoveryRequest,
    token: TokenData = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Execute automated product discovery with Server-Sent Events (SSE) streaming
    
    Returns real-time events showing progress of each step:
    - step_start: Step begins
    - ai_thinking: AI is processing/thinking
    - step_progress: Progress update within a step
    - step_complete: Step completed
    - step_error: Error occurred
    - final_result: Final result with AI analysis
    
    **Response Format:** text/event-stream (SSE)
    
    **Example Event:**
    ```
    data: {"type": "step_start", "step": "0", "step_name": "Phân tích yêu cầu", "message": "Đang phân tích yêu cầu của bạn..."}
    
    data: {"type": "ai_thinking", "step": "0", "message": "Đang hiểu ý định của bạn..."}
    
    data: {"type": "final_result", "message": "Hoàn thành!", "data": {...}}
    
    data: [DONE]
    ```
    """
    
    streaming_service = AutoDiscoveryStreamingService(db)
    
    async def event_generator():
        try:
            async for event in streaming_service.execute_auto_discovery_stream(
                project_id=request.project_id,
                user_id=token.user_id,
                user_input=request.user_input
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            error_event = {
                "type": "error",
                "message": f"Lỗi: {str(e)}",
                "timestamp": None
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
        finally:
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/execute-flow")
async def execute_detailed_flow(
    request: AutoDiscoveryFlowRequest,
    token: TokenData = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Execute detailed product analysis flow (Phase 2)
    
    After products are discovered and imported, this endpoint handles:
    1. Crawl reviews (configurable count per product)
    2. Calculate trust scores
    3. Analyze reviews with AI
    4. Generate marketing tasks
    
    **Input:**
    - `project_id`: Project ID
    - `products`: List of {product_id, review_count}
    
    **Response:** text/event-stream (SSE) with real-time events
    
    **Example Events:**
    ```
    data: {"type": "flow_start", "message": "...", "products_count": 2}
    data: {"type": "review_crawl_progress", "product_id": "...", "current": 50, ...}
    data: {"type": "trust_score_progress", "product_id": "...", "score": 8.5, ...}
    data: {"type": "analysis_progress", "product_id": "...", "insights": [...], ...}
    data: {"type": "task_generation_progress", "product_id": "...", "tasks": [...], ...}
    data: {"type": "flow_complete", "results": {...}}
    data: [DONE]
    ```
    """
    
    flow_service = AutoDiscoveryFlowService(db)
    
    async def event_generator():
        try:
            async for event in flow_service.execute_detailed_flow_stream(
                project_id=request.project_id,
                user_id=token.user_id,
                products_config=request.products
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            error_event = {
                "type": "error",
                "message": f"Lỗi: {str(e)}",
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
        finally:
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


