"""
Example: Using the production-ready cache system.

This example demonstrates all features of the CacheManager including
Redis caching, fallback to memory cache, batch operations, and the
@cached decorator.
"""

import asyncio
import time
from infrastructure import CacheManager, cached, setup_logging, get_logger

# Setup logging
setup_logging(log_level='INFO', environment='development')
logger = get_logger(__name__)

# Global cache manager instance
cache_manager = None


async def example_basic_operations():
    """Demonstrate basic cache operations."""
    logger.info("=" * 70)
    logger.info("Example 1: Basic Cache Operations")
    logger.info("=" * 70)
    
    async with CacheManager(
        redis_url=None,  # Use memory-only for this example
        memory_cache_size=1000,
    ) as cache:
        # Set a value
        await cache.set("user:123", {"name": "John Doe", "age": 30}, ttl=300)
        logger.info("Set user:123")
        
        # Get a value
        user = await cache.get("user:123")
        logger.info(f"Retrieved user:123: {user}")
        
        # Check existence
        exists = await cache.exists("user:123")
        logger.info(f"user:123 exists: {exists}")
        
        # Delete a value
        await cache.delete("user:123")
        logger.info("Deleted user:123")
        
        # Try to get deleted value
        user = await cache.get("user:123")
        logger.info(f"user:123 after delete: {user}")


async def example_batch_operations():
    """Demonstrate batch cache operations."""
    logger.info("\n" + "=" * 70)
    logger.info("Example 2: Batch Operations")
    logger.info("=" * 70)
    
    async with CacheManager() as cache:
        # Set multiple values at once
        users = {
            "user:1": {"name": "Alice", "age": 25},
            "user:2": {"name": "Bob", "age": 30},
            "user:3": {"name": "Charlie", "age": 35},
        }
        await cache.mset(users, ttl=600)
        logger.info(f"Set {len(users)} users in batch")
        
        # Get multiple values at once
        keys = ["user:1", "user:2", "user:3", "user:999"]
        results = await cache.mget(keys)
        logger.info(f"Retrieved {len(results)}/{len(keys)} users")
        
        for key, value in results.items():
            logger.info(f"  {key}: {value['name']}")


async def example_compression():
    """Demonstrate automatic compression for large values."""
    logger.info("\n" + "=" * 70)
    logger.info("Example 3: Compression for Large Values")
    logger.info("=" * 70)
    
    async with CacheManager(enable_compression=True) as cache:
        # Create a large value (> 1KB)
        large_data = {
            "violations": [
                {
                    "id": i,
                    "type": f"Violation {i}",
                    "description": "Long description " * 20,
                    "date": f"2024-01-{i:02d}",
                }
                for i in range(100)
            ]
        }
        
        # Set large value (will be compressed automatically)
        await cache.set("property:violations", large_data, ttl=300)
        logger.info("Set large violations data (automatically compressed)")
        
        # Get large value (will be decompressed automatically)
        retrieved = await cache.get("property:violations")
        logger.info(f"Retrieved {len(retrieved['violations'])} violations")


async def example_pattern_clearing():
    """Demonstrate pattern-based cache clearing."""
    logger.info("\n" + "=" * 70)
    logger.info("Example 4: Pattern-Based Cache Clearing")
    logger.info("=" * 70)
    
    async with CacheManager() as cache:
        # Set multiple values with different prefixes
        await cache.mset({
            "user:1": {"name": "Alice"},
            "user:2": {"name": "Bob"},
            "property:1": {"address": "123 Main St"},
            "property:2": {"address": "456 Oak Ave"},
        })
        logger.info("Set multiple cache entries")
        
        # Clear only user entries
        cleared = await cache.clear(pattern="user:*")
        logger.info(f"Cleared {cleared} user entries")
        
        # Verify user entries are gone
        user1 = await cache.get("user:1")
        prop1 = await cache.get("property:1")
        logger.info(f"user:1 after clear: {user1}")
        logger.info(f"property:1 after clear: {prop1}")


async def example_decorator():
    """Demonstrate the @cached decorator."""
    logger.info("\n" + "=" * 70)
    logger.info("Example 5: @cached Decorator")
    logger.info("=" * 70)
    
    # Initialize global cache manager
    global cache_manager
    cache_manager = CacheManager()
    await cache_manager.initialize()
    
    @cached(ttl=300, key_prefix="api")
    async def fetch_violations(bbl: str):
        """Simulate expensive API call."""
        logger.info(f"  Fetching violations for {bbl} (expensive operation)...")
        await asyncio.sleep(1)  # Simulate API delay
        return {
            "bbl": bbl,
            "violations": [
                {"type": "DOB", "date": "2024-01-01"},
                {"type": "HPD", "date": "2024-01-15"},
            ]
        }
    
    # First call - will execute function
    start = time.time()
    result1 = await fetch_violations("1012650001", _cache_manager=cache_manager)
    duration1 = time.time() - start
    logger.info(f"First call duration: {duration1:.3f}s")
    logger.info(f"Result: {len(result1['violations'])} violations")
    
    # Second call - will use cache
    start = time.time()
    result2 = await fetch_violations("1012650001", _cache_manager=cache_manager)
    duration2 = time.time() - start
    logger.info(f"Second call duration: {duration2:.3f}s (from cache)")
    logger.info(f"Speed improvement: {duration1/duration2:.1f}x faster")
    
    await cache_manager.close()


async def example_cache_warming():
    """Demonstrate cache warming."""
    logger.info("\n" + "=" * 70)
    logger.info("Example 6: Cache Warming")
    logger.info("=" * 70)
    
    async with CacheManager() as cache:
        # Define function to load frequently accessed data
        async def load_popular_properties():
            """Simulate loading popular properties from database."""
            logger.info("  Loading popular properties...")
            return [
                ("property:popular:1", {"address": "123 Main St", "views": 1000}, 3600),
                ("property:popular:2", {"address": "456 Oak Ave", "views": 950}, 3600),
                ("property:popular:3", {"address": "789 Pine Rd", "views": 900}, 3600),
            ]
        
        # Warm the cache
        count = await cache.warm_cache(load_popular_properties)
        logger.info(f"Cache warmed with {count} popular properties")
        
        # Verify data is cached
        prop = await cache.get("property:popular:1")
        logger.info(f"Retrieved from warmed cache: {prop['address']}")


async def example_health_and_stats():
    """Demonstrate health check and statistics."""
    logger.info("\n" + "=" * 70)
    logger.info("Example 7: Health Check and Statistics")
    logger.info("=" * 70)
    
    async with CacheManager() as cache:
        # Perform some operations
        await cache.set("test:1", "value1")
        await cache.get("test:1")  # Hit
        await cache.get("test:2")  # Miss
        await cache.get("test:1")  # Hit
        
        # Get statistics
        stats = cache.get_stats()
        logger.info("Cache Statistics:")
        logger.info(f"  Hits: {stats['hits']}")
        logger.info(f"  Misses: {stats['misses']}")
        logger.info(f"  Hit Rate: {stats['hit_rate']:.2%}")
        logger.info(f"  Memory Cache Size: {stats['memory_cache_size']}")
        logger.info(f"  Redis Available: {stats['redis_available']}")
        
        # Perform health check
        health = await cache.health_check()
        logger.info("\nCache Health:")
        logger.info(f"  Status: {health['status']}")
        logger.info(f"  Redis Status: {health['redis_status']}")
        logger.info(f"  Memory Cache: {health['memory_cache_size']}/{health['memory_cache_maxsize']}")


async def example_redis_fallback():
    """Demonstrate automatic fallback to memory cache."""
    logger.info("\n" + "=" * 70)
    logger.info("Example 8: Redis Fallback")
    logger.info("=" * 70)
    
    # Create cache manager with invalid Redis URL
    async with CacheManager(redis_url="redis://invalid-host:6379") as cache:
        logger.info("Created cache with invalid Redis URL")
        
        # Operations will automatically fall back to memory cache
        await cache.set("test:fallback", {"status": "working"})
        result = await cache.get("test:fallback")
        
        logger.info(f"Fallback successful: {result}")
        logger.info("Cache operations continue working despite Redis failure")
        
        # Check health
        health = await cache.health_check()
        logger.info(f"Health status: {health['status']} (degraded is expected)")


async def example_serialization_modes():
    """Demonstrate different serialization modes."""
    logger.info("\n" + "=" * 70)
    logger.info("Example 9: Serialization Modes")
    logger.info("=" * 70)
    
    # JSON serialization (default)
    async with CacheManager(serialization='json') as cache:
        data = {"numbers": [1, 2, 3], "text": "Hello"}
        await cache.set("json:test", data)
        result = await cache.get("json:test")
        logger.info(f"JSON serialization: {result}")
    
    # Pickle serialization (supports more Python types)
    async with CacheManager(serialization='pickle') as cache:
        # Pickle can serialize custom objects
        data = {"numbers": {1, 2, 3}, "text": "Hello"}  # Set (not JSON-serializable)
        await cache.set("pickle:test", data)
        result = await cache.get("pickle:test")
        logger.info(f"Pickle serialization: {result}")


async def main():
    """Run all examples."""
    logger.info("\n" + "=" * 70)
    logger.info("CACHE SYSTEM EXAMPLES")
    logger.info("=" * 70)
    
    # Run all examples
    await example_basic_operations()
    await example_batch_operations()
    await example_compression()
    await example_pattern_clearing()
    await example_decorator()
    await example_cache_warming()
    await example_health_and_stats()
    await example_redis_fallback()
    await example_serialization_modes()
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ All examples completed successfully!")
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
