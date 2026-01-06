"""
Repository for Team
"""
from typing import List, Optional, Type
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_

from models.team import Team
from schemas.team import TeamCreate, TeamUpdate
from .base import BaseRepository


class TeamRepository(BaseRepository[Team, TeamCreate, TeamUpdate]):
    def __init__(self, model: Type[Team], db: Session):
        super().__init__(model, db)

    def get_user_teams(self, user_id: UUID, is_active: bool = True) -> List[Team]:
        """Get teams created by user or user is member of"""
        from models.team_user import TeamUser
        
        query = (
            self.db.query(Team)
            .outerjoin(TeamUser, (Team.id == TeamUser.team_id) & (TeamUser.is_active == True))
            .filter(
                or_(
                    Team.created_by == user_id,
                    TeamUser.user_id == user_id
                )
            )
            .distinct()
        )
        
        if is_active:
            query = query.filter(Team.is_active == True)
        
        return query.all()

    def get_team_by_name(self, name: str) -> Optional[Team]:
        """Get team by name"""
        return self.db.query(Team).filter(Team.name == name).first()

    def get_active_teams(self, skip: int = 0, limit: int = 100) -> tuple[List[Team], int]:
        """Get all active teams with pagination"""
        query = self.db.query(Team).filter(Team.is_active == True)
        total = query.count()
        teams = query.offset(skip).limit(limit).all()
        return teams, total
