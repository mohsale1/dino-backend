"""
System Personas Routes
Endpoints for managing personas from the system (SuperAdmin) perspective.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.repositories.PersonaRepository import PersonaRepository
from src.system.middleware.RoleCheck import SystemPermissionCheck

router = APIRouter(prefix="/personas", tags=["System Personas"])


# ---------------------------------------------------------------------------
# GET /personas
# ---------------------------------------------------------------------------

@router.get("", dependencies=[Depends(SystemPermissionCheck.require('personas:read'))])
async def get_all_personas(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    workspace_id: Optional[int] = Query(None, description="Filter by workspace"),
    order_by: str = Query("created_at", description="Field to order by"),
    order_direction: str = Query("desc", description="Order direction (asc/desc)"),
    include_inactive: bool = Query(False, description="Include inactive personas"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all personas with pagination (SuperAdmin only).

    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 100)
    - workspace_id: Filter by workspace
    - order_by: Field to order by (default: created_at)
    - order_direction: Order direction (asc/desc, default: desc)
    - include_inactive: Include inactive personas (default: false)
    """
    if page_size > 100:
        page_size = 100

    repo = PersonaRepository(db)

    filters: Dict[str, Any] = {}
    if workspace_id is not None:
        filters["workspace_id"] = workspace_id
    if not include_inactive:
        filters["is_active"] = True

    items, total, total_pages = await repo.get_paginated(
        page=page,
        page_size=page_size,
        filters=filters,
        order_by=order_by,
        order_direction=order_direction,
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
# GET /personas/workspace/{workspace_id}
# Must be declared BEFORE GET /{persona_id} to avoid route shadowing.
# ---------------------------------------------------------------------------

@router.get("/workspace/{workspace_id}", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('personas:read'))])
async def get_personas_by_workspace(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get all personas belonging to a specific workspace (SuperAdmin only)."""
    repo = PersonaRepository(db)
    personas = await repo.get_by_workspace(workspace_id)

    return {
        "success": True,
        "message": "Personas retrieved successfully",
        "data": personas,
    }


# ---------------------------------------------------------------------------
# GET /personas/{persona_id}
# ---------------------------------------------------------------------------

@router.get("/{persona_id}", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('personas:read'))])
async def get_persona(
    persona_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get persona details by ID (SuperAdmin only)."""
    repo = PersonaRepository(db)
    persona = await repo.get_by_id(persona_id)

    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found",
        )

    return {
        "success": True,
        "message": "Persona retrieved successfully",
        "data": persona,
    }


# ---------------------------------------------------------------------------
# PUT /personas/{persona_id}/restore
# Must be declared BEFORE PUT /{persona_id} to avoid route shadowing.
# ---------------------------------------------------------------------------

@router.put("/{persona_id}/restore", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('personas:restore'))])
async def restore_persona(
    persona_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Restore an inactive persona (SuperAdmin only)."""
    repo = PersonaRepository(db)

    persona = await repo.get_by_id(persona_id)
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found",
        )

    if persona.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Persona is already active",
        )

    success = await repo.update(persona_id, {"is_active": True})

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found",
        )

    return {
        "success": True,
        "message": "Persona restored successfully",
    }


# ---------------------------------------------------------------------------
# PUT /personas/{persona_id}
# ---------------------------------------------------------------------------

@router.put("/{persona_id}", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('personas:update'))])
async def update_persona(
    persona_id: int,
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    """Update persona details (SuperAdmin only)."""
    repo = PersonaRepository(db)

    existing = await repo.get_by_id(persona_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found",
        )

    success = await repo.update(persona_id, data)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found",
        )

    return {
        "success": True,
        "message": "Persona updated successfully",
    }


# ---------------------------------------------------------------------------
# DELETE /personas/{persona_id}
# ---------------------------------------------------------------------------

@router.delete("/{persona_id}", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('personas:delete'))])
async def delete_persona(
    persona_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Deactivate persona (SuperAdmin only) — data is preserved."""
    repo = PersonaRepository(db)

    existing = await repo.get_by_id(persona_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found",
        )

    success = await repo.update(persona_id, {"is_active": False})

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found",
        )

    return {
        "success": True,
        "message": "Persona deactivated successfully (data preserved)",
    }
