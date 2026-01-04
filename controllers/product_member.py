"""
Controller cho Product Member Management & Invitations
"""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.dependencies.db import get_db
from core.dependencies.auth import verify_token, TokenData
from services.core.product_user import ProductUserService
from services.core.user import UserService
from schemas.product_user import (
    ProductUserResponse,
    ProductInviteRequest,
    ProductMemberResponse,
    ProductUserUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["Product Members"])


def get_product_user_service(db: Session = Depends(get_db)) -> ProductUserService:
    """Dependency để get ProductUserService"""
    return ProductUserService(db)


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Dependency để get UserService"""
    return UserService(db)


@router.post("/{product_id}/invite", response_model=ProductMemberResponse, status_code=status.HTTP_201_CREATED)
def invite_to_product(
    product_id: UUID,
    payload: ProductInviteRequest,
    token: TokenData = Depends(verify_token),
    product_user_service: ProductUserService = Depends(get_product_user_service),
    user_service: UserService = Depends(get_user_service),
):
    """Mời user vào product - chỉ product owner/admin được"""
    try:
        # TODO: Check authorization - user must be product owner/admin
        # For now, assume authorized
        
        # Find target user by email
        target_user = user_service.get_by_email(payload.user_email)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with email {payload.user_email} not found"
            )
        
        # Check if already invited
        existing = product_user_service.repository.get_by_product_and_user(
            product_id, target_user.id
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this product"
            )
        
        # Create invitation
        product_user = product_user_service.invite_to_product(
            product_id=product_id,
            user=target_user,
            role_id=payload.role_id,
            permissions=payload.permissions,
            invited_by_id=token.user_id,
        )
        
        # Build response
        return ProductMemberResponse(
            id=product_user.id,
            product_id=product_user.product_id,
            user_id=product_user.user_id,
            user_name=target_user.full_name,
            user_email=target_user.email,
            user_avatar=target_user.avatar_url,
            role_id=product_user.role_id,
            role_name=product_user.role.name if product_user.role else None,
            is_active=product_user.is_active,
            invited_at=product_user.invited_at,
            invited_by_name=token.user_id,  # Can fetch from user service if needed
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inviting to product: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error inviting user: {str(e)}"
        )


@router.get("/{product_id}/members", response_model=List[ProductMemberResponse])
def get_product_members(
    product_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    token: TokenData = Depends(verify_token),
    product_user_service: ProductUserService = Depends(get_product_user_service),
    user_service: UserService = Depends(get_user_service),
):
    """Lấy danh sách thành viên của product"""
    try:
        members = product_user_service.get_product_members(
            product_id=product_id,
            skip=skip,
            limit=limit,
            is_active_only=True
        )
        
        # Build response with user details
        result = []
        for member in members:
            user = member.user
            result.append(
                ProductMemberResponse(
                    id=member.id,
                    product_id=member.product_id,
                    user_id=member.user_id,
                    user_name=user.full_name if user else None,
                    user_email=user.email if user else None,
                    user_avatar=user.avatar_url if user else None,
                    role_id=member.role_id,
                    role_name=member.role.name if member.role else None,
                    is_active=member.is_active,
                    invited_at=member.invited_at,
                    invited_by_name=member.inviter.full_name if member.inviter else None,
                )
            )
        
        return result
    except Exception as e:
        logger.error(f"Error getting product members: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching product members"
        )


@router.patch("/{product_id}/members/{user_id}/role", response_model=ProductMemberResponse)
def update_product_member_role(
    product_id: UUID,
    user_id: UUID,
    payload: ProductUserUpdate,
    token: TokenData = Depends(verify_token),
    product_user_service: ProductUserService = Depends(get_product_user_service),
):
    """Cập nhật role của thành viên trong product"""
    try:
        # TODO: Check authorization
        
        member = product_user_service.update_member_role(
            product_id=product_id,
            user_id=user_id,
            role_id=payload.role_id,
            permissions=payload.permissions,
        )
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product member not found"
            )
        
        user = member.user
        return ProductMemberResponse(
            id=member.id,
            product_id=member.product_id,
            user_id=member.user_id,
            user_name=user.full_name if user else None,
            user_email=user.email if user else None,
            user_avatar=user.avatar_url if user else None,
            role_id=member.role_id,
            role_name=member.role.name if member.role else None,
            is_active=member.is_active,
            invited_at=member.invited_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating product member role: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error updating member role"
        )


@router.delete("/{product_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_product(
    product_id: UUID,
    user_id: UUID,
    token: TokenData = Depends(verify_token),
    product_user_service: ProductUserService = Depends(get_product_user_service),
):
    """Xoá user khỏi product"""
    try:
        # TODO: Check authorization
        
        success = product_user_service.remove_from_product(
            product_id=product_id,
            user_id=user_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product member not found"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing from product: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error removing member"
        )
