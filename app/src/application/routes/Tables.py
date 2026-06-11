"""
Tables router — CRUD for restaurant tables, scoped by persona_id.
"""

import logging
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Table import TableService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.config.Settings import settings
from src.core.Exceptions import BadRequestError, NotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tables", tags=["Tables"])


class CreateTableRequest(BaseModel):
    table_number: str = Field(..., min_length=1, max_length=50)
    area_id: int = Field(..., ge=1)
    persona_id: int = Field(..., ge=1)
    capacity: int = Field(4, ge=1, le=50)
    status: Literal["available", "occupied", "reserved", "out_of_service"] = "available"

    @field_validator("table_number")
    @classmethod
    def strip_table_number(cls, v: str) -> str:
        return v.strip()


class UpdateTableRequest(BaseModel):
    table_number: Optional[str] = Field(None, min_length=1, max_length=50)
    capacity: Optional[int] = Field(None, ge=1, le=50)
    status: Optional[Literal["available", "occupied", "reserved", "out_of_service"]] = None

    @field_validator("table_number")
    @classmethod
    def strip_table_number(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class UpdateTableStatusRequest(BaseModel):
    status: Literal["available", "occupied", "reserved", "out_of_service"]


@router.get("/summary", response_model=BaseResponse)
async def get_table_summary(
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get table status counts summary scoped to persona."""
    user_id = current_user.get("id")
    logger.info("tables.summary.request user_id=%s persona_id=%s", user_id, persona_id)

    summary = await TableService(db).get_table_status_summary(persona_id)

    logger.info("tables.summary.response user_id=%s persona_id=%s data=%s", user_id, persona_id, summary)
    return {"success": True, "message": "Table summary retrieved successfully", "data": summary}


@router.get("", response_model=BaseResponse)
async def get_tables(
    persona_id: int = Query(..., ge=1),
    area_id: Optional[int] = Query(None, ge=1),
    table_status: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated tables scoped to persona."""
    user_id = current_user.get("id")
    logger.info(
        "tables.list.request user_id=%s persona_id=%s area_id=%s status=%s page=%s page_size=%s",
        user_id, persona_id, area_id, table_status, page, page_size,
    )

    items, total, total_pages = await TableService(db).get_paginated_tables(
        persona_id=persona_id,
        area_id=area_id,
        status=table_status,
        page=page,
        page_size=page_size,
    )

    logger.info(
        "tables.list.response user_id=%s persona_id=%s total=%s page=%s returned=%s",
        user_id, persona_id, total, page, len(items),
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


@router.post("", response_model=BaseResponse, status_code=201)
async def create_table(
    request: CreateTableRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Create a new table scoped to persona."""
    user_id = current_user.get("id")
    logger.info(
        "tables.create.request user_id=%s persona_id=%s area_id=%s table_number=%r",
        user_id, request.persona_id, request.area_id, request.table_number,
    )

    data = request.model_dump()
    table = await TableService(db).create_table(data)

    logger.info(
        "tables.create.response user_id=%s table_id=%s persona_id=%s table_number=%r",
        user_id, table.get("id"), request.persona_id, table.get("table_number"),
    )
    return {"success": True, "message": "Table created successfully", "data": table}


@router.get("/{table_id}/qr-code")
async def get_table_qr_code(
    table_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Return a QR code PNG for the given table linking to the customer menu page."""
    user_id = current_user.get("id")
    logger.info(
        "tables.qr_code.request user_id=%s table_id=%s persona_id=%s",
        user_id, table_id, persona_id,
    )

    png_bytes = await TableService(db).generate_qr_code(
        table_id=table_id,
        persona_id=persona_id,
        frontend_url=settings.FRONTEND_URL,
    )

    logger.info("tables.qr_code.response user_id=%s table_id=%s", user_id, table_id)
    return Response(content=png_bytes, media_type="image/png")


@router.get("/{table_id}", response_model=BaseResponse)
async def get_table(
    table_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get a table by ID scoped to persona."""
    user_id = current_user.get("id")
    logger.info(
        "tables.get.request user_id=%s table_id=%s persona_id=%s",
        user_id, table_id, persona_id,
    )

    table = await TableService(db).get_table_for_persona(table_id, persona_id)
    if not table:
        logger.warning(
            "tables.get.not_found user_id=%s table_id=%s persona_id=%s",
            user_id, table_id, persona_id,
        )
        raise NotFoundError("Table not found")

    logger.info(
        "tables.get.response user_id=%s table_id=%s table_number=%r",
        user_id, table_id, table.get("table_number"),
    )
    return {"success": True, "message": "Table retrieved successfully", "data": table}


@router.put("/{table_id}", response_model=BaseResponse)
async def update_table(
    table_id: int,
    request: UpdateTableRequest,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update a table scoped to persona."""
    user_id = current_user.get("id")
    data = request.model_dump(exclude_unset=True)

    if not data:
        logger.warning("tables.update.empty_payload user_id=%s table_id=%s", user_id, table_id)
        raise BadRequestError("No fields provided for update")

    logger.info(
        "tables.update.request user_id=%s table_id=%s persona_id=%s fields=%s",
        user_id, table_id, persona_id, list(data.keys()),
    )

    updated = await TableService(db).update_table(table_id, persona_id, data)
    if not updated:
        logger.warning("tables.update.not_found user_id=%s table_id=%s", user_id, table_id)
        raise NotFoundError("Table not found")

    logger.info(
        "tables.update.response user_id=%s table_id=%s fields=%s",
        user_id, table_id, list(data.keys()),
    )
    return {"success": True, "message": "Table updated successfully"}


@router.put("/{table_id}/status", response_model=BaseResponse)
async def update_table_status(
    table_id: int,
    request: UpdateTableStatusRequest,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update only the status of a table scoped to persona."""
    user_id = current_user.get("id")
    logger.info(
        "tables.status.request user_id=%s table_id=%s persona_id=%s status=%s",
        user_id, table_id, persona_id, request.status,
    )

    updated = await TableService(db).update_table_status(table_id, persona_id, request.status)
    if not updated:
        logger.warning("tables.status.not_found user_id=%s table_id=%s", user_id, table_id)
        raise NotFoundError("Table not found")

    logger.info(
        "tables.status.response user_id=%s table_id=%s status=%s",
        user_id, table_id, request.status,
    )
    return {"success": True, "message": "Table status updated successfully"}


@router.delete("/{table_id}", response_model=BaseResponse)
async def delete_table(
    table_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a table scoped to persona."""
    user_id = current_user.get("id")
    logger.info(
        "tables.delete.request user_id=%s table_id=%s persona_id=%s",
        user_id, table_id, persona_id,
    )

    deleted = await TableService(db).soft_delete_table(table_id, persona_id)
    if not deleted:
        logger.warning("tables.delete.not_found user_id=%s table_id=%s", user_id, table_id)
        raise NotFoundError("Table not found")

    logger.info("tables.delete.response user_id=%s table_id=%s", user_id, table_id)
    return {"success": True, "message": "Table deleted successfully"}


@router.post("/{table_id}/restore", response_model=BaseResponse)
async def restore_table(
    table_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted table scoped to persona."""
    user_id = current_user.get("id")
    logger.info(
        "tables.restore.request user_id=%s table_id=%s persona_id=%s",
        user_id, table_id, persona_id,
    )

    restored = await TableService(db).restore_table(table_id, persona_id)
    if not restored:
        logger.warning("tables.restore.not_found user_id=%s table_id=%s", user_id, table_id)
        raise NotFoundError("Table not found or is not deleted")

    logger.info("tables.restore.response user_id=%s table_id=%s", user_id, table_id)
    return {"success": True, "message": "Table restored successfully"}
