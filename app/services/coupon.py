"""
Coupon Service
Business logic for coupon management and application
"""
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from fastapi import HTTPException, status

from app.repositories.coupon import CouponRepository
from app.models.coupon import (
    DiscountType, CouponStatus, ApplyCouponResponse, CouponResponseDTO
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class CouponService:
    """Service for coupon operations"""
    
    def __init__(self):
        self.coupon_repo = CouponRepository()
    
    def _calculate_discount(
        self,
        coupon: Dict[str, Any],
        order_amount: float
    ) -> Tuple[float, float]:
        """
        Calculate discount amount and final amount
        
        Args:
            coupon: Coupon data
            order_amount: Original order amount
            
        Returns:
            Tuple of (discount_amount, final_amount)
        """
        discount_type = coupon.get('discount_type')
        discount_value = coupon.get('discount_value', 0)
        max_discount = coupon.get('max_discount_amount')
        
        if discount_type == DiscountType.PERCENTAGE:
            # Calculate percentage discount
            discount_amount = (order_amount * discount_value) / 100
            
            # Apply max discount cap if specified
            if max_discount and discount_amount > max_discount:
                discount_amount = max_discount
                logger.info(f"Discount capped at max amount: {max_discount}")
        
        elif discount_type == DiscountType.FIXED:
            # Fixed amount discount
            discount_amount = discount_value
            
            # Ensure discount doesn't exceed order amount
            if discount_amount > order_amount:
                discount_amount = order_amount
                logger.info(f"Discount capped at order amount: {order_amount}")
        
        else:
            raise ValueError(f"Invalid discount type: {discount_type}")
        
        # Calculate final amount
        final_amount = max(0, order_amount - discount_amount)
        
        return discount_amount, final_amount
    
    def _validate_coupon_basic(self, coupon: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Perform basic coupon validation
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if active
        if not coupon.get('is_active', False):
            return False, "Coupon is inactive"
        
        # Check expiry
        expiry_date = coupon.get('expiry_date')
        if expiry_date and datetime.utcnow() > expiry_date:
            return False, "Coupon has expired"
        
        # Check usage limit
        usage_limit = coupon.get('usage_limit')
        usage_count = coupon.get('usage_count', 0)
        if usage_limit and usage_count >= usage_limit:
            return False, "Coupon usage limit reached"
        
        return True, ""
    
    def _validate_order_amount(
        self,
        coupon: Dict[str, Any],
        order_amount: float
    ) -> Tuple[bool, str]:
        """
        Validate order amount against coupon requirements
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        min_order_amount = coupon.get('min_order_amount')
        
        if min_order_amount and order_amount < min_order_amount:
            return False, f"Minimum order amount of ₹{min_order_amount} required"
        
        return True, ""
    
    async def apply_coupon(
        self,
        coupon_code: str,
        venue_id: str,
        order_amount: float,
        user_id: Optional[str] = None
    ) -> ApplyCouponResponse:
        """
        Apply a coupon and calculate discount
        
        Args:
            coupon_code: Coupon code to apply
            venue_id: Venue ID
            order_amount: Order amount before discount
            user_id: Optional user ID for per-user limit check
            
        Returns:
            ApplyCouponResponse with discount details
        """
        try:
            # Get coupon
            coupon = await self.coupon_repo.get_by_code(coupon_code, venue_id)
            
            if not coupon:
                logger.warning(f"Coupon not found: {coupon_code} for venue: {venue_id}")
                return ApplyCouponResponse(
                    success=False,
                    message="Invalid coupon code",
                    coupon_code=coupon_code
                )
            
            # Basic validation
            is_valid, error_msg = self._validate_coupon_basic(coupon)
            if not is_valid:
                logger.info(f"Coupon validation failed: {error_msg}")
                return ApplyCouponResponse(
                    success=False,
                    message=error_msg,
                    coupon_code=coupon_code
                )
            
            # Validate order amount
            is_valid, error_msg = self._validate_order_amount(coupon, order_amount)
            if not is_valid:
                logger.info(f"Order amount validation failed: {error_msg}")
                return ApplyCouponResponse(
                    success=False,
                    message=error_msg,
                    coupon_code=coupon_code
                )
            
            # Calculate discount
            discount_amount, final_amount = self._calculate_discount(coupon, order_amount)
            savings = discount_amount
            
            # Create coupon response DTO
            coupon_response = CouponResponseDTO(
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
                status=CouponStatus.ACTIVE,
                usage_limit=coupon.get('usage_limit'),
                usage_count=coupon.get('usage_count', 0),
                per_user_limit=coupon.get('per_user_limit'),
                description=coupon.get('description'),
                terms_and_conditions=coupon.get('terms_and_conditions'),
                created_at=coupon['created_at'],
                updated_at=coupon['updated_at'],
                created_by=coupon.get('created_by')
            )
            
            logger.info(
                f"Coupon applied successfully: {coupon_code}, "
                f"discount: ₹{discount_amount:.2f}, final: ₹{final_amount:.2f}"
            )
            
            return ApplyCouponResponse(
                success=True,
                message="Coupon applied successfully",
                coupon_code=coupon['code'],
                discount_type=coupon['discount_type'],
                discount_value=coupon['discount_value'],
                discount_amount=round(discount_amount, 2),
                original_amount=round(order_amount, 2),
                final_amount=round(final_amount, 2),
                savings=round(savings, 2),
                coupon_details=coupon_response
            )
            
        except Exception as e:
            logger.error(f"Error applying coupon: {e}", exc_info=True)
            return ApplyCouponResponse(
                success=False,
                message="Failed to apply coupon",
                coupon_code=coupon_code
            )
    
    async def validate_coupon_for_venue(
        self,
        coupon_code: str,
        venue_id: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Validate if a coupon exists and is valid for a venue
        
        Returns:
            Tuple of (is_valid, message, coupon_data)
        """
        try:
            coupon = await self.coupon_repo.get_by_code(coupon_code, venue_id)
            
            if not coupon:
                return False, "Coupon not found", None
            
            is_valid, error_msg = self._validate_coupon_basic(coupon)
            if not is_valid:
                return False, error_msg, coupon
            
            return True, "Coupon is valid", coupon
            
        except Exception as e:
            logger.error(f"Error validating coupon: {e}", exc_info=True)
            return False, "Error validating coupon", None
    
    async def increment_coupon_usage(self, coupon_id: str) -> bool:
        """
        Increment coupon usage count (call after successful order)
        
        Args:
            coupon_id: Coupon ID
            
        Returns:
            True if successful
        """
        try:
            return await self.coupon_repo.increment_usage_count(coupon_id)
        except Exception as e:
            logger.error(f"Error incrementing coupon usage: {e}", exc_info=True)
            return False


# Global service instance
coupon_service = CouponService()


def get_coupon_service() -> CouponService:
    """Get coupon service instance"""
    return coupon_service