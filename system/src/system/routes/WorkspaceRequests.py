from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Dependencies import get_current_system_user
from src.schemas.WorkspaceRequest import WorkspaceRequestCreate, WorkspaceRequestReject
from src.system.middleware.RoleCheck import SystemPermissionCheck
from src.system.services.WorkspaceRequest import WorkspaceRequestService

router = APIRouter(prefix="/workspace-requests", tags=["System Workspace Requests"])


@router.post(
    "",
    response_model=BaseResponse,
)
async def submit_workspace_request(
    body: WorkspaceRequestCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_system_user),
):
    """Submit a new workspace request."""
    service = WorkspaceRequestService(db)
    result = await service.submit_request(body.model_dump())
    return {
        "success": True,
        "message": "Workspace request submitted successfully",
        "data": {"id": result.get("id")},
    }


@router.get(
    "",
    dependencies=[Depends(SystemPermissionCheck.require("workspaces:read"))],
)
async def get_workspace_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated workspace requests."""
    service = WorkspaceRequestService(db)
    items, total, total_pages = await service.get_paginated_requests(
        status=status,
        page=page,
        page_size=page_size,
    )
    return {
        "success": True,
        "message": "Workspace requests retrieved successfully",
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


@router.get(
    "/{request_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("workspaces:read"))],
)
async def get_workspace_request(request_id: int, db: AsyncSession = Depends(get_db)):
    """Get workspace request details."""
    service = WorkspaceRequestService(db)
    request = await service.get_request(request_id)
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace request not found")
    return {"success": True, "message": "Workspace request retrieved successfully", "data": request}


@router.post(
    "/{request_id}/approve",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("workspaces:update"))],
)
async def approve_workspace_request(
    request_id: int,
    current_user: dict = Depends(get_current_system_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve a workspace request."""
    service = WorkspaceRequestService(db)
    result = await service.approve_request(request_id, current_user["id"])
    return {
        "success": True,
        "message": "Request approved successfully",
        "data": result,
    }


@router.post(
    "/{request_id}/reject",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("workspaces:update"))],
)
async def reject_workspace_request(
    request_id: int,
    body: WorkspaceRequestReject,
    current_user: dict = Depends(get_current_system_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a workspace request."""
    service = WorkspaceRequestService(db)
    result = await service.reject_request(request_id, current_user["id"], body.rejection_reason)
    return {
        "success": True,
        "message": "Request rejected successfully",
        "data": result,
    }


@router.delete(
    "/{request_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("workspaces:delete"))],
)
async def delete_workspace_request(request_id: int, db: AsyncSession = Depends(get_db)):
    """Soft delete a workspace request."""
    service = WorkspaceRequestService(db)
    success = await service.soft_delete(request_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace request not found")
    return {"success": True, "message": "Request deleted successfully"}
