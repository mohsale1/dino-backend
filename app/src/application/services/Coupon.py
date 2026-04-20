from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.repositories.CouponRepository import CouponRepository


class CouponService(BaseService):
    """Service for Coupon operations"""

    def __init__(self, db: AsyncSession):
        super().__init__(CouponRepository(db))
        self.repo = self.repository

    async def create_coupon(self, data: Dict[str, Any]) -> str:
        """Create a new coupon"""
        # Check if code already exists in workspace
        existing = await self.repo.get_by_code(data["code"], data["workspace_id"])
        if existing:
            raise ValueError(
                f"Coupon code '{data['code']}' already exists in this workspace"
            )

        data["usage_count"] = 0

        discount_value = data.get("discount_value", 0)
        if discount_value < 0:
            raise ValueError("Discount value cannot be negative")

        if data.get("discount_type") == "percentage" and discount_value > 100:
            raise ValueError("Percentage discount cannot exceed 100")

        valid_from = data.get("valid_from")
        valid_until = data.get("valid_until")
        if valid_from is not None and valid_until is not None:
            if valid_from >= valid_until:
                raise ValueError("valid_from must be earlier than valid_until")

        result = await self.create(data)
        return result["id"]

    async def get_coupon_by_id(
        self, coupon_id: str, include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get coupon by ID"""
        return await self.get_by_id(coupon_id, include_deleted)

    async def get_coupon_by_code(
        self,
        code: str,
        workspace_id: str,
        include_deleted: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Get coupon by code"""
        return await self.repo.get_by_code(code, workspace_id, include_deleted)

    async def get_paginated_coupons(
        self,
        workspace_id: str,
        page: int = 1,
        page_size: int = 10,
        is_available: Optional[bool] = None,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Get paginated coupons for a workspace"""
        return await self.repo.get_by_workspace(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
            is_available=is_available,
            order_by=order_by,
            order_direction=order_direction,
        )

    async def update_coupon(self, coupon_id: str, data: Dict[str, Any]) -> bool:
        """
        Update coupon fields.

        Fetches the coupon exactly once and reuses the result for all
        subsequent checks, avoiding redundant round-trips.  Returns False
        when the coupon does not exist.
        """
        # Single fetch — reused for every validation below.
        coupon = await self.get_by_id(coupon_id)
        if coupon is None:
            return False

        if "code" in data:
            existing = await self.repo.get_by_code(data["code"], coupon["workspace_id"])
            if existing and existing["id"] != coupon_id:
                raise ValueError(
                    f"Coupon code '{data['code']}' already exists in this workspace"
                )

        if "discount_type" in data or "discount_value" in data:
            discount_type = data.get("discount_type", coupon.get("discount_type"))
            discount_value = data.get("discount_value", coupon.get("discount_value", 0))

            if discount_type == "percentage" and (discount_value or 0) > 100:
                raise ValueError("Percentage discount cannot exceed 100")

        return await self.update(coupon_id, data)

    async def soft_delete_coupon(self, coupon_id: str) -> bool:
        """Soft delete coupon"""
        return await self.soft_delete(coupon_id)

    async def restore_coupon(self, coupon_id: str) -> bool:
        """Restore soft-deleted coupon"""
        return await self.restore(coupon_id)

    def _ensure_tz_aware(self, dt: Any) -> Optional[datetime]:
        """
        Return *dt* as a timezone-aware datetime, or None when conversion fails.

        Handles datetime objects (naive or aware) and ISO-8601 strings.
        Naive values are assumed to be UTC.
        """
        if dt is None:
            return None
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt)
            except ValueError:
                return None
        if isinstance(dt, datetime):
            return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        return None

    def _calculate_discount(self, coupon: Dict[str, Any], order_amount: float) -> float:
        """Compute the discount amount for *order_amount* given *coupon* rules."""
        discount_type = coupon.get("discount_type", "percentage")
        discount_value = float(coupon.get("discount_value") or 0)

        if discount_type == "percentage":
            discount_amount = (order_amount * discount_value) / 100
            max_discount = coupon.get("max_discount_amount")
            if max_discount is not None and discount_amount > float(max_discount):
                discount_amount = float(max_discount)
        else:  # fixed
            discount_amount = discount_value

        # Discount cannot exceed the order total.
        return min(discount_amount, order_amount)

    async def validate_coupon(
        self, code: str, workspace_id: str, order_amount: float
    ) -> Dict[str, Any]:
        """
        Validate whether a coupon can be applied WITHOUT consuming a use.

        This method is read-only and safe to call for preview/UI purposes.
        To atomically validate AND consume a use in a single DB round-trip,
        call `apply_coupon` instead.

        Timezone safety: all datetime comparisons use timezone-aware values.
        """
        coupon = await self.repo.get_by_code(code, workspace_id)

        if not coupon:
            return {
                "valid": False,
                "message": "Coupon not found",
                "discount_amount": 0,
                "coupon": None,
            }

        if not coupon.get("is_available", False):
            return {
                "valid": False,
                "message": "Coupon is not available",
                "discount_amount": 0,
                "coupon": coupon,
            }

        now = datetime.now(timezone.utc)

        valid_from = self._ensure_tz_aware(coupon.get("valid_from"))
        valid_until = self._ensure_tz_aware(coupon.get("valid_until"))

        if valid_from is not None and now < valid_from:
            return {
                "valid": False,
                "message": "Coupon is not yet valid",
                "discount_amount": 0,
                "coupon": coupon,
            }

        if valid_until is not None and now > valid_until:
            return {
                "valid": False,
                "message": "Coupon has expired",
                "discount_amount": 0,
                "coupon": coupon,
            }

        usage_limit = coupon.get("usage_limit")
        usage_count = coupon.get("usage_count", 0)
        if usage_limit is not None and usage_count >= usage_limit:
            return {
                "valid": False,
                "message": "Coupon usage limit reached",
                "discount_amount": 0,
                "coupon": coupon,
            }

        min_order_amount = coupon.get("min_order_amount")
        if min_order_amount is not None and order_amount < float(min_order_amount):
            return {
                "valid": False,
                "message": f"Minimum order amount of {min_order_amount} required",
                "discount_amount": 0,
                "coupon": coupon,
            }

        discount_amount = self._calculate_discount(coupon, order_amount)

        return {
            "valid": True,
            "message": "Coupon is valid",
            "discount_amount": discount_amount,
            "coupon": coupon,
        }

    async def apply_coupon(
        self, code: str, workspace_id: str, order_amount: float
    ) -> Dict[str, Any]:
        """
        Atomically validate and consume one coupon use.

        Issues a single conditional UPDATE … RETURNING to the database,
        eliminating the TOCTOU race that exists when validate_coupon and a
        separate increment are called sequentially.

        Returns the same shape as validate_coupon so callers can treat both
        methods uniformly:
            {valid, message, discount_amount, coupon}

        When the coupon is invalid, exhausted, inactive, or outside its
        validity window, no row is updated and valid=False is returned.
        """
        updated_coupon = await self.repo.validate_and_apply(
            code, workspace_id, order_amount
        )

        if updated_coupon is None:
            # The UPDATE matched nothing — determine a helpful message by
            # doing a read-only lookup (best-effort; no race concern here
            # because we are only building a user-facing error message).
            coupon = await self.repo.get_by_code(code, workspace_id, include_deleted=True)
            if coupon is None:
                message = "Coupon not found"
            elif not coupon.get("is_available", False):
                message = "Coupon is not available"
            else:
                usage_limit = coupon.get("usage_limit")
                usage_count = coupon.get("usage_count", 0)
                min_order_amount = coupon.get("min_order_amount")
                if usage_limit is not None and usage_count >= usage_limit:
                    message = "Coupon usage limit reached"
                elif min_order_amount is not None and order_amount < float(min_order_amount):
                    message = f"Minimum order amount of {min_order_amount} required"
                else:
                    message = "Coupon is not valid or has expired"

            return {
                "valid": False,
                "message": message,
                "discount_amount": 0,
                "coupon": coupon,
            }

        discount_amount = self._calculate_discount(updated_coupon, order_amount)

        return {
            "valid": True,
            "message": "Coupon applied successfully",
            "discount_amount": discount_amount,
            "coupon": updated_coupon,
        }
