"""
Personas router — CRUD for persona (outlet/branch) profiles.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Persona import PersonaService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db

router = APIRouter(prefix="/personas", tags=["Personas"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreatePersonaRequest(BaseModel):
    name: str
    description: Optional[str] = None
    workspace_id: Optional[int] = None
    persona_type: int = 0
    order_type: int = 0
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_open: bool = False


class UpdatePersonaRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    persona_type: Optional[int] = None
    order_type: Optional[int] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class ToggleOpenRequest(BaseModel):
    is_open: bool


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=BaseResponse)
async def get_personas(
    workspace_id: Optional[int] = Query(None),
    include_deleted: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("personas:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated personas."""
    wid = workspace_id or current_user.get("workspace_id")
    if not wid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workspace_id required")
    service = PersonaService(db)
    items, total, total_pages = await service.get_paginated_personas(
        workspace_id=wid,
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


@router.post("", response_model=BaseResponse)
async def create_persona(
    request: CreatePersonaRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("personas:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new persona and link it to the workspace."""
    wid = request.workspace_id or current_user.get("workspace_id")
    if not wid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workspace_id required")
    service = PersonaService(db)
    data = request.model_dump()
    data["workspace_id"] = wid
    persona = await service.create_persona(data)
    return {"success": True, "message": "Persona created successfully", "data": persona}


@router.get("/{persona_id}", response_model=BaseResponse)
async def get_persona(
    persona_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("personas:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a persona by ID."""
    service = PersonaService(db)
    persona = await service.get_by_id(persona_id)
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    return {"success": True, "message": "Persona retrieved successfully", "data": persona}


@router.put("/{persona_id}", response_model=BaseResponse)
async def update_persona(
    persona_id: int,
    request: UpdatePersonaRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("personas:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a persona."""
    service = PersonaService(db)
    existing = await service.get_by_id(persona_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    data = request.model_dump(exclude_unset=True)
    success = await service.update_persona(persona_id, data)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    return {"success": True, "message": "Persona updated successfully"}


@router.put("/{persona_id}/status", response_model=BaseResponse)
async def toggle_persona_open(
    persona_id: int,
    request: ToggleOpenRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("personas:update")),
    db: AsyncSession = Depends(get_db),
):
    """Toggle the is_open status of a persona."""
    service = PersonaService(db)
    existing = await service.get_by_id(persona_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    success = await service.toggle_open(persona_id, request.is_open)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    return {"success": True, "message": "Persona status updated successfully"}


@router.delete("/{persona_id}", response_model=BaseResponse)
async def delete_persona(
    persona_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("personas:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a persona."""
    service = PersonaService(db)
    existing = await service.get_by_id(persona_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    success = await service.soft_delete_persona(persona_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    return {"success": True, "message": "Persona deleted successfully"}


@router.post("/{persona_id}/restore", response_model=BaseResponse)
async def restore_persona(
    persona_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("personas:restore")),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted persona."""
    service = PersonaService(db)
    existing = await service.get_by_id(persona_id, include_deleted=True)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    if existing.get("is_active", False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Persona is not deleted")
    success = await service.restore_persona(persona_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    return {"success": True, "message": "Persona restored successfully"}
