from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Persona import PersonaService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.schemas.Persona import PersonaCreate, PersonaUpdate, PersonaResponse, PersonaStatusUpdate
from typing import Dict, Any

router = APIRouter(prefix="/personas", tags=["Application Personas"])


@router.post("", response_model=BaseResponse)
async def create_persona(
    persona: PersonaCreate,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('personas:create')),
    db: AsyncSession = Depends(get_db)
):
    """Create new persona (Admin only)"""
    service = PersonaService(db)

    persona_id = await service.create(persona.model_dump())

    return {
        "success": True,
        "message": "Persona created successfully",
        "data": {"id": persona_id}
    }


@router.get("")
async def get_all_personas(
    page: int = 1,
    page_size: int = 10,
    order_by: str = "created_at",
    order_direction: str = "desc",
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('personas:read')),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all personas with pagination (Admin, Manager, Operator)

    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 100)
    - order_by: Field to order by (default: created_at)
    - order_direction: Order direction (asc/desc, default: desc)
    """
    service = PersonaService(db)

    # Validate page_size
    if page_size > 100:
        page_size = 100

    user_role = user.get('role', {}).get('name')

    # Admin and Owner can see all personas in their workspace
    if user_role and user_role.lower() in ('admin', 'owner'):
        filters = {"workspace_id": user.get('workspace_id')}
        items, total, total_pages = await service.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            order_by=order_by,
            order_direction=order_direction
        )
    else:
        # Manager and Operator can only see their persona
        persona = await service.get_by_id(user.get('persona_id'))
        items = [persona] if persona else []
        total = len(items)
        total_pages = 1

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
            "has_prev": page > 1
        }
    }


@router.get("/{persona_id}", response_model=BaseResponse)
async def get_persona(
    persona_id: int,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('personas:read')),
    db: AsyncSession = Depends(get_db)
):
    """Get persona details (Admin, Manager, Operator)"""
    service = PersonaService(db)

    persona = await service.get_by_id(persona_id)

    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found"
        )

    return {
        "success": True,
        "message": "Persona retrieved successfully",
        "data": persona
    }


@router.put("/{persona_id}", response_model=BaseResponse)
async def update_persona(
    persona_id: int,
    persona: PersonaUpdate,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('personas:update')),
    db: AsyncSession = Depends(get_db)
):
    """Update persona (Admin only)"""
    service = PersonaService(db)

    success = await service.update(persona_id, persona.model_dump(exclude_unset=True))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found"
        )

    return {
        "success": True,
        "message": "Persona updated successfully"
    }


@router.put("/{persona_id}/status", response_model=BaseResponse)
async def update_persona_status(
    persona_id: int,
    body: PersonaStatusUpdate,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('personas:update')),
    db: AsyncSession = Depends(get_db)
):
    """Toggle persona open/closed status (Owner + Manager)"""
    service = PersonaService(db)

    persona = await service.get_by_id(persona_id)

    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found"
        )

    # Validate the persona belongs to the given workspace
    if persona.get("workspace_id") != body.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Persona does not belong to the specified workspace"
        )

    success = await service.update(persona_id, {"is_open": body.is_open})

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update persona status"
        )

    status_label = "open" if body.is_open else "closed"
    return {
        "success": True,
        "message": f"Persona is now {status_label}"
    }


@router.delete("/{persona_id}", response_model=BaseResponse)
async def delete_persona(
    persona_id: int,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('personas:delete')),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete persona (Admin only) - Data is preserved"""
    service = PersonaService(db)

    success = await service.soft_delete(persona_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found"
        )

    return {
        "success": True,
        "message": "Persona soft deleted successfully (data preserved)"
    }


@router.put("/{persona_id}/restore", response_model=BaseResponse)
async def restore_persona(
    persona_id: int,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('personas:restore')),
    db: AsyncSession = Depends(get_db)
):
    """Restore a soft-deleted persona (Admin only)"""
    service = PersonaService(db)

    # Check if persona exists (including inactive)
    persona = await service.get_by_id(persona_id, include_deleted=True)
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found"
        )

    # is_active=True means active (not deleted); raise error if not deleted
    if persona.get('is_active', True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Persona is not deleted"
        )

    success = await service.restore(persona_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found"
        )

    return {
        "success": True,
        "message": "Persona restored successfully"
    }


@router.get("/{persona_id}/config", response_model=BaseResponse)
async def get_persona_config(
    persona_id: int,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('personas:read')),
    db: AsyncSession = Depends(get_db)
):
    """
    Get persona configuration including order type and UI flow.
    This determines what UI components and flows to show.
    """
    service = PersonaService(db)

    persona = await service.get_by_id(persona_id)

    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found"
        )

    # organization_type is the correct column name (0=RESTAURANT, 1=RETAIL)
    organization_type = persona.get('organization_type', 0)

    # Determine which attributes to show based on organization type
    # 0 = RESTAURANT: Show vegetarian info
    # 1 = RETAIL: Hide food-specific attributes

    if organization_type == 0:  # RESTAURANT
        current_attributes = {
            "show_vegetarian_info": True,
            "attribute_labels": {
                "is_vegetarian": "Vegetarian/Non-Vegetarian"
            }
        }
    else:  # RETAIL (1)
        current_attributes = {
            "show_vegetarian_info": False,
            "attribute_labels": {}
        }

    # Build UI configuration
    ui_config = {
        "organization_type": organization_type,
        "organization_type_name": "RESTAURANT" if organization_type == 0 else "RETAIL",
        "item_attributes": current_attributes
    }

    return {
        "success": True,
        "message": "Persona configuration retrieved successfully",
        "data": ui_config
    }
