# Infrastructure Module

## Overview

Production-grade infrastructure utilities for ViolationSentinel including structured logging, request tracing, caching, and observability.

## Modules

### 1. Structured Logging (`logging_config.py`)

A comprehensive logging system with:

✅ **JSON-formatted logs** using python-json-logger  
✅ **Multiple log levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL  
✅ **Rich metadata**: timestamp, level, logger_name, function_name, line_number, request_id  
✅ **Contextual logging**: Add request context to all logs in a request  
✅ **Log rotation**: Daily rotation, keep 30 days  
✅ **Separate log files**: app.log, error.log, api.log, model.log  
✅ **Pretty console output** for development  
✅ **JSON output** for production  
✅ **Correlation IDs** for request tracing  
✅ **Performance decorators**: @log_execution_time  
✅ **Exception decorators**: @log_exceptions  

### 2. Production-Ready Caching (`cache.py`)

A comprehensive Redis caching layer with:

✅ **Connection pooling** (max 50 connections)  
✅ **Automatic serialization/deserialization** (JSON or pickle)  
✅ **TTL support** (time-to-live for cache entries)  
✅ **Cache invalidation** (by key, by pattern)  
✅ **Automatic fallback** to in-memory cache if Redis unavailable  
✅ **Async/await support** for non-blocking operations  
✅ **Cache statistics** (hits, misses, hit rate)  
✅ **LRU eviction policy** for memory cache  
✅ **Compression** for large values (>1KB)  
✅ **Batch operations** (mget, mset)  
✅ **@cached decorator** for automatic function result caching  
✅ **Cache warming** for frequently accessed data  
✅ **Health check** method  
✅ **Prometheus metrics** export  

## Installation

Install the required dependencies:

```bash
pip install python-json-logger>=2.0.0 redis>=5.0.0 cachetools>=5.3.0
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Initialize Logging at Application Startup

```python
from infrastructure import setup_logging

# Development environment (pretty console output)
setup_logging(log_level='DEBUG', environment='development')

# Production environment (JSON logs)
setup_logging(log_level='INFO', environment='production')
```

### 2. Get Logger in Your Modules

```python
from infrastructure import get_logger

logger = get_logger(__name__)

logger.info("Application started")
logger.warning("Configuration missing", extra={'config_key': 'API_TOKEN'})
logger.error("Request failed", exc_info=True)
```

### 3. Use Request Context for Tracing

```python
from infrastructure import set_request_context, clear_request_context
import uuid

# At the start of a request
request_id = str(uuid.uuid4())
set_request_context(request_id=request_id, user_id="user123")

logger.info("Processing request")  # Will include request_id and user_id

# At the end of the request
clear_request_context()
```

### 4. Use Decorators for Automatic Logging

```python
from infrastructure import log_execution_time, log_exceptions, get_logger

logger = get_logger(__name__)

@log_execution_time
@log_exceptions
async def fetch_data(property_id: str):
    """Fetch data with automatic logging."""
    # Function execution time and exceptions are logged automatically
    result = await some_api_call(property_id)
    return result
```

### 5. Initialize Cache Manager

```python
from infrastructure import CacheManager

# With Redis
cache = CacheManager(
    redis_url="redis://localhost:6379/0",
    max_connections=50,
    enable_compression=True,
)
await cache.initialize()

# Basic operations
await cache.set("key", {"data": "value"}, ttl=300)
value = await cache.get("key")
await cache.delete("key")

# Batch operations
await cache.mset({"key1": "val1", "key2": "val2"}, ttl=600)
results = await cache.mget(["key1", "key2"])

# Get statistics
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']:.2%}")

await cache.close()
```

### 6. Use @cached Decorator

```python
from infrastructure import CacheManager, cached

cache_manager = CacheManager(redis_url="redis://localhost:6379")
await cache_manager.initialize()

@cached(ttl=600, key_prefix="api")
async def expensive_function(param):
    # Function result is automatically cached
    result = await some_expensive_operation(param)
    return result

# Pass cache manager
result = await expensive_function("value", _cache_manager=cache_manager)
```

## Configuration

### Environment Variables (Logging)

- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default: `INFO`
- `LOG_DIR`: Directory for log files. Default: `./logs`
- `ENVIRONMENT`: Environment name (development, production). Default: `development`

### Example Configuration

```bash
# Development
export LOG_LEVEL=DEBUG
export LOG_DIR=./logs
export ENVIRONMENT=development

# Production
export LOG_LEVEL=INFO
export LOG_DIR=/var/log/violationsentinel
export ENVIRONMENT=production
```

## API Reference

### `setup_logging(log_level, log_dir, environment)`

Set up production-grade logging configuration.

**Parameters:**
- `log_level` (str, optional): Logging level. Defaults to LOG_LEVEL env var or INFO.
- `log_dir` (str, optional): Directory for log files. Defaults to LOG_DIR env var or './logs'.
- `environment` (str, optional): Environment name. Defaults to ENVIRONMENT env var or 'development'.

**Example:**
```python
setup_logging(log_level='INFO', log_dir='/var/log/app', environment='production')
```

### `get_logger(name)`

Get a configured logger instance.

**Parameters:**
- `name` (str): Logger name, typically `__name__` from the calling module.

**Returns:** Configured logger instance.

**Example:**
```python
logger = get_logger(__name__)
logger.info("Processing started")
```

### `set_request_context(request_id, user_id)`

Set contextual information for request tracing.

**Parameters:**
- `request_id` (str, optional): Unique request identifier (correlation ID).
- `user_id` (str, optional): User identifier for the current request.

**Example:**
```python
import uuid
set_request_context(request_id=str(uuid.uuid4()), user_id="user123")
```

### `clear_request_context()`

Clear contextual information for request tracing.

**Example:**
```python
clear_request_context()
```

### `@log_execution_time`

Decorator to log function execution time.

**Parameters:**
- `logger` (Logger, optional): Logger instance to use. Defaults to function's module logger.

**Example:**
```python
@log_execution_time
def process_data():
    # ... processing ...
    pass

@log_execution_time(logger=get_logger(__name__))
async def fetch_data():
    # ... fetching ...
    pass
```

### `@log_exceptions`

Decorator to automatically log exceptions.

**Parameters:**
- `logger` (Logger, optional): Logger instance to use. Defaults to function's module logger.
- `reraise` (bool): Whether to reraise the exception after logging. Default: True.

**Example:**
```python
@log_exceptions
def risky_operation():
    # Exceptions will be logged automatically
    pass

@log_exceptions(reraise=False)
def safe_operation():
    # Exception logged but not reraised
    pass
```

## Log Files

The logging system creates separate log files for different purposes:

### `app.log`
- **Content**: All application logs
- **Level**: Configured log level (default: INFO)
- **Rotation**: Daily, keep 30 days
- **Format**: JSON (production) or plain text (development)

### `error.log`
- **Content**: Only ERROR and CRITICAL logs
- **Level**: ERROR and above
- **Rotation**: Daily, keep 30 days
- **Format**: JSON (production) or plain text (development)

### `api.log`
- **Content**: API-related logs (from loggers named 'api.*')
- **Level**: Configured log level
- **Rotation**: Daily, keep 30 days
- **Format**: JSON (production) or plain text (development)

### `model.log`
- **Content**: Model-related logs (from loggers named 'model.*')
- **Level**: Configured log level
- **Rotation**: Daily, keep 30 days
- **Format**: JSON (production) or plain text (development)

## Log Format

### Development (Pretty Console)

```
2026-01-15 23:00:00 | INFO     | api.nyc_data_client  | nyc_data_client.py:123        [abc-123] | API request successful
```

### Production (JSON)

```json
{
  "timestamp": "2026-01-15T23:00:00.123456Z",
  "level": "INFO",
  "logger_name": "api.nyc_data_client",
  "function_name": "_make_request",
  "line_number": 123,
  "module": "nyc_data_client",
  "request_id": "abc-123",
  "user_id": "user123",
  "message": "API request successful",
  "duration": 0.456,
  "records": 10
}
```

## Integration Examples

### Example 1: Simple Application

```python
from infrastructure import setup_logging, get_logger

# Initialize at startup
setup_logging()

# Get logger
logger = get_logger(__name__)

# Use logger
logger.info("Application started")
logger.warning("Low memory", extra={'memory_mb': 100})
logger.error("Connection failed", exc_info=True)
```

### Example 2: FastAPI Integration

```python
from fastapi import FastAPI, Request
from infrastructure import setup_logging, get_logger, set_request_context, clear_request_context
import uuid

app = FastAPI()

# Initialize logging
setup_logging(environment='production')
logger = get_logger(__name__)

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    # Set request context
    request_id = str(uuid.uuid4())
    set_request_context(request_id=request_id)
    
    logger.info(f"Request started: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        logger.info(f"Request completed: {response.status_code}")
        return response
    finally:
        clear_request_context()

@app.get("/")
async def root():
    logger.info("Processing root request")
    return {"message": "Hello World"}
```

### Example 3: NYC Data Client Integration

```python
from infrastructure import setup_logging, get_logger, log_execution_time, set_request_context
from api.nyc_data_client import NYCDataClient
import uuid

setup_logging()
logger = get_logger(__name__)

@log_execution_time
async def fetch_property_data(bbl: str):
    request_id = str(uuid.uuid4())
    set_request_context(request_id=request_id)
    
    logger.info(f"Fetching data for BBL {bbl}")
    
    async with NYCDataClient() as client:
        violations = await client.get_dob_violations(bbl)
        logger.info(
            "Violations retrieved",
            extra={'bbl': bbl, 'count': len(violations)}
        )
        return violations
```

## Best Practices

### 1. Initialize Once at Startup
Call `setup_logging()` once at application startup, before any other code.

### 2. Use Module Loggers
Always get loggers using `get_logger(__name__)` to maintain proper logger hierarchy.

### 3. Add Contextual Information
Use the `extra` parameter to add structured metadata to logs:

```python
logger.info("User action", extra={'user_id': 'u123', 'action': 'login'})
```

### 4. Use Request Context
Set request context at the beginning of request handling for automatic tracing:

```python
set_request_context(request_id=str(uuid.uuid4()), user_id=user_id)
```

### 5. Use Decorators
Use `@log_execution_time` and `@log_exceptions` decorators for consistent logging:

```python
@log_execution_time
@log_exceptions
async def important_function():
    # ... code ...
    pass
```

### 6. Log at Appropriate Levels
- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages for potentially harmful situations
- **ERROR**: Error messages for serious problems
- **CRITICAL**: Critical messages for very serious errors

### 7. Include Exception Info
When logging exceptions, use `exc_info=True` to include stack traces:

```python
try:
    risky_operation()
except Exception as e:
    logger.error("Operation failed", exc_info=True)
```

## Troubleshooting

### Logs Not Appearing

Check:
1. Log level configuration (may be filtering messages)
2. Log directory permissions (must be writable)
3. Logger name hierarchy (child loggers inherit from parents)

### JSON Formatting Not Working

Ensure `python-json-logger` is installed:
```bash
pip install python-json-logger>=2.0.0
```

### Log Files Growing Too Large

Adjust rotation settings in `setup_logging()` or manually rotate logs:
```bash
find /var/log/app -name "*.log.*" -mtime +30 -delete
```

## Examples

### Logging Examples

See `example_logging_integration.py` for comprehensive usage examples including:
- Request context tracking
- Execution time logging
- Exception logging
- Structured metadata
- Batch processing with logging

### Cache Examples

See `example_cache_usage.py` for comprehensive caching examples including:
- Basic cache operations (get, set, delete, exists)
- Batch operations (mget, mset)
- Automatic compression for large values
- Pattern-based cache clearing
- @cached decorator usage
- Cache warming
- Health checks and statistics
- Redis fallback behavior
- Different serialization modes

## Cache API Reference

### `CacheManager`

Production-ready cache manager class.

**Constructor Parameters:**
- `redis_url` (str, optional): Redis connection URL
- `max_connections` (int): Maximum Redis connections (default: 50)
- `memory_cache_size` (int): In-memory cache size (default: 1000)
- `memory_cache_ttl` (int): In-memory cache TTL in seconds (default: 300)
- `enable_compression` (bool): Enable compression for values >1KB (default: True)
- `serialization` (str): Serialization method, 'json' or 'pickle' (default: 'json')

**Methods:**

#### `async initialize()`
Initialize Redis connection.

#### `async close()`
Close Redis connection and cleanup.

#### `async get(key: str) -> Optional[Any]`
Get value from cache. Returns None if not found.

#### `async set(key: str, value: Any, ttl: Optional[int] = None) -> bool`
Set value in cache with optional TTL (seconds).

#### `async delete(key: str) -> bool`
Delete value from cache.

#### `async exists(key: str) -> bool`
Check if key exists in cache.

#### `async clear(pattern: Optional[str] = None) -> int`
Clear cache entries. If pattern provided, clears matching keys (e.g., 'user:*').

#### `async mget(keys: List[str]) -> Dict[str, Any]`
Get multiple values from cache in one operation.

#### `async mset(mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool`
Set multiple values in cache in one operation.

#### `async health_check() -> Dict[str, Any]`
Perform health check on cache system.

#### `get_stats() -> Dict[str, Any]`
Get cache statistics including hits, misses, and hit rate.

#### `async warm_cache(data_loader: Callable) -> int`
Warm cache with frequently accessed data.

### `@cached` Decorator

Decorator for automatic function result caching.

**Parameters:**
- `ttl` (int): Time-to-live in seconds (default: 300)
- `key_prefix` (str): Prefix for cache keys (default: "")

**Usage:**
```python
@cached(ttl=600, key_prefix="api")
async def expensive_function(param):
    return await fetch_data(param)

# Must pass _cache_manager
result = await expensive_function("value", _cache_manager=cache_manager)
```

## Best Practices

### Caching

1. **Use appropriate TTLs**: Balance freshness with cache hit rates
2. **Enable compression**: For data > 1KB to save memory
3. **Use batch operations**: mget/mset for multiple keys
4. **Monitor hit rates**: Aim for >80% hit rate
5. **Warm cache**: Preload frequently accessed data
6. **Handle Redis failures**: Client automatically falls back to memory
7. **Use key prefixes**: Organize cache keys (e.g., 'user:', 'property:')
8. **Pattern-based clearing**: Clear related keys together

## License

MIT License - See LICENSE file for details.
