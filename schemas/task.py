"""
Schemas cho Task.
"""
from typing import Optional, Dict, Any
from datetime import date, datetime
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field


class TaskBase(BaseModel):
    """Base schema cho Task"""
    name: str = Field(..., max_length=200, description="Tên task")
    description: Optional[str] = Field(None, description="Mô tả chi tiết")
    pipeline_stage: str = Field(..., max_length=50, description="Pipeline stage")
    stage_order: int = Field(..., description="Thứ tự trong stage")
    task_order: Optional[int] = Field(None, ge=1, le=5, description="Thứ tự ưu tiên của task (1-5)")
    task_type: Optional[str] = Field(None, max_length=50, description="Loại task")
    status: Optional[str] = Field("pending", max_length=20, description="Trạng thái")
    priority: Optional[str] = Field("medium", max_length=20, description="Độ ưu tiên")
    assigned_to: Optional[UUID] = Field(None, description="User được assign")
    assigned_model_id: Optional[UUID] = Field(None, description="AI model được assign")
    due_date: Optional[date] = Field(None, description="Ngày hết hạn")
    estimated_hours: Optional[Decimal] = Field(None, description="Số giờ ước tính")
    actual_hours: Optional[Decimal] = Field(None, description="Số giờ thực tế")
    stage_metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata")


class TaskCreate(TaskBase):
    """Schema để tạo task mới"""
    project_id: UUID = Field(..., description="ID của project")
    crawl_session_id: Optional[UUID] = Field(None, description="ID của crawl session")


class TaskUpdate(BaseModel):
    """Schema để cập nhật task"""
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    pipeline_stage: Optional[str] = Field(None, max_length=50)
    stage_order: Optional[int] = None
    task_order: Optional[int] = Field(None, ge=1, le=5)
    task_type: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, max_length=20)
    priority: Optional[str] = Field(None, max_length=20)
    assigned_to: Optional[UUID] = None
    assigned_model_id: Optional[UUID] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[Decimal] = None
    actual_hours: Optional[Decimal] = None
    stage_metadata: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None


class TaskResponse(TaskBase):
    """Response schema cho Task"""
    id: UUID
    project_id: UUID
    crawl_session_id: Optional[UUID]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskGenerationRequest(BaseModel):
    """Request schema để generate tasks"""
    max_tasks: Optional[int] = Field(default=5, ge=1, le=10, description="Số lượng tasks tối đa")


class TaskGenerationResponse(BaseModel):
    """Response schema cho task generation"""
    product_id: UUID
    tasks_generated: int
    tasks: list[Dict[str, Any]] = Field(..., description="List of generated tasks")
    message: str = Field(..., description="Thông báo kết quả")
