from fastapi import APIRouter, Depends
from src.base.BaseSchema import BaseResponse
from src.core.Dependencies import get_current_application_user
from src.application.services.Permission import ApplicationPermissionService
from typing import Dict, Any

router = APIRouter(prefix="/permissions", tags=["Application Permissions"])


@router.get("", response_model=BaseResponse)
async def get_my_permissions(current_user: Dict[str, Any] = Depends(get_current_application_user)):
    """
    Get permissions for the currently authenticated application user.
    Returns the full permission objects assigned to the user's role.
    """
    service = ApplicationPermissionService()
    permissions = service.get_permissions_for_user(current_user)
    role = service.get_role_info(current_user)

    return {
        "success": True,
        "message": "Permissions retrieved successfully",
        "data": {
            "role": role,
            "permissions": permissions
        }
    }