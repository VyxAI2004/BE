import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from models.project_user import ProjectUser
from models.user import User
from repositories.project_user import ProjectUserRepository
from repositories.user import UserRepository
from schemas.project_user import ProjectUserCreate, ProjectUserUpdate, ProjectMemberAssignRequest
from .base import BaseService

class ProjectUserService(BaseService[ProjectUser, ProjectUserCreate, ProjectUserUpdate, ProjectUserRepository]):
    def __init__(self, db: Session):
        super().__init__(db, ProjectUser, ProjectUserRepository)
        self.user_repository = UserRepository(model=User, db=db)

    def get_project_members(self, project_id: uuid.UUID, is_active: bool = True) -> List[ProjectUser]:
        """Get all active members of a project"""
        return self.repository.get_project_members(project_id=project_id, is_active=is_active)

    def get_user_projects(self, user_id: uuid.UUID, is_active: bool = True) -> List[ProjectUser]:
        """Get all projects a user is member of"""
        return self.repository.get_user_projects(user_id=user_id, is_active=is_active)

    def is_project_member(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Check if user is a member of the project"""
        membership = self.repository.get_by_project_and_user(project_id, user_id)
        return membership is not None and (membership.is_active or False)

    def invite_user_by_email(
        self,
        project_id: uuid.UUID,
        email: str,
        role: str = "member",
        invited_by: uuid.UUID = None
    ) -> ProjectUser:
        """Invite a user to project by email"""
        # Find user by email using UserRepository
        user = self.user_repository.get_by_email(email=email)
        if not user:
            raise ValueError(f"User with email {email} not found")
        
        # Check if already a member
        existing_membership = self.repository.get_by_project_and_user(project_id, user.id)
        if existing_membership:
            if existing_membership.is_active:
                raise ValueError(f"User {email} is already a member of this project")
            # Reactivate
            existing_membership.is_active = True
            existing_membership.role = role
            existing_membership.status = "accepted"
            self.db.add(existing_membership)
            self.db.commit()
            self.db.refresh(existing_membership)
            return existing_membership
        
        # Create ProjectUser manually
        project_user = ProjectUser(
            project_id=project_id,
            user_id=user.id,
            role=role,
            status="accepted",
            invited_by=invited_by,
            is_active=True
        )
        self.db.add(project_user)
        self.db.commit()
        self.db.refresh(project_user)
        return project_user

    def update_member_role(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        new_role: str,
        requester_id: uuid.UUID = None
    ) -> ProjectUser:
        """Update member role in project"""
        updated_member = self.repository.update_member_role(project_id, user_id, new_role)
        if not updated_member:
            raise ValueError("User is not a member of this project")
        return updated_member

    def assign_users_to_project(
        self, 
        project_id: uuid.UUID, 
        request: ProjectMemberAssignRequest,
        invited_by: uuid.UUID
    ) -> List[ProjectUser]:
        """Assign multiple users to a project"""
        memberships_to_create = []
        
        for user_id in request.user_ids:
            # Check if user is already a member
            existing_membership = self.repository.get_by_project_and_user(project_id, user_id)
            
            if existing_membership:
                # If exists but inactive, reactivate
                if not existing_membership.is_active:
                    existing_membership.is_active = True
                    existing_membership.role_id = str(request.role_id) if request.role_id else None
                    existing_membership.permissions = request.permissions
                    existing_membership.invited_by = str(invited_by)
                    self.db.add(existing_membership)
                # If already active, skip
                continue
            else:
                # Create new membership
                membership_data = ProjectUserCreate(
                    project_id=project_id,
                    user_id=user_id,
                    role_id=request.role_id,
                    permissions=request.permissions,
                    invited_by=invited_by,
                    is_active=True
                )
                memberships_to_create.append(membership_data)
        
        # Bulk create new memberships
        new_memberships = []
        if memberships_to_create:
            new_memberships = self.repository.bulk_create_memberships(memberships_to_create)
        
        # Commit any updates to existing memberships
        self.db.commit()
        
        return new_memberships

    def remove_users_from_project(self, project_id: uuid.UUID, user_ids: List[uuid.UUID]) -> None:
        """Remove multiple users from a project"""
        for user_id in user_ids:
            self.repository.remove_membership(project_id, user_id)

    def deactivate_users_from_project(self, project_id: uuid.UUID, user_ids: List[uuid.UUID]) -> List[ProjectUser]:
        """Deactivate multiple users from a project (soft delete)"""
        deactivated_memberships = []
        for user_id in user_ids:
            membership = self.repository.deactivate_membership(project_id, user_id)
            if membership:
                deactivated_memberships.append(membership)
        return deactivated_memberships

    def update_user_role_in_project(
        self, 
        project_id: uuid.UUID, 
        user_id: uuid.UUID, 
        role_id: Optional[uuid.UUID] = None,
        permissions: Optional[dict] = None
    ) -> Optional[ProjectUser]:
        """Update a user's role/permissions in a project"""
        membership = self.repository.get_by_project_and_user(project_id, user_id)
        if not membership:
            return None
        
        update_data = ProjectUserUpdate()
        if role_id is not None:
            update_data.role_id = role_id
        if permissions is not None:
            update_data.permissions = permissions
            
        return self.update(db_obj=membership, payload=update_data)