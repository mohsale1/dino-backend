from fastapi import APIRouter, HTTPException, status, Depends
from src.base.BaseSchema import BaseResponse
from src.system.middleware.RoleCheck import SystemRoleCheck
from pydantic import BaseModel
from typing import Optional
import secrets
import string

router = APIRouter(prefix="/registration", tags=["System Registration"])

class RegistrationCodeCreate(BaseModel):
    workspace_id: str
    max_uses: Optional[int] = 1
    expires_in_days: Optional[int] = 30

class RegistrationCodeResponse(BaseModel):
    code: str
    workspace_id: str
    max_uses: int
    current_uses: int
    expires_at: str
    is_active: bool

def generate_registration_code(length: int = 12) -> str:
    """Generate random registration code"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

@router.post("/codes", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_marketing_agent)])
async def create_registration_code(request: RegistrationCodeCreate):
    """Create registration code (MarketingAgent, SuperAdmin)"""
    from src.base.BaseRepository import BaseRepository
    from datetime import datetime, timedelta
    
    repo = BaseRepository("registration_codes")
    
    code = generate_registration_code()
    expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
    
    code_data = {
        "code": code,
        "workspace_id": request.workspace_id,
        "max_uses": request.max_uses,
        "current_uses": 0,
        "expires_at": expires_at,
        "is_active": True
    }
    
    code_id = repo.create(code_data)
    
    return {
        "success": True,
        "message": "Registration code created successfully",
        "data": {
            "id": code_id,
            "code": code,
            "expires_at": expires_at.isoformat()
        }
    }

@router.get("/codes", dependencies=[Depends(SystemRoleCheck.require_marketing_agent)])
async def get_all_registration_codes(
    page: int = 1,
    page_size: int = 10,
    order_by: str = "created_at",
    order_direction: str = "desc",
    include_deleted: bool = False
):
    """
    Get all registration codes with pagination (MarketingAgent, SuperAdmin)
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 100)
    - order_by: Field to order by (default: created_at)
    - order_direction: Order direction (asc/desc, default: desc)
    - include_deleted: Include deactivated codes (default: false)
    """
    from src.base.BaseRepository import BaseRepository
    
    repo = BaseRepository("registration_codes")
    
    # Validate page_size
    if page_size > 100:
        page_size = 100
    
    items, total, total_pages = repo.get_paginated(
        page=page,
        page_size=page_size,
        include_deleted=include_deleted,
        order_by=order_by,
        order_direction=order_direction
    )
    
    return {
        "success": True,
        "message": "Registration codes retrieved successfully",
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

@router.get("/codes/{code}", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_marketing_agent)])
async def get_registration_code(code: str):
    """Get registration code details (MarketingAgent, SuperAdmin)"""
    from src.base.BaseRepository import BaseRepository
    
    repo = BaseRepository("registration_codes")
    
    code_data = repo.get_by_field("code", code)
    
    if not code_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration code not found"
        )
    
    return {
        "success": True,
        "message": "Registration code retrieved successfully",
        "data": code_data
    }

@router.delete("/codes/{code_id}", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_marketing_agent)])
async def deactivate_registration_code(code_id: str):
    """Soft delete registration code (MarketingAgent, SuperAdmin) - Data is preserved"""
    from src.base.BaseRepository import BaseRepository
    
    repo = BaseRepository("registration_codes")
    
    success = repo.soft_delete(code_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration code not found"
        )
    
    return {
        "success": True,
        "message": "Registration code soft deleted successfully (data preserved)"
    }

@router.put("/codes/{code_id}/restore", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_marketing_agent)])
async def restore_registration_code(code_id: str):
    """Restore a soft-deleted registration code (MarketingAgent, SuperAdmin)"""
    from src.base.BaseRepository import BaseRepository
    
    repo = BaseRepository("registration_codes")
    
    # Check if code exists (including deleted)
    code = repo.get_by_id(code_id, include_deleted=True)
    if not code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration code not found"
        )
    
    if not code.get('is_deleted', False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration code is not deleted"
        )
    
    success = repo.restore(code_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration code not found"
        )
    
    return {
        "success": True,
        "message": "Registration code restored successfully"
    }

@router.get("/stats", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_marketing_agent)])
async def get_registration_stats():
    """Get registration code statistics (MarketingAgent, SuperAdmin)"""
    from src.base.BaseRepository import BaseRepository
    
    repo = BaseRepository("registration_codes")
    
    # Get all codes (including deleted for total count)
    all_codes = repo.get_all(include_deleted=True)
    active_codes = [c for c in all_codes if not c.get('is_deleted', False) and c.get('is_active', True)]
    expired_codes = [c for c in all_codes if not c.get('is_deleted', False) and not c.get('is_active', False)]
    
    total_uses = sum(c.get('current_uses', 0) for c in all_codes)
    
    stats = {
        "total_codes": len(all_codes),
        "active_codes": len(active_codes),
        "expired_codes": len(expired_codes),
        "total_uses": total_uses
    }
    
    return {
        "success": True,
        "message": "Registration statistics retrieved successfully",
        "data": stats
    }

class RegistrationCodeUpdate(BaseModel):
    max_uses: Optional[int] = None
    expires_in_days: Optional[int] = None
    is_active: Optional[bool] = None

@router.put("/codes/{code_id}", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_marketing_agent)])
async def update_registration_code(code_id: str, request: RegistrationCodeUpdate):
    """Update registration code (MarketingAgent, SuperAdmin)"""
    from src.base.BaseRepository import BaseRepository
    from datetime import datetime, timedelta
    
    repo = BaseRepository("registration_codes")
    
    # Check if code exists
    code = repo.get_by_id(code_id)
    if not code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration code not found"
        )
    
    update_data = {}
    if request.max_uses is not None:
        update_data['max_uses'] = request.max_uses
    if request.expires_in_days is not None:
        update_data['expires_at'] = datetime.utcnow() + timedelta(days=request.expires_in_days)
    if request.is_active is not None:
        update_data['is_active'] = request.is_active
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update data provided"
        )
    
    success = repo.update(code_id, update_data)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration code not found"
        )
    
    return {
        "success": True,
        "message": "Registration code updated successfully"
    }
