from functools import wraps
import inspect
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, Depends, status
from sqlalchemy.orm import Session

from core.dependencies.auth import verify_token
from core.dependencies.db import get_db
from schemas.auth import TokenData
from shared.enums import RoleEnum, GlobalPermissionEnum, ProjectPermissionEnum
from services.core.permission import PermissionService


def check_global_permissions(*required_permissions: GlobalPermissionEnum):

    def decorator(func):
        @wraps(func)
        async def wrapper(
            *args, 
            token: TokenData = Depends(verify_token),
            db: Session = Depends(get_db),
            **kwargs
        ):
            # Optimize: Check signature once
            sig = inspect.signature(func)
            needs_token = 'token' in sig.parameters
            needs_db = 'db' in sig.parameters

            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )
            
            # SUPER_ADMIN có tất cả permissions - bypass check
            if RoleEnum.SUPER_ADMIN.value in token.roles:
                if needs_token: kwargs['token'] = token
                if needs_db: kwargs['db'] = db
                return await func(*args, **kwargs)
            
            # Check permissions từ database thông qua PermissionService
            # Ensure db is a Session instance - if not, resolve it directly
            if not hasattr(db, 'execute'):
                # If db doesn't have execute method, it's not a Session - get it directly
                db_gen = get_db()
                db = next(db_gen)
            permission_service = PermissionService(db)
            
            # Optimize: Fetch all permissions once (1 query)
            user_perms = permission_service.get_user_permissions(token.user_id)
            
            # Check intersection
            has_permission = any(req.value in user_perms for req in required_permissions)
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permissions: {', '.join(p.value for p in required_permissions)}"
                )
            
            if needs_token: kwargs['token'] = token
            if needs_db: kwargs['db'] = db
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def check_project_permissions(project_id_param: str = "project_id", *required_permissions: ProjectPermissionEnum):

    def decorator(func):
        @wraps(func)
        async def wrapper(
            *args,
            token: TokenData = Depends(verify_token),
            db: Session = Depends(get_db),
            **kwargs
        ):
            # Optimize: Check signature once
            sig = inspect.signature(func)
            needs_token = 'token' in sig.parameters
            needs_db = 'db' in sig.parameters

            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )
            
            # Lấy project_id từ kwargs
            project_id = kwargs.get(project_id_param)
            if not project_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing {project_id_param} parameter"
                )
            
            # Chuyển đổi project_id sang UUID nếu là string
            if isinstance(project_id, str):
                try:
                    project_id = UUID(project_id)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid {project_id_param} format"
                    )
            
            # SUPER_ADMIN có tất cả permissions - bypass check
            if RoleEnum.SUPER_ADMIN.value in token.roles:
                if needs_token: kwargs['token'] = token
                if needs_db: kwargs['db'] = db
                return await func(*args, **kwargs)
            
            # Check permissions từ database thông qua PermissionService
            # Ensure db is a Session instance - if not, resolve it directly
            if not hasattr(db, 'execute'):
                # If db doesn't have execute method, it's not a Session - get it directly
                db_gen = get_db()
                db = next(db_gen)
            permission_service = PermissionService(db)
            
            # Optimize: Check implicit permission (Owner/Assignee) OR explicit permissions
            has_permission = False
            
            # 1. Check implicit (Owner/Assignee) - 1 Query
            if permission_service.is_project_owner_or_assignee(token.user_id, project_id):
                has_permission = True
            else:
                # 2. Check explicit permissions - 1 Query
                user_perms = permission_service.get_user_permissions(token.user_id, project_id)
                if any(req.value in user_perms for req in required_permissions):
                    has_permission = True
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required project permissions: {', '.join(p.value for p in required_permissions)}"
                )
            
            if needs_token: kwargs['token'] = token
            if needs_db: kwargs['db'] = db

            return await func(*args, **kwargs)
        return wrapper
    return decorator