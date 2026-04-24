"""
Tables router — CRUD for restaurant tables.
"""

from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Table import TableService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db

router = APIRouter(prefix="/tables", tags=["Tables"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateTableRequest(BaseModel):
    table_number: str = Field(..., min_length=1, max_length=50)
    area_id: Optional[int] = None
    capacity: Optional[int] = Field(None, ge=1, le=50)
    status: Literal["available", "occupied", "reserved", "out_of_service"] = "available"
    display_order: Optional[int] = None


class UpdateTableRequest(BaseModel):
    table_number: Optional[str] = Field(None, min_length=1, max_length=50)
    area_id: Optional[int] = None
    capacity: Optional[int] = Field(None, ge=1, le=50)
    status: Optional[Literal["available", "occupied", "reserved", "out_of_service"]] = None
    display_order: Optional[int] = None


class UpdateTableStatusRequest(BaseModel):
    status: Literal["available", "occupied", "reserved", "out_of_service"]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=BaseResponse)
async def get_table_summary(
    workspace_id: Optional[int] = Query(None),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get table status counts summary."""
    wid = workspace_id or current_user.get("workspace_id")
    if not wid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workspace_id required")
    service = TableService(db)
    summary = await service.get_table_status_summary(wid)
    return {"success": True, "message": "Table summary retrieved successfully", "data": summary}


@router.get("", response_model=BaseResponse)
async def get_tables(
    workspace_id: Optional[int] = Query(None),
    area_id: Optional[int] = Query(None),
    table_status: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated tables."""
    wid = workspace_id or current_user.get("workspace_id")
    if not wid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workspace_id required")
    service = TableService(db)
    items, total, total_pages = await service.get_paginated_tables(
        workspace_id=wid,
        area_id=area_id,
        status=table_status,
        page=page,
        page_size=page_size,
    )
    return {
        "success": True,
        "message": "Tables retrieved successfully",
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


@router.post("", response_model=BaseResponse)
async def create_table(
    request: CreateTableRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new table."""
    wid = current_user.get("workspace_id")
    if not wid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workspace_id required")
    service = TableService(db)
    data = request.model_dump()
    data["workspace_id"] = wid
    table = await service.create_table(data)
    return {"success": True, "message": "Table created successfully", "data": table}


@router.get("/{table_id}", response_model=BaseResponse)
async def get_table(
    table_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a table by ID."""
    service = TableService(db)
    table = await service.get_by_id(table_id)
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    if table.get("workspace_id") != current_user.get("workspace_id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return {"success": True, "message": "Table retrieved successfully", "data": table}


@router.put("/{table_id}", response_model=BaseResponse)
async def update_table(
    table_id: int,
    request: UpdateTableRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a table."""
    service = TableService(db)
    existing = await service.get_by_id(table_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    if existing.get("workspace_id") != current_user.get("workspace_id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    data = request.model_dump(exclude_unset=True)
    success = await service.update_table(table_id, data)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    return {"success": True, "message": "Table updated successfully"}


@router.put("/{table_id}/status", response_model=BaseResponse)
async def update_table_status(
    table_id: int,
    request: UpdateTableStatusRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update only the status of a table."""
    service = TableService(db)
    existing = await service.get_by_id(table_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    if existing.get("workspace_id") != current_user.get("workspace_id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    success = await service.update_table_status(table_id, request.status)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    return {"success": True, "message": "Table status updated successfully"}


@router.delete("/{table_id}", response_model=BaseResponse)
async def delete_table(
    table_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a table."""
    service = TableService(db)
    existing = await service.get_by_id(table_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    if existing.get("workspace_id") != current_user.get("workspace_id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    success = await service.soft_delete_table(table_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    return {"success": True, "message": "Table deleted successfully"}


@router.post("/{table_id}/restore", response_model=BaseResponse)
async def restore_table(
    table_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:update")),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted table."""
    service = TableService(db)
    existing = await service.get_by_id(table_id, include_deleted=True)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    if existing.get("workspace_id") != current_user.get("workspace_id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if existing.get("is_active", False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Table is not deleted")
    success = await service.restore_table(table_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    return {"success": True, "message": "Table restored successfully"}
