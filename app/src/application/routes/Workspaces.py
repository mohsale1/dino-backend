"""
Workspaces router — workspace info and billing management.
All endpoints are scoped to the caller's own workspace via assert_own_workspace.
"""

import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.schemas.Workspace import (
    UpdateWorkspaceRequest,
    WorkspaceStatusResponse,
)
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Exceptions import BadRequestError, NotFoundError
from src.repositories.WorkspaceRepository import WorkspaceRepository
from src.application.services.Workspace import assert_own_workspace

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


# ---------------------------------------------------------------------------
# GET /workspaces/me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=BaseResponse)
async def get_my_workspace(
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("workspaces:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's workspace."""
    workspace_id = current_user.get("workspace_id")
    if not workspace_id:
        raise NotFoundError("User does not belong to a workspace")

    workspace = await WorkspaceRepository(db).get_by_id(workspace_id)
    if not workspace:
        raise NotFoundError("Workspace not found")

    return {"success": True, "message": "Workspace retrieved successfully", "data": workspace}


# ---------------------------------------------------------------------------
# GET /workspaces/{workspace_id}
# ---------------------------------------------------------------------------

@router.get("/{workspace_id}", response_model=BaseResponse)
async def get_workspace(
    workspace_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("workspaces:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a workspace by ID — must be the caller's own workspace."""
    assert_own_workspace(workspace_id, current_user)
    workspace = await WorkspaceRepository(db).get_by_id(workspace_id)
    if not workspace:
        raise NotFoundError("Workspace not found")
    return {"success": True, "message": "Workspace retrieved successfully", "data": workspace}


# ---------------------------------------------------------------------------
# PUT /workspaces/{workspace_id}
# ---------------------------------------------------------------------------

@router.put("/{workspace_id}", response_model=BaseResponse)
async def update_workspace(
    workspace_id: int,
    request: UpdateWorkspaceRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("workspaces:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update workspace name/description."""
    assert_own_workspace(workspace_id, current_user)
    data = request.model_dump(exclude_unset=True)
    if not data:
        raise BadRequestError("No fields provided for update")

    success = await WorkspaceRepository(db).update(workspace_id, data)
    if not success:
        raise NotFoundError("Workspace not found")
    return {"success": True, "message": "Workspace updated successfully"}

# ---------------------------------------------------------------------------
# GET /workspaces/{workspace_id}/status
# ---------------------------------------------------------------------------

@router.get("/{workspace_id}/status", response_model=BaseResponse)
async def get_workspace_status(
    workspace_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("workspaces:read")),
    db: AsyncSession = Depends(get_db),
):
    """Check the approval status of a workspace request."""
    assert_own_workspace(workspace_id, current_user)

    try:
        result = await db.execute(
            sa_text(
                "SELECT id, status, reviewed_at, rejection_reason "
                "FROM workspace_requests "
                "WHERE workspace_id = :wid AND is_active = true "
                "ORDER BY created_at DESC "
                "LIMIT 1"
            ),
            {"wid": workspace_id},
        )
        row = result.mappings().first()

        if row is None:
            return {
                "success": True,
                "message": "No workspace request found",
                "data": WorkspaceStatusResponse(
                    workspace_id=workspace_id,
                    request_exists=False,
                    approved=False,
                    status=None,
                    reviewed_at=None,
                    rejection_reason=None,
                ).model_dump(),
            }

        req_status = row["status"]
        return {
            "success": True,
            "message": "Workspace request status retrieved successfully",
            "data": WorkspaceStatusResponse(
                workspace_id=workspace_id,
                request_exists=True,
                approved=req_status == "approved",
                status=req_status,
                reviewed_at=str(row["reviewed_at"]) if row["reviewed_at"] else None,
                rejection_reason=row["rejection_reason"],
            ).model_dump(),
        }
    except Exception as e:
        logger.exception("workspaces.status.failed workspace_id=%s error=%s", workspace_id, str(e))
        return {"success": False, "message": "Failed to retrieve workspace status", "error_code": "INTERNAL_ERROR"} 