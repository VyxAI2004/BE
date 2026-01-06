"""
Repository for TeamUser
"""
from typing import List, Optional, Type
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.team_user import TeamUser
from models.user import User
from shared.enums import TeamRoleEnum
from schemas.team import TeamUserCreate, TeamUserUpdate, TeamUserResponse
from .base import BaseRepository


class TeamUserRepository(BaseRepository[TeamUser, TeamUserCreate, TeamUserUpdate]):
    def __init__(self, model: Type[TeamUser], db: Session):
        super().__init__(model, db)

    def get_team_members(self, team_id: UUID, is_active: bool = True) -> List[TeamUserResponse]:
        """Get all members of a team with user details"""
        query = self.db.query(
            TeamUser.id,
            TeamUser.team_id,
            TeamUser.user_id,
            User.username,
            User.email,
            User.full_name,
            TeamUser.role,
            TeamUser.status,
            TeamUser.is_active,
            TeamUser.joined_at,
            TeamUser.invited_at,
            TeamUser.accepted_at
        ).join(User, TeamUser.user_id == User.id).filter(TeamUser.team_id == team_id)
        
        if is_active:
            query = query.filter(TeamUser.is_active == True)
        
        results = query.all()
        
        # Convert tuples to TeamUserResponse objects
        members = []
        for row in results:
            member_response = TeamUserResponse(
                id=row.id,
                team_id=row.team_id,
                user_id=row.user_id,
                username=row.username,
                email=row.email,
                full_name=row.full_name,
                role=row.role,
                status=row.status,
                is_active=row.is_active,
                joined_at=row.joined_at,
                invited_at=row.invited_at,
                accepted_at=row.accepted_at
            )
            members.append(member_response)
        
        return members

    def get_team_member(self, team_id: UUID, user_id: UUID) -> Optional[TeamUser]:
        """Get specific team member"""
        return self.db.query(TeamUser).filter(
            TeamUser.team_id == team_id,
            TeamUser.user_id == user_id
        ).first()

    def is_team_member(self, team_id: UUID, user_id: UUID, is_active: bool = True) -> bool:
        """Check if user is a member of team"""
        query = self.db.query(TeamUser).filter(
            TeamUser.team_id == team_id,
            TeamUser.user_id == user_id
        )
        
        if is_active:
            query = query.filter(TeamUser.is_active == True)
        
        return query.first() is not None

    def get_user_teams(self, user_id: UUID, is_active: bool = True) -> List[TeamUser]:
        """Get all teams user is member of"""
        query = self.db.query(TeamUser).filter(TeamUser.user_id == user_id)
        
        if is_active:
            query = query.filter(TeamUser.is_active == True)
        
        return query.all()

    def get_by_email(self, team_id: UUID, email: str) -> Optional[TeamUser]:
        """Get team member by email"""
        from models.user import User
        
        return self.db.query(TeamUser).join(
            User, TeamUser.user_id == User.id
        ).filter(
            TeamUser.team_id == team_id,
            User.email == email
        ).first()

    def remove_member(self, team_id: UUID, user_id: UUID) -> bool:
        """Remove member from team"""
        team_user = self.get_team_member(team_id, user_id)
        if team_user:
            self.db.delete(team_user)
            self.db.commit()
            return True
        return False

    def update_member_role(self, team_id: UUID, user_id: UUID, role: str) -> Optional[TeamUser]:
        """Update member role"""
        team_user = self.get_team_member(team_id, user_id)
        if team_user:
            team_user.role = role
            self.db.commit()
            self.db.refresh(team_user)
        return team_user

    def update_member(self, team_id: UUID, user_id: UUID, role: str = None, status: str = None) -> Optional[TeamUserResponse]:
        """Update member role and/or status, return with user details"""
        team_user = self.get_team_member(team_id, user_id)
        if team_user:
            if role:
                team_user.role = role
            if status:
                team_user.status = status
            self.db.commit()
            self.db.refresh(team_user)
        
        # Query to get user details and return as TeamUserResponse
        if not team_user:
            return None
            
        result = self.db.query(
            TeamUser.id,
            TeamUser.team_id,
            TeamUser.user_id,
            User.username,
            User.email,
            User.full_name,
            TeamUser.role,
            TeamUser.status,
            TeamUser.is_active,
            TeamUser.joined_at,
            TeamUser.invited_at,
            TeamUser.accepted_at
        ).join(User, TeamUser.user_id == User.id).filter(
            TeamUser.team_id == team_id,
            TeamUser.user_id == user_id
        ).first()
        
        if result:
            return TeamUserResponse(
                id=result.id,
                team_id=result.team_id,
                user_id=result.user_id,
                username=result.username,
                email=result.email,
                full_name=result.full_name,
                role=result.role,
                status=result.status,
                is_active=result.is_active,
                joined_at=result.joined_at,
                invited_at=result.invited_at,
                accepted_at=result.accepted_at
            )
        
        return None
