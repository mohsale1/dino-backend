"""
Personas router — CRUD for persona (outlet/branch) profiles.
Scoped to the caller's workspace via workspace_personas join table.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Persona import PersonaService
from src.application.schemas.personas import (
    CreatePersonaRequest,
    UpdatePersonaRequest,
    ToggleOpenRequest,
    DeactivatePersonaRequest,
)
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Exceptions import BadRequestError, NotFoundError, PersonaNotDeletedError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/personas", tags=["Personas"])


def _require_workspace(current_user: Dict[str, Any]) -> int:
    wid = current_user.get("workspace_id")
    if not wid:
        raise BadRequestError("workspace_id could not be resolved for this user")
    return wid


@router.get("", response_model=BaseResponse)
async def get_personas(
    include_deleted: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated personas linked to the caller's workspace."""
    items, total, total_pages = await PersonaService(db).get_paginated_personas(
        workspace_id=_require_workspace(current_user),
        page=page,
        page_size=page_size,
        include_deleted=include_deleted,
    )
    return {
        "success": True,
        "message": "Personas retrieved successfully",
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
async def create_persona(
    request: CreatePersonaRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Create a new persona and link it to the caller's workspace."""
    data = request.model_dump()
    data["workspace_id"] = _require_workspace(current_user)
    persona = await PersonaService(db).create_persona(data)
    return {"success": True, "message": "Persona created successfully", "data": persona}


@router.get("/{persona_id}", response_model=BaseResponse)
async def get_persona(
    persona_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get a persona by ID scoped to the caller's workspace."""
    persona = await PersonaService(db).get_persona_by_id(persona_id, _require_workspace(current_user))
    if not persona:
        raise NotFoundError("Persona not found")
    return {"success": True, "message": "Persona retrieved successfully", "data": persona}


@router.put("/{persona_id}", response_model=BaseResponse)
async def update_persona(
    persona_id: int,
    request: UpdatePersonaRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update a persona scoped to the caller's workspace."""
    data = request.model_dump(exclude_unset=True)
    if not data:
        raise BadRequestError("No fields provided for update")
    updated = await PersonaService(db).update_persona(persona_id, _require_workspace(current_user), data)
    if not updated:
        raise NotFoundError("Persona not found")
    return {"success": True, "message": "Persona updated successfully"}


@router.put("/{persona_id}/status", response_model=BaseResponse)
async def toggle_persona_open(
    persona_id: int,
    request: ToggleOpenRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Toggle the is_open status of a persona."""
    updated = await PersonaService(db).toggle_open(persona_id, _require_workspace(current_user), request.is_open)
    if not updated:
        raise NotFoundError("Persona not found")
    return {"success": True, "message": "Persona status updated successfully"}


@router.put("/{persona_id}/deactivate", response_model=BaseResponse)
async def deactivate_persona(
    persona_id: int,
    request: DeactivatePersonaRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Toggle the billing-level suspension flag (is_deactivated) on a persona."""
    updated = await PersonaService(db).deactivate_persona(persona_id, _require_workspace(current_user), request.is_deactivated)
    if not updated:
        raise NotFoundError("Persona not found")
    action = "deactivated" if request.is_deactivated else "reactivated"
    return {"success": True, "message": f"Persona {action} successfully"}


@router.delete("/{persona_id}", response_model=BaseResponse)
async def delete_persona(
    persona_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a persona."""
    deleted = await PersonaService(db).soft_delete_persona(persona_id)
    if not deleted:
        raise NotFoundError("Persona not found")
    return {"success": True, "message": "Persona deleted successfully"}


@router.post("/{persona_id}/restore", response_model=BaseResponse)
async def restore_persona(
    persona_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted persona."""
    existing = await PersonaService(db).get_persona_by_id(
        persona_id, _require_workspace(current_user), include_deleted=True
    )
    if not existing:
        raise NotFoundError("Persona not found")
    if existing.get("is_active", False):
        raise PersonaNotDeletedError()

    await PersonaService(db).restore_persona(persona_id)
    return {"success": True, "message": "Persona restored successfully"}


@router.post("/{persona_id}/logo", response_model=BaseResponse)
async def upload_persona_logo(
    persona_id: int,
    file: UploadFile = File(..., description="Logo image (JPEG, PNG, WebP, GIF — max 5 MB)"),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload or replace the logo for a persona.

    - Stores to GCS at: personas/{workspace_id}/{persona_id}_logo.{ext}
    - Re-uploading overwrites the same blob
    - Updates logo_url on the persona row
    """
    workspace_id = _require_workspace(current_user)
    file_data = await file.read()

    url = await PersonaService(db).upload_logo(
        persona_id=persona_id,
        workspace_id=workspace_id,
        file_data=file_data,
        content_type=file.content_type or "",
    )
    return {
        "success": True,
        "message": "Logo uploaded successfully",
        "data": {"logo_url": url},
    }
