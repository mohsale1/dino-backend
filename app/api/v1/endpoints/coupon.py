"""
Coupon Management API Endpoints
Endpoints for creating, managing, and applying venue coupons
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
import uuid

from app.models.coupon import (
    CouponCreateDTO, CouponUpdateDTO, CouponResponseDTO,
    ApplyCouponRequest, ApplyCouponResponse, CouponStatus
)
from app.models.requests import ApiResponseDTO, SimpleApiResponseDTO
from app.repositories.coupon import CouponRepository
from app.services.coupon import get_coupon_service
from app.core.security import get_current_user, validate_venue_access
from app.core.logging import get_logger
from app.database.repository_manager import get_venue_repo

logger = get_logger(__name__)
router = APIRouter()


def _convert_to_response_dto(coupon: Dict[str, Any]) -> CouponResponseDTO:
    """Convert coupon dict to response DTO"""
    # Determine status
    if datetime.utcnow() > coupon.get('expiry_date'):
        coupon_status = CouponStatus.EXPIRED
    elif not coupon.get('is_active', False):
        coupon_status = CouponStatus.INACTIVE
    else:
        coupon_status = CouponStatus.ACTIVE
    
    return CouponResponseDTO(
        id=coupon['id'],
        code=coupon['code'],
        venue_id=coupon['venue_id'],
        workspace_id=coupon['workspace_id'],
        discount_type=coupon['discount_type'],
        discount_value=coupon['discount_value'],
        max_discount_amount=coupon.get('max_discount_amount'),
        min_order_amount=coupon.get('min_order_amount'),
        expiry_date=coupon['expiry_date'],
        is_active=coupon['is_active'],
        status=coupon_status,
        usage_limit=coupon.get('usage_limit'),
        usage_count=coupon.get('usage_count', 0),
        per_user_limit=coupon.get('per_user_limit'),
        description=coupon.get('description'),
        terms_and_conditions=coupon.get('terms_and_conditions'),
        created_at=coupon['created_at'],
        updated_at=coupon['updated_at'],
        created_by=coupon.get('created_by')
    )


@router.post("",
             response_model=ApiResponseDTO,
             status_code=status.HTTP_201_CREATED,
             summary="Create coupon",
             description="Create a new coupon for a venue")
async def create_coupon(
    coupon_data: CouponCreateDTO,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new coupon for a venue"""
    try:
        coupon_repo = CouponRepository()
        venue_repo = get_venue_repo()
        
        # Verify venue exists
        venue = await venue_repo.get_by_id(coupon_data.venue_id)
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found"
            )
        
        # Validate venue access
        await validate_venue_access(current_user, coupon_data.venue_id)
        
        # Check if coupon code already exists for this venue
        code_exists = await coupon_repo.check_code_exists(
            coupon_data.code,
            coupon_data.venue_id
        )
        
        if code_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Coupon code '{coupon_data.code}' already exists for this venue"
            )
        
        # Prepare coupon data
        coupon_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        new_coupon = {
            'id': coupon_id,
            'code': coupon_data.code.strip().upper(),
            'venue_id': coupon_data.venue_id,
            'workspace_id': venue.get('workspace_id'),
            'discount_type': coupon_data.discount_type,
            'discount_value': coupon_data.discount_value,
            'max_discount_amount': coupon_data.max_discount_amount,
            'min_order_amount': coupon_data.min_order_amount,
            'expiry_date': coupon_data.expiry_date,
            'is_active': coupon_data.is_active,
            'usage_limit': coupon_data.usage_limit,
            'usage_count': 0,
            'per_user_limit': coupon_data.per_user_limit,
            'description': coupon_data.description,
            'terms_and_conditions': coupon_data.terms_and_conditions,
            'created_at': now,
            'updated_at': now,
            'created_by': current_user['id']
        }
        
        # Create coupon
        created_coupon = await coupon_repo.create(new_coupon, doc_id=coupon_id)
        
        logger.info(
            f"Coupon created: {coupon_data.code} for venue: {coupon_data.venue_id} "
            f"by user: {current_user['id']}"
        )
        
        return ApiResponseDTO(
            success=True,
            message="Coupon created successfully",
            data=_convert_to_response_dto(created_coupon)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating coupon: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create coupon"
        )


@router.get("/venue/{venue_id}",
            response_model=ApiResponseDTO,
            summary="Get venue coupons",
            description="Get all coupons for a specific venue")
async def get_venue_coupons(
    venue_id: str,
    include_inactive: bool = Query(False, description="Include inactive coupons"),
    include_expired: bool = Query(False, description="Include expired coupons"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get all coupons for a venue"""
    try:
        coupon_repo = CouponRepository()
        venue_repo = get_venue_repo()
        
        # Verify venue exists
        venue = await venue_repo.get_by_id(venue_id)
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found"
            )
        
        # Validate venue access
        await validate_venue_access(current_user, venue_id)
        
        # Get coupons
        coupons = await coupon_repo.get_by_venue(venue_id, include_inactive=include_inactive)
        
        # Filter expired coupons if needed
        if not include_expired:
            now = datetime.utcnow()
            coupons = [c for c in coupons if c.get('expiry_date') and c['expiry_date'] > now]
        
        # Convert to response DTOs
        coupon_responses = [_convert_to_response_dto(c) for c in coupons]
        
        logger.info(f"Retrieved {len(coupon_responses)} coupons for venue: {venue_id}")
        
        return ApiResponseDTO(
            success=True,
            message=f"Found {len(coupon_responses)} coupons",
            data={
                "coupons": coupon_responses,
                "total": len(coupon_responses)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting venue coupons: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get venue coupons"
        )


@router.get("/{coupon_id}",
            response_model=ApiResponseDTO,
            summary="Get coupon by ID",
            description="Get a specific coupon by ID")
async def get_coupon(
    coupon_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get a specific coupon by ID"""
    try:
        coupon_repo = CouponRepository()
        
        # Get coupon
        coupon = await coupon_repo.get_by_id(coupon_id)
        if not coupon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Coupon not found"
            )
        
        # Validate venue access
        await validate_venue_access(current_user, coupon['venue_id'])
        
        return ApiResponseDTO(
            success=True,
            message="Coupon retrieved successfully",
            data=_convert_to_response_dto(coupon)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting coupon: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get coupon"
        )


@router.put("/{coupon_id}",
            response_model=ApiResponseDTO,
            summary="Update coupon",
            description="Update an existing coupon")
async def update_coupon(
    coupon_id: str,
    update_data: CouponUpdateDTO,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update an existing coupon"""
    try:
        coupon_repo = CouponRepository()
        
        # Get existing coupon
        coupon = await coupon_repo.get_by_id(coupon_id)
        if not coupon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Coupon not found"
            )
        
        # Validate venue access
        await validate_venue_access(current_user, coupon['venue_id'])
        
        # Prepare update data
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data provided for update"
            )
        
        update_dict['updated_at'] = datetime.utcnow()
        
        # Update coupon
        await coupon_repo.update(coupon_id, update_dict)
        
        # Get updated coupon
        updated_coupon = await coupon_repo.get_by_id(coupon_id)
        
        logger.info(f"Coupon updated: {coupon_id} by user: {current_user['id']}")
        
        return ApiResponseDTO(
            success=True,
            message="Coupon updated successfully",
            data=_convert_to_response_dto(updated_coupon)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating coupon: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update coupon"
        )


@router.delete("/{coupon_id}",
               response_model=SimpleApiResponseDTO,
               summary="Delete coupon",
               description="Delete a coupon (soft delete by setting is_active=false)")
async def delete_coupon(
    coupon_id: str,
    hard_delete: bool = Query(False, description="Permanently delete the coupon"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a coupon"""
    try:
        coupon_repo = CouponRepository()
        
        # Get coupon
        coupon = await coupon_repo.get_by_id(coupon_id)
        if not coupon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Coupon not found"
            )
        
        # Validate venue access
        await validate_venue_access(current_user, coupon['venue_id'])
        
        if hard_delete:
            # Permanently delete
            await coupon_repo.delete(coupon_id)
            message = "Coupon permanently deleted"
            logger.info(f"Coupon hard deleted: {coupon_id} by user: {current_user['id']}")
        else:
            # Soft delete
            await coupon_repo.update(coupon_id, {
                'is_active': False,
                'updated_at': datetime.utcnow()
            })
            message = "Coupon deactivated successfully"
            logger.info(f"Coupon soft deleted: {coupon_id} by user: {current_user['id']}")
        
        return SimpleApiResponseDTO(
            success=True,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting coupon: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete coupon"
        )


@router.post("/apply",
             response_model=ApplyCouponResponse,
             summary="Apply coupon",
             description="Apply a coupon code and calculate discount")
async def apply_coupon(
    request: ApplyCouponRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """
    Apply a coupon code and calculate the discount
    
    This endpoint validates the coupon and returns discount details without
    actually creating an order. Use this to show discount preview to users.
    """
    try:
        venue_repo = get_venue_repo()
        
        # Verify venue exists
        venue = await venue_repo.get_by_id(request.venue_id)
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found"
            )
        
        # Get coupon service
        coupon_service = get_coupon_service()
        
        # Apply coupon
        user_id = request.user_id or (current_user['id'] if current_user else None)
        
        result = await coupon_service.apply_coupon(
            coupon_code=request.coupon_code,
            venue_id=request.venue_id,
            order_amount=request.order_amount,
            user_id=user_id
        )
        
        if result.success:
            logger.info(
                f"Coupon applied: {request.coupon_code} for venue: {request.venue_id}, "
                f"discount: ₹{result.discount_amount}"
            )
        else:
            logger.info(
                f"Coupon application failed: {request.coupon_code} - {result.message}"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying coupon: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply coupon"
        )


@router.post("/validate",
             response_model=ApiResponseDTO,
             summary="Validate coupon",
             description="Check if a coupon code is valid for a venue")
async def validate_coupon(
    coupon_code: str = Query(..., description="Coupon code to validate"),
    venue_id: str = Query(..., description="Venue ID")
):
    """
    Validate if a coupon code is valid for a venue
    
    Public endpoint - no authentication required
    """
    try:
        coupon_service = get_coupon_service()
        
        is_valid, message, coupon_data = await coupon_service.validate_coupon_for_venue(
            coupon_code=coupon_code,
            venue_id=venue_id
        )
        
        response_data = {
            "is_valid": is_valid,
            "message": message
        }
        
        if is_valid and coupon_data:
            response_data["coupon"] = _convert_to_response_dto(coupon_data)
        
        logger.info(f"Coupon validation: {coupon_code} for venue: {venue_id} - {message}")
        
        return ApiResponseDTO(
            success=is_valid,
            message=message,
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"Error validating coupon: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate coupon"
        )


@router.get("/venue/{venue_id}/active",
            response_model=ApiResponseDTO,
            summary="Get active coupons",
            description="Get all active, non-expired coupons for a venue (public)")
async def get_active_coupons(venue_id: str):
    """
    Get all active, non-expired coupons for a venue
    
    Public endpoint - useful for displaying available coupons to customers
    """
    try:
        coupon_repo = CouponRepository()
        venue_repo = get_venue_repo()
        
        # Verify venue exists
        venue = await venue_repo.get_by_id(venue_id)
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found"
            )
        
        # Get active coupons
        coupons = await coupon_repo.get_active_coupons(venue_id)
        
        # Convert to response DTOs
        coupon_responses = [_convert_to_response_dto(c) for c in coupons]
        
        logger.info(f"Retrieved {len(coupon_responses)} active coupons for venue: {venue_id}")
        
        return ApiResponseDTO(
            success=True,
            message=f"Found {len(coupon_responses)} active coupons",
            data={
                "coupons": coupon_responses,
                "total": len(coupon_responses)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting active coupons: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get active coupons"
        )
