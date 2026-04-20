from src.base.BaseRepository import BaseRepository
from typing import Optional, List, Dict, Any, Tuple

class OrderRepository(BaseRepository):
    """Order repository"""
    
    def __init__(self):
        super().__init__("orders")
    
    def get_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all orders by workspace"""
        return self.get_all(filters={"workspace_id": workspace_id})
    
    def get_by_organization(self, organization_id: str) -> List[Dict[str, Any]]:
        """Get all orders by organization"""
        return self.get_all(filters={"organization_id": organization_id})
    
    def get_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all orders by status"""
        return self.get_all(filters={"status": status})

    def get_paginated_by_workspace(
        self,
        workspace_id: str,
        page: int = 1,
        page_size: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = "created_at",
        order_direction: str = "desc",
        include_deleted: bool = False
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Get paginated orders scoped to a specific workspace"""
        scoped_filters = {"workspace_id": workspace_id}
        if filters:
            scoped_filters.update(filters)

        return self.get_paginated(
            page=page,
            page_size=page_size,
            filters=scoped_filters,
            include_deleted=include_deleted,
            order_by=order_by,
            order_direction=order_direction
        )

    def get_paginated_by_organization(
        self,
        organization_id: str,
        page: int = 1,
        page_size: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = "created_at",
        order_direction: str = "desc",
        include_deleted: bool = False
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Get paginated orders scoped to a specific organization"""
        scoped_filters = {"organization_id": organization_id}
        if filters:
            scoped_filters.update(filters)

        return self.get_paginated(
            page=page,
            page_size=page_size,
            filters=scoped_filters,
            include_deleted=include_deleted,
            order_by=order_by,
            order_direction=order_direction
        )
