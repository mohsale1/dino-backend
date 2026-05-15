"""
Tables router — CRUD for restaurant tables.
"""

from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.Settings import settings

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Table import TableService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db

router = APIRouter(prefix="/tables", tags=["Tables"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_workspace(current_user: Dict[str, Any]) -> int:
    wid = current_user.get("workspace_id")
    if not wid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workspace_id required",
        )
    return wid


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateTableRequest(BaseModel):
    table_number: str = Field(..., min_length=1, max_length=50)
    area_id: int = Field(..., ge=1)
    persona_id: int = Field(..., ge=1)
    capacity: int = Field(4, ge=1, le=50)
    status: Literal["available", "occupied", "reserved", "out_of_service"] = "available"



class UpdateTableRequest(BaseModel):
    table_number: Optional[str] = Field(None, min_length=1, max_length=50)
    capacity: Optional[int] = Field(None, ge=1, le=50)
    status: Optional[Literal["available", "occupied", "reserved", "out_of_service"]] = None



class UpdateTableStatusRequest(BaseModel):
    status: Literal["available", "occupied", "reserved", "out_of_service"]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=BaseResponse)
async def get_table_summary(
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get table status counts summary."""
    wid = _require_workspace(current_user)
    service = TableService(db)
    summary = await service.get_table_status_summary(wid, persona_id)
    return {"success": True, "message": "Table summary retrieved successfully", "data": summary}


@router.get("", response_model=BaseResponse)
async def get_tables(
    persona_id: int = Query(..., ge=1),
    area_id: Optional[int] = Query(None),
    table_status: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated tables."""
    wid = _require_workspace(current_user)
    service = TableService(db)
    items, total, total_pages = await service.get_paginated_tables(
        workspace_id=wid,
        persona_id=persona_id,
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


@router.post("", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_table(
    request: CreateTableRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new table."""
    wid = _require_workspace(current_user)
    service = TableService(db)
    data = request.model_dump(exclude_none=True)
    data["workspace_id"] = wid
    table = await service.create_table(data)
    return {"success": True, "message": "Table created successfully", "data": table}



@router.get("/{table_id}/qr-code")
async def get_table_qr_code(
    table_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:read")),
    db: AsyncSession = Depends(get_db),
):
    """Return a QR code PNG for the given table linking to the customer menu page."""
    wid = _require_workspace(current_user)
    service = TableService(db)
    png_bytes = await service.generate_qr_code(
        table_id=table_id,
        workspace_id=wid,
        persona_id=persona_id,
        frontend_url=settings.FRONTEND_URL,
    )
    return Response(content=png_bytes, media_type="image/png")


@router.get("/{table_id}", response_model=BaseResponse)
async def get_table(
    table_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a table by ID scoped to persona."""
    wid = _require_workspace(current_user)
    service = TableService(db)
    table = await service.get_table_for_persona(table_id, wid, persona_id)
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    return {"success": True, "message": "Table retrieved successfully", "data": table}


@router.put("/{table_id}", response_model=BaseResponse)
async def update_table(
    table_id: int,
    request: UpdateTableRequest,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a table."""
    wid = _require_workspace(current_user)
    data = request.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )
    service = TableService(db)
    updated = await service.update_table(table_id, wid, persona_id, data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    return {"success": True, "message": "Table updated successfully"}


@router.put("/{table_id}/status", response_model=BaseResponse)
async def update_table_status(
    table_id: int,
    request: UpdateTableStatusRequest,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update only the status of a table."""
    wid = _require_workspace(current_user)
    service = TableService(db)
    updated = await service.update_table_status(table_id, wid, persona_id, request.status)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    return {"success": True, "message": "Table status updated successfully"}


@router.delete("/{table_id}", response_model=BaseResponse)
async def delete_table(
    table_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a table."""
    wid = _require_workspace(current_user)
    service = TableService(db)
    deleted = await service.soft_delete_table(table_id, wid, persona_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    return {"success": True, "message": "Table deleted successfully"}


@router.post("/{table_id}/restore", response_model=BaseResponse)
async def restore_table(
    table_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:update")),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted table."""
    wid = _require_workspace(current_user)
    service = TableService(db)
    restored = await service.restore_table(table_id, wid, persona_id)
    if not restored:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found or is not deleted",
        )
    return {"success": True, "message": "Table restored successfully"}