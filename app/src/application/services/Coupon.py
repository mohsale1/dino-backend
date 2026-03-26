from src.base.BaseService import BaseService
from src.repositories.CouponRepository import CouponRepository
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

class CouponService(BaseService):
    """Service for Coupon operations"""
    
    def __init__(self):
        super().__init__(CouponRepository())
        self.repo = self.repository
    
    def create_coupon(self, data: Dict[str, Any]) -> str:
        """Create a new coupon"""
        # Check if code already exists in workspace
        existing = self.repo.get_by_code(data['code'], data['workspace_id'])
        if existing:
            raise ValueError(f"Coupon code '{data['code']}' already exists in this workspace")
        
        # Initialize usage count
        data['usage_count'] = 0
        
        # Validate discount value
        if data['discount_type'] == 'percentage' and data['discount_value'] > 100:
            raise ValueError("Percentage discount cannot exceed 100")
        
        return self.create(data)
    
    def get_coupon_by_id(self, coupon_id: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """Get coupon by ID"""
        return self.get_by_id(coupon_id, include_deleted)
    
    def get_coupon_by_code(self, code: str, workspace_id: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """Get coupon by code"""
        return self.repo.get_by_code(code, workspace_id, include_deleted)
    
    def get_paginated_coupons(
        self,
        workspace_id: str,
        page: int = 1,
        page_size: int = 10,
        is_available: Optional[bool] = None,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Get paginated coupons for a workspace"""
        return self.repo.get_by_workspace(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
            is_available=is_available,
            order_by=order_by,
            order_direction=order_direction
        )
    
    def update_coupon(self, coupon_id: str, data: Dict[str, Any]) -> bool:
        """Update coupon"""
        # If updating code, check for duplicates
        if 'code' in data:
            coupon = self.get_by_id(coupon_id)
            if not coupon:
                return False
            
            existing = self.repo.get_by_code(data['code'], coupon['workspace_id'])
            if existing and existing['id'] != coupon_id:
                raise ValueError(f"Coupon code '{data['code']}' already exists in this workspace")
        
        # Validate discount value if updating
        if 'discount_type' in data or 'discount_value' in data:
            coupon = self.get_by_id(coupon_id)
            discount_type = data.get('discount_type', coupon.get('discount_type'))
            discount_value = data.get('discount_value', coupon.get('discount_value'))
            
            if discount_type == 'percentage' and discount_value > 100:
                raise ValueError("Percentage discount cannot exceed 100")
        
        return self.update(coupon_id, data)
    
    def soft_delete_coupon(self, coupon_id: str) -> bool:
        """Soft delete coupon"""
        return self.soft_delete(coupon_id)
    
    def restore_coupon(self, coupon_id: str) -> bool:
        """Restore soft-deleted coupon"""
        return self.restore(coupon_id)
    
    def validate_coupon(self, code: str, workspace_id: str, order_amount: float) -> Dict[str, Any]:
        """
        Validate if a coupon can be applied
        Returns: {valid: bool, message: str, discount_amount: float, coupon: dict}
        """
        coupon = self.repo.get_by_code(code, workspace_id)
        
        if not coupon:
            return {
                "valid": False,
                "message": "Coupon not found",
                "discount_amount": 0,
                "coupon": None
            }
        
        if not coupon.get('is_available', False):
            return {
                "valid": False,
                "message": "Coupon is not available",
                "discount_amount": 0,
                "coupon": coupon
            }
        
        # Check validity dates
        now = datetime.utcnow()
        valid_from = coupon.get('valid_from')
        valid_until = coupon.get('valid_until')
        
        if valid_from and now < valid_from:
            return {
                "valid": False,
                "message": "Coupon is not yet valid",
                "discount_amount": 0,
                "coupon": coupon
            }
        
        if valid_until and now > valid_until:
            return {
                "valid": False,
                "message": "Coupon has expired",
                "discount_amount": 0,
                "coupon": coupon
            }
        
        # Check usage limit
        usage_limit = coupon.get('usage_limit')
        usage_count = coupon.get('usage_count', 0)
        
        if usage_limit and usage_count >= usage_limit:
            return {
                "valid": False,
                "message": "Coupon usage limit reached",
                "discount_amount": 0,
                "coupon": coupon
            }
        
        # Check minimum order amount
        min_order_amount = coupon.get('min_order_amount')
        if min_order_amount and order_amount < min_order_amount:
            return {
                "valid": False,
                "message": f"Minimum order amount of {min_order_amount} required",
                "discount_amount": 0,
                "coupon": coupon
            }
        
        # Calculate discount
        discount_type = coupon.get('discount_type', 'percentage')
        discount_value = coupon.get('discount_value', 0)
        
        if discount_type == 'percentage':
            discount_amount = (order_amount * discount_value) / 100
            max_discount = coupon.get('max_discount_amount')
            if max_discount and discount_amount > max_discount:
                discount_amount = max_discount
        else:  # fixed
            discount_amount = discount_value
        
        # Ensure discount doesn't exceed order amount
        if discount_amount > order_amount:
            discount_amount = order_amount
        
        return {
            "valid": True,
            "message": "Coupon is valid",
            "discount_amount": discount_amount,
            "coupon": coupon
        }
    
    def apply_coupon(self, coupon_id: str) -> bool:
        """Increment usage count when coupon is applied"""
        return self.repo.increment_usage(coupon_id)