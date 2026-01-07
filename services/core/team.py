import uuid
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from models.team import Team
from models.team_user import TeamUser
from models.user import User
from repositories.team import TeamRepository
from repositories.team_user import TeamUserRepository
from repositories.user import UserRepository
from schemas.team import (
    TeamCreate,
    TeamUpdate,
    TeamInviteRequest,
    TeamUserCreate,
    TeamUserUpdate,
    TeamUserResponse,
)
from shared.enums import TeamRoleEnum
from services.core.base import BaseService


class TeamService(BaseService[Team, TeamCreate, TeamUpdate, TeamRepository]):
    def __init__(self, db: Session):
        super().__init__(db, Team, TeamRepository)
        self.team_user_repo = TeamUserRepository(TeamUser, db)
        self.user_repository = UserRepository(User, db)

    def create_team(self, payload: TeamCreate, created_by: uuid.UUID) -> Team:
        team_data = payload.model_dump()
        team_data["created_by"] = created_by

        team = self.repository.create(obj_in=TeamCreate(**team_data))

        self.team_user_repo.create(
            obj_in=TeamUserCreate(
                team_id=team.id,
                user_id=created_by,
                role=TeamRoleEnum.OWNER.value,
                status="active",
                is_active=True,
            )
        )

        return team

    def get_team(self, team_id: uuid.UUID) -> Optional[Team]:
        return self.repository.get(id=team_id)

    def update_team(
        self, team_id: uuid.UUID, payload: TeamUpdate, user_id: uuid.UUID
    ) -> Optional[Team]:
        team = self.get_team(team_id)
        if not team:
            raise ValueError("Team not found")

        if not self.is_team_owner(team_id, user_id):
            raise ValueError("Only team owner can update team")

        db_team = self.repository.get(id=team_id)
        return self.repository.update(db_obj=db_team, payload=payload)

    def delete_team(self, team_id: uuid.UUID, user_id: uuid.UUID) -> None:
        team = self.get_team(team_id)
        if not team:
            raise ValueError("Team not found")

        if not self.is_team_owner(team_id, user_id):
            raise ValueError("Only team owner can delete team")

        self.repository.delete(id=team_id)

    def get_user_teams(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Team], int]:
        teams = self.repository.get_user_teams(user_id=user_id)
        total = len(teams)
        paginated = teams[skip : skip + limit]
        return paginated, total

    def get_team_members(self, team_id: uuid.UUID) -> List[TeamUserResponse]:
        return self.team_user_repo.get_team_members(team_id, is_active=True)

    def invite_user_to_team(
        self,
        team_id: uuid.UUID,
        request: TeamInviteRequest,
        inviter_id: uuid.UUID,
    ) -> TeamUser:
        team = self.get_team(team_id)
        if not team:
            raise ValueError("Team not found")

        if not self.can_manage_members(team_id, inviter_id):
            raise ValueError("You don't have permission to invite members")

        user = self.user_repository.get_by_email(email=request.email)
        if not user:
            raise ValueError(f"User with email {request.email} not found")

        existing = self.team_user_repo.get_team_member(team_id, user.id)

        if existing:
            if existing.is_active:
                raise ValueError("User is already a member of this team")
            return self.team_user_repo.update(
                db_obj=existing,
                obj_in=TeamUserUpdate(is_active=True, status="active"),
            )

        self.team_user_repo.create(
            obj_in=TeamUserCreate(
                team_id=team_id,
                user_id=user.id,
                role=request.role,
                status="active",
                invited_by=inviter_id,
                invited_at=datetime.utcnow(),
                joined_at=datetime.utcnow(),
                is_active=True,
            )
        )

        return self.team_user_repo.get_team_member_response(team_id, user.id)

    def remove_team_member(
        self, team_id: uuid.UUID, user_id: uuid.UUID, requester_id: uuid.UUID
    ) -> bool:
        team = self.get_team(team_id)
        if not team:
            raise ValueError("Team not found")

        if not self.can_manage_members(team_id, requester_id):
            raise ValueError("You don't have permission to remove members")

        if self.is_team_owner(team_id, user_id):
            raise ValueError("Cannot remove team owner")

        return self.team_user_repo.remove_member(team_id, user_id)

    def update_member_role(
        self,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        new_role: str,
        requester_id: uuid.UUID,
    ) -> TeamUser:
        team = self.get_team(team_id)
        if not team:
            raise ValueError("Team not found")

        if not self.is_team_owner(team_id, requester_id):
            raise ValueError("Only team owner can change member roles")

        if self.is_team_owner(team_id, user_id):
            raise ValueError("Cannot change owner role")

        return self.team_user_repo.update_member_role(team_id, user_id, new_role)

    def update_member(
        self,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        new_role: str = None,
        new_status: str = None,
        requester_id: uuid.UUID = None,
    ) -> Optional[TeamUser]:
        team = self.get_team(team_id)
        if not team:
            raise ValueError("Team not found")

        if requester_id and not self.is_team_owner(team_id, requester_id):
            raise ValueError("Only team owner can update member information")

        if new_role and self.is_team_owner(team_id, user_id):
            raise ValueError("Cannot change owner role")

        return self.team_user_repo.update_member(
            team_id, user_id, new_role, new_status
        )

    def is_team_member(self, team_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        return self.team_user_repo.is_team_member(
            team_id, user_id, is_active=True
        )

    def is_team_owner(self, team_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        member = self.team_user_repo.get_team_member(team_id, user_id)
        return (
            member is not None
            and member.role == TeamRoleEnum.OWNER.value
            and member.is_active
        )

    def is_team_lead(self, team_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        member = self.team_user_repo.get_team_member(team_id, user_id)
        return (
            member is not None
            and member.role
            in [TeamRoleEnum.OWNER.value, TeamRoleEnum.LEAD.value]
            and member.is_active
        )

    def can_manage_members(self, team_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        return self.is_team_lead(team_id, user_id)
