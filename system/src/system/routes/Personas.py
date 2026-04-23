from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.schemas.Persona import PersonaCreate, PersonaUpdate
from src.system.middleware.RoleCheck import SystemPermissionCheck
from src.system.services.Persona import PersonaService

router = APIRouter(prefix="/personas", tags=["System Personas"])


@router.get(
    "",
    dependencies=[Depends(SystemPermissionCheck.require("personas:read"))],
)
async def get_personas(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    workspace_id: Optional[int] = Query(None),
    include_deleted: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated personas."""
    service = PersonaService(db)
    items, total, total_pages = await service.get_paginated_personas(
        workspace_id=workspace_id,
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


@router.post(
    "",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("personas:create"))],
)
async def create_persona(persona: PersonaCreate, db: AsyncSession = Depends(get_db)):
    """Create a new persona."""
    service = PersonaService(db)
    created = await service.create_persona(persona.model_dump())
    return {
        "success": True,
        "message": "Persona created successfully",
        "data": {"id": created.get("id")},
    }


@router.get(
    "/{persona_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("personas:read"))],
)
async def get_persona(persona_id: int, db: AsyncSession = Depends(get_db)):
    """Get persona details."""
    service = PersonaService(db)
    persona = await service.get_by_id(persona_id)
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    return {"success": True, "message": "Persona retrieved successfully", "data": persona}


@router.put(
    "/{persona_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("personas:update"))],
)
async def update_persona(
    persona_id: int, persona: PersonaUpdate, db: AsyncSession = Depends(get_db)
):
    """Update persona."""
    service = PersonaService(db)
    success = await service.update_persona(persona_id, persona.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    return {"success": True, "message": "Persona updated successfully"}


@router.delete(
    "/{persona_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("personas:delete"))],
)
async def delete_persona(persona_id: int, db: AsyncSession = Depends(get_db)):
    """Soft delete persona."""
    service = PersonaService(db)
    success = await service.soft_delete_persona(persona_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    return {"success": True, "message": "Persona deleted successfully"}


@router.post(
    "/{persona_id}/restore",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("personas:update"))],
)
async def restore_persona(persona_id: int, db: AsyncSession = Depends(get_db)):
    """Restore a soft-deleted persona."""
    service = PersonaService(db)
    persona = await service.get_by_id(persona_id, include_deleted=True)
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    if persona.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Persona is not deleted",
        )
    success = await service.restore_persona(persona_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    return {"success": True, "message": "Persona restored successfully"}


@router.put(
    "/{persona_id}/status",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("personas:update"))],
)
async def toggle_persona_status(
    persona_id: int,
    is_open: bool = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
):
    """Toggle persona open/closed status."""
    service = PersonaService(db)
    success = await service.toggle_open(persona_id, is_open)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    return {"success": True, "message": f"Persona {'opened' if is_open else 'closed'} successfully"}


@router.put(
    "/{persona_id}/deactivate",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("personas:update"))],
)
async def deactivate_persona(persona_id: int, db: AsyncSession = Depends(get_db)):
    """Billing suspension: deactivate persona."""
    service = PersonaService(db)
    success = await service.deactivate_persona(persona_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    return {"success": True, "message": "Persona deactivated (billing suspension)"}


@router.put(
    "/{persona_id}/reactivate",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("personas:update"))],
)
async def reactivate_persona(persona_id: int, db: AsyncSession = Depends(get_db)):
    """Lift billing suspension: reactivate persona."""
    service = PersonaService(db)
    success = await service.reactivate_persona(persona_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    return {"success": True, "message": "Persona reactivated successfully"}
