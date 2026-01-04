"""
Controller cho Task - API Endpoints.
"""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.dependencies.db import get_db
from core.dependencies.auth import verify_token, TokenData
from services.core.task import TaskService
from schemas.task import TaskCreate, TaskUpdate, TaskResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def get_task_service(db: Session = Depends(get_db)) -> TaskService:
    """Dependency để get TaskService"""
    return TaskService(db)


@router.get("/", response_model=List[TaskResponse])
def get_tasks(
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    product_id: Optional[UUID] = Query(None, description="Filter by product"),
    assigned_to: Optional[UUID] = Query(None, description="Filter by assigned user"),
    status_filter: Optional[str] = Query(None, description="Filter by status", alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    task_service: TaskService = Depends(get_task_service),
    token: TokenData = Depends(verify_token),
):
    """Get tasks with authorization - only tasks user can access"""
    try:
        # Get user's accessible tasks
        user_id = token.user_id
        
        # Get all tasks user has access to (creator, assigned, or project member)
        all_accessible_tasks = task_service.get_user_accessible_tasks(user_id=user_id)
        
        # Apply filters
        filtered_tasks = all_accessible_tasks
        
        if project_id:
            filtered_tasks = [t for t in filtered_tasks if t.project_id == project_id]
        
        if product_id:
            filtered_tasks = [t for t in filtered_tasks if t.product_id == product_id]
        
        if assigned_to:
            filtered_tasks = [t for t in filtered_tasks if t.assigned_to == assigned_to]
        
        if status_filter:
            filtered_tasks = [t for t in filtered_tasks if t.status == status_filter]
        
        # Apply pagination
        paginated_tasks = filtered_tasks[skip : skip + limit]
        
        return paginated_tasks
    except Exception as e:
        logger.error(f"Error getting tasks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting tasks: {str(e)}",
        )


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: UUID,
    task_service: TaskService = Depends(get_task_service),
    token: TokenData = Depends(verify_token),
):
    """Get task by ID - only if user has access"""
    task = task_service.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    # Check authorization
    user_id = token.user_id
    can_access = task_service.can_user_access_task(user_id=user_id, task=task)
    
    if not can_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this task",
        )
    
    return task


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    task_service: TaskService = Depends(get_task_service),
    token: TokenData = Depends(verify_token),
):
    """Create a new task - set creator to current user"""
    try:
        # Set creator as current user
        payload_dict = payload.model_dump()
        payload_dict['created_by'] = token.user_id
        payload = TaskCreate(**payload_dict)
        
        return task_service.create(payload=payload)
    except Exception as e:
        logger.error(f"Error creating task: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating task: {str(e)}",
        )


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    task_service: TaskService = Depends(get_task_service),
    token: TokenData = Depends(verify_token),
):
    """Update task - only if user is creator or assigned"""
    task = task_service.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    # Check authorization - only creator or assigned user can update
    user_id = token.user_id
    is_creator = task.created_by == user_id
    is_assigned = task.assigned_to == user_id
    
    if not (is_creator or is_assigned):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only creator or assigned user can update this task",
        )
    
    try:
        return task_service.update(db_obj=task, payload=payload)
    except Exception as e:
        logger.error(f"Error updating task: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating task: {str(e)}",
        )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: UUID,
    task_service: TaskService = Depends(get_task_service),
    token: TokenData = Depends(verify_token),
):
    """Delete task"""
    task = task_service.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    try:
        task_service.delete(id=task_id)
        return None
    except Exception as e:
        logger.error(f"Error deleting task: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting task: {str(e)}",
        )


@router.patch("/{task_id}/complete", response_model=TaskResponse)
def complete_task(
    task_id: UUID,
    task_service: TaskService = Depends(get_task_service),
    token: TokenData = Depends(verify_token),
):
    """Mark task as completed - chỉ cho phép complete tuần tự theo task_order"""
    from datetime import datetime
    
    task = task_service.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    # Nếu task có task_order, kiểm tra thứ tự tuần tự
    if task.task_order is not None:
        # Lấy tất cả tasks cùng project có task_order
        project_tasks = task_service.get_by_project(task.project_id)
        project_tasks_with_order = [t for t in project_tasks if t.task_order is not None]
        
        # Tìm task có order nhỏ nhất chưa completed
        pending_tasks = [t for t in project_tasks_with_order if t.status != 'completed']
        if pending_tasks:
            min_pending_order = min(t.task_order for t in pending_tasks)
            
            # Chỉ cho phép complete task có order nhỏ nhất
            if task.task_order != min_pending_order:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Bạn phải hoàn thành nhiệm vụ thứ {min_pending_order} trước. Nhiệm vụ hiện tại là thứ {task.task_order}.",
                )
    
    try:
        update_payload = TaskUpdate(
            status="completed",
            completed_at=datetime.utcnow(),
        )
        return task_service.update(db_obj=task, payload=update_payload)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing task: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error completing task: {str(e)}",
        )
