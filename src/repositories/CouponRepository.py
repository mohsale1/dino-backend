from src.base.BaseRepository import BaseRepository
from typing import Optional, List, Dict, Any, Tuple
from google.cloud.firestore_v1 import FieldFilter
from google.cloud import firestore


class CouponRepository(BaseRepository):
    """Repository for Coupon operations"""

    def __init__(self):
        super().__init__("coupons")

    def get_by_code(self, code: str, workspace_id: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """Get coupon by code and workspace"""
        query = self.collection.where(filter=FieldFilter("code", "==", code))
        query = query.where(filter=FieldFilter("workspace_id", "==", workspace_id))

        if not include_deleted:
            query = query.where(filter=FieldFilter("is_deleted", "==", False))

        docs = query.limit(1).get()
        if docs:
            return docs[0].to_dict()
        return None

    def get_by_workspace(
        self,
        workspace_id: str,
        page: int = 1,
        page_size: int = 10,
        is_available: Optional[bool] = None,
        order_by: str = "created_at",
        order_direction: str = "desc",
        include_deleted: bool = False
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Get coupons by workspace with pagination"""
        filters = {"workspace_id": workspace_id}

        if is_available is not None:
            filters["is_available"] = is_available

        return self.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            include_deleted=include_deleted,
            order_by=order_by,
            order_direction=order_direction
        )

    def increment_usage(self, coupon_id: str) -> bool:
        """Atomically increment usage count for a coupon"""
        try:
            self.collection.document(coupon_id).update({'usage_count': firestore.Increment(1)})
            return True
        except Exception:
            return False