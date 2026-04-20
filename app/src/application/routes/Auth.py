from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Auth import ApplicationAuthService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db, get_system_db
from src.core.Security import decode_token, get_password_hash, verify_password, verify_token_type
from src.repositories.PersonaRepository import PersonaRepository
from src.repositories.UserRepository import UserRepository
from src.repositories.WorkspaceRepository import WorkspaceRepository
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


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Application user login."""
    auth_service = ApplicationAuthService(db)
    result = await auth_service.login(request.email, request.password)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return result


# ---------------------------------------------------------------------------
# GET /auth/validate-referral
# ---------------------------------------------------------------------------

@router.get("/validate-referral", response_model=BaseResponse)
async def validate_referral_code(
    code: str = Query(..., min_length=4, max_length=4, description="4-digit referral code"),
    system_db: AsyncSession = Depends(get_system_db),
):
    """
    Validate referral code (4-digit system user ID).
    Returns user details if valid.
    """
    try:
        if not code.isdigit() or len(code) != 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Referral code must be a 4-digit number",
            )

        # Use a temporary service instance solely for the system-user lookup.
        # The primary db session is not needed here so we pass system_db for both.
        auth_service = ApplicationAuthService(db=system_db, system_db=system_db)
        user = await auth_service.get_system_user_by_id(code)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid referral code. User not found.",
            )

        if not user.get("is_active", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Referral code is inactive. Please contact support.",
            )

        return {
            "success": True,
            "message": "Referral code is valid",
            "data": {
                "user_id": user.get("id"),
                "email": user.get("email"),
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating referral code: {str(e)}",
        )


# ---------------------------------------------------------------------------
# POST /auth/signup
# ---------------------------------------------------------------------------

@router.post("/signup", response_model=SignupResponse)
async def signup(
    request: SignupRequest,
    db: AsyncSession = Depends(get_db),
    system_db: AsyncSession = Depends(get_system_db),
):
    """
    Complete signup process for a new workspace.
    Creates workspace, persona, and admin user.
    Validates referral code and tracks who onboarded the workspace.
    """
    auth_service = ApplicationAuthService(db=db, system_db=system_db)

    try:
        workspace_data = {
            "name": request.workspace_name,
            "description": request.workspace_description,
        }

        persona_data = request.persona.model_dump()
        admin_data = request.admin_user.model_dump()

        billing_data = {
            "billing_name": request.billing_name,
            "billing_email": request.billing_email,
            "billing_phone": request.billing_phone,
            "billing_address": request.billing_address,
            "billing_city": request.billing_city,
            "billing_state": request.billing_state,
            "billing_postal_code": request.billing_postal_code,
            "billing_country": request.billing_country,
        }

        result = await auth_service.signup(
            request.referral_code,
            workspace_data,
            persona_data,
            admin_data,
            billing_data,
        )

        return SignupResponse(
            workspace=result["workspace"],
            persona=result["persona"],
            admin_user=result["admin_user"],
            message="Signup successful. You can now login with your credentials.",
        )

    except Exception as e:
        error_message = str(e)

        if "already exists" in error_message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_message,
            )
        elif "not found" in error_message:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"System configuration error: {error_message}",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message,
            )


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------

@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token (JWT-only, no DB lookup required)."""
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
        "user_type": "application",
    }

    access_token = auth_service.create_access_token(token_data)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=BaseResponse)
async def get_current_user(
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get current application user with full details."""
    user_repo = UserRepository(db)
    workspace_repo = WorkspaceRepository(db)
    persona_repo = PersonaRepository(db)

    user_id = current_user.get("id")
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    workspace = None
    if user.get("workspace_id"):
        workspace = await workspace_repo.get_by_id(user["workspace_id"])

    venue = None
    if user.get("persona_id"):
        venue = await persona_repo.get_by_id(user["persona_id"])

    return {
        "success": True,
        "message": "User retrieved successfully",
        "data": {
            "user": {
                "id": user.get("id"),
                "email": user.get("email"),
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "phone": user.get("phone"),
                "role": current_user.get("role", {}).get("name", "operator"),
                "venue_ids": [user.get("persona_id")] if user.get("persona_id") else [],
                "is_active": user.get("is_active", True),
                "created_at": user.get("created_at"),
                "updated_at": user.get("updated_at"),
            },
            "workspace": workspace,
            "venue": venue,
        },
    }


@router.get("/me/data", response_model=BaseResponse)
async def get_current_user_data(
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get current application user data (alias for /me for compatibility)."""
    return await get_current_user(current_user, db)


# ---------------------------------------------------------------------------
# POST /auth/change-password
# ---------------------------------------------------------------------------

@router.post("/change-password", response_model=BaseResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Change password for the currently authenticated application user."""
    user_repo = UserRepository(db)

    user_id = current_user.get("id")
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not verify_password(request.old_password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    if verify_password(request.new_password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password",
        )

    new_hash = get_password_hash(request.new_password)
    success = await user_repo.update(user_id, {"password_hash": new_hash})

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password",
        )

    return {
        "success": True,
        "message": "Password changed successfully",
    }
