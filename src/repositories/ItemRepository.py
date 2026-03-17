from src.base.BaseRepository import BaseRepository
from typing import List, Dict, Any, Tuple, Optional

class ItemRepository(BaseRepository):
    """Item repository"""
    
    def __init__(self):
        super().__init__("items")
    
    def get_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all items by workspace"""
        return self.get_all(filters={"workspace_id": workspace_id})
    
    def get_by_category(self, category_id: str) -> List[Dict[str, Any]]:
        """Get all items by category"""
        return self.get_all(filters={"category_id": category_id})
    
    def get_paginated_by_workspace(
        self,
        workspace_id: str,
        page: int = 1,
        page_size: int = 10,
        category_id: Optional[str] = None,
        is_available: Optional[bool] = None,
        is_vegetarian: Optional[bool] = None,
        search_query: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Get paginated items by workspace with filters"""
        filters = {"workspace_id": workspace_id}
        
        if category_id:
            filters["category_id"] = category_id
        
        if is_available is not None:
            filters["is_available"] = is_available
        
        if is_vegetarian is not None:
            filters["is_vegetarian"] = is_vegetarian
        
        # Get paginated results
        items, total, total_pages = self.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            order_by=order_by,
            order_direction=order_direction
        )
        
        # Apply search filter in memory (Firestore limitation)
        if search_query:
            search_lower = search_query.lower()
            items = [
                item for item in items
                if search_lower in item.get('name', '').lower() or
                   search_lower in item.get('description', '').lower()
            ]
            total = len(items)
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        return items, total, total_pages