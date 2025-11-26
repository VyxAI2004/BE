import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from core.dependencies.services import get_activity_log_service
from schemas.activity_log import (
    ListActivityLogsResponse,
    ActivityLogResponse,
    ActivityLogCreate,
    ActivityLogUpdate,
)
from services.sale_smart_ai_app.activity_log import ActivityLogService
from repositories.activity_log import ActivityLogFilters

router = APIRouter(prefix="/activity-logs", tags=["activity-logs"])


@router.post("/", response_model=ActivityLogResponse)
def create_activity_log(
    *,
    payload: ActivityLogCreate,
    activity_log_service: ActivityLogService = Depends(get_activity_log_service),
):
    """Tạo log mới"""
    try:
        log = activity_log_service.create(payload=payload)
        return log
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=ListActivityLogsResponse)
def get_activity_logs(
    *,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_id: Optional[uuid.UUID] = Query(None),
    action: Optional[str] = Query(None),
    target_id: Optional[uuid.UUID] = Query(None),
    target_type: Optional[str] = Query(None),
    activity_log_service: ActivityLogService = Depends(get_activity_log_service),
):
    """Lấy danh sách activity logs với filter"""
    try:
        filters = ActivityLogFilters(
            user_id=user_id,
            action=action,
            target_id=target_id,
            target_type=target_type,
        )
        logs = activity_log_service.search(filters=filters, skip=skip, limit=limit)
        total = activity_log_service.count(filters=filters)
        return ListActivityLogsResponse(
            total=total,
            items=[ActivityLogResponse.model_validate(log) for log in logs],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{log_id}", response_model=ActivityLogResponse)
def get_activity_log(
    *,
    log_id: uuid.UUID,
    activity_log_service: ActivityLogService = Depends(get_activity_log_service),
):
    """Lấy chi tiết 1 log"""
    log = activity_log_service.get(log_id)
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log not found")
    return log


@router.get("/users/{user_id}", response_model=ListActivityLogsResponse)
def get_by_user(
    user_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    activity_log_service: ActivityLogService = Depends(get_activity_log_service),
):
    """Lấy danh sách log theo user_id"""
    logs = activity_log_service.get_by_user(user_id=user_id, skip=skip, limit=limit)
    total = activity_log_service.count(filters=ActivityLogFilters(user_id=user_id))
    return ListActivityLogsResponse(
        total=total,
        items=[ActivityLogResponse.model_validate(log) for log in logs],
    )