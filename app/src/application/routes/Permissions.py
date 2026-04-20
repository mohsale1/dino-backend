from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Permission import ApplicationPermissionService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db

router = APIRouter(prefix="/permissions", tags=["Application Permissions"])


@router.get("", response_model=BaseResponse)
async def get_my_permissions(
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """
    Get permissions for the currently authenticated application user.
    Returns the full permission objects assigned to the user's role.
    """
    service = ApplicationPermissionService(db)
    permissions = await service.get_permissions_for_user(current_user)
    role = service.get_role_info(current_user)

    return {
        "success": True,
        "message": "Permissions retrieved successfully",
        "data": {
            "role": role,
            "permissions": permissions,
        },
    }
