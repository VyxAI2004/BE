from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Annotated
from uuid import UUID
from pydantic import BaseModel, Field

from shared.enums import ProjectStatusEnum, PipelineTypeEnum, ScheduleEnum

class ProjectBase(BaseModel):
    """Base schema for Project model"""
    name: Annotated[str, Field(min_length=1, max_length=200)]
    description: Optional[str] = None
    target_product_name: Annotated[str, Field(min_length=1, max_length=200)]
    target_product_category: Optional[Annotated[str, Field(max_length=100)]] = None
    target_budget_range: Optional[Decimal] = None
    currency: Optional[Annotated[str, Field(max_length=10)]] = "VND"
    status: Optional[ProjectStatusEnum] = ProjectStatusEnum.DRAFT
    pipeline_type: Optional[PipelineTypeEnum] = PipelineTypeEnum.STANDARD
    crawl_schedule: Optional[ScheduleEnum] = None
    assigned_to: Optional[UUID] = None
    assigned_model_id: Optional[UUID] = None
    created_by: Optional[UUID] = None
    deadline: Optional[date] = None

class ProjectCreate(ProjectBase):
    """Schema for creating project"""
    pass

class ProjectUpdate(BaseModel):
    """Schema for updating project information"""
    name: Optional[Annotated[str, Field(min_length=1, max_length=200)]] = None
    description: Optional[str] = None
    target_product_name: Optional[Annotated[str, Field(min_length=1, max_length=200)]] = None
    target_product_category: Optional[Annotated[str, Field(max_length=100)]] = None
    target_budget_range: Optional[Decimal] = None
    currency: Optional[Annotated[str, Field(max_length=10)]] = None
    status: Optional[ProjectStatusEnum] = None
    pipeline_type: Optional[PipelineTypeEnum] = None
    crawl_schedule: Optional[ScheduleEnum] = None
    assigned_to: Optional[UUID] = None
    assigned_model_id: Optional[UUID] = None
    deadline: Optional[date] = None
    next_crawl_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class ProjectResponse(ProjectBase):
    """Schema for project response"""
    id: UUID
    created_by: Optional[UUID] = None
    next_crawl_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ListProjectsResponse(BaseModel):
    """Schema for list projects response"""
    items: List[ProjectResponse]
    total: int

    class Config:
        from_attributes = True

class ProjectAssignRequest(BaseModel):
    """Schema for assigning project to user"""
    assigned_to: UUID

class ProjectStatusUpdateRequest(BaseModel):
    """Schema for updating project status"""
    status: ProjectStatusEnum