from typing import List, Optional, Type, TypedDict

from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session

from models.role import Role, Permission, UserRole, RolePermission
from schemas.role import RoleCreate, RoleUpdate

from .base import BaseRepository


class RoleFilters(TypedDict, total=False):
    """Role filters for comprehensive search"""
    q: Optional[str]
    name: Optional[str]
    slug: Optional[str]
    category: Optional[str]
    is_active: Optional[bool]
    is_system_role: Optional[bool]


class RoleRepository(BaseRepository[Role, RoleCreate, RoleUpdate]):
    def __init__(self, model: Type[Role], db: Session):
        super().__init__(model, db)

    def search(
        self,
        *,
        filters: Optional[RoleFilters] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Role]:
        """Search roles with filters"""
        db_query = self.db.query(Role)

        if filters:
            filter_conditions = []
            
            if filters.get("q"):
                query = filters.get("q")
                filter_conditions.append(
                    or_(
                        Role.name.ilike(f"%{query}%"),
                        Role.description.ilike(f"%{query}%"),
                        Role.slug.ilike(f"%{query}%"),
                    )
                )
            
            if filters.get("name"):
                filter_conditions.append(Role.name.ilike(f"%{filters.get('name')}%"))
            
            if filters.get("slug"):
                filter_conditions.append(Role.slug == filters.get("slug"))
            
            if filters.get("category"):
                # Search in permissions' category
                filter_conditions.append(
                    Role.id.in_(
                        self.db.query(RolePermission.role_id)
                        .join(Permission)
                        .filter(Permission.category == filters.get("category"))
                    )
                )
            
            if filters.get("is_active") is not None:
                filter_conditions.append(Role.is_active == filters.get("is_active"))
            
            if filters.get("is_system_role") is not None:
                filter_conditions.append(Role.is_system_role == filters.get("is_system_role"))
            
            if filter_conditions:
                db_query = db_query.filter(and_(*filter_conditions))

        return db_query.order_by(Role.priority.desc(), Role.created_at.desc()).offset(skip).limit(limit).all()

    def get_by_slug(self, *, slug: str) -> Optional[Role]:
        """Get role by slug"""
        return self.db.query(Role).filter(Role.slug == slug).first()

    def get_by_name(self, *, name: str) -> Optional[Role]:
        """Get role by name"""
        return self.db.query(Role).filter(Role.name == name).first()

    def get_with_permissions(self, role_id: str) -> Optional[Role]:
        """Get role with all permissions loaded"""
        return (
            self.db.query(Role)
            .filter(Role.id == role_id)
            .first()
        )

    def count_by_filters(self, *, filters: Optional[RoleFilters] = None) -> int:
        """Count roles with filters"""
        db_query = self.db.query(func.count(Role.id))

        if filters:
            filter_conditions = []
            
            if filters.get("q"):
                query = filters.get("q")
                filter_conditions.append(
                    or_(
                        Role.name.ilike(f"%{query}%"),
                        Role.description.ilike(f"%{query}%"),
                        Role.slug.ilike(f"%{query}%"),
                    )
                )
            
            if filters.get("name"):
                filter_conditions.append(Role.name.ilike(f"%{filters.get('name')}%"))
            
            if filters.get("slug"):
                filter_conditions.append(Role.slug == filters.get("slug"))
            
            if filters.get("is_active") is not None:
                filter_conditions.append(Role.is_active == filters.get("is_active"))
            
            if filters.get("is_system_role") is not None:
                filter_conditions.append(Role.is_system_role == filters.get("is_system_role"))
            
            if filter_conditions:
                db_query = db_query.filter(and_(*filter_conditions))

        return db_query.scalar() or 0

    def assign_permissions(self, role_id: str, permission_ids: List[str]) -> Role:
        """Assign permissions to a role"""
        # Xóa các permissions cũ
        self.db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
        
        # Thêm permissions mới
        for perm_id in permission_ids:
            role_perm = RolePermission(role_id=role_id, permission_id=perm_id)
            self.db.add(role_perm)
        
        self.db.commit()
        return self.get(role_id)

    def remove_permissions(self, role_id: str, permission_ids: List[str]) -> Role:
        """Remove specific permissions from a role"""
        self.db.query(RolePermission).filter(
            RolePermission.role_id == role_id,
            RolePermission.permission_id.in_(permission_ids)
        ).delete()
        
        self.db.commit()
        return self.get(role_id)

    def get_permission_ids_for_role(self, role_id: str) -> List[str]:
        """Get all permission IDs for a role"""
        return [
            perm_id for perm_id, in self.db.query(RolePermission.permission_id).filter(
                RolePermission.role_id == role_id
            ).all()
        ]

    def activate_role(self, role_id: str) -> Optional[Role]:
        """Activate a role"""
        role = self.get(role_id)
        if role and not role.is_system_role:
            role.is_active = True
            self.db.commit()
            self.db.refresh(role)
        return role

    def deactivate_role(self, role_id: str) -> Optional[Role]:
        """Deactivate a role (system roles cannot be deactivated)"""
        role = self.get(role_id)
        if role and not role.is_system_role:
            role.is_active = False
            self.db.commit()
            self.db.refresh(role)
        return role

    def check_user_has_role(self, *, user_id: str, role_id: str) -> bool:
        """Check if user already has a specific role"""
        existing = (
            self.db.query(UserRole)
            .filter_by(user_id=user_id, role_id=role_id)
            .first()
        )
        return existing is not None

    def get_admin_roles(self, *, slugs: List[str] = None) -> List[Role]:
        """Get admin roles by slugs. Default to ['admin', 'super_admin']"""
        if slugs is None:
            slugs = ["admin", "super_admin"]
        return self.db.query(Role).filter(Role.slug.in_(slugs)).all()
