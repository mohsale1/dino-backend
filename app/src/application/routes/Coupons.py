from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.Coupon import CouponCreate, CouponUpdate, CouponResponse
from src.application.services.Coupon import CouponService
from src.base.BaseSchema import BaseResponse
from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.config.Database import get_db
from typing import Optional
from pydantic import BaseModel

router = APIRouter(prefix="/coupons", tags=["Application Coupons"])


class ValidateCouponRequest(BaseModel):
    """Validate coupon request"""
    code: str
    workspace_id: int
    order_amount: float


# ==================== COLLECTION ENDPOINTS ====================

@router.post("", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('coupons:create'))])
async def create_coupon(
    coupon: CouponCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create new coupon (Admin only)"""
    service = CouponService(db)

    try:
        coupon_id = await service.create_coupon(coupon.model_dump())

        return {
            "success": True,
            "message": "Coupon created successfully",
            "data": {"id": coupon_id}
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", dependencies=[Depends(ApplicationPermissionCheck.require('coupons:read'))])
async def get_all_coupons(
    workspace_id: int = Query(..., description="Workspace ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    is_available: Optional[bool] = Query(None, description="Filter by availability"),
    order_by: str = Query("created_at", description="Field to order by"),
    order_direction: str = Query("desc", description="Order direction (asc/desc)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all coupons with pagination

    Query Parameters:
    - workspace_id: Workspace ID (required)
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 100)
    - is_available: Filter by availability
    - order_by: Field to order by (default: created_at)
    - order_direction: Order direction (asc/desc, default: desc)
    """
    service = CouponService(db)

    if page_size > 100:
        page_size = 100

    items, total, total_pages = await service.get_paginated_coupons(
        workspace_id=workspace_id,
        page=page,
        page_size=page_size,
        is_available=is_available,
        order_by=order_by,
        order_direction=order_direction
    )

    return {
        "success": True,
        "message": "Coupons retrieved successfully",
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


# ==================== STATIC-PATH ENDPOINTS (must be BEFORE /{coupon_id}) ====================

@router.get("/code/{code}", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('coupons:read'))])
async def get_coupon_by_code(
    code: str,
    workspace_id: int = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get coupon by code"""
    service = CouponService(db)

    coupon = await service.get_coupon_by_code(code, workspace_id)

    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found"
        )

    return {
        "success": True,
        "message": "Coupon retrieved successfully",
        "data": coupon
    }


@router.post("/validate", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('coupons:read'))])
async def validate_coupon(
    request: ValidateCouponRequest,
    db: AsyncSession = Depends(get_db)
):
    """Validate if a coupon can be applied to an order"""
    service = CouponService(db)

    result = await service.validate_coupon(
        code=request.code,
        workspace_id=request.workspace_id,
        order_amount=request.order_amount
    )

    return {
        "success": result["valid"],
        "message": result["message"],
        "data": {
            "valid": result["valid"],
            "discount_amount": result["discount_amount"],
            "coupon": result["coupon"]
        }
    }


# ==================== COUPON-SCOPED ENDPOINTS (/{coupon_id}) ====================

@router.get("/{coupon_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('coupons:read'))])
async def get_coupon(
    coupon_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get coupon by ID"""
    service = CouponService(db)

    coupon = await service.get_coupon_by_id(coupon_id)

    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found"
        )

    return {
        "success": True,
        "message": "Coupon retrieved successfully",
        "data": coupon
    }


@router.put("/{coupon_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('coupons:update'))])
async def update_coupon(
    coupon_id: int,
    coupon: CouponUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update coupon (Admin only)"""
    service = CouponService(db)

    existing_coupon = await service.get_coupon_by_id(coupon_id)
    if not existing_coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found"
        )

    try:
        success = await service.update_coupon(coupon_id, coupon.model_dump(exclude_unset=True))

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Coupon not found"
            )

        return {
            "success": True,
            "message": "Coupon updated successfully"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{coupon_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('coupons:delete'))])
async def delete_coupon(
    coupon_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Soft delete coupon (Admin only)"""
    service = CouponService(db)

    coupon = await service.get_coupon_by_id(coupon_id)
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found"
        )

    success = await service.soft_delete_coupon(coupon_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found"
        )

    return {
        "success": True,
        "message": "Coupon soft deleted successfully"
    }


@router.put("/{coupon_id}/restore", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('coupons:restore'))])
async def restore_coupon(
    coupon_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Restore soft-deleted coupon (Admin only)"""
    service = CouponService(db)

    coupon = await service.get_coupon_by_id(coupon_id, include_deleted=True)
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found"
        )

    if coupon.get('is_active', True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coupon is not deleted"
        )

    success = await service.restore_coupon(coupon_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found"
        )

    return {
        "success": True,
        "message": "Coupon restored successfully"
    }


@router.post("/{coupon_id}/apply", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('coupons:update'))])
async def apply_coupon(
    coupon_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Increment usage count when coupon is applied"""
    service = CouponService(db)

    coupon = await service.get_coupon_by_id(coupon_id)
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found"
        )

    success = await service.apply_coupon(coupon_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply coupon"
        )

    return {
        "success": True,
        "message": "Coupon applied successfully"
    }
