"""
Controller cho AI Task Generation.
"""
import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session

from core.dependencies.db import get_db
from core.dependencies.auth import verify_token, TokenData
from services.features.product_intelligence.task_generation.task_generator_service import (
    TaskGeneratorService,
)
from schemas.task import TaskGenerationRequest, TaskGenerationResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["AI Task Generation"])


def get_task_generator_service(db: Session = Depends(get_db)) -> TaskGeneratorService:
    """Dependency để get TaskGeneratorService"""
    return TaskGeneratorService(db)


@router.post(
    "/{product_id}/generate-tasks",
    response_model=TaskGenerationResponse,
    status_code=status.HTTP_200_OK,
)
def generate_marketing_tasks(
    product_id: UUID,
    request: TaskGenerationRequest,
    task_generator_service: TaskGeneratorService = Depends(get_task_generator_service),
    token: TokenData = Depends(verify_token),
):
    """
    Generate marketing tasks từ product analytics.
    
    **Flow:**
    1. Lấy analytics data từ product (trust score, reviews, sentiment)
    2. Sử dụng LLM để generate marketing tasks dựa trên analytics
    3. Tạo tasks trong database
    4. Trả về list tasks đã tạo
    
    **Tasks được generate sẽ focus vào:**
    - Marketing research (research đối thủ)
    - Competitive analysis (phân tích cạnh tranh)
    - Content strategy (chiến lược nội dung)
    - Pricing strategy (chiến lược giá)
    - Market positioning (định vị thị trường)
    
    **Example Response:**
    ```json
    {
        "product_id": "uuid",
        "tasks_generated": 5,
        "tasks": [
            {
                "id": "uuid",
                "name": "Research 5 sản phẩm đối thủ có trust score > 80",
                "description": "...",
                "task_type": "marketing_research",
                "priority": "high",
                "status": "pending"
            }
        ],
        "message": "Đã tạo 5 marketing tasks thành công"
    }
    ```
    """
    try:
        logger.info(f"Generating tasks for product {product_id}, user {token.user_id}, max_tasks={request.max_tasks}")

        # Validate và set default max_tasks
        max_tasks = request.max_tasks if request.max_tasks is not None else 5
        if max_tasks < 1 or max_tasks > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="max_tasks phải từ 1 đến 10",
            )

        # Generate và save tasks
        created_tasks = task_generator_service.generate_and_save_tasks(
            product_id=product_id,
            user_id=token.user_id,
            max_tasks=max_tasks,
        )

        if not created_tasks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể generate tasks. Vui lòng đảm bảo product đã có analytics data.",
            )

        return TaskGenerationResponse(
            product_id=product_id,
            tasks_generated=len(created_tasks),
            tasks=created_tasks,
            message=f"Đã tạo {len(created_tasks)} marketing tasks thành công từ analytics data",
        )

    except ValueError as e:
        logger.error(f"ValueError generating tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error generating tasks for product {product_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi generate tasks: {str(e)}",
        )


@router.post(
    "/{product_id}/generate-tasks-preview",
    response_model=TaskGenerationResponse,
    status_code=status.HTTP_200_OK,
)
def preview_marketing_tasks(
    product_id: UUID,
    request: TaskGenerationRequest,
    task_generator_service: TaskGeneratorService = Depends(get_task_generator_service),
    token: TokenData = Depends(verify_token),
):
    """
    Preview marketing tasks (không lưu vào database).
    
    Dùng để xem trước tasks sẽ được generate trước khi lưu.
    """
    try:
        logger.info(f"Previewing tasks for product {product_id}, user {token.user_id}")

        # Generate tasks (không save)
        generated_tasks = task_generator_service.generate_tasks_from_product_analytics(
            product_id=product_id,
            user_id=token.user_id,
            max_tasks=request.max_tasks,
        )

        if not generated_tasks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể generate tasks. Vui lòng đảm bảo product đã có analytics data.",
            )

        return TaskGenerationResponse(
            product_id=product_id,
            tasks_generated=len(generated_tasks),
            tasks=generated_tasks,
            message=f"Preview {len(generated_tasks)} marketing tasks (chưa lưu vào database)",
        )

    except ValueError as e:
        logger.error(f"ValueError previewing tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error previewing tasks for product {product_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi preview tasks: {str(e)}",
        )
