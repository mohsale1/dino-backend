from typing import Optional, List, Dict, Any, Tuple
from src.base.BaseRepository import BaseRepository

class BaseService:
    """Base service with common business logic"""
    
    def __init__(self, repository: BaseRepository):
        self.repository = repository
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new entity"""
        return self.repository.create(data)
    
    def get_by_id(self, entity_id: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """Get entity by ID (excludes soft-deleted by default)"""
        return self.repository.get_by_id(entity_id, include_deleted)
    
    def get_all(
        self, 
        filters: Optional[Dict[str, Any]] = None, 
        limit: Optional[int] = None,
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """Get all entities (excludes soft-deleted by default)"""
        return self.repository.get_all(filters, limit, include_deleted)
    
    def get_paginated(
        self,
        page: int = 1,
        page_size: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        include_deleted: bool = False,
        order_by: Optional[str] = None,
        order_direction: str = "asc"
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Get paginated entities (excludes soft-deleted by default)
        Returns: (items, total_count, total_pages)
        """
        return self.repository.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            include_deleted=include_deleted,
            order_by=order_by,
            order_direction=order_direction
        )
    
    def update(self, entity_id: str, data: Dict[str, Any]) -> bool:
        """Update entity"""
        return self.repository.update(entity_id, data)
    
    def delete(self, entity_id: str) -> bool:
        """Hard delete entity (NOT RECOMMENDED - use soft_delete instead)"""
        return self.repository.delete(entity_id)
    
    def soft_delete(self, entity_id: str) -> bool:
        """Soft delete entity (RECOMMENDED)"""
        return self.repository.soft_delete(entity_id)
    
    def restore(self, entity_id: str) -> bool:
        """Restore a soft-deleted entity"""
        return self.repository.restore(entity_id)
    
    def exists(self, field: str, value: Any, include_deleted: bool = False) -> bool:
        """Check if entity exists (excludes soft-deleted by default)"""
        return self.repository.exists(field, value, include_deleted)
    
    def count(self, filters: Optional[Dict[str, Any]] = None, include_deleted: bool = False) -> int:
        """Count entities (excludes soft-deleted by default)"""
        return self.repository.count(filters, include_deleted)
