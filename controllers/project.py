import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from core.dependencies.auth import verify_token
from core.dependencies.services import get_project_service
from schemas.auth import TokenData
from schemas.project import (
    ListProjectsResponse,
    ProjectResponse,
    ProjectCreate,
    ProjectUpdate,
    ProjectAssignRequest,
    ProjectStatusUpdateRequest,
)
from schemas.project_user import (
    ProjectMemberAssignRequest,
    ProjectMemberRemoveRequest,
    ProjectUserResponse
)
from shared.enums import ProjectStatusEnum
from services.sale_smart_ai_app.project import ProjectService
from repositories.project import ProjectFilters

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("/", response_model=ProjectResponse)
def create_project(
    *,
    payload: ProjectCreate,
    project_service: ProjectService = Depends(get_project_service),
    user_from_token: TokenData = Depends(verify_token),
):
    """Create new project"""
    try:
        # Add the created_by field to the payload
        # We need to manually handle this since we removed create_project wrapper
        project_data = payload.model_dump()
        project_data["created_by"] = user_from_token.user_id
        
        project = project_service.create(
            payload=ProjectCreate(**project_data)
        )
        return project
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=ListProjectsResponse)
def get_list_projects(
    *,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    q: Optional[str] = Query(None, description="Search in name, description, target product"),
    name: Optional[str] = Query(None, description="Filter by project name"),
    project_status: Optional[ProjectStatusEnum] = Query(None, description="Filter by project status", alias="status"),
    created_by: Optional[uuid.UUID] = Query(None, description="Filter by creator"),
    assigned_to: Optional[uuid.UUID] = Query(None, description="Filter by assignee"),
    pipeline_type: Optional[str] = Query(None, description="Filter by pipeline type"),
    target_product_category: Optional[str] = Query(None, description="Filter by target product category"),
    project_service: ProjectService = Depends(get_project_service),
    user_from_token: TokenData = Depends(verify_token),
):
    try:
        user_roles = user_from_token.roles if hasattr(user_from_token, 'roles') else []
        is_admin = any(role in ["Admin", "Super Admin"] for role in user_roles)
        
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Admin or Super Admin can view all projects. Use GET /projects/my to see your projects."
            )
        
        filters_dict = {}
        if q:
            filters_dict["q"] = q
        if name:
            filters_dict["name"] = name
        if project_status:
            filters_dict["status"] = project_status
        if created_by:
            filters_dict["created_by"] = created_by
        if assigned_to:
            filters_dict["assigned_to"] = assigned_to
        if pipeline_type:
            filters_dict["pipeline_type"] = pipeline_type
        if target_product_category:
            filters_dict["target_product_category"] = target_product_category

        filters = ProjectFilters(**filters_dict) if filters_dict else None
        
        projects = project_service.get_multi(
            filters=filters,
            skip=skip,
            limit=limit,
        )

        total = project_service.count(filters=filters)

        return ListProjectsResponse(
            total=total,
            items=[ProjectResponse.model_validate(project) for project in projects]
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/my", response_model=ListProjectsResponse)
def get_my_projects(
    *,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    project_service: ProjectService = Depends(get_project_service),
    user_from_token: TokenData = Depends(verify_token),
):
    """Get all projects related to current user (created, assigned, or member of)"""
    try:
        user_id = user_from_token.user_id
        projects, total = project_service.get_my_projects(
            user_id=user_id,
            skip=skip,
            limit=limit
        )
        return ListProjectsResponse(
            total=total,
            items=[ProjectResponse.model_validate(project) for project in projects]
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    *,
    project_id: uuid.UUID,
    project_service: ProjectService = Depends(get_project_service),
    user_from_token: TokenData = Depends(verify_token),
):
    """Get project detail by ID"""
    project = project_service.get(id=project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    *,
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    project_service: ProjectService = Depends(get_project_service),
    user_from_token: TokenData = Depends(verify_token),
):
    """Update project"""
    try:
        project = project_service.update_project(
            project_id=project_id,
            payload=payload,
            user_id=user_from_token.user_id
        )
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.put("/{project_id}", response_model=ProjectResponse)
def replace_project(
    *,
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    project_service: ProjectService = Depends(get_project_service),
    user_from_token: TokenData = Depends(verify_token),
):
    """Replace project (same as PATCH for this implementation)"""
    try:
        project = project_service.update_project(
            project_id=project_id,
            payload=payload,
            user_id=user_from_token.user_id
        )
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    *,
    project_id: uuid.UUID,
    project_service: ProjectService = Depends(get_project_service),
    user_from_token: TokenData = Depends(verify_token),
):
    """Delete project"""
    try:
        project_service.delete_project(
            project_id=project_id,
            user_id=user_from_token.user_id
        )
        return None
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{project_id}/assign", response_model=ProjectResponse)
def assign_project(
    *,
    project_id: uuid.UUID,
    request: ProjectAssignRequest,
    project_service: ProjectService = Depends(get_project_service),
    user_from_token: TokenData = Depends(verify_token),
):
    """Assign project to a single user (legacy endpoint)"""
    try:
        project = project_service.assign_project(
            project_id=project_id,
            assigned_to=request.assigned_to,
            user_id=user_from_token.user_id
        )
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{project_id}/members", response_model=ProjectResponse)
def assign_multiple_users_to_project(
    *,
    project_id: uuid.UUID,
    request: ProjectMemberAssignRequest,
    project_service: ProjectService = Depends(get_project_service),
    user_from_token: TokenData = Depends(verify_token),
):
    """Assign multiple users to project as members"""
    try:
        project = project_service.assign_multiple_users_to_project(
            project_id=project_id,
            request=request,
            user_id=user_from_token.user_id
        )
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete("/{project_id}/members", response_model=ProjectResponse)
def remove_users_from_project(
    *,
    project_id: uuid.UUID,
    request: ProjectMemberRemoveRequest,
    project_service: ProjectService = Depends(get_project_service),
    user_from_token: TokenData = Depends(verify_token),
):
    """Remove multiple users from project"""
    try:
        project = project_service.remove_users_from_project(
            project_id=project_id,
            user_ids=request.user_ids,
            user_id=user_from_token.user_id
        )
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{project_id}/members", response_model=List[ProjectUserResponse])
def get_project_members(
    *,
    project_id: uuid.UUID,
    project_service: ProjectService = Depends(get_project_service),
    user_from_token: TokenData = Depends(verify_token),
):
    """Get all members of a project"""
    try:
        members = project_service.get_project_members(project_id=project_id)
        return [ProjectUserResponse.model_validate(member) for member in members]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{project_id}/status", response_model=ProjectResponse)
def update_project_status(
    *,
    project_id: uuid.UUID,
    request: ProjectStatusUpdateRequest,
    project_service: ProjectService = Depends(get_project_service),
    user_from_token: TokenData = Depends(verify_token),
):
    """Update project status"""
    try:
        project = project_service.update_project_status(
            project_id=project_id,
            status=request.status,
            user_id=user_from_token.user_id
        )
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
