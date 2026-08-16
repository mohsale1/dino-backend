"""
Tables router — CRUD for restaurant tables, scoped by persona_id.
"""

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Table import TableService
from src.schemas.Table import TableCreate, TableUpdate, TableStatusUpdate
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.config.Settings import settings
from src.core.Exceptions import BadRequestError, NotFoundError, PermissionDeniedError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tables", tags=["Tables"])


@router.get("/summary", response_model=BaseResponse)
async def get_table_summary(
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get table status counts summary scoped to persona."""
    try:
        summary = await TableService(db).get_table_status_summary(persona_id)
        return {"success": True, "message": "Table summary retrieved successfully", "data": summary}
    except Exception as e:
        logger.exception("tables.summary.failed error=%s", str(e))
        return {"success": False, "message": "Failed to retrieve table summary", "error_code": "INTERNAL_ERROR"}


@router.get("", response_model=BaseResponse)
async def get_tables(
    persona_id: int = Query(..., ge=1),
    area_id: Optional[int] = Query(None, ge=1),
    table_status: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated tables scoped to persona."""
    try:
        items, total, total_pages = await TableService(db).get_paginated_tables(
            persona_id=persona_id, area_id=area_id, status=table_status, page=page, page_size=page_size
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
    except Exception as e:
        logger.exception("tables.list.failed error=%s", str(e))
        return {"success": False, "message": "Failed to retrieve tables", "error_code": "INTERNAL_ERROR"}


@router.post("", response_model=BaseResponse, status_code=201)
async def create_table(
    request: TableCreate,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new table scoped to persona."""
    try:
        table = await TableService(db).create_table(request.model_dump())
        return {"success": True, "message": "Table created successfully", "data": table}
    except PermissionDeniedError:
        return {"success": False, "message": "You do not have permission to create tables", "error_code": "PERMISSION_DENIED"}
    except Exception as e:
        logger.exception("tables.create.failed error=%s", str(e))
        return {"success": False, "message": "Failed to create table", "error_code": "INTERNAL_ERROR"}


@router.get("/{table_id}/qr-code")
async def get_table_qr_code(
    table_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:read")),
    db: AsyncSession = Depends(get_db),
):
    """Return a QR code PNG for the given table linking to the customer menu page."""
    try:
        png_bytes = await TableService(db).generate_qr_code(
            table_id=table_id, persona_id=persona_id, frontend_url=settings.FRONTEND_URL
        )
        return Response(content=png_bytes, media_type="image/png")
    except Exception as e:
        logger.exception("tables.qr_code.failed error=%s", str(e))
        return Response(content=b"", media_type="image/png", status_code=500)


@router.get("/{table_id}", response_model=BaseResponse)
async def get_table(
    table_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a table by ID scoped to persona."""
    try:
        table = await TableService(db).get_table_for_persona(table_id, persona_id)
        if not table:
            raise NotFoundError("Table not found")
        return {"success": True, "message": "Table retrieved successfully", "data": table}
    except NotFoundError as e:
        return {"success": False, "message": str(e), "error_code": "NOT_FOUND"}
    except Exception as e:
        logger.exception("tables.get.failed error=%s", str(e))
        return {"success": False, "message": "Failed to retrieve table", "error_code": "INTERNAL_ERROR"}


@router.put("/{table_id}", response_model=BaseResponse)
async def update_table(
    table_id: int,
    request: TableUpdate,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a table scoped to persona."""
    try:
        data = request.model_dump(exclude_unset=True)
        if not data:
            raise BadRequestError("No fields provided for update")

        updated = await TableService(db).update_table(table_id, persona_id, data)
        if not updated:
            raise NotFoundError("Table not found")
        return {"success": True, "message": "Table updated successfully"}
    except BadRequestError as e:
        return {"success": False, "message": str(e), "error_code": "BAD_REQUEST"}
    except NotFoundError as e:
        return {"success": False, "message": str(e), "error_code": "NOT_FOUND"}
    except Exception as e:
        logger.exception("tables.update.failed error=%s", str(e))
        return {"success": False, "message": "Failed to update table", "error_code": "INTERNAL_ERROR"}


@router.put("/{table_id}/status", response_model=BaseResponse)
async def update_table_status(
    table_id: int,
    request: TableStatusUpdate,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update only the status of a table scoped to persona."""
    try:
        updated = await TableService(db).update_table_status(table_id, persona_id, request.status)
        if not updated:
            raise NotFoundError("Table not found")
        return {"success": True, "message": "Table status updated successfully"}
    except NotFoundError as e:
        return {"success": False, "message": str(e), "error_code": "NOT_FOUND"}
    except PermissionDeniedError:
        return {"success": False, "message": "You do not have permission to update table status", "error_code": "PERMISSION_DENIED"}
    except Exception as e:
        logger.exception("tables.status.failed error=%s", str(e))
        return {"success": False, "message": "Failed to update table status", "error_code": "INTERNAL_ERROR"}

@router.delete("/{table_id}", response_model=BaseResponse)
async def delete_table(
    table_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a table scoped to persona."""
    try:
        deleted = await TableService(db).soft_delete_table(table_id, persona_id)
        if not deleted:
            raise NotFoundError("Table not found")
        return {"success": True, "message": "Table deleted successfully"}
    except NotFoundError as e:
        return {"success": False, "message": str(e), "error_code": "NOT_FOUND"}
    except PermissionDeniedError:
        return {"success": False, "message": "You do not have permission to delete tables", "error_code": "PERMISSION_DENIED"}
    except Exception as e:
        logger.exception("tables.delete.failed error=%s", str(e))
        return {"success": False, "message": "Failed to delete table", "error_code": "INTERNAL_ERROR"}


@router.post("/{table_id}/restore", response_model=BaseResponse)
async def restore_table(
    table_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("tables:restore")),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted table scoped to persona."""
    try:
        restored = await TableService(db).restore_table(table_id, persona_id)
        if not restored:
            raise NotFoundError("Table not found or is not deleted")
        return {"success": True, "message": "Table restored successfully"}
    except PermissionDeniedError:
        return {"success": False, "message": "You do not have permission to restore tables", "error_code": "PERMISSION_DENIED"}
    except NotFoundError as e:
        return {"success": False, "message": str(e), "error_code": "NOT_FOUND"}
    except Exception as e:
        logger.exception("tables.restore.failed error=%s", str(e))
        return {"success": False, "message": "Failed to restore table", "error_code": "INTERNAL_ERROR"}
