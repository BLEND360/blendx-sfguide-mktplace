"""
Simple TTL cache utilities for performance optimization.
"""

import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple


class TTLCache:
    """Simple time-based cache with TTL (Time To Live)."""

    def __init__(self, ttl_seconds: int = 60):
        """
        Initialize TTL cache.

        Args:
            ttl_seconds: Time to live for cache entries in seconds
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value if exists and not expired, None otherwise
        """
        if key not in self._cache:
            return None

        value, timestamp = self._cache[key]
        if time.time() - timestamp > self.ttl_seconds:
            # Expired, remove from cache
            del self._cache[key]
            return None

        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache with current timestamp.

        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = (value, time.time())

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def size(self) -> int:
        """Get number of cached entries."""
        return len(self._cache)


def ttl_cache(ttl_seconds: int = 60):
    """
    Decorator for caching function results with TTL.

    Args:
        ttl_seconds: Time to live for cache entries in seconds

    Returns:
        Decorated function with caching
    """
    cache = TTLCache(ttl_seconds=ttl_seconds)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            # For simplicity, only cache functions with no arguments
            # or simple hashable arguments
            if args or kwargs:
                # Don't cache if function has arguments
                return func(*args, **kwargs)

            cache_key = func.__name__
            cached_value = cache.get(cache_key)

            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            return result

        # Expose cache for manual clearing if needed
        wrapper.cache = cache
        return wrapper

    return decorator
