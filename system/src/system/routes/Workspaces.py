from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.schemas.Workspace import WorkspaceBillingUpdate, WorkspaceCreate, WorkspaceUpdate
from src.system.middleware.RoleCheck import SystemPermissionCheck
from src.system.services.Workspace import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["System Workspaces"])


@router.get(
    "",
    dependencies=[Depends(SystemPermissionCheck.require("workspaces:list"))],
)
async def get_workspaces(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = Query(None),
    plan: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated workspaces."""
    service = WorkspaceService(db)
    items, total, total_pages = await service.get_paginated_workspaces(
        is_active=is_active,
        plan=plan,
        page=page,
        page_size=page_size,
    )
    return {
        "success": True,
        "message": "Workspaces retrieved successfully",
        "data": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
    }


@router.post(
    "",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("workspaces:create"))],
)
async def create_workspace(workspace: WorkspaceCreate, db: AsyncSession = Depends(get_db)):
    """Create a new workspace."""
    service = WorkspaceService(db)
    result = await service.create_workspace(workspace.model_dump())
    return {
        "success": True,
        "message": "Workspace created successfully",
        "data": {"id": result.get("id")},
    }


@router.get(
    "/{workspace_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("workspaces:read"))],
)
async def get_workspace(workspace_id: int, db: AsyncSession = Depends(get_db)):
    """Get workspace details with billing and personas."""
    service = WorkspaceService(db)
    workspace = await service.get_workspace_details(workspace_id)
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return {"success": True, "message": "Workspace retrieved successfully", "data": workspace}


@router.put(
    "/{workspace_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("workspaces:update"))],
)
async def update_workspace(
    workspace_id: int, workspace: WorkspaceUpdate, db: AsyncSession = Depends(get_db)
):
    """Update workspace."""
    service = WorkspaceService(db)
    success = await service.update_workspace(workspace_id, workspace.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return {"success": True, "message": "Workspace updated successfully"}


@router.delete(
    "/{workspace_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("workspaces:delete"))],
)
async def delete_workspace(workspace_id: int, db: AsyncSession = Depends(get_db)):
    """Soft delete workspace."""
    service = WorkspaceService(db)
    success = await service.soft_delete(workspace_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return {"success": True, "message": "Workspace deleted successfully"}


@router.post(
    "/{workspace_id}/restore",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("workspaces:manage"))],
)
async def restore_workspace(workspace_id: int, db: AsyncSession = Depends(get_db)):
    """Restore a soft-deleted workspace."""
    service = WorkspaceService(db)
    workspace = await service.get_by_id(workspace_id, include_deleted=True)
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    if workspace.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace is not deleted",
        )
    success = await service.restore(workspace_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return {"success": True, "message": "Workspace restored successfully"}


@router.get(
    "/{workspace_id}/billing",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("billing:read"))],
)
async def get_workspace_billing(workspace_id: int, db: AsyncSession = Depends(get_db)):
    """Get workspace billing information."""
    service = WorkspaceService(db)
    billing = await service.get_billing(workspace_id)
    if not billing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing record not found",
        )
    return {"success": True, "message": "Billing retrieved successfully", "data": billing}


@router.put(
    "/{workspace_id}/billing",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("billing:update"))],
)
async def update_workspace_billing(
    workspace_id: int,
    billing: WorkspaceBillingUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update workspace billing information."""
    service = WorkspaceService(db)
    success = await service.update_billing(workspace_id, billing.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing record not found",
        )
    return {"success": True, "message": "Billing updated successfully"}


@router.post(
    "/{workspace_id}/personas/{persona_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("workspaces:manage"))],
)
async def add_persona_to_workspace(
    workspace_id: int, persona_id: int, db: AsyncSession = Depends(get_db)
):
    """Add a persona to a workspace."""
    service = WorkspaceService(db)
    await service.add_persona(workspace_id, persona_id)
    return {"success": True, "message": "Persona added to workspace successfully"}


@router.delete(
    "/{workspace_id}/personas/{persona_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("workspaces:manage"))],
)
async def remove_persona_from_workspace(
    workspace_id: int, persona_id: int, db: AsyncSession = Depends(get_db)
):
    """Remove a persona from a workspace."""
    service = WorkspaceService(db)
    await service.remove_persona(workspace_id, persona_id)
    return {"success": True, "message": "Persona removed from workspace successfully"}
