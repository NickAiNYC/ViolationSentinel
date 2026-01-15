"""
Production-ready Redis caching layer with automatic failover.

This module provides a comprehensive caching system with Redis as the primary
cache and automatic fallback to in-memory cache if Redis is unavailable.
"""

import asyncio
import functools
import gzip
import hashlib
import json
import pickle
import time
from typing import Any, Optional, Dict, List, Callable, Union
from datetime import timedelta
import logging

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

from cachetools import TTLCache

try:
    from prometheus_client import Counter, Histogram, Gauge
    PROMETHEUS_AVAILABLE = True
except ImportError:
    # Create dummy metrics if prometheus not available
    PROMETHEUS_AVAILABLE = False
    class DummyMetric:
        def labels(self, **kwargs):
            return self
        def inc(self, *args, **kwargs):
            pass
        def observe(self, *args, **kwargs):
            pass
        def set(self, *args, **kwargs):
            pass
    Counter = Histogram = Gauge = lambda *args, **kwargs: DummyMetric()


# Configure logging
logger = logging.getLogger(__name__)


# Prometheus Metrics
CACHE_OPERATIONS = Counter(
    'cache_operations_total',
    'Total number of cache operations',
    ['operation', 'status', 'cache_type']
)
CACHE_LATENCY = Histogram(
    'cache_operation_duration_seconds',
    'Cache operation latency',
    ['operation', 'cache_type']
)
CACHE_SIZE = Gauge(
    'cache_entries_count',
    'Number of entries in cache',
    ['cache_type']
)
CACHE_MEMORY_BYTES = Gauge(
    'cache_memory_bytes',
    'Memory used by cache',
    ['cache_type']
)


class CacheError(Exception):
    """Base exception for cache operations."""
    pass


class CacheConnectionError(CacheError):
    """Raised when cache connection fails."""
    pass


class CacheSerializationError(CacheError):
    """Raised when serialization/deserialization fails."""
    pass


class CacheManager:
    """
    Production-ready cache manager with Redis primary and in-memory fallback.
    
    Features:
    - Automatic connection pooling
    - JSON/Pickle serialization
    - TTL support
    - Pattern-based invalidation
    - Automatic fallback to in-memory cache
    - Compression for large values
    - Batch operations
    - Cache statistics and metrics
    """
    
    # Compression threshold (1KB)
    COMPRESSION_THRESHOLD = 1024
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_connections: int = 50,
        memory_cache_size: int = 1000,
        memory_cache_ttl: int = 300,
        enable_compression: bool = True,
        serialization: str = 'json',
    ):
        """
        Initialize cache manager.
        
        Args:
            redis_url: Redis connection URL (e.g., 'redis://localhost:6379/0')
            max_connections: Maximum Redis connections in pool
            memory_cache_size: In-memory cache size (number of entries)
            memory_cache_ttl: In-memory cache TTL in seconds
            enable_compression: Enable compression for large values
            serialization: Serialization method ('json' or 'pickle')
        """
        self.redis_url = redis_url
        self.max_connections = max_connections
        self.enable_compression = enable_compression
        self.serialization = serialization.lower()
        
        # Initialize Redis client (may be None if unavailable)
        self._redis: Optional[Any] = None  # redis.Redis if available
        self._redis_available = False
        
        # Initialize in-memory fallback cache
        self._memory_cache = TTLCache(maxsize=memory_cache_size, ttl=memory_cache_ttl)
        
        # Cache statistics
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0,
            'redis_hits': 0,
            'memory_hits': 0,
            'fallbacks': 0,
        }
        
        logger.info(
            "CacheManager initialized",
            extra={
                'redis_url': bool(redis_url),
                'memory_cache_size': memory_cache_size,
                'serialization': serialization,
            }
        )
    
    async def initialize(self):
        """Initialize Redis connection."""
        if not self.redis_url:
            logger.warning("No Redis URL provided, using memory cache only")
            return
        
        if not REDIS_AVAILABLE:
            logger.warning("Redis package not installed, using memory cache only")
            return
        
        try:
            # Create Redis connection pool
            self._redis = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,  # We handle encoding ourselves
                max_connections=self.max_connections,
            )
            
            # Test connection
            await self._redis.ping()
            self._redis_available = True
            logger.info("Redis connection established")
        
        except Exception as e:
            logger.warning(
                f"Failed to connect to Redis: {e}. Using memory cache only.",
                exc_info=True
            )
            self._redis = None
            self._redis_available = False
    
    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis_available = False
            logger.info("Redis connection closed")
    
    def _serialize(self, value: Any) -> bytes:
        """
        Serialize value to bytes.
        
        Args:
            value: Value to serialize
        
        Returns:
            Serialized bytes
        """
        try:
            if self.serialization == 'json':
                data = json.dumps(value).encode('utf-8')
            else:  # pickle
                data = pickle.dumps(value)
            
            # Compress if larger than threshold
            if self.enable_compression and len(data) > self.COMPRESSION_THRESHOLD:
                data = b'GZIP:' + gzip.compress(data)
            
            return data
        
        except Exception as e:
            raise CacheSerializationError(f"Serialization failed: {e}")
    
    def _deserialize(self, data: bytes) -> Any:
        """
        Deserialize bytes to value.
        
        Args:
            data: Serialized bytes
        
        Returns:
            Deserialized value
        """
        try:
            # Decompress if compressed
            if data.startswith(b'GZIP:'):
                data = gzip.decompress(data[5:])
            
            if self.serialization == 'json':
                return json.loads(data.decode('utf-8'))
            else:  # pickle
                return pickle.loads(data)
        
        except Exception as e:
            raise CacheSerializationError(f"Deserialization failed: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if not found
        """
        start_time = time.time()
        
        try:
            # Try Redis first if available
            if self._redis_available:
                try:
                    data = await self._redis.get(key)
                    duration = time.time() - start_time
                    CACHE_LATENCY.labels(operation='get', cache_type='redis').observe(duration)
                    
                    if data:
                        value = self._deserialize(data)
                        self._stats['hits'] += 1
                        self._stats['redis_hits'] += 1
                        CACHE_OPERATIONS.labels(
                            operation='get',
                            status='hit',
                            cache_type='redis'
                        ).inc()
                        logger.debug(f"Cache hit (Redis): {key}")
                        return value
                
                except Exception as e:
                    logger.warning(f"Redis get failed for key {key}: {e}")
                    self._stats['errors'] += 1
                    self._stats['fallbacks'] += 1
                    # Fall through to memory cache
            
            # Try memory cache
            if key in self._memory_cache:
                value = self._memory_cache[key]
                duration = time.time() - start_time
                CACHE_LATENCY.labels(operation='get', cache_type='memory').observe(duration)
                self._stats['hits'] += 1
                self._stats['memory_hits'] += 1
                CACHE_OPERATIONS.labels(
                    operation='get',
                    status='hit',
                    cache_type='memory'
                ).inc()
                logger.debug(f"Cache hit (memory): {key}")
                return value
            
            # Cache miss
            self._stats['misses'] += 1
            CACHE_OPERATIONS.labels(operation='get', status='miss', cache_type='all').inc()
            logger.debug(f"Cache miss: {key}")
            return None
        
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}", exc_info=True)
            self._stats['errors'] += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (optional)
        
        Returns:
            True if successful, False otherwise
        """
        start_time = time.time()
        success = False
        
        try:
            # Set in Redis if available
            if self._redis_available:
                try:
                    data = self._serialize(value)
                    if ttl:
                        await self._redis.setex(key, ttl, data)
                    else:
                        await self._redis.set(key, data)
                    
                    duration = time.time() - start_time
                    CACHE_LATENCY.labels(operation='set', cache_type='redis').observe(duration)
                    CACHE_OPERATIONS.labels(
                        operation='set',
                        status='success',
                        cache_type='redis'
                    ).inc()
                    success = True
                    logger.debug(f"Cache set (Redis): {key}, TTL: {ttl}")
                
                except Exception as e:
                    logger.warning(f"Redis set failed for key {key}: {e}")
                    self._stats['errors'] += 1
                    self._stats['fallbacks'] += 1
            
            # Always set in memory cache as well
            self._memory_cache[key] = value
            duration = time.time() - start_time
            CACHE_LATENCY.labels(operation='set', cache_type='memory').observe(duration)
            CACHE_OPERATIONS.labels(
                operation='set',
                status='success',
                cache_type='memory'
            ).inc()
            
            self._stats['sets'] += 1
            logger.debug(f"Cache set (memory): {key}")
            return True
        
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}", exc_info=True)
            self._stats['errors'] += 1
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if successful, False otherwise
        """
        success = False
        
        try:
            # Delete from Redis if available
            if self._redis_available:
                try:
                    await self._redis.delete(key)
                    CACHE_OPERATIONS.labels(
                        operation='delete',
                        status='success',
                        cache_type='redis'
                    ).inc()
                    success = True
                    logger.debug(f"Cache delete (Redis): {key}")
                
                except Exception as e:
                    logger.warning(f"Redis delete failed for key {key}: {e}")
                    self._stats['errors'] += 1
            
            # Delete from memory cache
            if key in self._memory_cache:
                del self._memory_cache[key]
                CACHE_OPERATIONS.labels(
                    operation='delete',
                    status='success',
                    cache_type='memory'
                ).inc()
                logger.debug(f"Cache delete (memory): {key}")
            
            self._stats['deletes'] += 1
            return True
        
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}", exc_info=True)
            self._stats['errors'] += 1
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if key exists, False otherwise
        """
        try:
            # Check Redis first if available
            if self._redis_available:
                try:
                    exists = await self._redis.exists(key)
                    if exists:
                        return True
                except Exception as e:
                    logger.warning(f"Redis exists check failed for key {key}: {e}")
            
            # Check memory cache
            return key in self._memory_cache
        
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}", exc_info=True)
            return False
    
    async def clear(self, pattern: Optional[str] = None) -> int:
        """
        Clear cache entries.
        
        Args:
            pattern: Key pattern to match (e.g., 'user:*'). If None, clears all.
        
        Returns:
            Number of keys deleted
        """
        count = 0
        
        try:
            # Clear Redis if available
            if self._redis_available:
                try:
                    if pattern:
                        # Delete by pattern
                        cursor = 0
                        while True:
                            cursor, keys = await self._redis.scan(
                                cursor=cursor,
                                match=pattern,
                                count=100
                            )
                            if keys:
                                deleted = await self._redis.delete(*keys)
                                count += deleted
                            if cursor == 0:
                                break
                    else:
                        # Clear all
                        await self._redis.flushdb()
                        count = -1  # Unknown count
                    
                    logger.info(f"Cache cleared (Redis): pattern={pattern}, count={count}")
                
                except Exception as e:
                    logger.warning(f"Redis clear failed: {e}")
                    self._stats['errors'] += 1
            
            # Clear memory cache
            if pattern:
                # Clear by pattern in memory cache
                import fnmatch
                keys_to_delete = [
                    k for k in list(self._memory_cache.keys())
                    if fnmatch.fnmatch(k, pattern)
                ]
                for key in keys_to_delete:
                    del self._memory_cache[key]
                    count += 1
            else:
                # Clear all from memory
                memory_count = len(self._memory_cache)
                self._memory_cache.clear()
                if count == -1:
                    count = memory_count
                else:
                    count += memory_count
            
            logger.info(f"Cache cleared (memory): pattern={pattern}")
            return count
        
        except Exception as e:
            logger.error(f"Cache clear error: {e}", exc_info=True)
            self._stats['errors'] += 1
            return 0
    
    async def mget(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple values from cache.
        
        Args:
            keys: List of cache keys
        
        Returns:
            Dictionary mapping keys to values (missing keys are omitted)
        """
        results = {}
        
        try:
            # Try Redis batch get if available
            if self._redis_available:
                try:
                    values = await self._redis.mget(keys)
                    for key, data in zip(keys, values):
                        if data:
                            try:
                                results[key] = self._deserialize(data)
                                self._stats['redis_hits'] += 1
                            except Exception as e:
                                logger.warning(f"Deserialization failed for key {key}: {e}")
                    
                    CACHE_OPERATIONS.labels(
                        operation='mget',
                        status='success',
                        cache_type='redis'
                    ).inc()
                    logger.debug(f"Cache mget (Redis): {len(results)}/{len(keys)} hits")
                
                except Exception as e:
                    logger.warning(f"Redis mget failed: {e}")
                    self._stats['errors'] += 1
                    self._stats['fallbacks'] += 1
            
            # Fill in missing keys from memory cache
            for key in keys:
                if key not in results and key in self._memory_cache:
                    results[key] = self._memory_cache[key]
                    self._stats['memory_hits'] += 1
            
            self._stats['hits'] += len(results)
            self._stats['misses'] += len(keys) - len(results)
            
            return results
        
        except Exception as e:
            logger.error(f"Cache mget error: {e}", exc_info=True)
            self._stats['errors'] += 1
            return {}
    
    async def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Set multiple values in cache.
        
        Args:
            mapping: Dictionary mapping keys to values
            ttl: Time-to-live in seconds (optional, applied to all keys)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Set in Redis if available
            if self._redis_available:
                try:
                    # Serialize all values
                    serialized = {
                        key: self._serialize(value)
                        for key, value in mapping.items()
                    }
                    
                    # Use pipeline for efficiency
                    async with self._redis.pipeline() as pipe:
                        for key, data in serialized.items():
                            if ttl:
                                pipe.setex(key, ttl, data)
                            else:
                                pipe.set(key, data)
                        await pipe.execute()
                    
                    CACHE_OPERATIONS.labels(
                        operation='mset',
                        status='success',
                        cache_type='redis'
                    ).inc()
                    logger.debug(f"Cache mset (Redis): {len(mapping)} keys, TTL: {ttl}")
                
                except Exception as e:
                    logger.warning(f"Redis mset failed: {e}")
                    self._stats['errors'] += 1
                    self._stats['fallbacks'] += 1
            
            # Set in memory cache
            for key, value in mapping.items():
                self._memory_cache[key] = value
            
            CACHE_OPERATIONS.labels(
                operation='mset',
                status='success',
                cache_type='memory'
            ).inc()
            
            self._stats['sets'] += len(mapping)
            logger.debug(f"Cache mset (memory): {len(mapping)} keys")
            return True
        
        except Exception as e:
            logger.error(f"Cache mset error: {e}", exc_info=True)
            self._stats['errors'] += 1
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on cache system.
        
        Returns:
            Dictionary with health status
        """
        health = {
            'status': 'healthy',
            'redis_available': self._redis_available,
            'memory_cache_size': len(self._memory_cache),
            'memory_cache_maxsize': self._memory_cache.maxsize,
        }
        
        # Test Redis connection
        if self._redis:
            try:
                await self._redis.ping()
                health['redis_status'] = 'connected'
            except Exception as e:
                health['redis_status'] = 'disconnected'
                health['redis_error'] = str(e)
                health['status'] = 'degraded'
        else:
            health['redis_status'] = 'not_configured'
        
        return health
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = (
            self._stats['hits'] / total_requests
            if total_requests > 0
            else 0.0
        )
        
        # Update Prometheus gauges
        CACHE_SIZE.labels(cache_type='memory').set(len(self._memory_cache))
        
        return {
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'sets': self._stats['sets'],
            'deletes': self._stats['deletes'],
            'errors': self._stats['errors'],
            'hit_rate': hit_rate,
            'redis_hits': self._stats['redis_hits'],
            'memory_hits': self._stats['memory_hits'],
            'fallbacks': self._stats['fallbacks'],
            'memory_cache_size': len(self._memory_cache),
            'redis_available': self._redis_available,
        }
    
    async def warm_cache(self, data_loader: Callable[[], List[tuple]]) -> int:
        """
        Warm cache with frequently accessed data.
        
        Args:
            data_loader: Async function that returns list of (key, value, ttl) tuples
        
        Returns:
            Number of entries loaded
        """
        try:
            logger.info("Starting cache warming")
            entries = await data_loader()
            
            count = 0
            for entry in entries:
                key, value = entry[0], entry[1]
                ttl = entry[2] if len(entry) > 2 else None
                await self.set(key, value, ttl=ttl)
                count += 1
            
            logger.info(f"Cache warming completed: {count} entries loaded")
            return count
        
        except Exception as e:
            logger.error(f"Cache warming failed: {e}", exc_info=True)
            return 0
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator for automatic function result caching.
    
    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache keys
    
    Example:
        >>> cache_manager = CacheManager(redis_url="redis://localhost")
        >>> await cache_manager.initialize()
        >>> 
        >>> @cached(ttl=600, key_prefix="user")
        >>> async def get_user(user_id: int):
        >>>     # Expensive operation
        >>>     return fetch_user_from_db(user_id)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get cache manager from kwargs or use global instance
            cache_manager = kwargs.pop('_cache_manager', None)
            if not cache_manager:
                # Try to get from function's module
                import sys
                module = sys.modules[func.__module__]
                cache_manager = getattr(module, 'cache_manager', None)
            
            if not cache_manager:
                # No cache manager available, call function directly
                logger.warning(f"No cache manager for {func.__name__}, calling directly")
                return await func(*args, **kwargs)
            
            # Generate cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            cache_key = ":".join(key_parts)
            
            # Hash long keys
            if len(cache_key) > 200:
                cache_key = f"{key_prefix}:{func.__name__}:" + hashlib.md5(
                    cache_key.encode()
                ).hexdigest()
            
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}: {cache_key}")
                return cached_result
            
            # Call function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl=ttl)
            logger.debug(f"Cached result for {func.__name__}: {cache_key}")
            
            return result
        
        return wrapper
    
    return decorator


# Example usage
if __name__ == "__main__":
    async def main():
        # Initialize cache manager
        cache_manager = CacheManager(
            redis_url="redis://localhost:6379/0",
            memory_cache_size=1000,
            enable_compression=True,
        )
        
        await cache_manager.initialize()
        
        try:
            # Basic operations
            await cache_manager.set("user:123", {"name": "John", "age": 30}, ttl=300)
            user = await cache_manager.get("user:123")
            print(f"User: {user}")
            
            # Batch operations
            await cache_manager.mset({
                "user:124": {"name": "Jane", "age": 25},
                "user:125": {"name": "Bob", "age": 35},
            }, ttl=300)
            
            users = await cache_manager.mget(["user:123", "user:124", "user:125"])
            print(f"Users: {len(users)}")
            
            # Statistics
            stats = cache_manager.get_stats()
            print(f"Cache stats: {stats}")
            
            # Health check
            health = await cache_manager.health_check()
            print(f"Health: {health}")
        
        finally:
            await cache_manager.close()
    
    asyncio.run(main())
