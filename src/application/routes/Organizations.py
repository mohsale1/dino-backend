from fastapi import APIRouter, HTTPException, status, Depends
from src.schemas.Organization import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse
)
from src.application.services.Organization import OrganizationService
from src.base.BaseSchema import BaseResponse
from src.application.middleware.RoleCheck import ApplicationRoleCheck
from typing import Dict, Any

router = APIRouter(prefix="/organizations", tags=["Application Organizations"])

@router.post("", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def create_organization(organization: OrganizationCreate):
    """Create new organization (Admin only)"""
    service = OrganizationService()
    
    org_id = service.create(organization.model_dump())
    
    return {
        "success": True,
        "message": "Organization created successfully",
        "data": {"id": org_id}
    }

@router.get("", dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_all_organizations(
    page: int = 1,
    page_size: int = 10,
    order_by: str = "created_at",
    order_direction: str = "desc",
    user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_operator)
):
    """
    Get all organizations with pagination (Admin, Manager, Operator)
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 100)
    - order_by: Field to order by (default: created_at)
    - order_direction: Order direction (asc/desc, default: desc)
    """
    service = OrganizationService()
    
    # Validate page_size
    if page_size > 100:
        page_size = 100
    
    user_role = user.get('role', {}).get('name')
    
    if user_role == 'Admin':
        # Admin can see all organizations in their workspace
        filters = {"workspace_id": user.get('workspace_id')}
        items, total, total_pages = service.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            order_by=order_by,
            order_direction=order_direction
        )
    else:
        # Manager and Operator can only see their organization
        org = service.get_by_id(user.get('organization_id'))
        items = [org] if org else []
        total = len(items)
        total_pages = 1
    
    return {
        "success": True,
        "message": "Organizations retrieved successfully",
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

@router.get("/{organization_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_organization(organization_id: str, user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_operator)):
    """Get organization details (Admin, Manager, Operator)"""
    service = OrganizationService()
    
    organization = service.get_by_id(organization_id)
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check access
    user_role = user.get('role', {}).get('name')
    
    if user_role in ['Manager', 'Operator']:
        if organization.get('id') != user.get('organization_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization"
            )
    
    return {
        "success": True,
        "message": "Organization retrieved successfully",
        "data": organization
    }

@router.put("/{organization_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def update_organization(organization_id: str, organization: OrganizationUpdate):
    """Update organization (Admin only)"""
    service = OrganizationService()
    
    success = service.update(organization_id, organization.model_dump(exclude_unset=True))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return {
        "success": True,
        "message": "Organization updated successfully"
    }

@router.delete("/{organization_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def delete_organization(organization_id: str):
    """Soft delete organization (Admin only) - Data is preserved"""
    service = OrganizationService()
    
    success = service.soft_delete(organization_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return {
        "success": True,
        "message": "Organization soft deleted successfully (data preserved)"
    }

@router.put("/{organization_id}/restore", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def restore_organization(organization_id: str):
    """Restore a soft-deleted organization (Admin only)"""
    service = OrganizationService()
    
    # Check if organization exists (including deleted)
    organization = service.get_by_id(organization_id, include_deleted=True)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    if not organization.get('is_deleted', False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization is not deleted"
        )
    
    success = service.restore(organization_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return {
        "success": True,
        "message": "Organization restored successfully"
    }


@router.get("/{organization_id}/config", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_organization_config(organization_id: str):
    """
    Get organization configuration including order type and UI flow
    This determines what UI components and flows to show
    """
    service = OrganizationService()
    
    organization = service.get_by_id(organization_id)
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Organization only has industry_type now (0=RESTAURANT, 1=RETAIL)
    industry_type = organization.get('industry_type', 0)
    
    # Determine which attributes to show based on industry type
    # 0 = RESTAURANT: Show vegetarian info
    # 1 = RETAIL: Hide food-specific attributes
    
    if industry_type == 0:  # RESTAURANT
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
        "industry_type": industry_type,
        "industry_type_name": "RESTAURANT" if industry_type == 0 else "RETAIL",
        "item_attributes": current_attributes
    }
    
    return {
        "success": True,
        "message": "Organization configuration retrieved successfully",
        "data": ui_config
    }