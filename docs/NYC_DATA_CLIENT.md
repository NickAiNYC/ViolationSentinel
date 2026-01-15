# NYC Data Client - Production-Grade Resilience

## Overview

The NYC Data Client (`api/nyc_data_client.py`) provides a robust, production-ready interface for accessing NYC Open Data APIs with comprehensive resilience features.

## Features

### 1. **Async HTTP with Connection Pooling**
- Built on `aiohttp` for high-performance async requests
- Connection pool with up to 50 concurrent connections
- DNS caching (300s TTL) for improved performance
- Configurable request timeouts (default: 30 seconds)

### 2. **Circuit Breaker**
- Automatically opens after 5 consecutive failures
- 60-second recovery timeout before retry attempts
- Prevents cascading failures in distributed systems
- Prometheus metrics for monitoring circuit breaker state

### 3. **Rate Limiting**
- Token bucket algorithm for smooth rate limiting
- Default: 1000 requests per 60 seconds
- Configurable limits based on API tier
- Automatic rate limit error handling

### 4. **Multi-Layer Caching**
- **In-Memory LRU Cache**: Fast first-level cache with TTL (default: 300s)
- **Redis Cache** (optional): Distributed second-level cache with TTL (default: 3600s)
- Cache hit rate tracking and statistics
- Automatic cache key generation based on method and parameters

### 5. **Exponential Backoff Retry**
- Uses `tenacity` library for sophisticated retry logic
- 3 retry attempts with exponential backoff (1-10 seconds)
- Jitter to prevent thundering herd
- Retries on transient network errors

### 6. **Automatic Failover**
- Falls back to cached data when API is unavailable
- Graceful degradation under failure conditions
- Prevents total service outage

### 7. **Structured Logging**
- Contextual information in all log messages
- Request duration, record counts, error details
- Compatible with log aggregation systems
- Configurable log levels

### 8. **Prometheus Metrics**
- Request counts by method and status
- Request latency histograms
- Cache hit/miss counters
- Error counts by type
- Circuit breaker state gauge

### 9. **Health Checks**
- Component-level health status
- Cache statistics
- Request statistics
- Ready for Kubernetes liveness/readiness probes

### 10. **Type Safety**
- Comprehensive type hints throughout
- Custom exception hierarchy
- Clear API contracts

## Installation

```bash
pip install aiohttp tenacity redis prometheus-client circuitbreaker cachetools
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
```

## Quick Start

### Basic Usage

```python
import asyncio
from api.nyc_data_client import NYCDataClient

async def main():
    async with NYCDataClient(
        app_token="your_nyc_data_token",  # Optional, improves rate limits
        redis_url="redis://localhost:6379",  # Optional, for distributed caching
    ) as client:
        # Fetch DOB violations
        violations = await client.get_dob_violations("1012650001")
        print(f"Found {len(violations)} DOB violations")
        
        # Fetch HPD violations
        hpd = await client.get_hpd_violations("1012650001")
        print(f"Found {len(hpd)} HPD violations")
        
        # Fetch 311 complaints (last 30 days)
        complaints = await client.get_311_complaints("1012650001", days=30)
        print(f"Found {len(complaints)} 311 complaints")

asyncio.run(main())
```

### Batch Fetching

```python
async def batch_example():
    async with NYCDataClient() as client:
        bbls = ["1012650001", "2012650001", "3012650001"]
        
        # Fetch all data types for multiple properties concurrently
        results = await client.batch_fetch(
            bbls,
            include_dob=True,
            include_hpd=True,
            include_311=True,
            include_permits=False,
        )
        
        for bbl, data in results.items():
            print(f"{bbl}: {len(data['dob_violations'])} DOB, "
                  f"{len(data['hpd_violations'])} HPD")
```

### Health Monitoring

```python
async def health_check():
    async with NYCDataClient() as client:
        health = await client.health_check()
        
        print(f"Status: {health['status']}")
        print(f"Components: {health['components']}")
        print(f"Cache stats: {health['cache_stats']}")
        print(f"Request stats: {health['request_stats']}")
```

## API Methods

### `get_dob_violations(bbl: str, limit: int = 1000, use_cache: bool = True)`
Fetch Department of Buildings violations.

**Parameters:**
- `bbl`: Borough-Block-Lot identifier (10 digits)
- `limit`: Maximum records to return
- `use_cache`: Enable caching

**Returns:** List of violation records

### `get_hpd_violations(bbl: str, limit: int = 1000, use_cache: bool = True)`
Fetch Housing Preservation and Development violations.

**Parameters:**
- `bbl`: Borough-Block-Lot identifier
- `limit`: Maximum records to return
- `use_cache`: Enable caching

**Returns:** List of violation records

### `get_311_complaints(bbl: str, days: int = 30, limit: int = 1000, use_cache: bool = True, as_of_date: Optional[datetime] = None)`
Fetch 311 complaints within a time window.

**Parameters:**
- `bbl`: Borough-Block-Lot identifier
- `days`: Days to look back (from as_of_date)
- `limit`: Maximum records to return
- `use_cache`: Enable caching
- `as_of_date`: Reference date (defaults to now)

**Returns:** List of complaint records

### `get_permits(bbl: str, limit: int = 1000, use_cache: bool = True)`
Fetch building permits.

**Parameters:**
- `bbl`: Borough-Block-Lot identifier
- `limit`: Maximum records to return
- `use_cache`: Enable caching

**Returns:** List of permit records

### `batch_fetch(bbls: List[str], include_dob: bool = True, include_hpd: bool = True, include_311: bool = True, include_permits: bool = True, days_311: int = 30, use_cache: bool = True)`
Batch fetch data for multiple properties concurrently.

**Parameters:**
- `bbls`: List of BBL identifiers
- `include_*`: Flags to enable/disable data types
- `days_311`: Days to look back for 311 complaints
- `use_cache`: Enable caching

**Returns:** Dictionary mapping BBL to data records

### `health_check()`
Get health status of all components.

**Returns:** Health status dictionary

### `get_stats()`
Get client statistics.

**Returns:** Statistics dictionary with request counts, cache hit rates, etc.

## Configuration

### Environment Variables

- `NYC_DATA_APP_TOKEN`: NYC Open Data API token (optional, improves rate limits)
- `REDIS_URL`: Redis connection URL (optional, enables distributed caching)

### Constructor Parameters

```python
NYCDataClient(
    app_token: Optional[str] = None,           # NYC API token
    redis_url: Optional[str] = None,           # Redis connection
    max_connections: int = 50,                 # Connection pool size
    request_timeout: int = 30,                 # Request timeout (seconds)
    memory_cache_size: int = 1000,             # LRU cache size
    memory_cache_ttl: int = 300,               # Memory cache TTL (seconds)
    redis_cache_ttl: int = 3600,               # Redis cache TTL (seconds)
    rate_limit: int = 1000,                    # Requests per period
    rate_limit_period: float = 60.0,           # Rate limit period (seconds)
)
```

## Error Handling

### Exception Hierarchy

```python
NYCDataError                    # Base exception
├── RateLimitError             # Rate limit exceeded
├── CircuitBreakerOpenError    # Circuit breaker is open
└── CacheError                 # Cache operation failed
```

### Example Error Handling

```python
from api.nyc_data_client import (
    NYCDataClient,
    NYCDataError,
    RateLimitError,
    CircuitBreakerOpenError,
)

async def safe_fetch():
    async with NYCDataClient() as client:
        try:
            data = await client.get_dob_violations("1012650001")
        except RateLimitError:
            print("Rate limit exceeded, try again later")
        except CircuitBreakerOpenError:
            print("Service unavailable, falling back to cache")
        except NYCDataError as e:
            print(f"API error: {e}")
```

## Monitoring

### Prometheus Metrics

The client exposes the following metrics:

- `nyc_data_requests_total{method, status}` - Total requests
- `nyc_data_request_duration_seconds{method}` - Request latency
- `nyc_data_cache_hits_total{cache_type}` - Cache hits
- `nyc_data_cache_misses_total{cache_type}` - Cache misses
- `nyc_data_errors_total{error_type}` - Error counts
- `nyc_data_circuit_breaker_state{endpoint}` - Circuit breaker state (0=closed, 1=open)

### Sample Prometheus Queries

```promql
# Request rate by method
rate(nyc_data_requests_total[5m])

# Average latency
rate(nyc_data_request_duration_seconds_sum[5m]) / rate(nyc_data_request_duration_seconds_count[5m])

# Cache hit rate
rate(nyc_data_cache_hits_total[5m]) / (rate(nyc_data_cache_hits_total[5m]) + rate(nyc_data_cache_misses_total[5m]))

# Error rate
rate(nyc_data_errors_total[5m])
```

## Best Practices

### 1. Use Context Manager
Always use the async context manager for automatic cleanup:

```python
async with NYCDataClient() as client:
    # Your code here
    pass
# Resources are automatically cleaned up
```

### 2. Enable Caching
Leave caching enabled unless you need real-time data:

```python
# Good: Uses cache (faster, less load on API)
data = await client.get_dob_violations(bbl, use_cache=True)

# Use only when you need fresh data
data = await client.get_dob_violations(bbl, use_cache=False)
```

### 3. Use Batch Fetching
For multiple properties, use batch_fetch for better performance:

```python
# Good: Concurrent fetching
results = await client.batch_fetch(bbls)

# Avoid: Sequential fetching
for bbl in bbls:
    await client.get_dob_violations(bbl)  # Slow!
```

### 4. Monitor Health
Regularly check health status for production deployments:

```python
# Kubernetes liveness probe endpoint
@app.get("/health")
async def health():
    return await client.health_check()
```

### 5. Handle Errors Gracefully
Always handle potential errors:

```python
try:
    data = await client.get_dob_violations(bbl)
except NYCDataError as e:
    logger.error(f"Failed to fetch violations: {e}")
    # Fallback logic
```

## Performance Tips

1. **Use connection pooling**: The default 50 connections handles most workloads
2. **Enable Redis caching**: Reduces API calls and improves response times
3. **Batch operations**: Use `batch_fetch()` for multiple properties
4. **Adjust cache TTLs**: Longer TTLs = fewer API calls, but less fresh data
5. **Monitor metrics**: Use Prometheus to identify bottlenecks

## Troubleshooting

### High Error Rates
- Check API token validity
- Verify network connectivity
- Review rate limits
- Check circuit breaker status

### Cache Issues
- Verify Redis connection (if used)
- Check cache TTL settings
- Monitor cache hit rates
- Review memory limits

### Performance Issues
- Increase connection pool size
- Adjust rate limits
- Enable Redis caching
- Use batch operations

## Testing

The client includes comprehensive tests:

```bash
# Run all tests
pytest test_nyc_data_client.py -v

# Run specific test class
pytest test_nyc_data_client.py::TestNYCDataClient -v

# Run with coverage
pytest test_nyc_data_client.py --cov=api.nyc_data_client
```

## Example Script

See `example_nyc_data_client.py` for comprehensive usage examples demonstrating:
- Single property data fetch
- Batch fetching
- Caching behavior
- Health checks
- Error handling

## License

MIT License - See LICENSE file for details.

## Support

For issues and questions:
- GitHub Issues: https://github.com/NickAiNYC/ViolationSentinel/issues
- Documentation: This file and inline docstrings
- Examples: See `example_nyc_data_client.py`
