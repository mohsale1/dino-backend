from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.repositories.PersonaRepository import PersonaRepository
from src.repositories.WorkspaceRepository import WorkspaceRepository

router = APIRouter(prefix="/workspaces", tags=["Application Workspaces"])


# ---------------------------------------------------------------------------
# GET /workspaces/me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=BaseResponse)
async def get_my_workspace(
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the workspace that the currently authenticated application user belongs to.
    Returns workspace details including linked personas.
    """
    workspace_id = current_user.get("workspace_id")
    if not workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not belong to a workspace",
        )

    workspace_repo = WorkspaceRepository(db)
    workspace = await workspace_repo.get_by_id(workspace_id)

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Resolve linked personas
    persona_repo = PersonaRepository(db)
    personas = await persona_repo.get_by_workspace(workspace_id)
    workspace["personas"] = personas

    return {
        "success": True,
        "message": "Workspace retrieved successfully",
        "data": workspace,
    }


# ---------------------------------------------------------------------------
# GET /workspaces/{workspace_id}
# ---------------------------------------------------------------------------

@router.get("/{workspace_id}", response_model=BaseResponse)
async def get_workspace(
    workspace_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """
    Get workspace details by ID.

    Application users may only access their own workspace.
    SuperAdmin (system user) may access any workspace.
    """
    user_type = current_user.get("user_type", "application")

    # Enforce workspace scope for non-SuperAdmin callers
    if user_type != "system":
        caller_workspace_id = current_user.get("workspace_id")
        if workspace_id != caller_workspace_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to other workspaces is not allowed",
            )

    workspace_repo = WorkspaceRepository(db)
    workspace = await workspace_repo.get_by_id(workspace_id)

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Resolve linked personas
    persona_repo = PersonaRepository(db)
    personas = await persona_repo.get_by_workspace(workspace_id)
    workspace["personas"] = personas

    return {
        "success": True,
        "message": "Workspace retrieved successfully",
        "data": workspace,
    }


# ---------------------------------------------------------------------------
# PUT /workspaces/{workspace_id}
# ---------------------------------------------------------------------------

@router.put("/{workspace_id}", response_model=BaseResponse)
async def update_workspace(
    workspace_id: int,
    data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('workspaces:update')),
    db: AsyncSession = Depends(get_db),
):
    """
    Update workspace details (Owner/Admin only).

    Application users may only update their own workspace.
    SuperAdmin (system user) may update any workspace.
    """
    user_type = current_user.get("user_type", "application")

    # SuperAdmin bypasses the workspace scope check
    if user_type != "system":
        caller_workspace_id = current_user.get("workspace_id")
        if workspace_id != caller_workspace_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to other workspaces is not allowed",
            )

    workspace_repo = WorkspaceRepository(db)

    existing = await workspace_repo.get_by_id(workspace_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Strip fields that must not be updated via this endpoint
    protected_fields = {"id", "owner_id", "referred_by", "created_at"}
    update_data = {k: v for k, v in data.items() if k not in protected_fields}

    success = await workspace_repo.update(workspace_id, update_data)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    return {
        "success": True,
        "message": "Workspace updated successfully",
    }


# ---------------------------------------------------------------------------
# GET /workspaces/{workspace_id}/personas
# ---------------------------------------------------------------------------

@router.get("/{workspace_id}/personas", response_model=BaseResponse)
async def get_workspace_personas(
    workspace_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all personas linked to a workspace.

    Application users may only access their own workspace's personas.
    SuperAdmin may access any workspace.
    """
    user_type = current_user.get("user_type", "application")

    if user_type != "system":
        caller_workspace_id = current_user.get("workspace_id")
        if workspace_id != caller_workspace_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to other workspaces is not allowed",
            )

    workspace_repo = WorkspaceRepository(db)
    workspace = await workspace_repo.get_by_id(workspace_id)

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    persona_repo = PersonaRepository(db)
    personas = await persona_repo.get_by_workspace(workspace_id)

    return {
        "success": True,
        "message": "Personas retrieved successfully",
        "data": personas,
    }
