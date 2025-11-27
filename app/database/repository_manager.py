"""
Repository Manager
Centralized repository management with connection pooling and caching
"""
from typing import Dict, Any, Optional, Type
from functools import lru_cache
import asyncio
from datetime import datetime, timedelta

from app.core.logging import get_logger

# Import new repository architecture
from app.repositories import (
    WorkspaceRepository, UserRepository, VenueRepository,
    RoleRepository, PermissionRepository, MenuItemRepository, MenuCategoryRepository,
    TableRepository, TableAreaRepository, OrderRepository, CustomerRepository,
    TransactionRepository, NotificationRepository, ReviewRepository,
    get_workspace_repository, get_user_repository, get_venue_repository,
    get_role_repository, get_permission_repository, get_menu_item_repository, 
    get_menu_category_repository, get_table_repository, get_table_area_repository, 
    get_order_repository, get_customer_repository, get_transaction_repository, 
    get_notification_repository, get_review_repository
)

logger = get_logger(__name__)


class RepositoryManager:
    """Centralized repository manager with caching and optimization"""
    
    def __init__(self):
        self._repositories: Dict[str, Any] = {}
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl: Dict[str, datetime] = {}
        self._cache_duration = timedelta(minutes=5)  # 5-minute cache
        
    def _get_cache_key(self, repo_name: str, method: str, *args) -> str:
        """Generate cache key for repository operations"""
        return f"{repo_name}:{method}:{':'.join(str(arg) for arg in args)}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid"""
        if cache_key not in self._cache_ttl:
            return False
        return datetime.utcnow() < self._cache_ttl[cache_key]
    
    def _set_cache(self, cache_key: str, data: Any) -> None:
        """Set cache entry with TTL"""
        self._cache[cache_key] = data
        self._cache_ttl[cache_key] = datetime.utcnow() + self._cache_duration
    
    def _get_cache(self, cache_key: str) -> Optional[Any]:
        """Get cache entry if valid"""
        if self._is_cache_valid(cache_key):
            return self._cache.get(cache_key)
        else:
            # Clean up expired cache
            if cache_key in self._cache:
                del self._cache[cache_key]
            if cache_key in self._cache_ttl:
                del self._cache_ttl[cache_key]
            return None
    
    @lru_cache(maxsize=20)
    def get_repository(self, repo_type: str) -> Any:
        """Get repository instance with caching"""
        if repo_type not in self._repositories:
            repo_classes = {
                'workspace': WorkspaceRepository,
                'user': UserRepository,
                'venue': VenueRepository,
                'role': RoleRepository,
                'permission': PermissionRepository,
                'menu_item': MenuItemRepository,
                'menu_category': MenuCategoryRepository,
                'table': TableRepository,
                'table_area': TableAreaRepository,
                'order': OrderRepository,
                'customer': CustomerRepository,
                'transaction': TransactionRepository,
                'notification': NotificationRepository,
                'review': ReviewRepository,
            }
            
            if repo_type in repo_classes:
                self._repositories[repo_type] = repo_classes[repo_type]()
            else:
                raise ValueError(f"Unknown repository type: {repo_type}")
        
        return self._repositories[repo_type]
    
    async def cached_get_by_id(self, repo_type: str, item_id: str) -> Optional[Dict[str, Any]]:
        """Get item by ID with caching"""
        cache_key = self._get_cache_key(repo_type, "get_by_id", item_id)
        
        # Check cache first
        cached_result = self._get_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Get from repository
        repo = self.get_repository(repo_type)
        result = await repo.get_by_id(item_id)
        
        # Cache the result
        if result:
            self._set_cache(cache_key, result)
        
        return result
    
    async def cached_get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email with caching"""
        cache_key = self._get_cache_key("user", "get_by_email", email)
        
        cached_result = self._get_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        repo = self.get_repository('user')
        result = await repo.get_by_email(email)
        
        if result:
            self._set_cache(cache_key, result)
        
        return result
    
    async def invalidate_cache(self, repo_type: str, item_id: Optional[str] = None) -> None:
        """Invalidate cache entries for a repository or specific item"""
        if item_id:
            # Invalidate specific item cache
            cache_keys_to_remove = [
                key for key in self._cache.keys() 
                if key.startswith(f"{repo_type}:") and item_id in key
            ]
        else:
            # Invalidate all cache for repository type
            cache_keys_to_remove = [
                key for key in self._cache.keys() 
                if key.startswith(f"{repo_type}:")
            ]
        
        for key in cache_keys_to_remove:
            if key in self._cache:
                del self._cache[key]
            if key in self._cache_ttl:
                del self._cache_ttl[key]
    
    async def batch_get_by_ids(self, repo_type: str, item_ids: list) -> Dict[str, Any]:
        """Batch get items by IDs with caching"""
        results = {}
        uncached_ids = []
        
        # Check cache for each ID
        for item_id in item_ids:
            cache_key = self._get_cache_key(repo_type, "get_by_id", item_id)
            cached_result = self._get_cache(cache_key)
            
            if cached_result is not None:
                results[item_id] = cached_result
            else:
                uncached_ids.append(item_id)
        
        # Fetch uncached items
        if uncached_ids:
            repo = self.get_repository(repo_type)
            
            # Use asyncio.gather for concurrent fetching
            tasks = [repo.get_by_id(item_id) for item_id in uncached_ids]
            uncached_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and update cache
            for item_id, result in zip(uncached_ids, uncached_results):
                if not isinstance(result, Exception) and result:
                    results[item_id] = result
                    cache_key = self._get_cache_key(repo_type, "get_by_id", item_id)
                    self._set_cache(cache_key, result)
        
        return results
    
    def clear_all_cache(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
        self._cache_ttl.clear()
        logger.info("All repository cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_entries = len(self._cache)
        valid_entries = sum(1 for key in self._cache.keys() if self._is_cache_valid(key))
        
        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "expired_entries": total_entries - valid_entries,
            "cache_hit_ratio": valid_entries / max(total_entries, 1),
            "repositories_loaded": len(self._repositories)
        }


# Global repository manager instance
repo_manager = RepositoryManager()


# Convenience functions for backward compatibility
def get_workspace_repo() -> WorkspaceRepository:
    """Get workspace repository instance"""
    return get_workspace_repository()

def get_user_repo() -> UserRepository:
    """Get user repository instance"""
    return get_user_repository()

def get_venue_repo() -> VenueRepository:
    """Get venue repository instance"""
    return get_venue_repository()

def get_role_repo() -> RoleRepository:
    """Get role repository instance"""
    return get_role_repository()

def get_permission_repo() -> PermissionRepository:
    """Get permission repository instance"""
    return get_permission_repository()

def get_menu_item_repo() -> MenuItemRepository:
    """Get menu item repository instance"""
    return get_menu_item_repository()

def get_menu_category_repo() -> MenuCategoryRepository:
    """Get menu category repository instance"""
    return get_menu_category_repository()

def get_table_repo() -> TableRepository:
    """Get table repository instance"""
    return get_table_repository()

def get_table_area_repo() -> TableAreaRepository:
    """Get table area repository instance"""
    return get_table_area_repository()

def get_order_repo() -> OrderRepository:
    """Get order repository instance"""
    return get_order_repository()

def get_customer_repo() -> CustomerRepository:
    """Get customer repository instance"""
    return get_customer_repository()

def get_transaction_repo() -> TransactionRepository:
    """Get transaction repository instance"""
    return get_transaction_repository()

def get_notification_repo() -> NotificationRepository:
    """Get notification repository instance"""
    return get_notification_repository()

def get_review_repo() -> ReviewRepository:
    """Get review repository instance"""
    return get_review_repository()

def get_coupon_repo():
    """Get coupon repository instance"""
    from app.repositories.coupon import CouponRepository
    return CouponRepository()

def get_repository_manager() -> RepositoryManager:
    """Get repository manager instance"""
    return repo_manager