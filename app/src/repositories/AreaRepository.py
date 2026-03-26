from src.base.BaseRepository import BaseRepository
from typing import List, Dict, Any, Tuple, Optional

class AreaRepository(BaseRepository):
    """Area repository"""
    
    def __init__(self):
        super().__init__("areas")
    
    def get_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all areas by workspace"""
        return self.get_all(filters={"workspace_id": workspace_id})
    
    def get_paginated_by_workspace(
        self,
        workspace_id: str,
        page: int = 1,
        page_size: int = 10,
        is_available: Optional[bool] = None,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Get paginated areas by workspace"""
        filters = {"workspace_id": workspace_id}
        
        if is_available is not None:
            filters["is_available"] = is_available
        
        return self.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            order_by=order_by,
            order_direction=order_direction
        )
