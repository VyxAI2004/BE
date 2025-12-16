import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from models.user import User
from core.security import hash_password
from repositories.user import UserFilters, UserRepository
from repositories.role import RoleRepository
from models.role import Role
from schemas.user import UserCreate, UserUpdate
from .base import BaseService

class UserService(BaseService[User, UserCreate, UserUpdate, UserRepository]):
    def __init__(self, db: Session):
        super().__init__(db, User, UserRepository)

        self.role_repository = RoleRepository(model=Role, db=db)

    def get_by_email(self, *, email: str) -> Optional[User]:
        return self.repository.get_by_email(email=email)

    def get_user(self, *, user_id: uuid.UUID) -> Optional[User]:
        return self.get(user_id)

    def search(
        self,
        *,
        q: Optional[str] = None,
        username: Optional[str] = None,
        email: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[User]:
        """Search users with filters"""
        filters: Optional[UserFilters] = None

        filter_dict = {}
        if q:
            filter_dict["q"] = q
        if username:
            filter_dict["username"] = username
        if email:
            filter_dict["email"] = email

        if filter_dict:
            filters = UserFilters(**filter_dict)

        return self.repository.search(filters=filters, skip=skip, limit=limit)
    

    def create_user(self, payload: UserCreate) -> User:
        hashed = hash_password(payload.password_hash)
        payload_dict = payload.model_dump() if hasattr(payload, 'model_dump') else payload.dict()
        payload_dict["password_hash"] = hashed
        payload_dict.pop("password", None)
        user = self.create(payload=UserCreate(**payload_dict))
        
        # Assign default role 'User' using role repository
        default_role = self.role_repository.get_by_name(name="User")
        if default_role:
            self.repository.add_role(user.id, default_role.id)
            
        return user

    def assign_role_to_user(self, user_id: uuid.UUID, role_id: uuid.UUID) -> Optional[User]:
        # 1. Check role exists using role repository
        role = self.role_repository.get(role_id)
        if not role:
            raise ValueError("Role not found")
            
        # 2. Check user exists
        user = self.get(user_id)
        if not user:
            raise ValueError("User not found")

        # 3. Check if already assigned using role repository
        if self.role_repository.check_user_has_role(user_id=str(user_id), role_id=str(role_id)):
            return user

        # 4. Assign
        return self.repository.add_role(user_id, role_id)

    def remove_role_from_user(self, user_id: uuid.UUID, role_id: uuid.UUID) -> Optional[User]:
        return self.repository.remove_role(user_id, role_id)

    def promote_user_to_admin(
        self, 
        user_id: uuid.UUID, 
        role_slug: str, 
        promoted_by: uuid.UUID,
        reason: Optional[str] = None
    ) -> Optional[User]:
        """
        Promote user to admin or super_admin role
        Only super_admin can promote users
        """
        # 1. Validate role_slug
        if role_slug not in ["admin", "super_admin"]:
            raise ValueError("Can only promote to 'admin' or 'super_admin' roles")
        
        # 2. Get target role using role repository
        target_role = self.role_repository.get_by_slug(slug=role_slug)
        if not target_role:
            raise ValueError(f"Role '{role_slug}' not found")
        
        # 3. Check user exists
        user = self.get(user_id)
        if not user:
            raise ValueError("User not found")
        
        # 4. Check if user already has this role using role repository
        if self.role_repository.check_user_has_role(
            user_id=str(user_id), 
            role_id=str(target_role.id)
        ):
            raise ValueError(f"User already has '{role_slug}' role")
        
        # 5. Remove existing admin/super_admin roles using role repository
        admin_roles = self.role_repository.get_admin_roles(slugs=["admin", "super_admin"])
        admin_role_ids = [str(role.id) for role in admin_roles]
        self.repository.remove_admin_roles(user_id=str(user_id), admin_role_ids=admin_role_ids)
        
        # 6. Assign new role with reason using repository
        default_reason = reason or f"Promoted to {role_slug} by super admin"
        user = self.repository.assign_role_with_reason(
            user_id=str(user_id),
            role_id=str(target_role.id),
            reason=default_reason
        )
        
        # 7. Log the promotion
        print(f"User {user.email} promoted to {role_slug} by user {promoted_by}")
        
        return user

    def update_user(self, user_id: uuid.UUID, payload: UserUpdate) -> Optional[User]:
        db_user = self.get(user_id)
        if not db_user:
            return None
        payload_dict = payload.model_dump(exclude_unset=True)
        if payload_dict.get("password"):
            payload_dict["password_hash"] = hash_password(payload_dict.pop("password"))
        
        # Convert urls list to JSON format for storage
        # SQLAlchemy JSON field can store list directly, but ensure it's a list
        if "urls" in payload_dict:
            if payload_dict["urls"] is None:
                payload_dict["urls"] = None
            elif isinstance(payload_dict["urls"], list):
                # Keep as list - SQLAlchemy JSON will handle it
                payload_dict["urls"] = payload_dict["urls"]
            else:
                payload_dict["urls"] = []
        
        payload_update = UserUpdate(**payload_dict)
        updated_user = self.update(db_obj=db_user, payload=payload_update)
        
        # Convert urls from JSON to list for response
        if updated_user and updated_user.urls:
            if isinstance(updated_user.urls, dict):
                # If stored as dict, convert to list
                updated_user.urls = updated_user.urls.get('items', []) if 'items' in updated_user.urls else []
            elif not isinstance(updated_user.urls, list):
                updated_user.urls = []
        
        return updated_user

    def delete_user(self, user_id: uuid.UUID) -> None:
        self.delete(id=user_id)

    def count_users(self, *, filters: Optional[UserFilters] = None) -> int:
        filters_dict = dict(filters) if filters else None
        return self.repository.count(filters=filters_dict)