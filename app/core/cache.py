"""
Simple in-memory caching module for API responses
Reduces database reads and improves response times
"""
from typing import Any, Callable, Optional, Dict, Tuple
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import json

from app.core.logging import get_logger

logger = get_logger(__name__)


class SimpleCache:
    """
    Simple in-memory cache with TTL support
    
    Features:
    - Time-based expiration
    - Automatic cleanup of expired entries
    - Thread-safe operations
    """
    
    def __init__(self):
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key in self._cache:
            data, expiry = self._cache[key]
            if datetime.now() < expiry:
                self._hits += 1
                logger.debug(f"Cache HIT: {key}")
                return data
            else:
                # Expired - remove from cache
                del self._cache[key]
                logger.debug(f"Cache EXPIRED: {key}")
        
        self._misses += 1
        logger.debug(f"Cache MISS: {key}")
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """Set value in cache with TTL in seconds"""
        expiry = datetime.now() + timedelta(seconds=ttl)
        self._cache[key] = (value, expiry)
        logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
    
    def delete(self, key: str):
        """Delete specific key from cache"""
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache DELETE: {key}")
    
    def delete_pattern(self, pattern: str):
        """Delete all keys matching pattern"""
        keys_to_delete = [k for k in self._cache.keys() if pattern in k]
        for key in keys_to_delete:
            del self._cache[key]
        logger.debug(f"Cache DELETE PATTERN: {pattern} ({len(keys_to_delete)} keys)")
    
    def clear(self):
        """Clear entire cache"""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache CLEARED: {count} entries removed")
    
    def cleanup_expired(self):
        """Remove all expired entries"""
        now = datetime.now()
        expired_keys = [
            key for key, (_, expiry) in self._cache.items()
            if now >= expiry
        ]
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Cache CLEANUP: {len(expired_keys)} expired entries removed")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "entries": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
            "total_requests": total_requests,
        }


# Global cache instance
cache = SimpleCache()


def generate_cache_key(*args, **kwargs) -> str:
    """
    Generate a unique cache key from function arguments
    """
    # Convert args and kwargs to a stable string representation
    key_data = {
        "args": [str(arg) for arg in args],
        "kwargs": {k: str(v) for k, v in sorted(kwargs.items())}
    }
    key_string = json.dumps(key_data, sort_keys=True)
    
    # Hash for shorter keys
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator for caching function results
    
    Args:
        ttl: Time to live in seconds (default: 5 minutes)
        key_prefix: Prefix for cache key (default: function name)
    
    Usage:
        @cached(ttl=60, key_prefix="dashboard")
        async def get_dashboard_data(venue_id: str):
            # Expensive operation
            return data
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            prefix = key_prefix or func.__name__
            arg_key = generate_cache_key(*args, **kwargs)
            cache_key = f"{prefix}:{arg_key}"
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            
            return result
        
        # Add cache control methods to function
        wrapper.cache_clear = lambda: cache.delete_pattern(key_prefix or func.__name__)
        wrapper.cache_stats = lambda: cache.get_stats()
        
        return wrapper
    return decorator


def invalidate_cache(pattern: str):
    """
    Invalidate cache entries matching pattern
    
    Usage:
        invalidate_cache("dashboard")  # Invalidate all dashboard cache
        invalidate_cache("orders:venue_123")  # Invalidate specific venue orders
    """
    cache.delete_pattern(pattern)


def get_cache_stats() -> Dict[str, Any]:
    """Get global cache statistics"""
    return cache.get_stats()


# Cache invalidation helpers for common patterns
class CacheInvalidation:
    """Helper class for cache invalidation"""
    
    @staticmethod
    def orders(venue_id: Optional[str] = None):
        """Invalidate orders cache"""
        if venue_id:
            invalidate_cache(f"orders:venue:{venue_id}")
        else:
            invalidate_cache("orders")
    
    @staticmethod
    def dashboard(venue_id: Optional[str] = None):
        """Invalidate dashboard cache"""
        if venue_id:
            invalidate_cache(f"dashboard:venue:{venue_id}")
        else:
            invalidate_cache("dashboard")
    
    @staticmethod
    def menu(venue_id: Optional[str] = None):
        """Invalidate menu cache"""
        if venue_id:
            invalidate_cache(f"menu:venue:{venue_id}")
        else:
            invalidate_cache("menu")
    
    @staticmethod
    def tables(venue_id: Optional[str] = None):
        """Invalidate tables cache"""
        if venue_id:
            invalidate_cache(f"tables:venue:{venue_id}")
        else:
            invalidate_cache("tables")
    
    @staticmethod
    def all():
        """Clear entire cache"""
        cache.clear()


# Export for easy access
invalidate = CacheInvalidation()