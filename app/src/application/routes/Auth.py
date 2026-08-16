import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Auth import ApplicationAuthService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Exceptions import (
    ConflictError,
    InvalidCredentialsError,
    InternalError,
    NotFoundError,
    TokenInvalidError,
    NotAuthenticatedError,
)
from src.core.Security import decode_token
from src.config.Utility import _client_ip
from src.models.User import User
from src.schemas.Auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    SignupRequest,
    SignupResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Application Auth"])


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Application user login."""
    ip = _client_ip(request)
    logger.info("auth.login.request email=%s ip=%s", body.email, ip)

    result = await ApplicationAuthService(db).login(body.email, body.password)
    if not result:
        logger.warning("auth.login.failed email=%s ip=%s reason=invalid_credentials", body.email, ip)
        raise InvalidCredentialsError()

    user_id = result.get("user", {}).get("id")
    logger.info("auth.login.success user_id=%s email=%s ip=%s", user_id, body.email, ip)
    return result


@router.post("/signup", response_model=SignupResponse, status_code=201)
async def signup(request: Request, body: SignupRequest, db: AsyncSession = Depends(get_db)):
    """Complete signup: create workspace, persona, and admin user."""
    ip = _client_ip(request)
    logger.info("auth.signup.request workspace=%r email=%s ip=%s", body.workspace_name, body.admin_email, ip)

    try:
        result = await ApplicationAuthService(db).signup(
            workspace_data={"name": body.workspace_name, "description": body.workspace_description},
            persona_data={
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
            },
            admin_data={
                "email": body.admin_email,
                "password": body.admin_password,
                "first_name": body.admin_first_name,
                "last_name": body.admin_last_name,
                "phone": body.admin_phone,
            },
            referral_email=body.referral_email,
        )
    except ValueError as e:
        logger.warning("auth.signup.conflict workspace=%r email=%s ip=%s reason=%s", body.workspace_name, body.admin_email, ip, str(e))
        raise ConflictError(str(e))
    except Exception:
        logger.error("auth.signup.error workspace=%r email=%s ip=%s", body.workspace_name, body.admin_email, ip, exc_info=True)
        raise InternalError("An unexpected error occurred. Please try again later.")

    workspace_id = result["workspace"].get("id")
    user_id = result["user"].get("id")
    persona_id = result["persona"].get("id")
    logger.info("auth.signup.success workspace_id=%s persona_id=%s user_id=%s email=%s ip=%s", workspace_id, persona_id, user_id, body.admin_email, ip)

    return SignupResponse(
        workspace=result["workspace"],
        persona=result["persona"],
        user=result["user"],
        message="Signup successful. You can now login with your credentials.",
    )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(request: Request, body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Refresh access token using a valid refresh token."""
    ip = _client_ip(request)
    logger.info("auth.token.refresh.request ip=%s", ip)

    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh" or payload.get("user_type") != 1:
        logger.warning("auth.token.refresh.invalid_type ip=%s type=%s", ip, payload.get("type"))
        raise TokenInvalidError("Invalid refresh token")

    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError, KeyError):
        logger.warning("auth.token.refresh.invalid_sub ip=%s", ip)
        raise TokenInvalidError("Invalid refresh token")

    stmt = select(User.is_active).where(User.id == user_id, User.user_type == 1)
    row = (await db.execute(stmt)).one_or_none()
    if not row or not row.is_active:
        logger.warning("auth.token.refresh.user_not_found user_id=%s ip=%s", user_id, ip)
        raise NotAuthenticatedError("User not found or inactive")

    token_data = {"sub": payload["sub"], "email": payload["email"], "user_type": 1}
    access_token = ApplicationAuthService(db).create_access_token(token_data)

    logger.info("auth.token.refresh.success user_id=%s ip=%s", user_id, ip)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=BaseResponse)
async def get_current_user(
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
):
    """Return the currently authenticated user — resolved from JWT, no extra DB call."""
    logger.info("auth.me.request user_id=%s", current_user.get("id"))
    return {"success": True, "message": "User retrieved successfully", "data": {"user": current_user}}


@router.post("/change-password", response_model=BaseResponse)
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Change password for the currently authenticated user."""
    user_id = current_user["id"]
    ip = _client_ip(request)
    logger.info("auth.change_password.request user_id=%s ip=%s", user_id, ip)

    await ApplicationAuthService(db).change_password(user_id, body.old_password, body.new_password)

    logger.info("auth.change_password.success user_id=%s ip=%s", user_id, ip)
    return {"success": True, "message": "Password changed successfully"}
