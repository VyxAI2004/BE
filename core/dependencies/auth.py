from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
from datetime import datetime, timezone
from jwt import decode
from sqlalchemy.orm import Session

from env import env
from services.sale_smart_ai_app.user import UserService
from schemas.auth import TokenData
from core.dependencies.services import get_user_service
from core.dependencies.db import get_db

api_key_header = APIKeyHeader(name="Authorization")

JWT_SECRET_KEY = env.JWT_SECRET_KEY
JWT_ALGORITHM = env.JWT_ALGORITHM


def verify_token(
    authorization: str = Depends(api_key_header),
    user_service: UserService = Depends(get_user_service),
    db: Session = Depends(get_db),
) -> TokenData:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")

    token = authorization[len("Bearer ") :]

    try:
        data = decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    # Verify token type
    if "type" not in data or data["type"] != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    try:
        token_data = TokenData(
            user_id=data["sub"],
            email=data["email"],
            roles=data["roles"],
            exp=datetime.fromtimestamp(data["exp"], timezone.utc)
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token format")

    user = user_service.get_by_email(email=token_data.email)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if token_data.exp < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Token has expired")

    db.info["current_user_id"] = user.id

    return token_data