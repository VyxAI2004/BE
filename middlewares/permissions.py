from functools import wraps
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, Depends, status
from sqlalchemy.orm import Session

from core.dependencies.auth import verify_token
from core.dependencies.db import get_db
from schemas.auth import TokenData
from shared.enums import RoleEnum, GlobalPermissionEnum, ProjectPermissionEnum
from services.sale_smart_ai_app.permission import PermissionService


def check_global_permissions(*required_permissions: GlobalPermissionEnum):
    """
    Middleware để kiểm tra global permissions của user từ database.
    
    Usage:
        @router.get("/users")
        @check_global_permissions(GlobalPermissionEnum.VIEW_USERS)
        async def get_users():
            ...
    
    Logic:
    - SUPER_ADMIN: Bypass tất cả permission checks (có tất cả quyền)
    - Các role khác: Phải có ít nhất một trong các permissions được yêu cầu trong database
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(
            *args, 
            token: TokenData = Depends(verify_token),
            db: Session = Depends(get_db),
            **kwargs
        ):
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )
            
            # SUPER_ADMIN có tất cả permissions - bypass check
            if RoleEnum.SUPER_ADMIN.value in token.roles:
                return await func(*args, token=token, db=db, **kwargs)
            
            # Check permissions từ database thông qua PermissionService
            permission_service = PermissionService(db)
            
            # Kiểm tra xem user có ít nhất một trong các permissions yêu cầu
            has_permission = False
            for required_perm in required_permissions:
                if permission_service.has_permission(
                    user_id=token.user_id,
                    permission_name=required_perm.value
                ):
                    has_permission = True
                    break
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permissions: {', '.join(p.value for p in required_permissions)}"
                )
            
            return await func(*args, token=token, db=db, **kwargs)
        return wrapper
    return decorator


def check_project_permissions(project_id_param: str = "project_id", *required_permissions: ProjectPermissionEnum):
    """
    Middleware để kiểm tra project-specific permissions của user từ database.
    
    Usage:
        @router.get("/projects/{project_id}/tasks")
        @check_project_permissions("project_id", ProjectPermissionEnum.VIEW_TASKS)
        async def get_project_tasks(project_id: UUID):
            ...
    
    Logic:
    - SUPER_ADMIN: Bypass tất cả permission checks (có tất cả quyền)
    - Project Owner/Creator: Có tất cả permissions trong project của mình
    - Các role khác: Phải có permissions trong project-specific roles từ database
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(
            *args,
            token: TokenData = Depends(verify_token),
            db: Session = Depends(get_db),
            **kwargs
        ):
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
                return await func(*args, token=token, db=db, **kwargs)
            
            # Check permissions từ database thông qua PermissionService
            permission_service = PermissionService(db)
            
            # Kiểm tra xem user có ít nhất một trong các permissions yêu cầu trong project này
            has_permission = False
            for required_perm in required_permissions:
                if permission_service.has_permission(
                    user_id=token.user_id,
                    permission_name=required_perm.value,
                    project_id=project_id
                ):
                    has_permission = True
                    break
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required project permissions: {', '.join(p.value for p in required_permissions)}"
                )
            
            return await func(*args, token=token, db=db, **kwargs)
        return wrapper
    return decorator