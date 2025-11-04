from fastapi import Depends
from sqlalchemy.orm import Session

from core.dependencies.db import get_db

def get_user_service(db: Session = Depends(get_db)):
    from services.sale_smart_ai_app.user import UserService
    return UserService(db)

def get_activity_log_service(db: Session = Depends(get_db)):
    from services.sale_smart_ai_app.activity_log import ActivityLogService
    return ActivityLogService(db)

def get_auth_service(db: Session = Depends(get_db)):
    from services.sale_smart_ai_app.auth import AuthService
    return AuthService(db)

def get_project_service(db: Session = Depends(get_db)):
    from services.sale_smart_ai_app.project import ProjectService
    return ProjectService(db)

def get_project_user_service(db: Session = Depends(get_db)):
    from services.sale_smart_ai_app.project_user import ProjectUserService
    return ProjectUserService(db)

def get_ai_model_service(db: Session = Depends(get_db)):
    from services.sale_smart_ai_app.ai_model import AIModelService
    return AIModelService(db)

def get_role_service(db: Session = Depends(get_db)):
    from services.sale_smart_ai_app.role import RoleService
    return RoleService(db)

def get_permission_service(db: Session = Depends(get_db)):
    from services.sale_smart_ai_app.role import PermissionService
    return PermissionService(db)