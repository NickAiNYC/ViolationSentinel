# Infrastructure Module

## Overview

Production-grade infrastructure utilities for ViolationSentinel including structured logging, request tracing, and observability.

## Features

### Structured Logging (`logging_config.py`)

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

## Installation

Install the required dependency:

```bash
pip install python-json-logger>=2.0.0
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

## Configuration

### Environment Variables

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

See `example_logging_integration.py` for comprehensive usage examples including:
- Request context tracking
- Execution time logging
- Exception logging
- Structured metadata
- Batch processing with logging

## License

MIT License - See LICENSE file for details.
