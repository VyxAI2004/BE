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
    assigned_to: Optional[UUID] = Query(None, description="Filter by assigned user"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    task_service: TaskService = Depends(get_task_service),
    token: TokenData = Depends(verify_token),
):
    """Get tasks với filters"""
    try:
        if project_id:
            tasks = task_service.get_by_project(project_id=project_id, skip=skip, limit=limit)
        elif assigned_to:
            tasks = task_service.get_by_assigned_to(user_id=assigned_to, skip=skip, limit=limit)
        elif status:
            tasks = task_service.get_by_status(status=status, skip=skip, limit=limit)
        else:
            # Get all tasks for user's projects
            tasks = task_service.get_multi(skip=skip, limit=limit)
        
        return tasks
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
    """Get task by ID"""
    task = task_service.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    task_service: TaskService = Depends(get_task_service),
    token: TokenData = Depends(verify_token),
):
    """Create a new task"""
    try:
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
    """Update task - nếu đang uncheck completed, không cần validate thứ tự"""
    task = task_service.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    # Nếu đang uncheck (từ completed về in_progress), cho phép
    # Nếu đang mark as completed, redirect đến complete endpoint
    if payload.status == "completed" and task.status != "completed":
        # Redirect logic sẽ được handle bởi frontend gọi complete endpoint
        pass
    
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
