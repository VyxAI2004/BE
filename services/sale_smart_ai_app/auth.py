from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from datetime import datetime, timezone, timedelta
from jwt import encode, decode
from env import env
from passlib.context import CryptContext

from shared.enums import RoleEnum
from models.user import User
from schemas.user import UserCreate, UserUpdate, UserUpdateInternal
from repositories.user import UserRepository
from .base import BaseService
from schemas.auth import Token
from .permission import PermissionService

api_key_header = APIKeyHeader(name="Authorization")

JWT_SECRET_KEY = env.JWT_SECRET_KEY
JWT_ALGORITHM = env.JWT_ALGORITHM


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class AuthService(
    BaseService[
        User,
        UserCreate,
        UserUpdate,
        UserRepository,
    ]
):
    def __init__(self, db: Session):
        super().__init__(db, User, UserRepository)

    def verify_password(self, plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password):
        return pwd_context.hash(password)

    def _create_tokens(self, user: User, roles: list[str]) -> Token:
        now = datetime.now(timezone.utc)
        
        # Get user permissions using PermissionService

        perm_service = PermissionService(self.db)
        global_permissions, project_permissions = perm_service.get_all_user_permissions(user.id)

        access_token = encode(
            {
                "sub": str(user.id),
                "email": user.email,
                "roles": roles,
                "global_permissions": global_permissions,
                "project_permissions": project_permissions,
                "iat": now,
                "exp": now + timedelta(weeks=env.JWT_ACCESS_TOKEN_EXPIRE_WEEKS),
                "type": "access"
            },
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM
        )

        refresh_token = encode(
            {
                "sub": str(user.id),
                "type": "refresh",
                "iat": now,
                "exp": now + timedelta(weeks=env.JWT_REFRESH_TOKEN_EXPIRE_WEEKS)
            },
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM
        )

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=env.JWT_ACCESS_TOKEN_EXPIRE_WEEKS * 7 * 24 * 60 * 60,
            token_type="Bearer"
        )

    def sign_in(self, email: str, password: str) -> Token:
        user = self.repository.get_by_email(email=email)
        if (
            not user
            or not user.password_hash
            or not self.verify_password(password, user.password_hash)
        ):
            raise HTTPException(status_code=401, detail="Wrong email or password")

        roles = [ur.role.name for ur in user.roles]
        return self._create_tokens(user, roles)

    def change_password(self, user_id: UUID, old_password: str, new_password: str) -> Token:
        if old_password == new_password:
            raise HTTPException(
                status_code=400,
                detail="New password must be different from old password",
            )

        user = self.repository.get(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not self.verify_password(old_password, user.password_hash):
            raise HTTPException(status_code=401, detail="Old password is incorrect")

        update_data = UserUpdateInternal(password_hash=self.get_password_hash(new_password))
        updated_user = self.repository.update(db_obj=user, obj_in=update_data)

        roles = [ur.role.name for ur in updated_user.roles]
        return self._create_tokens(updated_user, roles)

    def refresh_token(self, refresh_token: str) -> Token:
        try:
            data = decode(refresh_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        if data.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id = data.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        user = self.repository.get(UUID(user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        roles = [ur.role.name for ur in user.roles]
        return self._create_tokens(user, roles)
