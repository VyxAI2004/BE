from typing import List, Optional, Type, TypedDict

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.user import User
from schemas.user import UserCreate, UserUpdate

from .base import BaseRepository

class UserFilters(TypedDict, total=False):
    """User filters for comprehensive search"""

    q: Optional[str]
    username: Optional[str]
    email: Optional[str]

class UserRepository(BaseRepository[User, UserCreate , UserUpdate ]):
    def __init__(self, model: Type[User], db: Session):
        super().__init__(model, db)

    def _apply_filters(self, query, filters: Optional[UserFilters] = None):
        if not filters:
            return query

        filter_conditions = []
        if filters.get("q"):
            q = filters.get("q")
            filter_conditions.append(
                or_(
                    User.username.ilike(f"%{q}%"),
                    User.email.ilike(f"%{q}%"),
                )
            )
        if filters.get("username"):
            filter_conditions.append(
                User.username.ilike(f"%{filters.get('username')}%")
            )
        if filters.get("email"):
            filter_conditions.append(User.email.ilike(f"%{filters.get('email')}%"))
        
        if filter_conditions:
            query = query.filter(*filter_conditions)
        
        return query

    def search(
        self,
        *,
        filters: Optional[UserFilters] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[User]:
        db_query = self.db.query(User)
        db_query = self._apply_filters(db_query, filters)
        return db_query.offset(skip).limit(limit).all()

    def get_by_email(self, *, email: str) -> Optional[User]:
        return (
            self.db.query(User)
            .filter(User.email == email)
            .first()
        )
    
    def get_by_username(self, *, username: str) -> Optional[User]:
        return (
            self.db.query(User)
            .filter(User.username == username)
            .first()
        )
    
    def count(self, filters: Optional[UserFilters] = None) -> int:
        db_query = self.db.query(User)
        db_query = self._apply_filters(db_query, filters)
        return db_query.count()