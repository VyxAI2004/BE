import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from core.dependencies.auth import verify_token
from core.dependencies.services import get_team_service, get_permission_service
from schemas.auth import TokenData
from schemas.team import (
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    TeamUserResponse,
    TeamInviteRequest,
    ListTeamsResponse,
)
from services.core.team import TeamService
from services.core.permission import PermissionService

router = APIRouter(prefix="/teams", tags=["teams"])


@router.post("/", response_model=TeamResponse)
def create_team(
    *,
    payload: TeamCreate,
    team_service: TeamService = Depends(get_team_service),
    user_from_token: TokenData = Depends(verify_token),
):
    """Create a new team. Creator automatically becomes the owner."""
    try:
        # Validate user is authenticated
        if not user_from_token.user_id:
            raise ValueError("User not authenticated - missing user ID in token")
        
        team = team_service.create_team(
            payload=payload,
            created_by=user_from_token.user_id
        )
        return team
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/my", response_model=ListTeamsResponse)
def get_my_teams(
    *,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    team_service: TeamService = Depends(get_team_service),
    user_from_token: TokenData = Depends(verify_token),
):
    """Get all teams where the user is a member or creator"""
    try:
        teams, total = team_service.get_user_teams(
            user_id=user_from_token.user_id,
            skip=skip,
            limit=limit
        )
        
        # Build response with enriched members for each team
        team_responses = []
        for team in teams:
            members = team_service.get_team_members(team.id)
            team_responses.append(TeamResponse(
                id=team.id,
                name=team.name,
                description=team.description,
                created_by=team.created_by,
                is_active=team.is_active,
                created_at=team.created_at,
                updated_at=team.updated_at,
                members=members
            ))
        
        return ListTeamsResponse(items=team_responses, total=total)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{team_id}", response_model=TeamResponse)
def get_team(
    *,
    team_id: uuid.UUID,
    team_service: TeamService = Depends(get_team_service),
    permission_service: PermissionService = Depends(get_permission_service),
    user_from_token: TokenData = Depends(verify_token),
):
    """Get team details. User must be a member."""
    try:
        team = team_service.get_team(team_id=team_id)
        
        if not team:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
        
        # Check membership
        permission_service.enforce_team_membership(
            user_id=user_from_token.user_id,
            team_id=team_id
        )
        
        return team
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{team_id}", response_model=TeamResponse)
def update_team(
    *,
    team_id: uuid.UUID,
    payload: TeamUpdate,
    team_service: TeamService = Depends(get_team_service),
    user_from_token: TokenData = Depends(verify_token),
):
    """Update team details. Only owner can update."""
    try:
        team = team_service.update_team(
            team_id=team_id,
            payload=payload,
            user_id=user_from_token.user_id
        )
        return team
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(
    *,
    team_id: uuid.UUID,
    team_service: TeamService = Depends(get_team_service),
    user_from_token: TokenData = Depends(verify_token),
):
    """Delete a team and all its projects. Only owner can delete."""
    try:
        team_service.delete_team(
            team_id=team_id,
            user_id=user_from_token.user_id
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{team_id}/invite", response_model=TeamUserResponse)
def invite_user_to_team(
    *,
    team_id: uuid.UUID,
    request: TeamInviteRequest,
    team_service: TeamService = Depends(get_team_service),
    user_from_token: TokenData = Depends(verify_token),
):
    """Invite a user to the team. Only leads and owners can invite."""
    try:
        team_user = team_service.invite_user_to_team(
            team_id=team_id,
            request=request,
            inviter_id=user_from_token.user_id
        )
        return team_user
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{team_id}/members", response_model=List[TeamUserResponse])
def get_team_members(
    *,
    team_id: uuid.UUID,
    team_service: TeamService = Depends(get_team_service),
    permission_service: PermissionService = Depends(get_permission_service),
    user_from_token: TokenData = Depends(verify_token),
):
    """Get all members of a team. User must be a member."""
    try:
        permission_service.enforce_team_membership(
            user_id=user_from_token.user_id,
            team_id=team_id
        )
        
        members = team_service.get_team_members(team_id=team_id)
        return members
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{team_id}/members/{user_id}", response_model=TeamUserResponse)
def update_member_role(
    *,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    new_role: str = Query(None, description="New role: owner, lead, or member"),
    new_status: str = Query(None, description="New status: active, inactive, or pending"),
    team_service: TeamService = Depends(get_team_service),
    user_from_token: TokenData = Depends(verify_token),
):
    """Update a member's role and/or status. Only owner can change roles/status."""
    try:
        team_user = team_service.update_member(
            team_id=team_id,
            user_id=user_id,
            new_role=new_role,
            new_status=new_status,
            requester_id=user_from_token.user_id
        )
        return team_user
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_team_member(
    *,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    team_service: TeamService = Depends(get_team_service),
    user_from_token: TokenData = Depends(verify_token),
):
    """Remove a member from the team. Only leads+ can remove."""
    try:
        team_service.remove_team_member(
            team_id=team_id,
            user_id=user_id,
            requester_id=user_from_token.user_id
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
