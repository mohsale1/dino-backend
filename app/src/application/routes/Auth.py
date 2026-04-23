from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Auth import ApplicationAuthService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Security import decode_token, get_password_hash, verify_password, verify_token_type
from src.repositories.UserRepository import UserRepository
from src.repositories.WorkspaceRepository import WorkspaceRepository
from src.repositories.PersonaRepository import PersonaRepository
from src.schemas.Auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    SignupRequest,
    SignupResponse,
)

router = APIRouter(prefix="/auth", tags=["Application Auth"])

limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Application user login."""
    auth_service = ApplicationAuthService(db)
    try:
        result = await auth_service.login(body.email, body.password)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return result


@router.post("/signup", response_model=SignupResponse)
@limiter.limit("3/minute")
async def signup(request: Request, body: SignupRequest, db: AsyncSession = Depends(get_db)):
    """Complete signup: create workspace, persona, and admin user."""
    auth_service = ApplicationAuthService(db)

    workspace_data = {
        "name": body.workspace_name,
        "description": body.workspace_description,
    }
    persona_data = {
        "name": body.persona_name,
        "persona_type": body.persona_type,
        "order_type": body.order_type,
        "address": body.persona_address,
        "city": body.persona_city,
        "state": body.persona_state,
        "country": body.persona_country,
        "postal_code": body.persona_postal_code,
        "phone": body.persona_phone,
        "email": body.persona_email,
    }
    admin_data = {
        "email": body.admin_email,
        "password": body.admin_password,
        "first_name": body.admin_first_name,
        "last_name": body.admin_last_name,
        "phone": body.admin_phone,
    }

    try:
        result = await auth_service.signup(
            workspace_data=workspace_data,
            persona_data=persona_data,
            admin_data=admin_data,
            referred_by=body.owner_referred_by,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return SignupResponse(
        workspace=result["workspace"],
        persona=result["persona"],
        user=result["user"],
        message="Signup successful. You can now login with your credentials.",
    )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Refresh access token."""
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
    auth_service = ApplicationAuthService(db)
    token_data = {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "user_type": 1,
    }
    access_token = auth_service.create_access_token(token_data)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=BaseResponse)
async def get_current_user(
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get current application user."""
    user_repo = UserRepository(db)
    workspace_repo = WorkspaceRepository(db)

    user_id = current_user.get("id")
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    workspace = None
    if user.get("workspace_id"):
        workspace = await workspace_repo.get_by_id(user["workspace_id"])

    user.pop("password_hash", None)
    return {
        "success": True,
        "message": "User retrieved successfully",
        "data": {"user": user, "workspace": workspace},
    }


@router.post("/change-password", response_model=BaseResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Change password for the currently authenticated user."""
    user_repo = UserRepository(db)
    user_id = current_user.get("id")
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not verify_password(request.old_password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    new_hash = get_password_hash(request.new_password)
    success = await user_repo.update(user_id, {"password_hash": new_hash})

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password",
        )

    return {"success": True, "message": "Password changed successfully"}
