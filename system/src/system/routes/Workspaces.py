from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.Workspace import WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse
from src.system.services.Workspace import WorkspaceService
from src.base.BaseSchema import BaseResponse
from src.system.middleware.RoleCheck import SystemPermissionCheck
from src.config.Database import get_db
from typing import List, Dict, Any

router = APIRouter(prefix="/workspaces", tags=["System Workspaces"])

@router.post("", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('workspaces:create'))])
async def create_workspace(workspace: WorkspaceCreate, db: AsyncSession = Depends(get_db)):
    """Create new workspace (SuperAdmin only)"""
    service = WorkspaceService(db)

    workspace_id = await service.create_workspace(workspace.model_dump())

    return {
        "success": True,
        "message": "Workspace created successfully",
        "data": {"id": workspace_id}
    }

@router.get("", dependencies=[Depends(SystemPermissionCheck.require('workspaces:read'))])
async def get_all_workspaces(
    page: int = 1,
    page_size: int = 10,
    order_by: str = "created_at",
    order_direction: str = "desc",
    include_deleted: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all workspaces with pagination (SuperAdmin only)

    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 100)
    - order_by: Field to order by (default: created_at)
    - order_direction: Order direction (asc/desc, default: desc)
    - include_deleted: Include soft-deleted workspaces (default: false)
    """
    service = WorkspaceService(db)

    # Validate page_size
    if page_size > 100:
        page_size = 100

    items, total, total_pages = await service.get_paginated(
        page=page,
        page_size=page_size,
        include_deleted=include_deleted,
        order_by=order_by,
        order_direction=order_direction
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
            "has_prev": page > 1
        }
    }

@router.get("/{workspace_id}", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('workspaces:read'))])
async def get_workspace(workspace_id: int, db: AsyncSession = Depends(get_db)):
    """Get workspace details (SuperAdmin only)"""
    service = WorkspaceService(db)

    workspace = await service.get_workspace_details(workspace_id)

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    return {
        "success": True,
        "message": "Workspace retrieved successfully",
        "data": workspace
    }

@router.put("/{workspace_id}", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('workspaces:update'))])
async def update_workspace(workspace_id: int, workspace: WorkspaceUpdate, db: AsyncSession = Depends(get_db)):
    """Update workspace (SuperAdmin only)"""
    service = WorkspaceService(db)

    data = workspace.model_dump(exclude_unset=True)
    # persona_ids is managed via the join table — strip it from the direct update payload
    persona_ids = data.pop('persona_ids', None)

    success = await service.update(workspace_id, data)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    # If persona_ids were supplied, sync the join table
    if persona_ids is not None:
        from sqlalchemy import delete
        from src.models.Workspace import workspace_personas
        # Clear existing associations then re-add
        await service.db.execute(
            delete(workspace_personas).where(
                workspace_personas.c.workspace_id == workspace_id
            )
        )
        for pid in persona_ids:
            await service.add_persona(workspace_id, pid)

    return {
        "success": True,
        "message": "Workspace updated successfully"
    }

@router.delete("/{workspace_id}", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('workspaces:delete'))])
async def delete_workspace(workspace_id: int, db: AsyncSession = Depends(get_db)):
    """Soft delete workspace (SuperAdmin only) - Data is preserved"""
    service = WorkspaceService(db)

    success = await service.soft_delete(workspace_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    return {
        "success": True,
        "message": "Workspace soft deleted successfully (data preserved)"
    }

@router.put("/{workspace_id}/restore", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('workspaces:restore'))])
async def restore_workspace(workspace_id: int, db: AsyncSession = Depends(get_db)):
    """Restore a soft-deleted workspace (SuperAdmin only)"""
    service = WorkspaceService(db)

    # Check if workspace exists (including deleted)
    workspace = await service.get_by_id(workspace_id, include_deleted=True)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    if workspace.get('is_active', True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace is not deleted"
        )

    success = await service.restore(workspace_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    return {
        "success": True,
        "message": "Workspace restored successfully"
    }
