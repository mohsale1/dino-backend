"""
Menu Repository
Data access layer for menu categories and items
"""
from typing import List, Dict, Any, Optional

from app.repositories.base import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class MenuCategoryRepository(BaseRepository):
    """Repository for menu category operations"""
    
    def __init__(self):
        super().__init__("menu_categories")
    
    async def get_by_venue(self, venue_id: str, active_only: bool = False) -> List[Dict[str, Any]]:
        """Get categories by venue"""
        filters = [('venue_id', '==', venue_id)]
        if active_only:
            filters.append(('is_active', '==', True))
        return await self.query(filters)
    
    async def get_by_name(self, venue_id: str, name: str) -> Optional[Dict[str, Any]]:
        """Get category by name within a venue"""
        results = await self.query([
            ('venue_id', '==', venue_id),
            ('name', '==', name)
        ])
        return results[0] if results else None


class MenuItemRepository(BaseRepository):
    """Repository for menu item operations"""
    
    def __init__(self):
        super().__init__("menu_items")
    
    async def get_by_venue(self, venue_id: str, available_only: bool = False) -> List[Dict[str, Any]]:
        """Get items by venue"""
        filters = [('venue_id', '==', venue_id)]
        if available_only:
            filters.append(('is_available', '==', True))
        return await self.query(filters)
    
    async def get_by_category(self, category_id: str, available_only: bool = False) -> List[Dict[str, Any]]:
        """Get items by category"""
        filters = [('category_id', '==', category_id)]
        if available_only:
            filters.append(('is_available', '==', True))
        return await self.query(filters)
    
    async def get_vegetarian_items(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get vegetarian items"""
        return await self.query([
            ('venue_id', '==', venue_id),
            ('is_vegetarian', '==', True),
            ('is_available', '==', True)
        ])
    
    async def search_by_name(self, venue_id: str, name: str) -> List[Dict[str, Any]]:
        """Search items by name"""
        all_items = await self.get_by_venue(venue_id)
        name_lower = name.lower()
        return [
            item for item in all_items
            if name_lower in item.get('name', '').lower()
        ]
    
    async def update_rating(self, item_id: str, rating: float) -> bool:
        """Update menu item rating"""
        try:
            item = await self.get_by_id(item_id)
            if not item:
                return False
            
            current_total = item.get('rating_total', 0.0)
            current_count = item.get('rating_count', 0)
            
            new_total = current_total + rating
            new_count = current_count + 1
            new_average = new_total / new_count if new_count > 0 else 0.0
            
            await self.update(item_id, {
                'rating_total': new_total,
                'rating_count': new_count,
                'average_rating': new_average
            })
            
            return True
        except Exception as e:
            logger.error(f"Error updating menu item rating: {e}")
            raise
    
    async def update_availability(self, item_id: str, is_available: bool) -> bool:
        """Update item availability"""
        try:
            await self.update(item_id, {'is_available': is_available})
            return True
        except Exception as e:
            logger.error(f"Error updating item availability: {e}")
            raise


# Singleton instances
_category_repo = None
_item_repo = None

def get_menu_category_repository() -> MenuCategoryRepository:
    """Get menu category repository singleton"""
    global _category_repo
    if _category_repo is None:
        _category_repo = MenuCategoryRepository()
    return _category_repo

def get_menu_item_repository() -> MenuItemRepository:
    """Get menu item repository singleton"""
    global _item_repo
    if _item_repo is None:
        _item_repo = MenuItemRepository()
    return _item_repo