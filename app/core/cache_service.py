"""
Enhanced Caching Service
Provides intelligent caching with TTL, invalidation, and performance optimization
"""
import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Callable, Union
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import logging

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class CacheEntry:
    """Cache entry with metadata"""
    
    def __init__(self, data: Any, ttl: int = 300):
        self.data = data
        self.created_at = time.time()
        self.ttl = ttl
        self.access_count = 0
        self.last_accessed = time.time()
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return time.time() - self.created_at > self.ttl
    
    @property
    def age(self) -> float:
        """Get age of cache entry in seconds"""
        return time.time() - self.created_at
    
    def access(self) -> Any:
        """Access cache entry and update metadata"""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.data


class InMemoryCache:
    """High-performance in-memory cache with intelligent eviction"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._lock = asyncio.Lock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'sets': 0
        }
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        async with self._lock:
            if key not in self.cache:
                self._stats['misses'] += 1
                return None
            
            entry = self.cache[key]
            if entry.is_expired:
                del self.cache[key]
                self._stats['misses'] += 1
                return None
            
            self._stats['hits'] += 1
            return entry.access()
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        async with self._lock:
            if len(self.cache) >= self.max_size:
                await self._evict_entries()
            
            ttl = ttl or self.default_ttl
            self.cache[key] = CacheEntry(value, ttl)
            self._stats['sets'] += 1
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self.cache.clear()
    
    async def _evict_entries(self) -> None:
        """Evict least recently used entries"""
        if not self.cache:
            return
        
        # Sort by last accessed time and remove oldest 25%
        sorted_entries = sorted(
            self.cache.items(),
            key=lambda x: x[1].last_accessed
        )
        
        evict_count = max(1, len(sorted_entries) // 4)
        for i in range(evict_count):
            key, _ = sorted_entries[i]
            del self.cache[key]
            self._stats['evictions'] += 1
    
    async def cleanup_expired(self) -> int:
        """Remove expired entries"""
        async with self._lock:
            expired_keys = [
                key for key, entry in self.cache.items()
                if entry.is_expired
            ]
            
            for key in expired_keys:
                del self.cache[key]
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hit_rate': hit_rate,
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'evictions': self._stats['evictions'],
            'sets': self._stats['sets']
        }


class CacheService:
    """Enhanced caching service with multiple cache types"""
    
    def __init__(self):
        # Different caches for different data types
        self.user_cache = InMemoryCache(max_size=500, default_ttl=600)  # 10 minutes
        self.venue_cache = InMemoryCache(max_size=200, default_ttl=900)  # 15 minutes
        self.workspace_cache = InMemoryCache(max_size=100, default_ttl=1200)  # 20 minutes
        self.menu_cache = InMemoryCache(max_size=300, default_ttl=300)  # 5 minutes
        self.permission_cache = InMemoryCache(max_size=200, default_ttl=900)  # 15 minutes
        self.query_cache = InMemoryCache(max_size=1000, default_ttl=180)  # 3 minutes
        
        # Start cleanup task
        self._cleanup_task = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(60)  # Run every minute
                    await self.cleanup_expired_entries()
                except Exception as e:
                    logger.error(f"Cache cleanup error: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    async def cleanup_expired_entries(self):
        """Clean up expired entries from all caches"""
        caches = [
            self.user_cache, self.venue_cache, self.workspace_cache,
            self.menu_cache, self.permission_cache, self.query_cache
        ]
        
        total_cleaned = 0
        for cache in caches:
            cleaned = await cache.cleanup_expired()
            total_cleaned += cleaned
        
        if total_cleaned > 0:
            logger.info(f"Cleaned up {total_cleaned} expired cache entries")
    
    def _get_cache_for_type(self, cache_type: str) -> InMemoryCache:
        """Get appropriate cache for data type"""
        cache_map = {
            'user': self.user_cache,
            'venue': self.venue_cache,
            'workspace': self.workspace_cache,
            'menu': self.menu_cache,
            'permission': self.permission_cache,
            'query': self.query_cache
        }
        return cache_map.get(cache_type, self.query_cache)
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_parts = [prefix]
        
        # Add positional arguments
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            else:
                key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
        
        # Add keyword arguments
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            kwargs_str = json.dumps(sorted_kwargs, sort_keys=True)
            key_parts.append(hashlib.md5(kwargs_str.encode()).hexdigest()[:8])
        
        return ':'.join(key_parts)
    
    async def get(self, cache_type: str, key: str) -> Optional[Any]:
        """Get value from cache"""
        cache = self._get_cache_for_type(cache_type)
        return await cache.get(key)
    
    async def set(self, cache_type: str, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        cache = self._get_cache_for_type(cache_type)
        await cache.set(key, value, ttl)
    
    async def delete(self, cache_type: str, key: str) -> bool:
        """Delete key from cache"""
        cache = self._get_cache_for_type(cache_type)
        return await cache.delete(key)
    
    async def invalidate_pattern(self, cache_type: str, pattern: str) -> int:
        """Invalidate cache entries matching pattern"""
        cache = self._get_cache_for_type(cache_type)
        
        async with cache._lock:
            matching_keys = [
                key for key in cache.cache.keys()
                if pattern in key
            ]
            
            for key in matching_keys:
                del cache.cache[key]
            
            return len(matching_keys)
    
    async def get_or_set(self, 
                        cache_type: str, 
                        key: str, 
                        fetch_func: Callable, 
                        ttl: Optional[int] = None) -> Any:
        """Get from cache or fetch and cache"""
        # Try to get from cache first
        cached_value = await self.get(cache_type, key)
        if cached_value is not None:
            return cached_value
        
        # Fetch new value
        try:
            if asyncio.iscoroutinefunction(fetch_func):
                value = await fetch_func()
            else:
                value = fetch_func()
            
            # Cache the value
            await self.set(cache_type, key, value, ttl)
            return value
            
        except Exception as e:
            logger.error(f"Error fetching data for cache key {key}: {e}")
            raise
    
    # Convenience methods for specific data types
    async def get_user(self, user_id: str) -> Optional[Any]:
        """Get user from cache"""
        return await self.get('user', f"user:{user_id}")
    
    async def set_user(self, user_id: str, user_data: Any, ttl: int = 600) -> None:
        """Set user in cache"""
        await self.set('user', f"user:{user_id}", user_data, ttl)
    
    async def invalidate_user(self, user_id: str) -> bool:
        """Invalidate user cache"""
        return await self.delete('user', f"user:{user_id}")
    
    async def get_venue(self, venue_id: str) -> Optional[Any]:
        """Get venue from cache"""
        return await self.get('venue', f"venue:{venue_id}")
    
    async def set_venue(self, venue_id: str, venue_data: Any, ttl: int = 900) -> None:
        """Set venue in cache"""
        await self.set('venue', f"venue:{venue_id}", venue_data, ttl)
    
    async def invalidate_venue(self, venue_id: str) -> bool:
        """Invalidate venue cache"""
        return await self.delete('venue', f"venue:{venue_id}")
    
    async def invalidate_workspace_venues(self, workspace_id: str) -> int:
        """Invalidate all venue caches for a workspace"""
        return await self.invalidate_pattern('venue', f"workspace:{workspace_id}")
    
    async def get_workspace(self, workspace_id: str) -> Optional[Any]:
        """Get workspace from cache"""
        return await self.get('workspace', f"workspace:{workspace_id}")
    
    async def set_workspace(self, workspace_id: str, workspace_data: Any, ttl: int = 1200) -> None:
        """Set workspace in cache"""
        await self.set('workspace', f"workspace:{workspace_id}", workspace_data, ttl)
    
    async def invalidate_workspace(self, workspace_id: str) -> bool:
        """Invalidate workspace cache"""
        return await self.delete('workspace', f"workspace:{workspace_id}")
    
    async def get_user_permissions(self, user_id: str) -> Optional[Any]:
        """Get user permissions from cache"""
        return await self.get('permission', f"permissions:{user_id}")
    
    async def set_user_permissions(self, user_id: str, permissions: Any, ttl: int = 900) -> None:
        """Set user permissions in cache"""
        await self.set('permission', f"permissions:{user_id}", permissions, ttl)
    
    async def invalidate_user_permissions(self, user_id: str) -> bool:
        """Invalidate user permissions cache"""
        return await self.delete('permission', f"permissions:{user_id}")
    
    async def cache_query_result(self, query_key: str, result: Any, ttl: int = 180) -> None:
        """Cache query result"""
        await self.set('query', f"query:{query_key}", result, ttl)
    
    async def get_cached_query(self, query_key: str) -> Optional[Any]:
        """Get cached query result"""
        return await self.get('query', f"query:{query_key}")
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all caches"""
        return {
            'user_cache': self.user_cache.get_stats(),
            'venue_cache': self.venue_cache.get_stats(),
            'workspace_cache': self.workspace_cache.get_stats(),
            'menu_cache': self.menu_cache.get_stats(),
            'permission_cache': self.permission_cache.get_stats(),
            'query_cache': self.query_cache.get_stats()
        }
    
    async def clear_all_caches(self) -> None:
        """Clear all caches"""
        caches = [
            self.user_cache, self.venue_cache, self.workspace_cache,
            self.menu_cache, self.permission_cache, self.query_cache
        ]
        
        for cache in caches:
            await cache.clear()
        
        logger.info("All caches cleared")


# Global cache service instance
cache_service = CacheService()


def cached(cache_type: str = 'query', ttl: int = 300, key_prefix: str = None):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            prefix = key_prefix or func.__name__
            cache_key = cache_service._generate_cache_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = await cache_service.get(cache_type, cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            await cache_service.set(cache_type, cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


def get_cache_service() -> CacheService:
    """Get cache service instance"""
    return cache_service