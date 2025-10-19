"""
Cached Repository Base Class
Provides intelligent caching layer for database operations
"""
from typing import Any, Dict, List, Optional, Union
from abc import ABC, abstractmethod
import asyncio
import hashlib
import json

from app.core.logging_config import get_logger
from app.core.cache_service import get_cache_service, cached

logger = get_logger(__name__)


class CachedRepository(ABC):
    """Base repository class with intelligent caching"""
    
    def __init__(self, collection_name: str, cache_type: str = 'query'):
        self.collection_name = collection_name
        self.cache_type = cache_type
        self.cache_service = get_cache_service()
        
        # Cache TTL configurations (in seconds)
        self.cache_ttl = {
            'get_by_id': 600,      # 10 minutes
            'get_all': 300,        # 5 minutes
            'query': 180,          # 3 minutes
            'search': 120,         # 2 minutes
            'count': 300,          # 5 minutes
        }
    
    def _generate_cache_key(self, operation: str, *args, **kwargs) -> str:
        """Generate cache key for operation"""
        key_parts = [self.collection_name, operation]
        
        # Add arguments to key
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            elif isinstance(arg, (list, tuple)):
                # For filters and queries
                key_parts.append(hashlib.md5(str(sorted(arg)).encode()).hexdigest()[:8])
            else:
                key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
        
        # Add keyword arguments
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            kwargs_str = json.dumps(sorted_kwargs, sort_keys=True, default=str)
            key_parts.append(hashlib.md5(kwargs_str.encode()).hexdigest()[:8])
        
        return ':'.join(key_parts)
    
    async def _get_cached_or_fetch(self, 
                                  cache_key: str, 
                                  fetch_func, 
                                  ttl: int = 300) -> Any:
        """Get from cache or fetch and cache"""
        return await self.cache_service.get_or_set(
            self.cache_type, 
            cache_key, 
            fetch_func, 
            ttl
        )
    
    async def _invalidate_cache_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern"""
        return await self.cache_service.invalidate_pattern(self.cache_type, pattern)
    
    async def _invalidate_item_cache(self, item_id: str) -> None:
        """Invalidate all cache entries for a specific item"""
        patterns = [
            f"{self.collection_name}:get_by_id:{item_id}",
            f"{self.collection_name}:get_all",
            f"{self.collection_name}:query",
            f"{self.collection_name}:search",
            f"{self.collection_name}:count"
        ]
        
        for pattern in patterns:
            await self.cache_service.invalidate_pattern(self.cache_type, pattern)
    
    # Abstract methods that must be implemented by subclasses
    @abstractmethod
    async def _fetch_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Fetch item by ID from database"""
        pass
    
    @abstractmethod
    async def _fetch_all(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch all items from database"""
        pass
    
    @abstractmethod
    async def _fetch_query(self, filters: List[tuple], limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch items by query from database"""
        pass
    
    @abstractmethod
    async def _create_item(self, data: Dict[str, Any]) -> str:
        """Create item in database"""
        pass
    
    @abstractmethod
    async def _update_item(self, item_id: str, data: Dict[str, Any]) -> bool:
        """Update item in database"""
        pass
    
    @abstractmethod
    async def _delete_item(self, item_id: str) -> bool:
        """Delete item from database"""
        pass
    
    # Cached public methods
    async def get_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get item by ID with caching"""
        cache_key = self._generate_cache_key('get_by_id', item_id)
        
        async def fetch():
            return await self._fetch_by_id(item_id)
        
        return await self._get_cached_or_fetch(
            cache_key, 
            fetch, 
            self.cache_ttl['get_by_id']
        )
    
    async def get_all(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all items with caching"""
        cache_key = self._generate_cache_key('get_all', limit or 'no_limit')
        
        async def fetch():
            return await self._fetch_all(limit)
        
        return await self._get_cached_or_fetch(
            cache_key, 
            fetch, 
            self.cache_ttl['get_all']
        )
    
    async def query(self, filters: List[tuple], limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Query items with caching"""
        cache_key = self._generate_cache_key('query', filters, limit or 'no_limit')
        
        async def fetch():
            return await self._fetch_query(filters, limit)
        
        return await self._get_cached_or_fetch(
            cache_key, 
            fetch, 
            self.cache_ttl['query']
        )
    
    async def search_text(self, 
                         search_fields: List[str], 
                         search_term: str,
                         additional_filters: Optional[List[tuple]] = None,
                         limit: int = 50) -> List[Dict[str, Any]]:
        """Search items by text with caching"""
        cache_key = self._generate_cache_key(
            'search', 
            search_fields, 
            search_term, 
            additional_filters or [], 
            limit
        )
        
        async def fetch():
            # Get all items matching additional filters
            if additional_filters:
                items = await self._fetch_query(additional_filters, None)
            else:
                items = await self._fetch_all(None)
            
            # Filter by search term
            search_term_lower = search_term.lower()
            matching_items = []
            
            for item in items:
                for field in search_fields:
                    field_value = item.get(field, '')
                    if isinstance(field_value, str) and search_term_lower in field_value.lower():
                        matching_items.append(item)
                        break
                    elif isinstance(field_value, list):
                        # Handle array fields like cuisine_types
                        for value in field_value:
                            if isinstance(value, str) and search_term_lower in value.lower():
                                matching_items.append(item)
                                break
                        else:
                            continue
                        break
            
            return matching_items[:limit]
        
        return await self._get_cached_or_fetch(
            cache_key, 
            fetch, 
            self.cache_ttl['search']
        )
    
    async def count(self, filters: Optional[List[tuple]] = None) -> int:
        """Count items with caching"""
        cache_key = self._generate_cache_key('count', filters or [])
        
        async def fetch():
            if filters:
                items = await self._fetch_query(filters, None)
            else:
                items = await self._fetch_all(None)
            return len(items)
        
        return await self._get_cached_or_fetch(
            cache_key, 
            fetch, 
            self.cache_ttl['count']
        )
    
    async def create(self, data: Dict[str, Any]) -> str:
        """Create item and invalidate cache"""
        try:
            item_id = await self._create_item(data)
            
            # Invalidate relevant caches
            await self._invalidate_cache_pattern(f"{self.collection_name}:get_all")
            await self._invalidate_cache_pattern(f"{self.collection_name}:query")
            await self._invalidate_cache_pattern(f"{self.collection_name}:search")
            await self._invalidate_cache_pattern(f"{self.collection_name}:count")
            
            logger.info(f"Created {self.collection_name} item: {item_id}")
            return item_id
            
        except Exception as e:
            logger.error(f"Error creating {self.collection_name} item: {e}")
            raise
    
    async def update(self, item_id: str, data: Dict[str, Any]) -> bool:
        """Update item and invalidate cache"""
        try:
            success = await self._update_item(item_id, data)
            
            if success:
                # Invalidate all caches for this item
                await self._invalidate_item_cache(item_id)
                logger.info(f"Updated {self.collection_name} item: {item_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating {self.collection_name} item {item_id}: {e}")
            raise
    
    async def delete(self, item_id: str) -> bool:
        """Delete item and invalidate cache"""
        try:
            success = await self._delete_item(item_id)
            
            if success:
                # Invalidate all caches for this item
                await self._invalidate_item_cache(item_id)
                logger.info(f"Deleted {self.collection_name} item: {item_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting {self.collection_name} item {item_id}: {e}")
            raise
    
    async def bulk_invalidate(self, item_ids: List[str]) -> None:
        """Bulk invalidate cache for multiple items"""
        for item_id in item_ids:
            await self._invalidate_item_cache(item_id)
        
        logger.info(f"Bulk invalidated cache for {len(item_ids)} {self.collection_name} items")
    
    async def refresh_cache(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Refresh cache for specific item"""
        # Invalidate existing cache
        await self._invalidate_item_cache(item_id)
        
        # Fetch fresh data
        return await self.get_by_id(item_id)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for this repository"""
        all_stats = self.cache_service.get_all_stats()
        return all_stats.get(self.cache_type, {})


class WorkspaceCachedRepository(CachedRepository):
    """Repository with workspace-specific caching"""
    
    def __init__(self, collection_name: str):
        super().__init__(collection_name, 'workspace')
    
    async def get_by_workspace(self, workspace_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get items by workspace with caching"""
        cache_key = self._generate_cache_key('get_by_workspace', workspace_id, limit or 'no_limit')
        
        async def fetch():
            return await self._fetch_query([('workspace_id', '==', workspace_id)], limit)
        
        return await self._get_cached_or_fetch(
            cache_key, 
            fetch, 
            self.cache_ttl['query']
        )
    
    async def invalidate_workspace_cache(self, workspace_id: str) -> int:
        """Invalidate all cache entries for a workspace"""
        return await self._invalidate_cache_pattern(f"{self.collection_name}:get_by_workspace:{workspace_id}")


class VenueCachedRepository(CachedRepository):
    """Repository with venue-specific caching"""
    
    def __init__(self, collection_name: str):
        super().__init__(collection_name, 'venue')
    
    async def get_by_venue(self, venue_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get items by venue with caching"""
        cache_key = self._generate_cache_key('get_by_venue', venue_id, limit or 'no_limit')
        
        async def fetch():
            return await self._fetch_query([('venue_id', '==', venue_id)], limit)
        
        return await self._get_cached_or_fetch(
            cache_key, 
            fetch, 
            self.cache_ttl['query']
        )
    
    async def invalidate_venue_cache(self, venue_id: str) -> int:
        """Invalidate all cache entries for a venue"""
        return await self._invalidate_cache_pattern(f"{self.collection_name}:get_by_venue:{venue_id}")


class UserCachedRepository(CachedRepository):
    """Repository with user-specific caching"""
    
    def __init__(self, collection_name: str):
        super().__init__(collection_name, 'user')
    
    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email with caching"""
        cache_key = self._generate_cache_key('get_by_email', email.lower())
        
        async def fetch():
            results = await self._fetch_query([('email', '==', email.lower())], 1)
            return results[0] if results else None
        
        return await self._get_cached_or_fetch(
            cache_key, 
            fetch, 
            self.cache_ttl['get_by_id']
        )
    
    async def invalidate_user_email_cache(self, email: str) -> bool:
        """Invalidate user email cache"""
        cache_key = self._generate_cache_key('get_by_email', email.lower())
        return await self.cache_service.delete(self.cache_type, cache_key)