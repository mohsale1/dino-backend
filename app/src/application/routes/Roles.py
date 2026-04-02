
from fastapi import APIRouter, Depends
from src.base.BaseSchema import BaseResponse
from src.core.Dependencies import get_current_application_user
from src.repositories.RoleRepository import RoleRepository
from typing import Dict, Any

router = APIRouter(prefix="/roles", tags=["Application Roles"])


@router.get("", response_model=BaseResponse)
async def get_application_roles(
    current_user: Dict[str, Any] = Depends(get_current_application_user),
):
    """
    Get all application roles (role_type=1).
    Available to any authenticated application user so the create-user
    form can populate the role dropdown.
    """
    repository = RoleRepository()
    roles = repository.get_by_type(1)

    return {
        "success": True,
        "message": "Application roles retrieved successfully",
        "data": roles,
    }
