from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Security import decode_token, verify_token_type
from src.schemas.Auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
)
from src.system.middleware.RoleCheck import SystemPermissionCheck
from src.system.services.Auth import SystemAuthService

router = APIRouter(prefix="/auth", tags=["System Auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate a system user and return tokens."""
    service = SystemAuthService(db)
    result = await service.login(body.email, body.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return result


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Refresh access token using a valid refresh token."""
    if not verify_token_type(request.refresh_token, "refresh"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    payload = decode_token(request.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    service = SystemAuthService(db)
    token_data = {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "user_type": 0,
    }
    access_token = service.create_access_token(token_data)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=BaseResponse)
async def get_current_user(
    user: Dict[str, Any] = Depends(SystemPermissionCheck.require_authenticated),
):
    """Return the currently authenticated system user."""
    return {"success": True, "message": "User retrieved successfully", "data": user}


@router.post("/change-password", response_model=BaseResponse)
async def change_password(
    request: ChangePasswordRequest,
    user: Dict[str, Any] = Depends(SystemPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Change the current user's password."""
    service = SystemAuthService(db)
    success = await service.change_password(
        user["id"], request.old_password, request.new_password
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to change password",
        )
    return {"success": True, "message": "Password changed successfully", "data": None}

