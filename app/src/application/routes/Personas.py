"""
Personas router — CRUD for persona (outlet/branch) profiles.
Scoped to the caller's workspace via workspace_personas join table.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Persona import PersonaService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Exceptions import BadRequestError, NotFoundError, PersonaNotDeletedError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/personas", tags=["Personas"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreatePersonaRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    persona_type: int = Field(0, ge=0, le=1)
    order_type: int = Field(0, ge=0, le=1)
    logo_url: Optional[str] = Field(None, max_length=500)
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    phone: Optional[str] = Field(None, max_length=30, pattern=r'^\+?[0-9\s\-\(\)]{7,30}$')
    email: Optional[EmailStr] = None
    is_open: bool = False

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class UpdatePersonaRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    persona_type: Optional[int] = Field(None, ge=0, le=1)
    order_type: Optional[int] = Field(None, ge=0, le=1)
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    phone: Optional[str] = Field(None, max_length=30, pattern=r'^\+?[0-9\s\-\(\)]{7,30}$')
    email: Optional[EmailStr] = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class ToggleOpenRequest(BaseModel):
    is_open: bool


class DeactivatePersonaRequest(BaseModel):
    is_deactivated: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_workspace(current_user: Dict[str, Any]) -> int:
    wid = current_user.get("workspace_id")
    if not wid:
        raise BadRequestError("workspace_id could not be resolved for this user")
    return wid


# ---------------------------------------------------------------------------
# GET /personas
# ---------------------------------------------------------------------------

@router.get("", response_model=BaseResponse)
async def get_personas(
    include_deleted: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated personas linked to the caller's workspace."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "personas.list.request user_id=%s workspace_id=%s "
        "include_deleted=%s page=%s page_size=%s",
        user_id, workspace_id, include_deleted, page, page_size,
    )

    items, total, total_pages = await PersonaService(db).get_paginated_personas(
        workspace_id=workspace_id,
        page=page,
        page_size=page_size,
        include_deleted=include_deleted,
    )

    logger.info(
        "personas.list.response user_id=%s workspace_id=%s "
        "total=%s page=%s total_pages=%s returned=%s",
        user_id, workspace_id, total, page, total_pages, len(items),
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


# ---------------------------------------------------------------------------
# POST /personas
# ---------------------------------------------------------------------------

@router.post("", response_model=BaseResponse, status_code=201)
async def create_persona(
    request: CreatePersonaRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Create a new persona and link it to the caller's workspace."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "personas.create.request user_id=%s workspace_id=%s name=%r",
        user_id, workspace_id, request.name,
    )

    data = request.model_dump()
    data["workspace_id"] = workspace_id

    persona = await PersonaService(db).create_persona(data)

    logger.info(
        "personas.create.response user_id=%s workspace_id=%s "
        "persona_id=%s name=%r",
        user_id, workspace_id, persona.get("id"), persona.get("name"),
    )
    return {"success": True, "message": "Persona created successfully", "data": persona}


# ---------------------------------------------------------------------------
# GET /personas/{persona_id}
# ---------------------------------------------------------------------------

@router.get("/{persona_id}", response_model=BaseResponse)
async def get_persona(
    persona_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get a persona by ID scoped to the caller's workspace."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "personas.get.request user_id=%s workspace_id=%s persona_id=%s",
        user_id, workspace_id, persona_id,
    )

    persona = await PersonaService(db).get_persona_by_id(persona_id, workspace_id)
    if not persona:
        logger.warning(
            "personas.get.not_found user_id=%s workspace_id=%s persona_id=%s",
            user_id, workspace_id, persona_id,
        )
        raise NotFoundError("Persona not found")

    logger.info(
        "personas.get.response user_id=%s persona_id=%s name=%r",
        user_id, persona_id, persona.get("name"),
    )
    return {"success": True, "message": "Persona retrieved successfully", "data": persona}


# ---------------------------------------------------------------------------
# PUT /personas/{persona_id}
# ---------------------------------------------------------------------------

@router.put("/{persona_id}", response_model=BaseResponse)
async def update_persona(
    persona_id: int,
    request: UpdatePersonaRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update a persona scoped to the caller's workspace. Single round-trip."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)
    data = request.model_dump(exclude_unset=True)

    if not data:
        logger.warning(
            "personas.update.empty_payload user_id=%s persona_id=%s",
            user_id, persona_id,
        )
        raise BadRequestError("No fields provided for update")

    logger.info(
        "personas.update.request user_id=%s workspace_id=%s "
        "persona_id=%s fields=%s",
        user_id, workspace_id, persona_id, list(data.keys()),
    )

    updated = await PersonaService(db).update_persona(persona_id, workspace_id, data)
    if not updated:
        logger.warning(
            "personas.update.not_found user_id=%s workspace_id=%s persona_id=%s",
            user_id, workspace_id, persona_id,
        )
        raise NotFoundError("Persona not found")

    logger.info(
        "personas.update.response user_id=%s persona_id=%s fields=%s",
        user_id, persona_id, list(data.keys()),
    )
    return {"success": True, "message": "Persona updated successfully"}


# ---------------------------------------------------------------------------
# PUT /personas/{persona_id}/status
# ---------------------------------------------------------------------------

@router.put("/{persona_id}/status", response_model=BaseResponse)
async def toggle_persona_open(
    persona_id: int,
    request: ToggleOpenRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Toggle the is_open status of a persona. Single round-trip."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "personas.status.request user_id=%s workspace_id=%s "
        "persona_id=%s is_open=%s",
        user_id, workspace_id, persona_id, request.is_open,
    )

    updated = await PersonaService(db).toggle_open(persona_id, workspace_id, request.is_open)
    if not updated:
        logger.warning(
            "personas.status.not_found user_id=%s workspace_id=%s persona_id=%s",
            user_id, workspace_id, persona_id,
        )
        raise NotFoundError("Persona not found")

    logger.info(
        "personas.status.response user_id=%s persona_id=%s is_open=%s",
        user_id, persona_id, request.is_open,
    )
    return {"success": True, "message": "Persona status updated successfully"}


# ---------------------------------------------------------------------------
# PUT /personas/{persona_id}/deactivate
# ---------------------------------------------------------------------------

@router.put("/{persona_id}/deactivate", response_model=BaseResponse)
async def deactivate_persona(
    persona_id: int,
    request: DeactivatePersonaRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """
    Toggle the billing-level suspension flag (is_deactivated) on a persona.

    is_deactivated=true  → persona is suspended (e.g. billing overdue)
    is_deactivated=false → persona is reinstated

    This is separate from soft-delete. A deactivated persona still exists
    and is visible but should be treated as suspended by the UI/ordering flow.
    """
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "personas.deactivate.request user_id=%s workspace_id=%s "
        "persona_id=%s is_deactivated=%s",
        user_id, workspace_id, persona_id, request.is_deactivated,
    )

    updated = await PersonaService(db).deactivate_persona(
        persona_id, workspace_id, request.is_deactivated
    )
    if not updated:
        logger.warning(
            "personas.deactivate.not_found user_id=%s workspace_id=%s persona_id=%s",
            user_id, workspace_id, persona_id,
        )
        raise NotFoundError("Persona not found")

    action = "deactivated" if request.is_deactivated else "reactivated"
    logger.info(
        "personas.deactivate.response user_id=%s persona_id=%s action=%s",
        user_id, persona_id, action,
    )
    return {
        "success": True,
        "message": f"Persona {action} successfully",
    }


# ---------------------------------------------------------------------------
# DELETE /personas/{persona_id}
# ---------------------------------------------------------------------------

@router.delete("/{persona_id}", response_model=BaseResponse)
async def delete_persona(
    persona_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a persona."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "personas.delete.request user_id=%s workspace_id=%s persona_id=%s",
        user_id, workspace_id, persona_id,
    )

    deleted = await PersonaService(db).soft_delete_persona(persona_id)
    if not deleted:
        logger.warning(
            "personas.delete.not_found user_id=%s persona_id=%s",
            user_id, persona_id,
        )
        raise NotFoundError("Persona not found")

    logger.info(
        "personas.delete.response user_id=%s workspace_id=%s persona_id=%s",
        user_id, workspace_id, persona_id,
    )
    return {"success": True, "message": "Persona deleted successfully"}


# ---------------------------------------------------------------------------
# POST /personas/{persona_id}/restore
# ---------------------------------------------------------------------------

@router.post("/{persona_id}/restore", response_model=BaseResponse)
async def restore_persona(
    persona_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted persona."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "personas.restore.request user_id=%s workspace_id=%s persona_id=%s",
        user_id, workspace_id, persona_id,
    )

    # Fetch including deleted to give accurate error
    existing = await PersonaService(db).get_persona_by_id(
        persona_id, workspace_id, include_deleted=True
    )
    if not existing:
        logger.warning(
            "personas.restore.not_found user_id=%s persona_id=%s",
            user_id, persona_id,
        )
        raise NotFoundError("Persona not found")

    if existing.get("is_active", False):
        raise PersonaNotDeletedError()

    await PersonaService(db).restore_persona(persona_id)

    logger.info(
        "personas.restore.response user_id=%s workspace_id=%s persona_id=%s",
        user_id, workspace_id, persona_id,
    )
    return {"success": True, "message": "Persona restored successfully"}


# ---------------------------------------------------------------------------
# POST /personas/{persona_id}/logo
# ---------------------------------------------------------------------------

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
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "personas.logo.upload.request user_id=%s workspace_id=%s "
        "persona_id=%s filename=%r content_type=%s",
        user_id, workspace_id, persona_id,
        file.filename, file.content_type,
    )

    file_data = await file.read()

    url = await PersonaService(db).upload_logo(
        persona_id=persona_id,
        workspace_id=workspace_id,
        file_data=file_data,
        content_type=file.content_type or "",
    )

    logger.info(
        "personas.logo.upload.response user_id=%s persona_id=%s url=%s",
        user_id, persona_id, url,
    )
    return {
        "success": True,
        "message": "Logo uploaded successfully",
        "data": {"logo_url": url},
    }
