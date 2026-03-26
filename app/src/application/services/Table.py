from src.base.BaseService import BaseService
from src.repositories.TableRepository import TableRepository
from typing import Dict, Any, List, Tuple, Optional

class TableService(BaseService):
    """Table service"""
    
    def __init__(self):
        repository = TableRepository()
        super().__init__(repository)
    
    def create_table(self, data: Dict[str, Any]) -> str:
        """Create new table"""
        result = self.create(data)
        if isinstance(result, dict):
            return result.get('id')
        return result
    
    def get_table_by_id(self, table_id: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """Get table by ID"""
        return self.get_by_id(table_id, include_deleted)
    
    def get_tables_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all tables by workspace"""
        return self.repository.get_by_workspace(workspace_id)
    
    def get_tables_by_area(self, area_id: str) -> List[Dict[str, Any]]:
        """Get all tables by area"""
        return self.repository.get_by_area(area_id)
    
    def get_paginated_tables(
        self,
        workspace_id: str,
        page: int = 1,
        page_size: int = 10,
        area_id: Optional[str] = None,
        status: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Get paginated tables"""
        return self.repository.get_paginated_by_workspace(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
            area_id=area_id,
            status=status,
            order_by=order_by,
            order_direction=order_direction
        )
    
    def update_table(self, table_id: str, data: Dict[str, Any]) -> bool:
        """Update table"""
        return self.update(table_id, data)
    
    def soft_delete_table(self, table_id: str) -> bool:
        """Soft delete table"""
        return self.soft_delete(table_id)
    
    def restore_table(self, table_id: str) -> bool:
        """Restore soft-deleted table"""
        return self.restore(table_id)