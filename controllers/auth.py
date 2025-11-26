from fastapi import APIRouter, Depends, HTTPException, Body
import jwt
from schemas.auth import TokenData, Token
from schemas.user import UserResponse
from schemas.clerk import ClerkTokenExchangeRequest, ClerkTokenExchangeResponse
from core.dependencies.services import get_auth_service
from core.dependencies.auth import JWT_ALGORITHM, verify_token
from core.dependencies.clerk import get_clerk_service
from core.dependencies.db import get_db
from services.sale_smart_ai_app.auth import JWT_SECRET_KEY, AuthService
from services.sale_smart_ai_app.clerk import ClerkService
from sqlalchemy.orm import Session

router = APIRouter(prefix="/auth", tags=["authentication"])



@router.post("/clerk-exchange", response_model=ClerkTokenExchangeResponse)
def clerk_token_exchange(
    request: ClerkTokenExchangeRequest,
    clerk_service: ClerkService = Depends(get_clerk_service),
):
    """Exchange Clerk token for backend tokens"""
    try:
        result = clerk_service.exchange_clerk_token(request.clerk_token)
        return ClerkTokenExchangeResponse(**result)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login", response_model=Token)
def login(
    email: str = Body(..., embed=True),
    password: str = Body(..., embed=True),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Log in a user and return a JWT token."""
    try:
        return auth_service.sign_in(email=email, password=password)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me", response_model=UserResponse)
def get_profile(
    user_from_token: TokenData = Depends(verify_token),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Get the profile of the authenticated user."""
    user = auth_service.get_by_email(email=user_from_token.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)

@router.post("/refresh-token", response_model=Token)
def refresh_token(
    refresh_token: str = Body(..., embed=True),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Refresh JWT token using refresh_token."""
    return auth_service.refresh_token(refresh_token)

@router.post("/logout")
def logout():
    """Logout user (FE chỉ cần xóa token ở local storage)"""
    return {"detail": "Logged out successfully"}