from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.repositories.RoleRepository import RoleRepository

router = APIRouter(prefix="/roles", tags=["Application Roles"])


@router.get("", response_model=BaseResponse)
async def get_application_roles(
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all application roles (role_type=1).
    Available to any authenticated application user so the create-user
    form can populate the role dropdown.
    """
    repository = RoleRepository(db)
    roles = await repository.get_by_type(1)

    return {
        "success": True,
        "message": "Application roles retrieved successfully",
        "data": roles,
    }
