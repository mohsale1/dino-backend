from src.base.BaseService import BaseService
from src.repositories.AreaRepository import AreaRepository
from typing import Dict, Any, List, Tuple, Optional

class AreaService(BaseService):
    """Area service"""
    
    def __init__(self):
        repository = AreaRepository()
        super().__init__(repository)
    
    def create_area(self, data: Dict[str, Any]) -> str:
        """Create new area"""
        result = self.create(data)
        if isinstance(result, dict):
            return result.get('id')
        return result
    
    def get_area_by_id(self, area_id: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """Get area by ID"""
        return self.get_by_id(area_id, include_deleted)
    
    def get_areas_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all areas by workspace"""
        return self.repository.get_by_workspace(workspace_id)
    
    def get_paginated_areas(
        self,
        workspace_id: str,
        page: int = 1,
        page_size: int = 10,
        is_available: Optional[bool] = None,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Get paginated areas"""
        return self.repository.get_paginated_by_workspace(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
            is_available=is_available,
            order_by=order_by,
            order_direction=order_direction
        )
    
    def update_area(self, area_id: str, data: Dict[str, Any]) -> bool:
        """Update area"""
        return self.update(area_id, data)
    
    def soft_delete_area(self, area_id: str) -> bool:
        """Soft delete area"""
        return self.soft_delete(area_id)
    
    def restore_area(self, area_id: str) -> bool:
        """Restore soft-deleted area"""
        return self.restore(area_id)