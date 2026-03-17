from fastapi import APIRouter, HTTPException, status, Depends
from src.schemas.Workspace import WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse
from src.system.services.Workspace import WorkspaceService
from src.base.BaseSchema import BaseResponse
from src.system.middleware.RoleCheck import SystemRoleCheck
from typing import List, Dict, Any

router = APIRouter(prefix="/workspaces", tags=["System Workspaces"])

@router.post("", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def create_workspace(workspace: WorkspaceCreate):
    """Create new workspace (SuperAdmin only)"""
    service = WorkspaceService()
    
    workspace_id = service.create_workspace(workspace.model_dump())
    
    return {
        "success": True,
        "message": "Workspace created successfully",
        "data": {"id": workspace_id}
    }

@router.get("", dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_all_workspaces(
    page: int = 1,
    page_size: int = 10,
    order_by: str = "created_at",
    order_direction: str = "desc",
    include_deleted: bool = False
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
    service = WorkspaceService()
    
    # Validate page_size
    if page_size > 100:
        page_size = 100
    
    items, total, total_pages = service.get_paginated(
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

@router.get("/{workspace_id}", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_workspace(workspace_id: str):
    """Get workspace details (SuperAdmin only)"""
    service = WorkspaceService()
    
    workspace = service.get_workspace_details(workspace_id)
    
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

@router.put("/{workspace_id}", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def update_workspace(workspace_id: str, workspace: WorkspaceUpdate):
    """Update workspace (SuperAdmin only)"""
    service = WorkspaceService()
    
    success = service.update(workspace_id, workspace.model_dump(exclude_unset=True))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    return {
        "success": True,
        "message": "Workspace updated successfully"
    }

@router.delete("/{workspace_id}", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def delete_workspace(workspace_id: str):
    """Soft delete workspace (SuperAdmin only) - Data is preserved"""
    service = WorkspaceService()
    
    success = service.soft_delete(workspace_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    return {
        "success": True,
        "message": "Workspace soft deleted successfully (data preserved)"
    }

@router.put("/{workspace_id}/restore", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def restore_workspace(workspace_id: str):
    """Restore a soft-deleted workspace (SuperAdmin only)"""
    service = WorkspaceService()
    
    # Check if workspace exists (including deleted)
    workspace = service.get_by_id(workspace_id, include_deleted=True)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    if not workspace.get('is_deleted', False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace is not deleted"
        )
    
    success = service.restore(workspace_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    return {
        "success": True,
        "message": "Workspace restored successfully"
    }
